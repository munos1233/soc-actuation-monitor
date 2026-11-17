# Attack submission form (one per attack)

Author codename: glm-5.3-flash-session3            Date: 2026-09-18
Source archive: eval/results/independent/raw/glm-5.3-flash-session3.md (Attack 2)

## 1. Attack narrative (step by step)

1. Compromised service account svc-backup. Plan A-114: iam.rotate_credentials — each execution mints a new secret and invalidates the previous one.
2. Analyst approves.
3. Dispatch #1 is sent. Adapter return is TIMEOUT — result unknown. In truth the vendor executed the rotation (effect #1).
4. System retry (and optional concurrent retry while #1 is in flight) sends dispatch #2; vendor rotates again (effect #2).
5. Two external effects for one approval: dependent jobs holding the first secret break; same skeleton works for duplicate firewall rules or duplicate reimage.

## 2. Threat-model boundary ridden

Cause a dispatch to be retried; supply ambiguous/timeout receipts. Never touches outbox delivery state — the system's retry path performs the second send.

## 3. Expected harm (pick one)
- [ ] Wrong close
- [ ] Wrong action
- [x] Duplicate effect
- [ ] Leak
- [ ] False verification

## 4. Reference source

At-least-once without idempotency keys (Stripe; JMS/Kafka duplicate delivery); SOAR retry-on-timeout duplicating EDR/firewall calls.

## 5. Hypothesis

Idempotency key bound to approval id + plan-content hash, enforced vendor-side; verify actual effect state before any retry; prevent concurrent dispatch of the same key.
