"""Privileged writes that may run only in a PROCESS_ROLE=actuation worker."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core.celery_app import celery_app
from app.core.config import ProcessRole, get_settings
from app.core.errors import ConfigurationError
from app.db.session import get_actuation_session_factory, get_session_factory
from app.models.enums import EventStatus
from app.models.security_event import SecurityEvent
from app.models.workflow import TransitionContext

logger = logging.getLogger(__name__)

ACTUATION_QUEUE = "actuation"
TRANSITION_TASK = "actuation.transition"
FORCE_CLOSE_TASK = "actuation.force_close"
DISPOSITION_TASK = "actuation.disposition_call"
STATE_TASK = "actuation.state_call"


def _require_actuation_role() -> None:
    role = get_settings().process_role
    if role is ProcessRole.PLANNER:
        raise ConfigurationError(
            "PROCESS_ROLE=planner cannot execute privileged actuation tasks",
            error_code="configuration_error",
        )


async def _build_state_machine() -> Any:
    from app.core.event_bus import EventBus
    from app.core.redis_client import RedisClient
    from app.services.context_service import EventContextStore
    from app.services.degraded_flag_service import create_degraded_flag_service
    from app.services.event_audit_log_service import EventAuditLogService
    from app.services.state_machine_service import StateMachineService

    _require_actuation_role()
    factory = get_session_factory()
    write_factory = get_actuation_session_factory()
    redis = RedisClient()
    store = EventContextStore(redis, factory)
    return StateMachineService(
        factory,
        store,
        event_bus=EventBus(redis),
        audit_log=EventAuditLogService(factory),
        degraded_flags=create_degraded_flag_service(store, factory),
        write_session_factory=write_factory,
    )


async def _build_disposition_sync() -> Any:
    from app.adapters.factory import build_disposition_adapter_registry
    from app.core.event_bus import EventBus
    from app.core.guardrails import OutboundDispositionGuard
    from app.core.redis_client import RedisClient
    from app.services.context_service import EventContextStore
    from app.services.disposition_sync_service import DispositionSyncService

    _require_actuation_role()
    factory = get_actuation_session_factory()
    redis = RedisClient()
    store = EventContextStore(redis, get_session_factory())
    settings = get_settings()
    return DispositionSyncService(
        factory,
        context_store=store,
        adapter_registry=build_disposition_adapter_registry(settings),
        outbound_guard=OutboundDispositionGuard(),
        event_bus=EventBus(redis),
    )


def _dump(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "model_dump"):
        return {"__pydantic__": type(value).__name__, "data": value.model_dump(mode="json")}
    if isinstance(value, (list, tuple)):
        return [_dump(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _dump(item) for key, item in value.items()}
    return value


async def _transition_async(
    event_id: str,
    target: str,
    *,
    context: dict[str, Any] | None,
    operator: str | None,
    reason: str | None,
) -> dict[str, Any]:
    machine = await _build_state_machine()
    ctx = TransitionContext.model_validate(context) if context else None
    result = await machine.transition(
        event_id,
        EventStatus(target),
        context=ctx,
        operator=operator,
        reason=reason,
    )
    return result.model_dump(mode="json")


async def _force_close_async(
    event_id: str,
    principal: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    from app.core.auth import Principal

    machine = await _build_state_machine()
    result = await machine.force_close(
        event_id,
        Principal.model_validate(principal),
        reason,
    )
    return result.model_dump(mode="json")


async def _disposition_async(method: str, args: list[Any], kwargs: dict[str, Any]) -> Any:
    sync = await _build_disposition_sync()
    target = getattr(sync, method)
    result = await target(*args, **kwargs)
    return _dump(result)


@celery_app.task(  # type: ignore[untyped-decorator]
    name=TRANSITION_TASK,
    acks_late=True,
    soft_time_limit=120,
    queue=ACTUATION_QUEUE,
)
def transition_event(
    event_id: str,
    target: str,
    context: dict[str, Any] | None = None,
    operator: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return asyncio.run(
        _transition_async(
            event_id,
            target,
            context=context,
            operator=operator,
            reason=reason,
        )
    )


@celery_app.task(  # type: ignore[untyped-decorator]
    name=FORCE_CLOSE_TASK,
    acks_late=True,
    soft_time_limit=120,
    queue=ACTUATION_QUEUE,
)
def force_close_event(
    event_id: str,
    principal: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return asyncio.run(_force_close_async(event_id, principal, reason))


async def _state_call_async(method: str, args: list[Any], kwargs: dict[str, Any]) -> Any:
    machine = await _build_state_machine()
    result = await getattr(machine, method)(*args, **kwargs)
    return _dump(result)


@celery_app.task(  # type: ignore[untyped-decorator]
    name=STATE_TASK,
    acks_late=True,
    soft_time_limit=120,
    queue=ACTUATION_QUEUE,
)
def state_call(
    method: str,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
) -> Any:
    return asyncio.run(_state_call_async(method, list(args or []), dict(kwargs or {})))


@celery_app.task(  # type: ignore[untyped-decorator]
    name=DISPOSITION_TASK,
    acks_late=True,
    soft_time_limit=180,
    queue=ACTUATION_QUEUE,
)
def disposition_call(
    method: str,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
) -> Any:
    return asyncio.run(_disposition_async(method, list(args or []), dict(kwargs or {})))


__all__ = [
    "ACTUATION_QUEUE",
    "DISPOSITION_TASK",
    "FORCE_CLOSE_TASK",
    "STATE_TASK",
    "TRANSITION_TASK",
    "disposition_call",
    "force_close_event",
    "transition_event",
]
