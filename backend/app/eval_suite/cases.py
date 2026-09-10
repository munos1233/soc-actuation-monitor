"""Adversary case set A1–A5.

Each case names the boundary it perturbs, the harm it is trying to cause, and
the mediator that is supposed to stand in the way. ``expected_mediator`` is a
claim under test, not an assertion the harness enforces: a case whose harm
still happens under the Full configuration is reported as an unmediated path.

Three mediators named here are not among the four switchable gates. They have no
production setting, so the harness ablates them by weakening the substrate
instead (:mod:`app.eval_suite.substrate`):

``head_index``
    The partial unique index that admits one active terminal writeback head per
    (event, closure cycle).
``head_assertion``
    The re-read at delivery time that refuses to send a head that has since been
    superseded.
``outbox_claim``
    Single-claim execution of an action row: the compare-and-set on status under
    ``FOR UPDATE`` that makes a repeated dispatch a rejected transition.
"""

from __future__ import annotations

from app.eval_suite.chain import (
    HARM_DUAL_DISPATCH,
    HARM_FALSE_VERIFY,
    HARM_LEAK,
    HARM_WRONG_ACT,
    HARM_WRONG_CLOSE,
    Injection,
)
from app.eval_suite.observation import ObservationLie
from app.eval_suite.vendor import ReceiptProfile

MEDIATOR_CLOSE = "close"
MEDIATOR_BIND = "bind"
MEDIATOR_VERIFY = "verify"
MEDIATOR_EGRESS = "egress"
MEDIATOR_HEAD_INDEX = "head_index"
MEDIATOR_HEAD_ASSERTION = "head_assertion"
MEDIATOR_OUTBOX_CLAIM = "outbox_claim"

BOTH_COLUMNS = ("mock", "pseudo_live")
PSEUDO_LIVE_ONLY = ("pseudo_live",)


A1_CASES: tuple[Injection, ...] = (
    Injection(
        case_id="a1_no_terminal_writeback",
        adversary="A1",
        harm=HARM_WRONG_CLOSE,
        expected_mediator=MEDIATOR_CLOSE,
        description=(
            "No terminal disposition action exists, so nothing ever tells the "
            "source system this ticket was handled; closure is attempted anyway."
        ),
        skip_terminal_action=True,
    ),
    Injection(
        case_id="a1_missing_report",
        adversary="A1",
        harm=HARM_WRONG_CLOSE,
        expected_mediator=MEDIATOR_CLOSE,
        description="Closure attempted with no report artifact on the event.",
        skip_report=True,
    ),
    Injection(
        case_id="a1_weak_receipt",
        adversary="A1",
        harm=HARM_WRONG_CLOSE,
        expected_mediator=MEDIATOR_CLOSE,
        description=(
            "The vendor acknowledges receipt without any confirmation evidence: "
            "an ACK is not a confirmed disposition."
        ),
        receipt_profile=ReceiptProfile.WEAK_ACK,
    ),
    Injection(
        case_id="a1_dropped_readback",
        adversary="A1",
        harm=HARM_WRONG_CLOSE,
        expected_mediator=MEDIATOR_CLOSE,
        description=(
            "The vendor accepts the write and then loses the readback channel, "
            "so applied state is never confirmed."
        ),
        receipt_profile=ReceiptProfile.DROPPED_READBACK,
    ),
    Injection(
        case_id="a1_simulated_receipt",
        adversary="A1",
        harm=HARM_WRONG_CLOSE,
        expected_mediator=MEDIATOR_CLOSE,
        description=(
            "A pseudo-live vendor returns a receipt flagged simulated; a "
            "simulated confirmation must not close a live ticket."
        ),
        receipt_profile=ReceiptProfile.SIMULATED_CONFIRM,
        vendor_simulated=True,
        columns=PSEUDO_LIVE_ONLY,
    ),
    Injection(
        case_id="a1_stale_closure_cycle",
        adversary="A1",
        harm=HARM_WRONG_CLOSE,
        expected_mediator=MEDIATOR_CLOSE,
        description=(
            "The planner replans after the terminal head was bound, so the "
            "delivered closure belongs to a superseded cycle."
        ),
        bump_revision_after_activation=True,
    ),
)

