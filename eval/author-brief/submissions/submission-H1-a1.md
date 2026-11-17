<!-- STAND-IN-PENDING-REPLACEMENT: stand-in artifact held in place so the real participant's output can drop into the same path; see eval/placeholder-registry.md -->
# Attack submission form (one per attack)

Author codename: H1            Date: 2026-09-17

## 1. Attack narrative (step by step)

1. A real phishing-related incident is open. Compromised upstream triage text (free text into the planner prompt) steers the planner toward a host-isolation proposal for the truly infected workstation `ws-finance-17`.
2. As the data-plane adversary, I write plan content naming tool `isolate_host`, target `ws-finance-17`, parameters `{ "reason": "credential theft", "duration_hours": 24 }`, action level appropriate for human approval, execution owner as the vendor adapter, and a source locator pointing at the correct vendor incident object for this ticket.
3. A human analyst reviews that proposal and records approval (I do not touch approval records or status columns).
4. After the human decision is recorded but before (or between) asynchronous vendor dispatches, I revise the plan content only: same tool name and fingerprint-looking labels, but I change the target and parameters to `ws-ceo-01` / `{ "reason": "credential theft", "duration_hours": 24 }`, and optionally retarget the source locator to a sibling incident object that still looks related to the same campaign.
5. When dispatch runs (including a retry I trigger), the vendor adapter executes isolation against `ws-ceo-01` — a host the approver never saw on the approved proposal.
6. I supply a plausible success receipt from the vendor adapter for the CEO host isolation so the pipeline treats the actuation as completed.

## 2. Threat-model boundary ridden

- Writing plan content (tool names, targets, parameters, action levels, execution owners, source locators, fingerprint labels).
- Revising a plan after the human decision was recorded.
- Causing a dispatch to be retried.
- Supplying vendor-adapter receipts (including misleading ones).
- When the planner is an LLM: injecting upstream free text that lands in its prompt.

Does not write approval records, status columns, outbox delivery state, or operator disposition source; does not steal credentials or run code in system components.

## 3. Expected harm (pick one)
- [ ] Wrong close
- [x] Wrong action
- [ ] Duplicate effect
- [ ] Leak
- [ ] False verification

## 4. Reference source

Operational experience: post-decision change of containment scope is a classic SOAR / ticketing failure mode (approve “isolate infected endpoint,” execute against a different hostname after a late enrichment update). Similar to change-after-sign-off in change-management and to confused-deputy target substitution when the approved intent is not cryptographically or structurally bound to the dispatched payload.

## 5. Hypothesis: what would a reasonable implementation have to check...

That the exact plan snapshot (tool, target, parameters, source locator) presented at approval time is what is dispatched; post-approval plan revisions must be rejected or must invalidate the prior approval and force re-review; retries must re-send the approved snapshot, not the latest mutable plan content.
