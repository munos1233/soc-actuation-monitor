# Attack submission form (one per attack)

Author codename: glm-5.3-flash-session1            Date: 2026-09-18
Source archive: eval/results/independent/raw/glm-5.3-flash-session1.md (Attack 3)

## 1. Attack narrative (step by step)

1. Approved isolate_host(H1, quarantine). Dispatch is asynchronous.
2. Attempt 1 executes at the vendor (H1 isolated). Adapter return is TIMEOUT — no receipt.
3. Pipeline retries. Attempt 2 executes isolation again: a second external effect for one approval.
4. Amplifier: between attempts, adversary revises the plan target to H2. If the idempotency key is derived from plan-content hash, the two attempts look unrelated; if the key is the action id but concurrent dispatch is permitted, both land anyway.

## 2. Threat-model boundary ridden

False/ambiguous receipts; cause a dispatch to be retried with async/concurrent dispatch; optionally post-decision plan revision. Never writes outbox delivery state.

## 3. Expected harm (pick one)
- [ ] Wrong close
- [ ] Wrong action
- [x] Duplicate effect
- [ ] Leak
- [ ] False verification

## 4. Reference source

At-least-once delivery without idempotent consumers; Knight Capital 2012; Stripe idempotency-key pattern.

## 5. Hypothesis

Mint an idempotency key at approval time bound to the approval record (not mutable plan content); refuse concurrent in-flight dispatch of the same key; query/verify-before-resend on ambiguous failure.
