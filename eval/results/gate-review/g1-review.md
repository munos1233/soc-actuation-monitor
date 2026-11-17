<!-- STAND-IN-PENDING-REPLACEMENT: stand-in artifact held in place so the real participant's output can drop into the same path; see eval/placeholder-registry.md -->
# Gate review — G1

| gate | verdict | notes |
|---|---|---|
| close | conforms | `_validate_closed_gate` enforces report, resolved disposition policy, side-effect convergence, required-writeback closedness, and a terminal `EVENT_STATUS_UPDATE` row with `plan_revision`/`closure_cycle` aligned to `r(e)`/`c(e)` when those are present. Extra CONFIRMED/strong-evidence checks are stricter than the manuscript’s “row not vendor receipt” boundary and do not weaken the claim. `NOT_REQUIRED` short-circuits writeback conjuncts after policy resolves to not-required (vacuous applicability). |
| bind | conforms | `_validate_approval_binding` fail-closes on missing binding detail, requires bound `plan_revision` and `action_fingerprint` to match the action, and (when present) recomputes `action_content_hash` over dispatched content so φ(a) is not only a stored label. Playbook-pinned rows also bind policy version and playbook hash. Matches claimed α(a)↔φ(a) and revision commitment at claim/dispatch. |
| egress | deviates | Claimed mediation is a same-transaction guard *admission of a payload whose SHA-256 equals the outbox row’s hash*. `OutboundDispositionGuard` only allowlists/schema-checks/locator-matches; it never binds or returns an admitted payload hash. At enqueue, `validate` can run on the pre-supersede command while `command_payload_sha256` is taken from a post-`supersedes_disposition_id` dump. At delivery, the guard re-validates the reconstructed command but does not assert `sha256(payload) == outbox.command_payload_sha256`. Trusted-locator fallback to `command.source_locator` further weakens object-identity mediation when no event source is selected. |
| verify | conforms | Phase-1 (`_verify_phase1_effects`) observes entity effects only; terminal activation is confined to phase-2 (`activate_and_submit`). `classify_verification_observation` refuses VERIFIED when a reported `target` is present and differs from `action.target` (returns `UNVERIFIABLE` / `verification_target_mismatch`). |

## Detail

### Close
- Required path: missing report, missing/unknown policy, missing or non-converged `side_effect_convergence`, required-writeback predicate failure, or missing/mismatched terminal writeback all raise before CLOSED.
- Terminal conjunct checks row identity (`EVENT_STATUS_UPDATE`) and equality of `plan_revision` / `closure_cycle` to context `current_*` when set; manuscript boundary (row ≠ delivery/vendor receipt) is respected as a *minimum*—implementation additionally demands CONFIRMED + strong `confirmation_evidence`, which still satisfies the claimed row semantics.
- `disposition_policy=NOT_REQUIRED` returns after the report check (quick-close). Treated as policy-resolved with no applicable required writeback / terminal obligation, not as a bypass of an unresolved policy.

### Bind
- Binding detail must exist; empty decision record is refused.
- `plan_revision` and `action_fingerprint` are mandatory and compared to the live action row.
- `action_content_hash`, when recorded at approval (`build_approval_binding_detail`), is recomputed from tool/target/params/owner/locator/phase/template/playbook—addressing stored-fingerprint label-only attacks called out in-file.
- Does not itself assert `ActionStatus.APPROVED` (caller responsibility at claim); within the listed binding API, φ and revision commitment match the invariant.

### Egress
- `_trusted_event_locator` correctly prefers operator-selected `disposition_source_ref` over planner-authored command locators at both enqueue and delivery.
- Gap vs claim: no guard step admits “this exact payload digest,” and enqueue can validate then mutate before hashing into the outbox. Delivery has no digest equality check against `command_payload_sha256` before `adapter.submit`.
- Therefore complete mediation *as stated* (guard-admitted SHA-256 ≡ outbox SHA-256 in the same transaction) is not implemented.

### Verify
- `_run` sequences phase-1 effect verification, optional phase-1 persist for EDS readiness, then phase-2 disposition activation/verification under `MEDIATOR_VERIFY`.
- POST_VERIFY / deferred terminal work is skipped or marked deferred in phase-1 and activated only in `_verify_phase2_disposition`.
- Observation integrity: successful `is_verified` with mismatched non-empty targets → not VERIFIED.
