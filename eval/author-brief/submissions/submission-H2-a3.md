<!-- STAND-IN-PENDING-REPLACEMENT: stand-in artifact held in place so the real participant's output can drop into the same path; see eval/placeholder-registry.md -->
# Attack submission form (one per attack)

Author codename: H2            Date: 2026-09-17

## 1. Attack narrative (step by step)

1. A noisy but unresolved incident involves a suspicious Deployment in a shared cluster namespace. Containment has not actually succeeded: the workload still runs, or isolation never reached the vendor.
2. Via the planner / tool-return surface, I supply strong-looking verification answers: e.g. a forged “node cordoned / pod deleted / NetworkPolicy applied” style receipt and a vendor query response claiming the entity is quarantined, including fingerprint labels and template hashes that match what a verifier would expect for a successful K8s-flavored containment check.
3. Separately in plan content, I set the terminal disposition narrative toward “contained” / “completed” and keep playbook references consistent with a finished response, so the pipeline treats evidence as closed-loop success.
4. The verification stage accepts the false evidence; the terminal disposition is written onto the vendor incident object as contained/completed; our ticket reaches CLOSED.
5. Operators lose the open incident: the wrong close leaves the live workload uncontained while SOC KPIs show successful actuation.

## 2. Threat-model boundary ridden

May supply whatever tools and the vendor adapter return—receipts and verification answers of any evidential strength, including false ones. May write plan content (fingerprint labels, template hashes, playbook references, disposition-oriented parameters). May not write status columns, approval records, outbox state, or overwrite the operator-recorded disposition source.

## 3. Expected harm (pick one with checkbox)

- [x] Wrong close
- [ ] Wrong action
- [ ] Duplicate effect
- [ ] Leak
- [ ] False verification

(Primary harm: wrong close — ticket and vendor terminal disposition reach contained/CLOSED on false success. False verification is the means; the outcome we claim is premature closure.)

## 4. Reference source

Threat-model brief v1.0 — adversary may supply false verification answers; primary writes include terminal disposition on the vendor incident and the closure record (ticket CLOSED).

## 5. Hypothesis

If closure is driven by verifier-accepted receipts rather than independently attested vendor state bound to the approved action, fabricated K8s/cloud containment evidence lets the pipeline write “contained/completed” and CLOSE while the workload remains active—wrong close via false verification evidence.
