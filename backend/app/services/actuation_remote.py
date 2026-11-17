"""Planner-process proxies: privileged writes enqueue to the actuation worker."""

from __future__ import annotations

from typing import Any

from app.core.config import TaskMode, get_settings
from app.core.errors import ConfigurationError
from app.models.enums import EventStatus
from app.models.security_event import SecurityEvent
from app.models.workflow import TransitionContext
from app.tasks.actuation_tasks import DISPOSITION_TASK, FORCE_CLOSE_TASK, STATE_TASK, TRANSITION_TASK

_CALL_TIMEOUT_S = 120


def _send(name: str, kwargs: dict[str, Any], *, timeout: int = _CALL_TIMEOUT_S) -> Any:
    settings = get_settings()
    if settings.task_mode is TaskMode.BACKGROUND:
        raise ConfigurationError(
            "PROCESS_ROLE=planner requires TASK_MODE=celery to issue privileged writes",
            error_code="configuration_error",
        )
    from app.core.celery_app import celery_app

    return celery_app.send_task(name, kwargs=kwargs, queue="actuation").get(timeout=timeout)


class RemoteStateMachine:
    """StateMachine surface that never constructs the writer factory."""

    async def transition(
        self,
        event_id: str,
        target: EventStatus,
        *,
        context: TransitionContext | None = None,
        operator: str | None = None,
        reason: str | None = None,
    ) -> SecurityEvent:
        payload = _send(
            TRANSITION_TASK,
            {
                "event_id": event_id,
                "target": target.value if isinstance(target, EventStatus) else str(target),
                "context": context.model_dump(mode="json") if context is not None else None,
                "operator": operator,
                "reason": reason,
            },
        )
        return SecurityEvent.model_validate(payload)

    async def force_close(self, event_id: str, principal: Any, reason: str) -> SecurityEvent:
        payload = _send(
            FORCE_CLOSE_TASK,
            {
                "event_id": event_id,
                "principal": principal.model_dump(mode="json"),
                "reason": reason,
            },
        )
        return SecurityEvent.model_validate(payload)

    async def get_current_status(self, event_id: str) -> EventStatus:
        from app.db.session import get_session_factory
        from app.db import models as orm

        factory = get_session_factory()
        async with factory() as session:
            row = await session.get(orm.SecurityEvent, event_id)
        if row is None:
            from app.core.errors import EventNotFoundError

            raise EventNotFoundError(
                f"security_event not found: {event_id}",
                details={"event_id": event_id},
            )
        return EventStatus(row.status)

    async def repair_post_commit_projection(self, event_id: str, **kwargs: Any) -> Any:
        return _send(
            STATE_TASK,
            {"method": "repair_post_commit_projection", "args": [event_id], "kwargs": kwargs},
        )


class RemoteDispositionSync:
    """DispositionSync surface that never constructs the writer factory."""

    async def enqueue_command(self, *args: Any, **kwargs: Any) -> Any:
        return _send(DISPOSITION_TASK, {"method": "enqueue_command", "args": list(args), "kwargs": kwargs})

    async def retry_writeback(self, *args: Any, **kwargs: Any) -> Any:
        return _send(DISPOSITION_TASK, {"method": "retry_writeback", "args": list(args), "kwargs": kwargs})

    async def activate_deferred_disposition(self, *args: Any, **kwargs: Any) -> Any:
        return _send(
            DISPOSITION_TASK,
            {"method": "activate_deferred_disposition", "args": list(args), "kwargs": kwargs},
        )

    async def resolve_writeback(self, *args: Any, **kwargs: Any) -> Any:
        return _send(DISPOSITION_TASK, {"method": "resolve_writeback", "args": list(args), "kwargs": kwargs})

    async def get_writeback(self, *args: Any, **kwargs: Any) -> Any:
        return _send(DISPOSITION_TASK, {"method": "get_writeback", "args": list(args), "kwargs": kwargs})

    async def list_event_dispositions(self, *args: Any, **kwargs: Any) -> Any:
        return _send(
            DISPOSITION_TASK,
            {"method": "list_event_dispositions", "args": list(args), "kwargs": kwargs},
        )

    async def get_disposition(self, *args: Any, **kwargs: Any) -> Any:
        return _send(DISPOSITION_TASK, {"method": "get_disposition", "args": list(args), "kwargs": kwargs})

    async def process_ready_outboxes(self, *args: Any, **kwargs: Any) -> Any:
        return _send(
            DISPOSITION_TASK,
            {"method": "process_ready_outboxes", "args": list(args), "kwargs": kwargs},
        )

    async def deliver_outbox(self, *args: Any, **kwargs: Any) -> Any:
        return _send(DISPOSITION_TASK, {"method": "deliver_outbox", "args": list(args), "kwargs": kwargs})

    async def lookup_writeback_status(self, *args: Any, **kwargs: Any) -> Any:
        return _send(
            DISPOSITION_TASK,
            {"method": "lookup_writeback_status", "args": list(args), "kwargs": kwargs},
        )

    async def update_writeback_status_from_lookup(self, *args: Any, **kwargs: Any) -> Any:
        return _send(
            DISPOSITION_TASK,
            {"method": "update_writeback_status_from_lookup", "args": list(args), "kwargs": kwargs},
        )


def planner_must_not_build_writer() -> bool:
    from app.core.config import ProcessRole

    return get_settings().process_role is ProcessRole.PLANNER


__all__ = [
    "RemoteDispositionSync",
    "RemoteStateMachine",
    "planner_must_not_build_writer",
]
