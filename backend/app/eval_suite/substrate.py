"""Harness-only weakening of the mechanisms that have no production switch.

The four gates are unloaded by a setting the production code reads
(:mod:`app.eval_monitor`). Four further mechanisms cannot be unloaded that way,
deliberately: a partial unique index in the schema, the in-transaction supersede
that retires the prior writeback head, a re-read of the active head at delivery
time, and a compare-and-set on action status under a row lock. A deployment has
no way to turn those off, which is the point of putting them there — and it is
also why the ablation could not speak about them, leaving the A3 rows zero in
every configuration including the naive one.

This module ablates them a different way. Instead of adding a production switch
we would then have to argue is safe, the harness weakens the substrate itself: it
drops the index in the evaluation database, and it substitutes the naive
implementation of each code-level mechanism — an outbox that appends a new head
without retiring the old one, a claim that re-reads without a lock. Production
code is unchanged and imports nothing from here.

What the resulting rows answer is therefore a different question from the gate
ablation. Not "was the gate loaded", but "would a plausible naive implementation
of this step have let the harm through".

The head mechanisms are layered, so they are weakened as a ladder rather than one
at a time, and the reason is worth stating because it is a result in itself.
Dropping only the index changes nothing: the supersede already retired the prior
head, so no second row is ever active. Weakening only the supersede changes
nothing either: the index rejects the second insert. Only with both gone do two
active heads coexist. The delivery-time re-read sits under both of those and can
only be reached once they are gone, which is why the arm that ablates it also
ablates them.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import text

from app.db import models as orm
from app.eval_suite.configs import MonitorConfig
from app.eval_suite.world import EvalWorld
from app.models.action import Action
from app.models.enums import (
    ActionCategory,
    ActionExecutionPhase,
    ActionStatus,
    WritebackReadiness,
)

ACTIVE_HEAD_INDEX = "uq_disposition_outbox_event_status_active_head"
ACTIVE_HEAD_COLUMNS = "event_id, closure_cycle, intent_kind, logical_slot"
ACTIVE_HEAD_WHERE = "superseded_by_disposition_id IS NULL AND intent_kind = 'event_status_update'"


async def set_active_head_index(world: EvalWorld, *, present: bool) -> None:
    """Create or drop the partial unique index on active terminal heads.

    Dropping it is the only faithful way to ask what the index is worth: the
    supersede logic in ``enqueue_command`` and the assertion at delivery are
    application code, and both stay in place here.
    """
    if present:
        statement = (
            f"CREATE UNIQUE INDEX IF NOT EXISTS {ACTIVE_HEAD_INDEX} "
            f"ON disposition_outbox ({ACTIVE_HEAD_COLUMNS}) WHERE {ACTIVE_HEAD_WHERE}"
        )
    else:
        statement = f"DROP INDEX IF EXISTS {ACTIVE_HEAD_INDEX}"
    async with world.session_factory() as session:
        async with session.begin():
            await session.execute(text(statement))


async def repair_duplicate_active_heads(world: EvalWorld) -> int:
    """Retire all but the newest active head in each group, and say how many.

    An arm that ran without the index leaves rows the index would have refused,
    and the index cannot be created again while they are there. Repairing them is
    harness bookkeeping between arms, not part of any measurement — every case has
    already been scored by the time this runs.
    """
    statement = text(
        f"""
        WITH ranked AS (
            SELECT outbox_id, disposition_id, {ACTIVE_HEAD_COLUMNS},
                   FIRST_VALUE(disposition_id) OVER w AS winner_id,
                   ROW_NUMBER() OVER w AS position
            FROM disposition_outbox
            WHERE {ACTIVE_HEAD_WHERE}
            WINDOW w AS (
                PARTITION BY {ACTIVE_HEAD_COLUMNS}
                ORDER BY created_at DESC, outbox_id DESC
            )
        )
        UPDATE disposition_outbox AS target
        SET superseded_by_disposition_id = ranked.winner_id
        FROM ranked
        WHERE target.outbox_id = ranked.outbox_id AND ranked.position > 1
        """
    )
    async with world.session_factory() as session:
        async with session.begin():
            result = await session.execute(statement)
    return int(cast(Any, result).rowcount or 0)


async def active_head_index_present(world: EvalWorld) -> bool:
    """Whether the index exists right now, so a run can record what it ran with."""
    async with world.session_factory() as session:
        found = await session.scalar(
            text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
            {"name": ACTIVE_HEAD_INDEX},
        )
    return found is not None


def _naive_claim(world: EvalWorld) -> Callable[[str], Awaitable[Action]]:
    """A claim that re-reads without a lock and assumes the row is claimable.

    This is the production ``_claim_action`` with two lines removed: the
    ``FOR UPDATE`` on the row read, and the rejection when the row is no longer
    ``APPROVED``. Everything else — the approval binding recheck, the phase and
    category rules, the writeback readiness check, the source-object
    precondition — is left alone, so the arm ablates single-claim execution and
    not four other things at once. The status transition is still validated
    against the pair the production code hard-codes (``APPROVED`` to
    ``EXECUTING``), which is exactly the assumption a naive implementation makes
    and the reason it is wrong.
    """
    service = cast(Any, world.execution)

    async def claim(action_id: str) -> Action:
        from app.core.errors import EventNotFoundError, ValidationError
        from app.models.action import TERMINAL_DISPOSITION_TOOL
        from app.models.workflow import validate_action_status_transition
        from app.services.action_execution_service import _action_from_row
        from app.services.playbook_approval_binding import validate_approval_binding

        async with service._session_factory() as session:
            async with session.begin():
                row = await session.get(orm.Action, action_id)
                if row is None:
                    raise EventNotFoundError(
                        f"action not found: {action_id}",
                        details={"action_id": action_id},
                    )
                action = _action_from_row(row)
                approval_detail = await service._latest_approval_detail(session, action.action_id)
                validate_approval_binding(action, approval_detail)
                # The window a lock would have closed. Yielding here makes the
                # interleaving deterministic instead of hoping for it.
                await asyncio.sleep(0)
                if action.execution_phase is ActionExecutionPhase.POST_VERIFY:
                    raise ValidationError(
                        "POST_VERIFY actions must remain APPROVED until ISSUE-059A",
                        details={"action_id": action_id},
                    )
                if action.tool_name == TERMINAL_DISPOSITION_TOOL:
                    raise ValidationError(
                        "POST_VERIFY deferred actions are not executed by execute_plan",
                        details={"action_id": action_id},
                    )
                if action.execution_phase is not ActionExecutionPhase.IMMEDIATE:
                    raise ValidationError(
                        "only IMMEDIATE actions are claimable in execute_plan",
                        details={"action_id": action_id},
                    )
                if action.superseded_by_revision is not None:
                    raise ValidationError(
                        "superseded action cannot be claimed",
                        details={"action_id": action_id},
                    )
                if action.action_category not in {
                    ActionCategory.RESPONSE,
                    ActionCategory.ROLLBACK,
                }:
                    raise ValidationError(
                        "only response/rollback actions are executable",
                        details={"action_id": action_id},
                    )
                if action.writeback_applicable and (
                    action.writeback_readiness is not WritebackReadiness.READY
                    or action.disposition_source_ref is None
                ):
                    raise ValidationError(
                        "action writeback readiness blocks execution",
                        details={"action_id": action_id},
                    )
                await service._validate_claim_preconditions(session, action)
                validate_action_status_transition(
                    action.action_category,
                    ActionStatus.APPROVED,
                    ActionStatus.EXECUTING,
                )
                row.status = ActionStatus.EXECUTING.value
                row.updated_at = datetime.now(UTC)
                return _action_from_row(row)

    return claim


def _naive_supersede() -> Callable[..., None]:
    """An outbox that appends a new head and leaves the old one alone.

    The production version writes the lineage pointer *and* moves the prior head
    out of the delivery queue. A naive one treats enqueue as an append: the new
    head is current because it is newest, and nothing says so in the row. That is
    the shape this codebase itself had before the invariant was made explicit.
    """

    def _finalize(*_args: Any, **_kwargs: Any) -> None:
        return None

    return _finalize


@asynccontextmanager
async def substrate_context(world: EvalWorld, config: MonitorConfig) -> AsyncIterator[None]:
    """Apply this configuration's substrate weakening, then put it all back.

    Restoration matters: one world serves every case in an arm, and a dropped
    index that leaked into the next arm would silently corrupt the whole table.
    """
    sync = cast(Any, world.sync)
    execution = cast(Any, world.execution)
    original_assert = sync._assert_active_head_for_delivery
    original_supersede = sync._finalize_superseded_head
    original_claim = execution._claim_action

    if not config.head_index:
        await set_active_head_index(world, present=False)
    if not config.head_supersede:
        sync._finalize_superseded_head = _naive_supersede()
    if not config.head_assertion:

        async def _always_active(*_args: Any, **_kwargs: Any) -> bool:
            return True

        sync._assert_active_head_for_delivery = _always_active
    if not config.claim_cas:
        execution._claim_action = _naive_claim(world)
    try:
        yield
    finally:
        execution._claim_action = original_claim
        sync._assert_active_head_for_delivery = original_assert
        sync._finalize_superseded_head = original_supersede
        if not config.head_index:
            await repair_duplicate_active_heads(world)
            await set_active_head_index(world, present=True)


__all__ = [
    "ACTIVE_HEAD_INDEX",
    "active_head_index_present",
    "repair_duplicate_active_heads",
    "set_active_head_index",
    "substrate_context",
]
