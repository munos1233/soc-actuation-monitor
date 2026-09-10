"""Real multi-process contention on one approved action and one writeback head.

Every A3 row in the matrix is contention the harness constructs inside a single
process: two dispatch attempts in sequence, two enqueues in sequence. That is
enough to show whether a mechanism refuses the second attempt, and it is not
enough to show that the mechanism is the reason nothing bad happens under
concurrency, because a sequential harness never produces the interleaving the
mechanism exists for.

This module produces it. Several OS processes, each with its own event loop, its
own database connections and its own service instances, race on the same row:
``dispatch`` has them all call ``execute_action`` on one approved action,
``deliver`` has them all run the outbox worker over the same queue. The workers
synchronise on a wall-clock instant rather than a barrier object, because a
barrier would have to be shared and the point is that they share nothing but the
database.

Evidence is read from the database afterwards rather than from an in-process
recorder, for the same reason: with several processes there is no shared vendor
stub to count against. What a duplicate external effect looks like in the schema
is more than one delivered ``entity_action_submit`` for one action, or more than
one active terminal head for one closure cycle.

The weakened arms need the substrate patches in every process, and they must not
be undone when a child exits, or the child would repair the very rows the parent
is about to count. So children apply the weakening without restoring it and the
parent, which owns the index for the whole probe, puts it back.
"""

from __future__ import annotations

import asyncio
import multiprocessing as mp
import os
import time
from dataclasses import dataclass, field
from typing import Any, cast

from sqlalchemy import select

from app.db import models as orm
from app.eval_suite.configs import (
    CONFIGS,
    FULL,
    FULL_MINUS_CLAIM_CAS,
    FULL_MINUS_HEAD_UNIQUENESS,
    MonitorConfig,
    VendorColumn,
    harness_context,
)
from app.eval_suite.substrate import (
    repair_duplicate_active_heads,
    set_active_head_index,
)
from app.eval_suite.world import EvalWorld, EventWorld, eval_world
from app.models.enums import DispositionIntentKind, OutboxDeliveryStatus

MODE_DISPATCH = "dispatch"
MODE_DELIVER = "deliver"
MODE_HEAD = "head"
MODE_REKEY = "rekey"
MODES = (MODE_DISPATCH, MODE_DELIVER, MODE_HEAD, MODE_REKEY)

DEFAULT_WORKERS = 4
DEFAULT_ROUNDS = 5
STARTUP_GRACE_SECONDS = 12.0
"""How long a child is given to migrate, connect and reach the start instant.

Generous on purpose: a child that arrives late has not raced, and a probe that
silently degrades into a sequential run is worse than one that says it failed.
"""

PROBE_CONFIGS: tuple[MonitorConfig, ...] = (
    FULL,
    FULL_MINUS_CLAIM_CAS,
    FULL_MINUS_HEAD_UNIQUENESS,
)


@dataclass
class RoundResult:
    """What one race produced.

    ``entity_effects`` and ``terminal_effects`` are distinct external effects
    counted at the vendor boundary across all processes, one per idempotency key,
    which is the same accounting the single-process suite uses. The remaining
    fields are read from the database.
    """

    config: str
    mode: str
    round_index: int
    workers: int
    entity_effects: int
    terminal_effects: int
    submit_calls: int
    active_terminal_heads: int
    event_id: str = ""
    outbox: dict[str, int] = field(default_factory=dict)
    worker_outcomes: list[str] = field(default_factory=list)
    late_workers: int = 0

    @property
    def duplicated(self) -> bool:
        return (
            self.entity_effects > 1 or self.terminal_effects > 1 or self.active_terminal_heads > 1
        )

    def as_row(self) -> dict[str, Any]:
        return {
            "config": self.config,
            "mode": self.mode,
            "round": self.round_index,
            "workers": self.workers,
            "entity_effects": self.entity_effects,
            "terminal_effects": self.terminal_effects,
            "submit_calls": self.submit_calls,
            "active_terminal_heads": self.active_terminal_heads,
            "event_id": self.event_id,
            "outbox": dict(self.outbox),
            "duplicated": self.duplicated,
            "late_workers": self.late_workers,
            "worker_outcomes": list(self.worker_outcomes),
        }


