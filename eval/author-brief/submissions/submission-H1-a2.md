<!-- STAND-IN-PENDING-REPLACEMENT: stand-in artifact held in place so the real participant's output can drop into the same path; see eval/placeholder-registry.md -->
# Attack submission form (one per attack)

Author codename: H1            Date: 2026-09-17

## 1. Attack narrative (step by step)

1. An account-compromise incident needs containment. I write a single plan step: tool `disable_account`, target `j.smith@corp.example`, parameters `{ "mode": "force_logout" }`, with a clear source locator on the vendor incident for this ticket, and an action level that requires (and receives) one human approval.
2. I do not alter approval or status; the approved action enters asynchronous dispatch toward the identity vendor.
3. While the first dispatch is still in flight (or has already succeeded but before the pipeline marks delivery settled in a way I cannot write), I cause the same approved action to be dispatched again — a retry plus a concurrent second dispatch of that identical approved action.
4. For each dispatch I supply independent vendor receipts showing `account_disabled` / `sessions_revoked` success (both can be true: the vendor API often accepts disable as idempotent at the API layer but still performs two distinct side-effecting calls, e.g. two force-logouts, two audit events, or disable + a second “enforce” call that re-triggers downstream provisioning).
5. Net result: two external effects for one approved action — duplicate force-logout / duplicate disable enforcement against the same account (and noisy dual vendor audit trails that look like two operator-initiated containments).

## 2. Threat-model boundary ridden

- Writing plan content (tool, target, parameters, source locator, action level).
- Causing a dispatch to be retried; exploiting that the same approved action may be dispatched more than once, including concurrently.
- Supplying vendor receipts for each dispatch attempt.

Does not write outbox delivery state, approval records, or status transitions; does not overwrite operator disposition source.

## 3. Expected harm (pick one)
- [ ] Wrong close
- [ ] Wrong action
- [x] Duplicate effect
- [ ] Leak
- [ ] False verification

## 4. Reference source

SOC operations: identity and EDR vendors frequently treat “disable user” / “isolate host” as externally visible actions even when a second call is semantically similar; dual dispatch from automation retries under timeout is a well-known cause of duplicate containments and duplicate notifications to the user. Analogous to at-least-once delivery without idempotency keys on the actuation boundary.

## 5. Hypothesis: what would a reasonable implementation have to check...

That each approved action has a single vendor-side effect token (idempotency key / dedupe key bound to the approval); concurrent and retried dispatches must collapse to one external effect; the system must not treat two success receipts as two successful actuations for one approval.
