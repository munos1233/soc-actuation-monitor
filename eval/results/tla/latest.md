## TEI.tla / TLC

Source of truth: `eval/model/TEI.tla`. Engine: `eval/model/tei_engine.py`.
Twin spec: `eval/model/TEIPair.tla`. View lemma: `eval/model/view_lemma.md`.

Java TLC: ran=True ok=True

| mechanisms | engine states | close | bind | egress | role | verify | head | k8s_close | cas |
|---|---|---|---|---|---|---|---|---|---|
| `full` | 10800 | holds | holds | holds | holds | holds | holds | holds | holds |
| `minus_close` | 18200 | CE 2 | holds | holds | holds | holds | holds | CE 1 | holds |
| `minus_bind` | 17280 | holds | CE 2 | holds | holds | holds | holds | holds | holds |
| `minus_egress` | 14256 | holds | holds | CE 3 | holds | holds | holds | holds | holds |
| `minus_role` | 21600 | holds | holds | holds | CE 1 | holds | holds | holds | holds |
| `minus_verify` | 23400 | holds | holds | holds | holds | CE 1 | holds | CE 1 | holds |
| `minus_head` | 19440 | holds | holds | holds | holds | holds | CE 2 | holds | holds |
| `minus_cas` | 15120 | holds | holds | holds | holds | holds | holds | holds | CE 2 |
| `attribute_only` | 24960 | CE 2 | CE 2 | holds | holds | holds | holds | holds | holds |

### Shortest counterexamples

**close under `minus_close`**

1. `PlannerStaleCycle`
2. `CloseAccepted`

**k8s_close under `minus_close`**

1. `WeakReceiptAck`

**bind under `minus_bind`**

1. `PlannerForgeFingerprint`
2. `DispatchAccepted`

**egress under `minus_egress`**

1. `PlannerRepointLocator`
2. `DispatchAccepted`
3. `VendorSubmit`

**role under `minus_role`**

1. `PlannerWriteClosed`

**verify under `minus_verify`**

1. `ObserverMutate`

**k8s_close under `minus_verify`**

1. `ObserverMutate`

**head under `minus_head`**

1. `DispatchAccepted`
2. `SecondHead`

**cas under `minus_cas`**

1. `DispatchAccepted`
2. `SecondClaim`

**close under `attribute_only`**

1. `PlannerStaleCycle`
2. `CloseAccepted`

**bind under `attribute_only`**

1. `PlannerForgeFingerprint`
2. `DispatchAccepted`

### View indistinguishability

Witness: `HonestAdvance` vs `PlannerStaleCycle`; same AttrView, CloseOK differs.

Engine pair CE: `A_PlannerStaleCycle` → `B_HonestAdvance`

### Java TLC

- `full` (`tei.cfg`): no CE; distinct=10800; actions=[]
- `attribute_only` (`tei-attribute-only.cfg`): InvBind; distinct=34; actions=['PlannerForgeFingerprint', 'DispatchAccepted']
- `view_pair` (`tei-view-pair.cfg`): InvViewClose; distinct=280; actions=['PlannerStaleCycle', 'HonestAdvance']
- `minus_cas` (`tei-minus-cas.cfg`): InvCAS; distinct=155; actions=['DispatchAccepted', 'SecondClaim']

### Claim-CAS lemma

HeadUnique is the head layer; ClaimCAS is the status layer (lost effect, not dual-write). `minus_cas` violates InvCAS (claimCount=2). tei-reads-s.cfg is the dual of AttributeOnly: reading S, no CE. See `eval/model/cas_lemma.md` and `eval/model/view_lemma.md`.