# --------------------------------------------------------------------------- #
# Cross-process tally at the vendor boundary.
#
# Each process has its own vendor stub, so ``received`` cannot answer how many
# distinct effects the race produced. Redis can: a set of idempotency keys gives
# distinct effects and a counter gives raw calls, so a delivery retry of one key
# stays distinguishable from a second dispatch.
#
# Keyed by the dispatched action rather than by the round, because the outbox
# worker drains the whole queue: a racing worker will happily deliver a row left
# over from an earlier round, and a per-round key would file that delivery under
# the wrong event and report a duplicate that never happened.
# --------------------------------------------------------------------------- #


def _tally_prefix(action_id: str) -> str:
    return f"evaltally:action:{action_id}"


def _install_tally(world: EvalWorld) -> None:
    client = world.redis.get_client()

    async def sink(payload: dict[str, Any]) -> None:
        prefix = _tally_prefix(str(payload.get("action_id") or "unknown"))
        intent = str(payload.get("intent_kind") or "unknown")
        key = str(payload.get("idempotency_key") or "")
        await client.sadd(f"{prefix}:{intent}", key)
        await client.incr(f"{prefix}:calls")

    world.vendor.tally_sink = sink


async def _read_tally(world: EvalWorld, action_ids: list[str]) -> tuple[int, int, int]:
    """Distinct entity effects, distinct terminal effects, and raw submit calls.

    Summed over every action of this event, including the terminal actions the
    racing workers created for themselves.
    """
    client = world.redis.get_client()
    entity = terminal = calls = 0
    for action_id in action_ids:
        prefix = _tally_prefix(action_id)
        entity += int(
            await client.scard(f"{prefix}:{DispositionIntentKind.ENTITY_ACTION_SUBMIT.value}") or 0
        )
        terminal += int(
            await client.scard(f"{prefix}:{DispositionIntentKind.EVENT_STATUS_UPDATE.value}") or 0
        )
        calls += int(await client.get(f"{prefix}:calls") or 0)
    return entity, terminal, calls


# --------------------------------------------------------------------------- #
# Substrate weakening without restoration, for use inside a child process.
# --------------------------------------------------------------------------- #


def _apply_substrate_patches(world: EvalWorld, config: MonitorConfig) -> None:
    """The in-process half of the weakening, applied and left applied.

    Deliberately not :func:`substrate_context`: that restores on exit, and a child
    exiting mid-probe would rebuild the index over rows the parent has not counted
    yet. The DDL half is the parent's job for the same reason.
    """
    from app.eval_suite.substrate import _naive_claim, _naive_supersede

    sync = cast(Any, world.sync)
    execution = cast(Any, world.execution)
    if not config.head_supersede:
        sync._finalize_superseded_head = _naive_supersede()
    if not config.head_assertion:

        async def _always_active(*_args: Any, **_kwargs: Any) -> bool:
            return True

        sync._assert_active_head_for_delivery = _always_active
    if not config.claim_cas:
        execution._claim_action = _naive_claim(world)


# --------------------------------------------------------------------------- #
# Child process.
# --------------------------------------------------------------------------- #


async def _rekey(world: EvalWorld, action_id: str, key: str) -> None:
    async with world.session_factory() as session:
        async with session.begin():
            row = await session.get(orm.Action, action_id, with_for_update=True)
            if row is not None:
                row.idempotency_key = key


def _event_from_job(job: dict[str, Any]) -> EventWorld:
    """Rebuild the seeded event's identifiers in the child.

    Only identifiers cross the process boundary; every service the child talks to
    is its own.
    """
    return EventWorld(
        event_id=str(job["event_id"]),
        source_record_id=str(job["source_record_id"]),
        connector_id=str(job["connector_id"]),
        object_id=str(job["object_id"]),
        plan_revision=int(job["plan_revision"]),
        entity_action_id=job.get("action_id"),
        terminal_action_id=job.get("terminal_action_id"),
    )


