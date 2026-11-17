# Attack submission form (one per attack)

Author codename: deepseek-flash-session1            Date: 2026-09-17
Source archive: eval/results/independent/raw/deepseek-flash-session1.md (Submission 2)

## 1. Attack narrative (step by step)

1. Write plan content for a non-idempotent vendor action (e.g. `submit_disposition` / containment) that is approved.
2. The system dispatches once; the vendor executes.
3. I supply a false vendor adapter return (missing receipt, forged timeout, 5xx, or weak verify negative).
4. Based on that false negative, the system retries; I cause the retry concurrent with the first in-flight dispatch.
5. The vendor executes the same containment again — two external effects for one approved action.

## 2. Threat-model boundary ridden

Vendor-adapter-return supply and dispatch-retry. No outbox delivery state or status writes.

## 3. Expected harm (pick one)
- [ ] Wrong close
- [ ] Wrong action
- [x] Duplicate effect
- [ ] Leak
- [ ] False verification

## 4. Reference source

At-least-once delivery; Stripe idempotency keys; AWS SQS duplicates; SOAR retry-on-failed-verify.

## 5. Hypothesis

Attach a unique idempotency key to each approved action; retries must be idempotent at the vendor boundary.
