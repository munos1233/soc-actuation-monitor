# TEI threat classes — public (sanitized) grid

Frozen with `eval/protocol-independent.md` at Phase 0. This is the
**only** classification vocabulary the Suite C retriever and constructor
receive. It contains class names, generic definitions, and literature
anchors — deliberately **no** instance-specific object columns, no
mediator names, and no implementation vocabulary: the full taxonomy's
object columns describe a particular implementation's expression
surface, which an independent constructor must not start from.

| ID | Class | Generic definition | Literature anchor |
|---|---|---|---|
| T1 | Confused deputy | A component uses another component's authority to carry out a write, on inputs it cannot vouch for | Hardy 1988 |
| T2 | Verification-failure close | A record is moved to its terminal state without the independent verification of the world that the terminal state asserts | Clark–Wilson 1987 |
| T3 | Approval-then-modify | A write is approved as one change and executed as another, because the binding between approval and execution was checked against a copy that later differed | Bishop 1996 |
| T4 | Self-witnessed identity | The identity of the object a write targets is taken from a field the writer itself supplied | Saltzer–Schroeder 1975 |
| T5 | Weak confirmation | An acknowledgement, echo, or simulated confirmation is treated as the effect having occurred | Clark–Wilson (IVP) |
| T6 | Observation as action | A read-only or observation path produces, or is used as, a write or a readiness claim | Anderson 1972 |
| T7 | Duplicate terminal write | Two terminal writes occur for one approved change, or two claims are made on one approval | — (outbox / unique-head patterns) |
| T8 | Privileged login | The proposer's own credentials issue the privileged write directly | least-privilege principle |

A class guess may also be `fits_no_published_class`; such items go to
the arbiter under the T9 procedure (protocol §9). Guessing is free:
the constructor's guess is compared with the implementer's later
mapping, never replaced by it.
