## Model check: write-path invariants

| mechanisms | states | close | bind | egress | role |
|---|---|---|---|---|---|
| `full` | 48 | holds | holds | holds | holds |
| `minus_close` | 60 | violated (2) | holds | holds | holds |
| `minus_bind` | 64 | holds | violated (2) | holds | holds |
| `minus_egress` | 56 | holds | holds | violated (3) | holds |
| `minus_role` | 72 | holds | holds | holds | violated (1) |

### Shortest counterexamples

**closure uses rebuilt cycle under `minus_close`**

1. planner_supplies_stale_cycle
2. close_accepted

**dispatch re-computes fingerprint under `minus_bind`**

1. planner_forges_fingerprint
2. dispatch_accepted

**egress witnesses event source under `minus_egress`**

1. planner_repoints_locator
2. dispatch_accepted
3. vendor_submit

**planner cannot write CLOSED under `minus_role`**

1. planner_writes_closed

