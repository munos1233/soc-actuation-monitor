# Attack submission form (one per attack)

Author codename: kimi-k3-session1            Date: 2026-09-17
Source archive: eval/results/independent/raw/kimi-k3-session1.md (Attack 2)

## 1. Attack narrative (step by step)

1. Approved isolate of a single host is dispatched.
2. Adversary causes a retry and a concurrent second dispatch of the same approved action.
3. Vendor executes two isolation commands for one approval.

## 2. Threat-model boundary ridden

Cause a dispatch to be retried; asynchronous concurrent dispatch of the same approved action.

## 3. Expected harm (pick one)
- [ ] Wrong close
- [ ] Wrong action
- [x] Duplicate effect
- [ ] Leak
- [ ] False verification

## 4. Reference source

Retry/idempotency failures in automated response.

## 5. Hypothesis

Idempotency key unique to the approved action; retries must not produce a second external effect.
