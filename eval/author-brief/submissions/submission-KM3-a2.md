# Attack submission form (one per attack)

Author codename: kimi-k3-session3            Date: 2026-09-17
Source archive: eval/results/independent/raw/kimi-k3-session3.md (Attack 2)

## 1. Attack narrative (step by step)

1. Approved isolate of web-server-03 is dispatched.
2. Adversary supplies a transient timeout receipt, causing retry, then a false success receipt.
3. Retry runs concurrent with the original in-flight dispatch. Two isolation commands reach the vendor.

## 2. Threat-model boundary ridden

Retry plus false adapter receipts/verification.

## 3. Expected harm (pick one)
- [ ] Wrong close
- [ ] Wrong action
- [x] Duplicate effect
- [ ] Leak
- [ ] False verification

## 4. Reference source

Retry storm / missing idempotency.

## 5. Hypothesis

Idempotency key per approved action; serialize dispatches to the same target.