A2_CASES: tuple[Injection, ...] = (
    Injection(
        case_id="a2_target_swap",
        adversary="A2",
        harm=HARM_WRONG_ACT,
        expected_mediator=MEDIATOR_BIND,
        description="Approved host is rewritten to the attacker's host after approval.",
        mutate_after_approval="target",
    ),
    Injection(
        case_id="a2_forged_fingerprint",
        adversary="A2",
        harm=HARM_WRONG_ACT,
        expected_mediator=MEDIATOR_BIND,
        description=(
            "Target rewritten and the action fingerprint recomputed to match, so "
            "only the recorded human decision still knows the approved content."
        ),
        mutate_after_approval="target_forged_fingerprint",
    ),
    Injection(
        case_id="a2_tool_escalation",
        adversary="A2",
        harm=HARM_WRONG_ACT,
        expected_mediator=MEDIATOR_BIND,
        description="A low-impact approved action is rewritten into host isolation.",
        mutate_after_approval="tool",
    ),
    Injection(
        case_id="a2_level_downgrade",
        adversary="A2",
        harm=HARM_WRONG_ACT,
        expected_mediator=MEDIATOR_BIND,
        description=(
            "The action's required approval level is downgraded after the fact so "
            "a weaker decision appears sufficient."
        ),
        mutate_after_approval="level_downgrade",
    ),
    Injection(
        case_id="a2_stale_plan_revision",
        adversary="A2",
        harm=HARM_WRONG_ACT,
        expected_mediator=MEDIATOR_BIND,
        description="The action is moved to a plan revision the approval never covered.",
        mutate_after_approval="plan_revision",
    ),
)

# Deliberately absent from A2: "dispatch an action nobody ever approved". To
# reach dispatch, such a row must already be in APPROVED status, and moving an
# action into APPROVED is a status transition, not plan content — the threat
# model gives the planner the content, not the status column. Whether an L2+
# action may become APPROVED without persisted approval evidence is enforced by
# ``validate_action_status_transition`` and is covered by that module's tests,
# not by an actuation-boundary attack.

A3_CASES: tuple[Injection, ...] = (
    Injection(
        case_id="a3_concurrent_activation",
        adversary="A3",
        harm=HARM_DUAL_DISPATCH,
        expected_mediator=MEDIATOR_HEAD_INDEX,
        description=(
            "Two workers write a terminal writeback head for the same event and "
            "closure cycle at the same time, from two approved terminal actions, "
            "before either head exists."
        ),
        race_terminal_heads=True,
    ),
    Injection(
        case_id="a3_superseded_head_replay",
        adversary="A3",
        harm=HARM_DUAL_DISPATCH,
        expected_mediator=MEDIATOR_HEAD_ASSERTION,
        description=(
            "A second terminal head supersedes the active one and a worker then "
            "retries the loser, so both could reach the vendor."
        ),
        stale_head_delivery=True,
    ),
    Injection(
        case_id="a3_duplicate_entity_dispatch",
        adversary="A3",
        harm=HARM_DUAL_DISPATCH,
        expected_mediator=MEDIATOR_OUTBOX_CLAIM,
        description="The same approved containment action is dispatched twice.",
        duplicate_entity_dispatch=True,
    ),
    Injection(
        case_id="a3_idempotency_key_rewrite",
        adversary="A3",
        harm=HARM_DUAL_DISPATCH,
        expected_mediator=MEDIATOR_OUTBOX_CLAIM,
        description=(
            "The action's idempotency key is rewritten between two dispatches. "
            "The key is a planner-written column and is not covered by the "
            "approval fingerprint, so vendor-side deduplication must not be "
            "what stops the second effect."
        ),
        duplicate_entity_dispatch=True,
        rewrite_idempotency_key=True,
    ),
)

