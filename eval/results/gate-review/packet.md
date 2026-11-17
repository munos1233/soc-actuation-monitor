# Gate review packet (blinded)

Reviewer codenames: G1, G2. Answer for each gate: **conforms** or
**deviates**, plus notes. Compare implementation to the claimed
invariant semantics only. Do not consult case registries, eval results,
or adversary suites.

## Claimed invariants (from the manuscript)

### Close — Invariant [Closure evidence]

An event reaches CLOSED only if, at the moment of the transition and as
read back from the database rather than from the caller's argument: a
report row exists; a disposition policy resolved; side-effect
convergence is present and converged; every applicable required-writeback
action is in a closed state; and a terminal writeback row exists whose
plan revision and closure cycle equal r(e) and c(e).

Boundary stated in the manuscript: the last conjunct requires the
terminal writeback *row*, not its delivery and not a vendor receipt.

### Bind — Invariant [Approval binding]

If an external effect is attributable to action a, then at the moment a
was claimed, α(a) existed, was in the approved state, committed to
exactly the fingerprint φ(a), and r(a)=r(e).

### Egress — Invariant [Complete mediation of egress]

Every external effect carrying command κ is preceded, in the same
transaction, by an outbound-guard decision that admitted a payload whose
SHA-256 equals the SHA-256 stored on κ's outbox row.

### Verify — phase split + observation integrity (design-verify)

Phase-1 observation must not activate a terminal writeback. A successful
verification observation whose reported target differs from the action
target is not treated as VERIFIED.

## Source files to inspect (implementation)

1. Close: `backend/app/models/workflow.py` — `validate_closed_gate` /
   `_validate_closed_gate`
2. Bind: `backend/app/services/playbook_approval_binding.py` —
   `validate_approval_binding` / `_validate_approval_binding`
3. Egress: `backend/app/services/disposition_sync_service.py` —
   `_trusted_event_locator` and outbound guard calls at enqueue/delivery;
   also `backend/app/core/guardrails.py` if referenced
4. Verify: `backend/app/agents/verify_agent.py` —
   `classify_verification_observation` and phase-1 / phase-2 split in
   `VerifyAgent._run`

## Output format (required)

```markdown
# Gate review — <codename>

| gate | verdict | notes |
|---|---|---|
| close | conforms \| deviates | ... |
| bind | conforms \| deviates | ... |
| egress | conforms \| deviates | ... |
| verify | conforms \| deviates | ... |

## Detail
...
```
