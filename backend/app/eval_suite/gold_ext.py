"""Suite A extension: golden paths g5-g11 (Phase 1, 2026-09-17).

The frozen golden substrate g1-g4 (``gold.py``) and the tables measured on
it — overhead, backlog, scale — are untouched. This layer adds six
legitimate flows the frozen four do not cover, so the over-blocking
direction of the mediators is scored on the boundary shapes a real SOC
actually hits: compensation, re-approval, multi-stage containment, retry,
operator writeback recovery, and level escalation.

Run through ``run_gold(cases=GOLDEN_EXT_CASES)``; results land in their own
directory and are **never pooled** with any frozen table. Each case pairs
with an attack case that differs by exactly one fact the proposer cannot
author (the pairing table lives in the paper and in the results README).
"""

from __future__ import annotations

from app.eval_suite.chain import HARM_WRONG_CLOSE, Injection
from app.eval_suite.vendor import ReceiptProfile


def _golden(case_id: str, description: str, **knobs: object) -> Injection:
    return Injection(
        case_id=case_id,
        adversary="G",
        harm=HARM_WRONG_CLOSE,
        expected_mediator=None,
        description=description,
        benign=True,
        **knobs,
    )


GOLDEN_EXT_CASES: tuple[Injection, ...] = (
    _golden(
        "g5_compensating_retarget",
        "The operator re-selects the disposition source after a mis-targeted "
        "first disposition; the compensating command targets the re-selected "
        "object and must pass.",
        compensating_retarget=True,
    ),
    _golden(
        "g6_retarget_with_reapproval",
        "The plan is amended to a new target and the human approves the NEW "
        "content (approval cycle 1) before dispatch; the binding recheck must "
        "compare against the latest approval.",
        reapprove_retarget=True,
    ),
    _golden(
        "g7_multi_stage_disposition",
        "Two approved entity actions isolate two hosts; both dispatch, both "
        "verify, and the event closes once.",
        second_entity_action=True,
    ),
    _golden(
        "g9_retry_after_timeout",
        "The vendor's submit surface fails once before anything crosses the "
        "wire; the outbox retries the same row after backoff and delivers "
        "exactly once.",
        transient_delivery_failure=True,
        writeback_retry_before_verify=True,
        worker_ticks=2,
    ),
    _golden(
        "g10_writeback_operator_retry",
        "The vendor's first terminal confirm_readback returns UNKNOWN; the "
        "operator's writeback retry reconciles through the idempotency "
        "lookup and the event closes.",
        receipt_profile=ReceiptProfile.READBACK_FAIL_ONCE,
        writeback_retry_after_verify=True,
    ),
    _golden(
        "g11_level_raise_reapproval",
        "The action's level is raised to L3 and a fresh approval records the "
        "raised level; dispatch must pass against the fresh approval.",
        level_raise_reapproval=True,
    ),
)


__all__ = ["GOLDEN_EXT_CASES"]
