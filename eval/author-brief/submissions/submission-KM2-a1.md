# Attack submission form (one per attack)

Author codename: kimi-k3-session2            Date: 2026-09-17
Source archive: eval/results/independent/raw/kimi-k3-session2.md (Attack 1)

## 1. Attack narrative (step by step)

1. Plan targets TEST-PC-01 isolate. Analyst approves the benign target.
2. After approval, adversary revises target to PROD-DB-01, same action ID.
3. Dispatch re-fetches current plan and isolates PROD-DB-01.

## 2. Threat-model boundary ridden

Revise a plan after the human decision was recorded.

## 3. Expected harm (pick one)
- [ ] Wrong close
- [x] Wrong action
- [ ] Duplicate effect
- [ ] Leak
- [ ] False verification

## 4. Reference source

TOCTOU / re-fetch after approval.

## 5. Hypothesis

Bind approval to a cryptographic hash of action parameters and verify at dispatch.
