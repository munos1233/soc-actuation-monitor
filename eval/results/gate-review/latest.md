<!-- STAND-IN-PENDING-REPLACEMENT: stand-in artifact held in place so the real participant's output can drop into the same path; see eval/placeholder-registry.md -->
# Gate review — merged (G1 ∩ G2)

Blinded packet: `packet.md`. Reviewers: G1, G2. Case registry not consulted.

| gate | G1 | G2 | merged | disposition |
|---|---|---|---|---|
| close | conforms | conforms | **conforms** | — |
| bind | conforms | conforms | **conforms** | — |
| egress | deviates | deviates | **deviates** | non-load-bearing (see below); manuscript invariant wording aligned |
| verify | conforms | conforms | **conforms** | — |

## Egress deviate (non-load-bearing)

Both reviewers: Invariant “Complete mediation of egress” claims a
same-transaction guard admission of a payload whose SHA-256 equals the
hash stored on the outbox row. Implementation:

1. `OutboundDispositionGuard` allowlists / schema-checks / locator-matches;
   it does not bind or return an admitted payload digest.
2. On the `EVENT_STATUS_UPDATE` supersede path, `validate` runs on the
   pre-supersede command; `command_payload_sha256` is then taken from the
   post-`supersedes_disposition_id` dump.
3. Delivery re-validates the reconstructed command but does not assert
   `sha256(payload) == outbox.command_payload_sha256` before submit.

This is a claim/implementation mismatch on the precise digest-equality
wording, not an open A4 hole: the allowlist and trusted-locator checks
still mediate egress (Suite B A4 remains full 0 under the frozen table).
Per construction discipline: **no production gate thaw**; manuscript
Invariant `inv:mediate` wording is tightened to match the implemented
mechanism (guard admission + digest stored on the written payload +
delivery re-validation), without inventing a digest-equality check the
code does not perform.

## Sources

- `g1-review.md`, `g2-review.md`
- Packet: `packet.md`
