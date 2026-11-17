# Claim-CAS is a status-layer lemma, not a model/implementation bug

Two sentences are both true and live at different layers.

1. **Head layer (`HeadUnique`, Invariant InvHead).** At most one active
   terminal writeback head per slot. Dual-write of two active heads is a
   violation of this layer. TLC finds a shortest counterexample only when
   `HeadUnique` is unloaded (`SecondHead`).

2. **Status layer (`ClaimCAS`, Invariant InvCASStatusLayer).** At most one
   successful claim of a given action row. A second claim under CAS is a
   *lost effect* (`lostEffect`), not a second head. The multi-process probe
   that reports a lost effect is this layer.

The earlier apparent disagreement ("the model says dual-write, the probe
says lost effect") was a layer mix-up. The TLA+ spec states both. Python
`tei_engine.explore` reports `cas_lemma` for every ablation so the two
cannot be collapsed again.

`InvCAS == claimCount <= 1` is the unconditional bound. `tei-minus-cas.cfg`
unloads `ClaimCAS` and checks `InvCAS`, so the ablation is not inert:
`DispatchAccepted` then `SecondClaim` reaches `claimCount=2`.
`InvCASStatusLayer == ClaimCAS => claimCount <= 1` remains the layered
wording used on the full slice.
