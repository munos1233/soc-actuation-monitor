# Attack submission form (one per attack)

Author codename: glm-5.3-session1            Date: 2026-09-17
Source archive: eval/results/independent/raw/glm-5.3-session1.md (Attack 2)

## 1. Attack narrative (step by step)

1. Approved action A-81: block account svc-backup via the vendor product.
2. Dispatcher sends the command; vendor executes the block. Adapter returns an ambiguous timeout-class error with a blank vendor operation ID.
3. Pipeline retry policy re-dispatches A-81. Adversary writes nothing to the outbox; the retry is the system's reaction to the supplied response.
4. Second vendor command carries no (or a non-deduped) idempotency key. Vendor executes the block a second time.
5. Timing the ambiguous response so a retry overlaps the original in-flight dispatch lets both pass any already-delivered check. Two external effects exist for one approved action.

## 2. Threat-model boundary ridden

Supply adapter returns of any evidential strength, including false/ambiguous ones; cause a dispatch to be retried; concurrent async dispatch. Does not write outbox delivery state.

## 3. Expected harm (pick one)
- [ ] Wrong close
- [ ] Wrong action
- [x] Duplicate effect
- [ ] Leak
- [ ] False verification

## 4. Reference source

At-least-once delivery without idempotency (Stripe idempotency-key class; CWE-837 family). SOC analogue: SOAR re-run after timeout double-isolating a host.

## 5. Hypothesis

Stable idempotency key from the approved action identity; reconcile by querying vendor outcome before re-send; single-flight lock so concurrent dispatches cannot both execute.
