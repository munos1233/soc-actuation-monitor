# Attack submission form (one per attack)

Author codename: glm-5.3-session2            Date: 2026-09-17
Source archive: eval/results/independent/raw/glm-5.3-session2.md (Attack 2)

## 1. Attack narrative (step by step)

1. Legitimate-looking action block account svc_backup is proposed and approved (or auto-approved as low tier).
2. Pipeline dispatches through the vendor adapter. Vendor rejects it or the adapter never forwards it. Adapter returns a forged success receipt with a receipt_id.
3. Effect-verification also flows through a channel the adversary supplies, so a false verification answer claims vendor state = blocked and matches the receipt. Variant: replay a genuine receipt from an earlier different action.
4. System records the effect as verified, writes terminal disposition contained, and the ticket closes. The account was never blocked.

## 2. Threat-model boundary ridden

Supply tool/adapter returns of any evidential strength, including false ones. System itself performs verified/disposition/close transitions. Does not write status, approval, or outbox.

## 3. Expected harm (pick one)
- [ ] Wrong close
- [ ] Wrong action
- [ ] Duplicate effect
- [ ] Leak
- [x] False verification

## 4. Reference source

CWE-345 insufficient verification of data authenticity; forged payment-gateway callbacks; lying endpoint agents.

## 5. Hypothesis

Verify the effect on a channel independent of the dispatch path; authenticate receipts bound to the exact command; fail closed on absent or self-attested evidence.
