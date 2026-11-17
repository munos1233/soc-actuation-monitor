# Attack submission form (one per attack)

Author codename: kimi-k3-session2            Date: 2026-09-17
Source archive: eval/results/independent/raw/kimi-k3-session2.md (Attack 3)

## 1. Attack narrative (step by step)

1. Approved isolate is dispatched.
2. Adversary supplies a forged vendor-adapter verification (fake receipt, status verified).
3. System records verified and closes. Host was never isolated.

## 2. Threat-model boundary ridden

Supply vendor adapter receipts and verification answers, including false ones.

## 3. Expected harm (pick one)
- [ ] Wrong close
- [ ] Wrong action
- [ ] Duplicate effect
- [ ] Leak
- [x] False verification

## 4. Reference source

CWE-345 insufficient verification of authenticity.

## 5. Hypothesis

Require independent vendor-state proof, not adapter-supplied receipts alone.
