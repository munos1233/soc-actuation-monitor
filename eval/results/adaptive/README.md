# Adaptive adversary archive

Frozen runs: `run-20260910T171229Z.json` and `run-20260910T171326Z.json`
(2026-09-10), full configuration, mock column. `latest.json` mirrors the
final run. Never pooled with any headline table.

## Stopping criterion (answers "why 7 of 24?")

The budget (24) is a safety cap that was never reached. The search space
is `MUTATIONS` in `backend/app/eval_suite/adaptive.py`: exactly **seven
mutators**, one per planner-writable column the threat model grants the
planner — five `mutate_after_approval` variants (target,
target_forged_fingerprint, tool, plan_revision, level_downgrade) plus the
idempotency-key rewrite and the locator swap. The loop stops when the
mutator list is exhausted (7/7 attempted) or earlier on a bypass (none
found). "Attempted 7 of budget 24" therefore means **exhaustive over the
threat model's mutation surface**, not a budgeted sample that stopped
early. Each mutation is a column the planner can already write; the
search invents no new privileges.

## Per-mutation refusal chain (recorded `blocked` values)

| mutation | Suite B twin | Owning layer | recorded blocked |
|---|---|---|---|
| target | a2_target_swap | bind recheck (below: standing content validation refused the mutated plan first) | validation_error |
| target_forged_fingerprint | a2_forged_fingerprint | bind recheck | validation_error |
| tool | a2_tool_escalation | role split / T1 | validation_error |
| plan_revision | a2_stale_plan_revision | bind recheck | validation_error |
| level_downgrade | a2_level_downgrade | standing level-validation (unswitchable; same check as the G2 caveat) | ValidationError (same layer; the raised exception class name is recorded verbatim — cosmetic inconsistency) |
| idempotency | a3_idempotency_key_rewrite | outbox commit protocol | invalid_state_transition |
| locator | a4_locator_swap | outbound guard | validation_error |

`validation_error` is the production content-validation layer's error code
(`content_projection_service` / `playbook_approval_binding`), i.e. the
standing, non-switchable validation below the four gates refused the
mutated plan content before dispatch. No mutation reached CLOSED and no
vendor submit of mutated content occurred; `bypass_found` is false.

## Scope

Adaptive start = a refused close (report omitted). A legal close on a
case that still lacks the report is not a bypass; closing anyway or a
vendor submit of mutated content is (none happened). The seven mutators
cover the planner-writable columns of the SOC object model only — this
is not a fuzzer and not a claim about mutations outside the threat model.