async def _await_start(start_at: float) -> bool:
    """Sleep until the shared instant. False if we got there after it passed."""
    delay = start_at - time.time()
    if delay <= 0:
        return False
    await asyncio.sleep(delay)
    return True


async def _child_async(job: dict[str, Any]) -> str:
    from app.eval_suite.chain import enqueue_terminal_head, second_terminal_action

    config = CONFIGS[str(job["config"])]
    column = VendorColumn(str(job["column"]))
    with harness_context(config, column):
        async with eval_world(column) as world:
            _apply_substrate_patches(world, config)
            _install_tally(world)
            event = _event_from_job(job)
            # Everything each worker needs that is not shared state is built
            # before the start instant, so the race is over the shared row and not
            # over who finished their setup first.
            own_terminal = (
                await second_terminal_action(world, event) if job["mode"] == MODE_HEAD else None
            )
            on_time = await _await_start(float(job["start_at"]))
            prefix = "" if on_time else "late:"
            try:
                if job["mode"] in (MODE_DISPATCH, MODE_REKEY):
                    if job["mode"] == MODE_REKEY:
                        # The dedupe input the approval fingerprint does not cover,
                        # rewritten per worker. Without this every racer carries the
                        # same key and the vendor collapses the duplicates, which
                        # would report the vendor's dedup as our mediation.
                        await _rekey(
                            world,
                            str(job["action_id"]),
                            f"idem-worker-{job['worker_index']}-{job['event_id']}",
                        )
                    await world.execution.execute_action(
                        str(job["action_id"]),
                        operator=f"eval-worker-{job['worker_index']}",
                    )
                    for _ in range(int(job["passes"])):
                        await world.sync.process_ready_outboxes(limit=20)
                    return f"{prefix}dispatched"
                if job["mode"] == MODE_HEAD:
                    outcome = await enqueue_terminal_head(
                        world,
                        event,
                        str(own_terminal),
                        operator=f"eval-worker-{job['worker_index']}",
                    )
                    for _ in range(int(job["passes"])):
                        await world.sync.process_ready_outboxes(limit=20)
                    return f"{prefix}head:{outcome}"
                delivered = 0
                for _ in range(int(job["passes"])):
                    delivered += await world.sync.process_ready_outboxes(limit=20)
                return f"{prefix}delivered:{delivered}"
            except Exception as exc:  # noqa: BLE001 — a refusal is the expected result
                code = getattr(exc, "error_code", None) or type(exc).__name__
                return f"{prefix}rejected:{code}"


def _child_entry(job: dict[str, Any], sink: Any) -> None:
    """Process entry point. Must be module level so spawn can import it."""
    # Children inherit the parent's mediator switches through the environment the
    # parent exported before forking the pool; harness_context re-applies them so
    # the child does not depend on inheritance order.
    for key, value in (job.get("env") or {}).items():
        os.environ[key] = str(value)
    try:
        outcome = asyncio.run(_child_async(job))
    except Exception as exc:  # noqa: BLE001
        outcome = f"worker_failed:{type(exc).__name__}:{str(exc)[:120]}"
    sink.put((int(job["worker_index"]), outcome))


# --------------------------------------------------------------------------- #
# Parent process.
# --------------------------------------------------------------------------- #


async def _delivered_rows(world: EvalWorld, event_id: str, intent: DispositionIntentKind) -> int:
    async with world.session_factory() as session:
        rows = await session.scalars(
            select(orm.DispositionOutbox.outbox_id).where(
                orm.DispositionOutbox.event_id == event_id,
                orm.DispositionOutbox.intent_kind == intent.value,
                orm.DispositionOutbox.delivery_status == OutboxDeliveryStatus.DELIVERED.value,
            )
        )
        return len(list(rows))


