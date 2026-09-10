"""Mediator kill switches used by the ablation harness.

Production builds never set these: :class:`~app.core.config.Settings` rejects any
``EVAL_DISABLE_*`` flag unless ``EVAL_HARNESS_MODE=true`` is also declared, so a
shipped deployment cannot unload a gate through a single environment variable.
The switches exist so the evaluation can remove exactly one mediator at a time
without rewriting business semantics.

The suite that drives adversaries through the real service chain lives in
``app.eval_suite``; this module only owns the flags themselves.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.core.config import get_settings

ENV_HARNESS = "EVAL_HARNESS_MODE"
ENV_CLOSED = "EVAL_DISABLE_CLOSED_GATE"
ENV_BIND = "EVAL_DISABLE_FINGERPRINT_RECHECK"
ENV_VERIFY = "EVAL_DISABLE_VERIFY_PHASE_SPLIT"
ENV_EGRESS = "EVAL_DISABLE_OUTBOUND_GUARD"

SWITCH_ENV = (ENV_HARNESS, ENV_CLOSED, ENV_BIND, ENV_VERIFY, ENV_EGRESS)


def _flag(name: str) -> bool:
    return bool(getattr(get_settings(), name))


def eval_disable_closed_gate() -> bool:
    return _flag("eval_disable_closed_gate")


def eval_disable_fingerprint_recheck() -> bool:
    return _flag("eval_disable_fingerprint_recheck")


def eval_disable_verify_phase_split() -> bool:
    return _flag("eval_disable_verify_phase_split")


def eval_disable_outbound_guard() -> bool:
    return _flag("eval_disable_outbound_guard")


def eval_count_deferred_as_failure() -> bool:
    return eval_disable_verify_phase_split()


def eval_skip_phase2_when_phase1_blocked() -> bool:
    return not eval_disable_verify_phase_split()


def eval_tool_success_is_verified(data: dict[str, Any] | None) -> bool:
    """Naive split: tool SUCCESS is treated as verified, even without is_verified."""
    if eval_disable_verify_phase_split():
        return True
    return bool(data and data.get("is_verified") is True)


@contextmanager
def eval_switch_context(
    *,
    disable_closed: bool = False,
    disable_bind: bool = False,
    disable_verify: bool = False,
    disable_egress: bool = False,
    extra_env: dict[str, str] | None = None,
) -> Iterator[None]:
    """Temporarily run under one mediator configuration.

    ``EVAL_HARNESS_MODE`` is set alongside the switches because ``Settings``
    refuses to construct a configuration with a mediator unloaded otherwise.
    """
    mapping = {
        ENV_HARNESS: "true",
        ENV_CLOSED: "true" if disable_closed else "false",
        ENV_BIND: "true" if disable_bind else "false",
        ENV_VERIFY: "true" if disable_verify else "false",
        ENV_EGRESS: "true" if disable_egress else "false",
    }
    mapping.update(extra_env or {})
    prior = {key: os.environ.get(key) for key in mapping}
    try:
        os.environ.update(mapping)
        get_settings.cache_clear()
        yield
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()


__all__ = [
    "ENV_BIND",
    "ENV_CLOSED",
    "ENV_EGRESS",
    "ENV_HARNESS",
    "ENV_VERIFY",
    "SWITCH_ENV",
    "eval_count_deferred_as_failure",
    "eval_disable_closed_gate",
    "eval_disable_fingerprint_recheck",
    "eval_disable_outbound_guard",
    "eval_disable_verify_phase_split",
    "eval_skip_phase2_when_phase1_blocked",
    "eval_switch_context",
    "eval_tool_success_is_verified",
]
