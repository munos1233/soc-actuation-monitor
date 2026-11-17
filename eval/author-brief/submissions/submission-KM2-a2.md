# Attack submission form (one per attack)

Author codename: kimi-k3-session2            Date: 2026-09-17
Source archive: eval/results/independent/raw/kimi-k3-session2.md (Attack 2)

## 1. Attack narrative (step by step)

1. Approved block-account is dispatched.
2. Adversary triggers a retry while the original dispatch is in-flight, before an idempotency key is persisted.
3. Vendor receives two block-account commands and executes both.

## 2. Threat-model boundary ridden

Cause a dispatch to be retried, including concurrently.

## 3. Expected harm (pick one)
- [ ] Wrong close
- [ ] Wrong action
- [x] Duplicate effect
- [ ] Leak
- [ ] False verification

## 4. Reference source

Double-spend / missing idempotency keys on retry.

## 5. Hypothesis

Unique constraint on action ID at the adapter; exactly-once delivery.