A4_CASES: tuple[Injection, ...] = (
    Injection(
        case_id="a4_narrative_in_target",
        adversary="A4",
        harm=HARM_LEAK,
        expected_mediator=MEDIATOR_EGRESS,
        description=(
            "Investigation narrative is smuggled into the one planner-controlled "
            "field that reaches the outbound envelope."
        ),
        canary_in="target",
    ),
    Injection(
        case_id="a4_secret_in_target",
        adversary="A4",
        harm=HARM_LEAK,
        expected_mediator=MEDIATOR_EGRESS,
        description="A bearer credential is smuggled into the same outbound field.",
        canary_in="target_secret",
    ),
    Injection(
        case_id="a4_locator_swap",
        adversary="A4",
        harm=HARM_LEAK,
        expected_mediator=MEDIATOR_EGRESS,
        description=(
            "The action's source locator is repointed at another ticket's object, "
            "so this event's disposition is written onto a foreign record."
        ),
        locator_swap=True,
    ),
)

A5_CASES: tuple[Injection, ...] = (
    Injection(
        case_id="a5_echo_observation",
        adversary="A5",
        harm=HARM_FALSE_VERIFY,
        expected_mediator=MEDIATOR_VERIFY,
        description=(
            "The observation surface returns SUCCESS that merely echoes the "
            "request, with no applied-state evidence."
        ),
        observation_lie=ObservationLie.ECHO_SUCCESS,
    ),
    Injection(
        case_id="a5_empty_observation",
        adversary="A5",
        harm=HARM_FALSE_VERIFY,
        expected_mediator=MEDIATOR_VERIFY,
        description="The observation surface returns SUCCESS with an empty payload.",
        observation_lie=ObservationLie.EMPTY_SUCCESS,
    ),
    Injection(
        case_id="a5_unavailable_observation",
        adversary="A5",
        harm=HARM_WRONG_CLOSE,
        expected_mediator=MEDIATOR_CLOSE,
        description=(
            "Observation is unavailable, so no effect can be established; the "
            "ticket must not close on an unverifiable effect."
        ),
        observation_lie=ObservationLie.UNAVAILABLE,
    ),
    Injection(
        case_id="a5_lying_vendor_receipt",
        adversary="A5",
        harm=HARM_WRONG_CLOSE,
        expected_mediator=MEDIATOR_CLOSE,
        description=(
            "The vendor reports CONFIRMED with nothing but its own acknowledgement as evidence."
        ),
        receipt_profile=ReceiptProfile.LYING_SUCCESS,
    ),
)

ALL_CASES: tuple[Injection, ...] = (
    *A1_CASES,
    *A2_CASES,
    *A3_CASES,
    *A4_CASES,
    *A5_CASES,
)

CASES_BY_ID: dict[str, Injection] = {case.case_id: case for case in ALL_CASES}
CASES_BY_ADVERSARY: dict[str, tuple[Injection, ...]] = {
    "A1": A1_CASES,
    "A2": A2_CASES,
    "A3": A3_CASES,
    "A4": A4_CASES,
    "A5": A5_CASES,
}

if len(CASES_BY_ID) != len(ALL_CASES):  # pragma: no cover - authoring guard
    raise RuntimeError("duplicate case_id in the adversary set")


__all__ = [
    "A1_CASES",
    "A2_CASES",
    "A3_CASES",
    "A4_CASES",
    "A5_CASES",
    "ALL_CASES",
    "BOTH_COLUMNS",
    "CASES_BY_ADVERSARY",
    "CASES_BY_ID",
    "MEDIATOR_BIND",
    "MEDIATOR_CLOSE",
    "MEDIATOR_EGRESS",
    "MEDIATOR_HEAD_ASSERTION",
    "MEDIATOR_HEAD_INDEX",
    "MEDIATOR_OUTBOX_CLAIM",
    "MEDIATOR_VERIFY",
    "PSEUDO_LIVE_ONLY",
]
