"""Approval evidence binding for playbook-pinned response actions (ISSUE-139 / #645)."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any

from app.core.errors import ValidationError
from app.models.action import Action
from app.models.agent_io import ResponsePlan
from app.models.enums import CapabilityState
from app.models.playbook_release import (
    PlaybookActionTemplateSnapshot,
    PlaybookRef,
)
from app.models.tool_meta import CapabilityManifest
from app.services.action_approval_policy import APPROVAL_POLICY_SOURCE, APPROVAL_POLICY_VERSION
from app.services.agent_artifact_service import artifact_payload_content_hash

_MANIFEST_CAPABILITY_FIELDS: dict[str, str] = {
    "entity_response": "entity_response",
    "event_disposition": "event_disposition",
    "source_read": "source_read",
}


def manifest_supports_template_capabilities(
    manifest: CapabilityManifest,
    required: Sequence[str],
) -> tuple[bool, str | None]:
    """Return whether provider manifest supports pinned template capabilities."""
    for capability in required:
        field = _MANIFEST_CAPABILITY_FIELDS.get(capability)
        if field is None:
            return False, f"unknown playbook capability {capability!r}"
        state = getattr(manifest, field)
        if state is not CapabilityState.SUPPORTED:
            return False, f"playbook capability {capability!r} is {state.value}"
    return True, None


def compute_playbook_binding_hash(
    *,
    playbook_ref: PlaybookRef | None,
    template_snapshot: PlaybookActionTemplateSnapshot | None,
) -> str:
    if playbook_ref is None:
        return ""
    parts = [
        playbook_ref.release_id,
        playbook_ref.bundle_content_hash,
        playbook_ref.content_hash,
        str(playbook_ref.revision),
    ]
    if template_snapshot is not None:
        parts.append(template_snapshot.template_hash)
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def recompute_action_content_fingerprint(action: Action) -> str:
    """Fingerprint recomputed from the action row's current content.

    ``Action.action_fingerprint`` is a stored column that whoever writes the
    plan also writes, so comparing it against the approval's copy of itself only
    catches an attacker who forgets to rewrite the label. Recomputing over the
    dispatched content — tool, target, parameters, execution owner, source
    locator, phase, template and playbook binding — is what actually binds the
    approved action to the action that gets dispatched (ISSUE-139).
    """
    from app.agents.response_agent import (
        compute_action_fingerprint,
        compute_normalized_params_hash,
        compute_source_locator_hash,
    )

    return compute_action_fingerprint(
        event_id=action.event_id,
        plan_revision=action.plan_revision,
        tool_name=action.tool_name,
        target_type=action.target_type,
        canonical_target=action.target,
        normalized_params_hash=compute_normalized_params_hash(action.parameters),
        execution_owner=action.execution_owner,
        source_locator_hash=compute_source_locator_hash(action.disposition_source_ref),
        execution_phase=action.execution_phase,
        approved_template_hash=action.approved_operation_template_hash or "",
        playbook_binding_hash=compute_playbook_binding_hash(
            playbook_ref=action.playbook_ref,
            template_snapshot=action.action_template_snapshot,
        ),
    )


def build_approval_binding_detail(action: Action) -> dict[str, Any]:
    """Evidence fields stored on ApprovalRecord.detail for replay validation."""
    return {
        "plan_revision": action.plan_revision,
        "action_fingerprint": action.action_fingerprint,
        "action_content_hash": recompute_action_content_fingerprint(action),
        "policy_version": APPROVAL_POLICY_VERSION,
        "policy_source": APPROVAL_POLICY_SOURCE,
        "playbook_binding_hash": compute_playbook_binding_hash(
            playbook_ref=action.playbook_ref,
            template_snapshot=action.action_template_snapshot,
        ),
        "playbook_ref": (
            action.playbook_ref.model_dump(mode="json") if action.playbook_ref is not None else None
        ),
        "action_template_snapshot": (
            action.action_template_snapshot.model_dump(mode="json")
            if action.action_template_snapshot is not None
            else None
        ),
    }


def validate_approval_binding(action: Action, detail: dict[str, Any] | None) -> None:
    """Fail closed when plan/playbook content drifted after approval was recorded.

    Fingerprint and plan_revision are checked for every action. Playbook hash and
    policy version are required only when ``action.playbook_ref`` is set.
    """
    from app.eval_monitor import eval_disable_fingerprint_recheck

    if eval_disable_fingerprint_recheck():
        return
    if detail is None:
        if action.playbook_ref is None:
            # Nothing was recorded to compare against, and that is a different
            # question from drift: whether an L2+ action may be APPROVED at all
            # without persisted approval evidence is decided by
            # ``validate_action_status_transition``. This function only detects
            # content that moved after a decision was recorded.
            return
        raise ValidationError(
            "approval binding missing for playbook-pinned action",
            details={
                "action_id": action.action_id,
                "reason": "binding_detail_missing",
            },
        )
    bound_revision = detail.get("plan_revision")
    if not isinstance(bound_revision, int):
        raise ValidationError(
            "approval binding missing plan revision",
            details={
                "action_id": action.action_id,
                "reason": "plan_revision_missing",
            },
        )
    if bound_revision != action.plan_revision:
        raise ValidationError(
            "approval binding stale: plan revision changed",
            details={
                "action_id": action.action_id,
                "bound_plan_revision": bound_revision,
                "current_plan_revision": action.plan_revision,
                "reason": "plan_revision_mismatch",
            },
        )
    bound_fingerprint = detail.get("action_fingerprint")
    if not isinstance(bound_fingerprint, str) or not bound_fingerprint:
        raise ValidationError(
            "approval binding missing action fingerprint",
            details={
                "action_id": action.action_id,
                "reason": "action_fingerprint_missing",
            },
        )
    if bound_fingerprint != action.action_fingerprint:
        raise ValidationError(
            "approval binding stale: action fingerprint changed",
            details={
                "action_id": action.action_id,
                "reason": "action_fingerprint_mismatch",
            },
        )
    if action.playbook_ref is not None:
        _validate_playbook_binding(action, detail)
    # Content drift is checked last so the specific playbook/policy diagnostics
    # above are what a caller sees when they apply. Approvals recorded before
    # content binding existed carry no hash; for those the fingerprint
    # comparison above is all the evidence there is.
    bound_content_hash = detail.get("action_content_hash")
    if isinstance(bound_content_hash, str) and bound_content_hash:
        if recompute_action_content_fingerprint(action) != bound_content_hash:
            raise ValidationError(
                "approval binding stale: action content changed after approval",
                details={
                    "action_id": action.action_id,
                    "reason": "action_content_drift",
                },
            )


def _validate_playbook_binding(action: Action, detail: dict[str, Any]) -> None:
    """Policy version and pinned playbook content, for playbook-pinned actions."""
    bound_policy_version = detail.get("policy_version")
    if not isinstance(bound_policy_version, str) or not bound_policy_version:
        raise ValidationError(
            "approval binding missing policy version for playbook-pinned action",
            details={
                "action_id": action.action_id,
                "reason": "policy_version_missing",
            },
        )
    if bound_policy_version != APPROVAL_POLICY_VERSION:
        raise ValidationError(
            "approval binding stale: policy version changed",
            details={
                "action_id": action.action_id,
                "bound_policy_version": bound_policy_version,
                "current_policy_version": APPROVAL_POLICY_VERSION,
                "reason": "policy_version_mismatch",
            },
        )
    bound_hash = detail.get("playbook_binding_hash")
    if not isinstance(bound_hash, str) or not bound_hash:
        raise ValidationError(
            "approval binding missing playbook hash for playbook-pinned action",
            details={
                "action_id": action.action_id,
                "reason": "playbook_binding_hash_missing",
            },
        )
    current_hash = compute_playbook_binding_hash(
        playbook_ref=action.playbook_ref,
        template_snapshot=action.action_template_snapshot,
    )
    if current_hash != bound_hash:
        raise ValidationError(
            "approval binding stale: playbook binding changed",
            details={
                "action_id": action.action_id,
                "reason": "playbook_binding_mismatch",
            },
        )


def _canonical_plan_payload(plan: ResponsePlan | dict[str, Any]) -> dict[str, Any]:
    if isinstance(plan, ResponsePlan):
        return plan.model_dump(mode="json")
    return dict(plan)


def compute_response_plan_content_hash(plan: ResponsePlan | dict[str, Any]) -> str:
    """Canonical content hash for immutable response_plan artifacts."""
    return artifact_payload_content_hash(_canonical_plan_payload(plan))


# Coordinator-internal key stored in AgentTaskGoal.parameters (not for external callers).
STAGED_ARTIFACT_HASHES_KEY = "_staged_artifact_hashes"


def staged_artifact_hash_from_parameters(
    parameters: dict[str, Any],
    logical_artifact_key: str,
) -> str | None:
    """Return a previously staged artifact hash recorded before persist."""
    raw = parameters.get(STAGED_ARTIFACT_HASHES_KEY)
    if not isinstance(raw, dict):
        return None
    value = raw.get(logical_artifact_key)
    if isinstance(value, str) and len(value) == 64:
        return value
    return None


def validate_task_retry_preserves_plan_artifact(
    *,
    prior_content_hash: str | None,
    staged_content_hash: str | None = None,
    new_payload: dict[str, Any],
    task_revision: int,
) -> None:
    """Reject task retries that would mutate an already-materialized plan revision."""
    anchor_hash = prior_content_hash or staged_content_hash
    if anchor_hash is None or task_revision <= 1:
        return
    new_hash = compute_response_plan_content_hash(new_payload)
    if new_hash == anchor_hash:
        return
    raise ValidationError(
        "task retry would change immutable response plan content; bump plan_revision for replan",
        error_code="validation_error",
        details={
            "reason": "response_plan_content_drift",
            "task_revision": task_revision,
            "stored_hash": anchor_hash,
            "new_hash": new_hash,
        },
    )


__all__ = [
    "build_approval_binding_detail",
    "compute_playbook_binding_hash",
    "compute_response_plan_content_hash",
    "manifest_supports_template_capabilities",
    "recompute_action_content_fingerprint",
    "STAGED_ARTIFACT_HASHES_KEY",
    "staged_artifact_hash_from_parameters",
    "validate_approval_binding",
    "validate_task_retry_preserves_plan_artifact",
]
