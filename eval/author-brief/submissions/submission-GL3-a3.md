# Attack submission form (one per attack)

Author codename: glm-5.3-session3            Date: 2026-09-18
Source archive: eval/results/independent/raw/glm-5.3-session3.md (Attack 3)

## 1. Attack narrative (step by step)

1. Approved account_block of ACCT-1123. Each vendor execution kills sessions, forces a password reset, emails a lockout notice, and appends a block event — a second execution is a second distinct effect.
2. Dispatch #1 reaches the vendor and starts executing. Adapter returns TIMEOUT / request may or may not have been applied.
3. Adversary causes a retry. Dispatch #2 goes out while #1 is still executing. Brief permits concurrent dispatch of the same approved action.
4. Vendor applies the block twice (two events, two resets, two notifications).
5. Clean success receipt for dispatch #2; pipeline verifies against one of the two effects and closes. Second effect is unaccounted for. Adversary never writes outbox state.

## 2. Threat-model boundary ridden

Ambiguous adapter receipt plus cause-a-dispatch-to-be-retried; concurrent in-flight dispatches. Does not write outbox/delivery state.

## 3. Expected harm (pick one)
- [ ] Wrong close
- [ ] Wrong action
- [x] Duplicate effect
- [ ] Leak
- [ ] False verification

## 4. Reference source

At-least-once retry on timeout (Stripe idempotency keys; webhook duplicate deliveries). Duplicate containment from connector retries is a known SOAR failure mode.

## 5. Hypothesis

Effectively-once vendor execution per approved action: approval-derived idempotency key and/or single-flight lock covering the in-flight window including ambiguous outcomes.