async def _action_ids(world: EvalWorld, event_id: str) -> list[str]:
    async with world.session_factory() as session:
        rows = await session.scalars(
            select(orm.Action.action_id).where(orm.Action.event_id == event_id)
        )
        return [str(row) for row in rows]


async def _outbox_census(world: EvalWorld, event_id: str) -> dict[str, int]:
    """Queue state per (intent, delivery status), so a round that produced nothing
    can be told apart from one that produced something and failed to deliver it."""
    census: dict[str, int] = {}
    for row in await world.outbox_rows(event_id):
        key = f"{row.intent_kind}:{row.delivery_status}"
        census[key] = census.get(key, 0) + 1
    return census


def _switch_env(config: MonitorConfig, column: VendorColumn) -> dict[str, str]:
    """The environment the children need, captured from inside harness_context."""
    keys = (
        "EVAL_HARNESS_MODE",
        "EVAL_DISABLE_CLOSED_GATE",
        "EVAL_DISABLE_APPROVAL_BINDING",
        "EVAL_DISABLE_VERIFY_PHASE_SPLIT",
        "EVAL_DISABLE_OUTBOUND_GUARD",
        "DISPOSITION_MODE",
        "DISPOSITION_ADAPTER_KIND",
        "ALLOW_XDR_WRITEBACK",
        "DATABASE_URL",
        "REDIS_URL",
    )
    with harness_context(config, column):
        return {key: os.environ[key] for key in keys if key in os.environ}


async def _run_round(
    *,
    config: MonitorConfig,
    column: VendorColumn,
    mode: str,
    round_index: int,
    workers: int,
) -> RoundResult:
    env = _switch_env(config, column)
    with harness_context(config, column):
        async with eval_world(column) as world:
            _apply_substrate_patches(world, config)
            event = await world.seed_event(tag=f"conc-{config.name}-{mode}-{round_index}")
            action_id = await world.add_entity_action(event)
            terminal_action_id = await world.add_terminal_action(event)
            await _approve(world, event_id=event.event_id, action_id=action_id)
            await _approve(world, event_id=event.event_id, action_id=terminal_action_id)
            _install_tally(world)

            if mode == MODE_DELIVER:
                # A row has to be queued before anyone can race to deliver it, so
                # the dispatch that queues it is done once, by the parent, and the
                # tally it produces is subtracted from nothing: the parent's own
                # delivery is what the children are racing to repeat.
                await world.execution.execute_action(action_id, operator="eval-seed")

            start_at = time.time() + STARTUP_GRACE_SECONDS
            jobs = [
                {
                    "config": config.name,
                    "column": column.value,
                    "mode": mode,
                    "action_id": action_id,
                    "terminal_action_id": terminal_action_id,
                    "event_id": event.event_id,
                    "source_record_id": event.source_record_id,
                    "connector_id": event.connector_id,
                    "object_id": event.object_id,
                    "plan_revision": event.plan_revision,
                    "worker_index": index,
                    "start_at": start_at,
                    "passes": 3,
                    "env": env,
                }
                for index in range(workers)
            ]
            outcomes = await asyncio.to_thread(_spawn_and_wait, jobs)
            # One drain by the parent, so a row left queued by a worker that lost
            # its lease is still counted rather than silently scoring as prevented.
            for _ in range(3):
                await world.sync.process_ready_outboxes(limit=20)

            entity, terminal, calls = await _read_tally(
                world, await _action_ids(world, event.event_id)
            )
            return RoundResult(
                config=config.name,
                mode=mode,
                round_index=round_index,
                workers=workers,
                entity_effects=entity,
                terminal_effects=terminal,
                submit_calls=calls,
                active_terminal_heads=await world.active_terminal_heads(event.event_id),
                event_id=event.event_id,
                outbox=await _outbox_census(world, event.event_id),
                worker_outcomes=outcomes,
                late_workers=sum(1 for item in outcomes if item.startswith("late:")),
            )


