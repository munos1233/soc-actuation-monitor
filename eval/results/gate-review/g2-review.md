<!-- STAND-IN-PENDING-REPLACEMENT: stand-in artifact held in place so the real participant's output can drop into the same path; see eval/placeholder-registry.md -->
# Gate review — G2

| gate | verdict | notes |
|---|---|---|
| close | conforms | Gate enforces report, resolved policy, convergence, applicable required-writeback closedness, and terminal `EVENT_STATUS_UPDATE` row with `plan_revision`/`closure_cycle` match when those currents are projected. Extra `CONFIRMED` / strong `confirmation_evidence` checks are stricter than the manuscript “row not vendor receipt” boundary and are not counted as deviations. |
| bind | conforms | `_validate_approval_binding` requires approval detail α, matches bound `plan_revision` and `action_fingerprint` to the action, and when `action_content_hash` is present recomputes content φ. Playbook hash/policy version required when `playbook_ref` is set. Approved-state and event-level `r(e)` are outside this function’s contract (drift-after-approval). |
| egress | deviates | On the `EVENT_STATUS_UPDATE` supersede path, `OutboundDispositionGuard.validate` runs on `command` *before* `model_copy(supersedes_disposition_id=…)`, then the outbox stores SHA-256 of the mutated dump — so the admitted payload hash is not the hash stored on κ. Delivery re-validates the reconstructed command but does not assert `_payload_sha256(command_payload) == command_payload_sha256` before `adapter.submit`. |
| verify | conforms | Phase-1 (`_verify_phase1_effects`) skips `POST_VERIFY` and never calls `activate_and_submit`; terminal activation is confined to phase-2. `classify_verification_observation` maps target mismatch to `UNVERIFIABLE`, not `VERIFIED`, when both observed and expected targets are present. |

## Detail

### Close

`_validate_closed_gate` matches the claimed conjuncts for the required path:

1. **Report** — refuses CLOSED when `ctx.report_exists` is false.
2. **Policy** — `None` fails closed; `NOT_REQUIRED` returns after the report check (resolved policy; writeback conjuncts do not apply).
3. **Convergence** — requires `side_effect_convergence` and `check_gate_applicable_side_effect_convergence`.
4. **Applicable required writebacks** — `check_required_writeback_close_gate` on `applicable_required_actions`.
5. **Terminal row** — requires `terminal_event_writeback` with `EVENT_STATUS_UPDATE` and equality to `current_plan_revision` / `current_closure_cycle` when those fields are non-`None`.

`TransitionContext` documents that gate projections must be DB/server projections, not caller self-report. Receipt `CONFIRMED` and strong confirmation evidence go beyond the manuscript’s last-conjunct boundary (row, not delivery/vendor receipt); that is extra strength, not a semantic miss.

Residual (not upgraded to deviate): revision/cycle equality is skipped when the current projection fields are `None` (fail-open on missing currents rather than fail-closed).

### Bind

Relative to [Approval binding], this mediator checks that α’s stored detail exists and still commits to the action’s fingerprint and plan revision at claim/dispatch time. `build_approval_binding_detail` always records `action_content_hash`; validation recomputes it when present (legacy approvals without the field fall back to column fingerprint only — documented present-then-check). The function does not itself assert action status ∈ approved set or `action.plan_revision == event.r(e)`; those are outside the listed binding API and are not treated as deviations of this file’s claimed drift check.

### Egress

Claimed invariant: every external effect for κ is preceded, in the same transaction, by a guard admission of a payload whose SHA-256 equals the SHA-256 on κ’s outbox row.

- **Enqueue (happy path, no prior head):** `await self._guard.validate(command, ctx)` then `command_payload_sha256=_payload_sha256(command.model_dump(...))` in the same session — by construction the stored hash is of the guarded object. Trusted locator is preferred via `_trusted_event_locator`.
- **Supersede path (deviates):** after the guard, when a prior `EVENT_STATUS_UPDATE` head exists and the idempotent short-circuit does not apply, `command` is replaced with `model_copy(update={"supersedes_disposition_id": ...})` and *that* dump is hashed and stored. The guard therefore did not admit the payload whose digest is persisted on the outbox row.
- **Delivery:** command is rebuilt from `outbox.command_payload`, guard runs again, then `adapter.submit`. There is no check that the payload’s digest still equals `outbox.command_payload_sha256`. When `_trusted_event_locator` is empty, context falls back to `command.source_locator` (self-witness); secondary to the SHA mismatch, but weakens complete mediation of object identity.

`OutboundDispositionGuard` is fail-closed on blocking violations; that does not repair the admit-hash ≠ store-hash ordering bug.

### Verify

Design-verify claims hold in the inspected paths:

- **Phase split:** Module and `_run` confine `activate_and_submit` to `_verify_phase2_disposition`. Phase-1 only observes IMMEDIATE effects and records deferred `POST_VERIFY` as skipped (`deferred_pending_activation`); it does not enqueue terminal writeback. Phase-1 persistence for the EDS gate is observation state only, not activation.
- **Observation integrity:** On tool SUCCESS, `classify_verification_observation` requires `is_verified`; if both `data_dict["target"]` and `action.target` are truthy and differ, status is `UNVERIFIABLE` with `verification_target_mismatch`, never `VERIFIED`.

Note (not deviate under the stated wording): if either target is missing/empty, the mismatch branch does not fire and `is_verified=True` still yields `VERIFIED`. Eval knobs (`eval_disable_verify_phase_split`, etc.) are out of production semantics for this review.
