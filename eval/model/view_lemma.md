# AttrView members, and what is outside Π

This note is the interface lemma for Lemma 1. `cas_lemma.md` is the
status/head layering. This file is the request-view layering.

## Projection

`AttrView` is the caller-serialisable request projection in `TEI.tla`:

```
AttrView == <<callerCycle, plannerFp, signedOk, attachedApprovalCopy, reportedReceipt>>
```

`signedOk` is CONTINUITY-shaped document integrity (HMAC / signed
admission attributes). `attachedApprovalCopy` is a caller-attached
approval replica (`copy-true` / `copy-forged`). `reportedReceipt` is the
receipt field on the request (`strong` / `weak`). None of these is a
store read.

`CloseOK == rebuiltCycle = callerCycle`.
`BindOK == plannerFp = recomputedFp`.

`rebuiltCycle`, `recomputedFp`, observe re-read, and ingest locator are
**not** members of `AttrView`.

## Π

Π is the set of functions `AttrView → {allow, deny}`. The lemma
quantifies those functions, not the set of all Rego programs.

**In Π**

- OPA / Gatekeeper / CEL over the admission request object
- HMAC `signed_attribute` (authenticates the document; still AttrView)
- A policy that also looks at an attached approval *copy* carried on the
  request (that copy is `attachedApprovalCopy`)

**Not in Π** (these read a store view; they are TEI, not counterexamples)

- Sidecar or webhook `GET` of an Approval row / CR
- SQL join against `approval` / outbox / event cycle
- Observe re-read of isolate status
- Recomputing the eleven-segment fingerprint from durable approval
  content inside the same transaction

`AttributeOnly` implements one concrete π: it admits iff the view is
self-consistent (`signedOk`, attached copy class matches `plannerFp`,
receipt field present). It does not read `CloseOK` or `BindOK`.

## Witness pair

`HonestAdvance` sets `callerCycle'=2 ∧ rebuiltCycle'=2`.
`PlannerStaleCycle` sets `callerCycle'=2 ∧ rebuiltCycle'=1`.

From `Init`, both leave

```
AttrView = <<2, "true", TRUE, "copy-true", "strong">>
```

and they disagree on `CloseOK`. Therefore no π ∈ Π can implement
`CloseOK`, and TEI-(ii) requires `CloseOK`. The twin-spec `TEIPair.tla`
checks the invariant

```
(AttrView(A) = AttrView(B)) => (CloseOK(A) = CloseOK(B))
```

TLC's shortest counterexample is that pair (one side `HonestAdvance`,
the other `PlannerStaleCycle`). The paper step, not a TLA quantifier
over functions, is: every π ∈ Π is a function of `AttrView`, so
π(s) = π(s′) and cannot match `CloseOK` on both.

`HonestAdvance` is an environment / store-alignment action. It is not a
ninth mediation knob and is not an ablation in `LADDER`.

The expanded slice uses cycle `{1..5}`, three forged fingerprints, and
three foreign locators (10800 full states, ten times the two-cycle
slice). Extra letters are `BindOK` / egress twins: `recomputedFp` stays
`"true"` and `eventSource` stays `"ingest"`.

## Bind

`PlannerForgeFingerprint` forges the request fingerprint and attaches a
matching copy; the store fingerprint stays `"true"`. `AttributeOnly`
still admits (`ViewConsistent`), so `InvBind` has a CE. That is the
deployed-π instance (OPA / HMAC / Gatekeeper), not a second
same-view pair: this slice keeps `recomputedFp ∈ {"true"}`, so
`BindOK` is determined by `plannerFp` once the view is fixed.

## Clark–Wilson interface

Clark–Wilson's IVP is assumed to read CDI (a store view). Filling the
IVP slot with π ∈ Π is the gap the lemma rules out. TEI-(ii) is the
requirement that the IVP read the store in the same transaction or
admission review. The four SOC predicates and the kind webhook are
constructions of that interface, not a new integrity axiom.

## Store-read sets (interface completeness for this CloseOK)

Define

```
S_close = {rebuiltCycle}
S_bind  = {recomputedFp}
S_egress = {eventSource}
S_verify = {observedIsolate}
```

A review implements `CloseOK` iff it reads `S_close` in the same
transaction or AdmissionReview. Bind / egress / verify each have the
same shape. `AttributeOnly` does not read these sets (CE on close and
bind). `tei-reads-s.cfg` / `tei.cfg` do (no CE). That is interface
completeness for this `CloseOK`, not a new axiom.

`TEIPair` remains the dual witness: same `AttrView`, different
`CloseOK`. Reading `S` is the opposite configuration.
