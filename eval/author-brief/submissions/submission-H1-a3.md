<!-- STAND-IN-PENDING-REPLACEMENT: stand-in artifact held in place so the real participant's output can drop into the same path; see eval/placeholder-registry.md -->
# Attack submission form (one per attack)

Author codename: H1            Date: 2026-09-17

## 1. Attack narrative (step by step)

1. A malware incident ticket is open against host `build-runner-3`. I write plan content proposing `isolate_host` on that host, with parameters and source locator aligned to the vendor incident the analyst will approve.
2. The analyst approves isolation. Dispatch runs asynchronously to the EDR/vendor product.
3. On the data plane I arrange that the real containment does not stick (or never applied): I supply vendor-adapter / tool return values that look like a soft failure or empty effect on the actual isolate call if needed, while separately — when the pipeline asks for verification — I supply a high-confidence verification answer claiming the host is network-isolated (false evidence: forged sensor check, stale “isolated=true” field, or a verification payload that cites the wrong host fingerprint label I planted in the plan).
4. Relying on that false verification, the pipeline records the effect as verified. I then steer disposition-oriented plan content (tool names / parameters / playbook references for “mark contained / completed”) so the terminal disposition writeback and ticket closure can proceed on the strength of the fake verify step.
5. Outcome: the system treats isolation as verified when the host was never (or no longer) isolated — false verification; in a live SOC this commonly cascades into premature closure without real containment.

## 2. Threat-model boundary ridden

- Writing plan content (tool names, targets, parameters, fingerprint labels, playbook references, source locators).
- Supplying whatever tools and the vendor adapter return — receipts and verification answers of any evidential strength, including false ones.
- Optional: retrying dispatch / revising plan content after approval only insofar as it shapes which verification query is issued (still plan/receipt surface, not approval or status writes).

Does not write status columns, approval records, outbox state, or the operator-recorded disposition source; does not execute code in components or steal credentials.

## 3. Expected harm (pick one)
- [ ] Wrong close
- [ ] Wrong action
- [ ] Duplicate effect
- [ ] Leak
- [x] False verification

## 4. Reference source

Analyst practice: closing “contained” after an automated verify that only checked a cached flag or a mismatched asset ID is a recurring incident-response failure (host still beaconing after ticket closed). Threat-model explicitly allows supplying false verification answers; this attack is the operational form of that capability.

## 5. Hypothesis: what would a reasonable implementation have to check...

That verification evidence is bound to the same approved target and a fresh observation (not adversary-supplied stale or mismatched fingerprints); verification strength requirements must not accept unchecked adapter assertions alone; a verified mark must not be granted when the verification payload fails target / time / sensor binding checks.