def _spawn_and_wait(jobs: list[dict[str, Any]]) -> list[str]:
    ctx = mp.get_context("spawn")
    sink: Any = ctx.Queue()
    procs = [ctx.Process(target=_child_entry, args=(job, sink)) for job in jobs]
    for proc in procs:
        proc.start()
    results: dict[int, str] = {}
    for _ in jobs:
        try:
            index, outcome = sink.get(timeout=180)
        except Exception:  # noqa: BLE001 — a silent child is itself the finding
            break
        results[index] = outcome
    for proc in procs:
        proc.join(timeout=30)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=10)
    return [results.get(index, "no_result") for index in range(len(jobs))]


async def _approve(world: EvalWorld, *, event_id: str, action_id: str) -> None:
    # Imported here rather than at module scope: chain imports this module's
    # sibling modules and a top-level import would close the cycle.
    from app.eval_suite.chain import _record_approval

    await _record_approval(world, event_id=event_id, action_id=action_id)


async def run_concurrency_probe(
    *,
    column: VendorColumn = VendorColumn.MOCK,
    configs: tuple[MonitorConfig, ...] = PROBE_CONFIGS,
    workers: int = DEFAULT_WORKERS,
    rounds: int = DEFAULT_ROUNDS,
) -> list[dict[str, Any]]:
    """Race ``workers`` processes for ``rounds`` rounds under each configuration."""
    results: list[dict[str, Any]] = []
    for config in configs:
        index_dropped = not config.head_index
        if index_dropped:
            with harness_context(config, column):
                async with eval_world(column) as world:
                    await set_active_head_index(world, present=False)
        try:
            for mode in MODES:
                for round_index in range(rounds):
                    result = await _run_round(
                        config=config,
                        column=column,
                        mode=mode,
                        round_index=round_index,
                        workers=workers,
                    )
                    results.append(result.as_row())
        finally:
            if index_dropped:
                with harness_context(config, column):
                    async with eval_world(column) as world:
                        await repair_duplicate_active_heads(world)
                        await set_active_head_index(world, present=True)
    return results


def summarize_concurrency(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One line per (configuration, mode): how often contention produced a duplicate."""
    keys = sorted({(str(row["config"]), str(row["mode"])) for row in rows})
    table: list[dict[str, Any]] = []
    for config, mode in keys:
        group = [row for row in rows if row["config"] == config and row["mode"] == mode]
        table.append(
            {
                "config": config,
                "mode": mode,
                "rounds": len(group),
                "duplicated_rounds": sum(1 for row in group if row["duplicated"]),
                "max_entity_effects": max((int(row["entity_effects"]) for row in group), default=0),
                "max_terminal_effects": max(
                    (int(row["terminal_effects"]) for row in group), default=0
                ),
                "max_active_heads": max(
                    (int(row["active_terminal_heads"]) for row in group), default=0
                ),
                "late_workers": sum(int(row["late_workers"]) for row in group),
            }
        )
    return table


def render_concurrency_markdown(table: list[dict[str, Any]]) -> str:
    lines = [
        "| configuration | contention | rounds with a duplicate | max entity effects "
        "| max terminal effects | max active heads | late workers |",
        "|---|---|---|---|---|---|---|",
    ]
    for entry in table:
        lines.append(
            f"| {entry['config']} | {entry['mode']} "
            f"| {entry['duplicated_rounds']}/{entry['rounds']} "
            f"| {entry['max_entity_effects']} | {entry['max_terminal_effects']} "
            f"| {entry['max_active_heads']} | {entry['late_workers']} |"
        )
    return "\n".join(lines)


__all__ = [
    "DEFAULT_ROUNDS",
    "DEFAULT_WORKERS",
    "MODE_DELIVER",
    "MODE_DISPATCH",
    "MODE_HEAD",
    "MODES",
    "PROBE_CONFIGS",
    "RoundResult",
    "render_concurrency_markdown",
    "run_concurrency_probe",
    "summarize_concurrency",
]
