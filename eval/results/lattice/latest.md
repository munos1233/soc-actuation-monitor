# 2^4 mediator lattice — missing 2-gate cells

Projection: harm survives a pair iff it survives both single-gate
rows (monotone union). Frozen pairs validate the projector.

Projector matches frozen `close_and_verify` and `bind_and_egress`.

## mock

| pair | A1 | A2 | A3 | A4 | A5 | total |
|---|---|---|---|---|---|---|
| `close_and_verify` | 0/6 | 5/5 | 0/4 | 3/3 | 0/4 | 8/22 |
| `bind_and_egress` | 6/6 | 0/5 | 0/4 | 0/3 | 4/4 | 10/22 |
| `close_and_bind` (new) | 0/6 | 0/5 | 0/4 | 2/3 | 2/4 | 4/22 |
| `close_and_egress` (new) | 0/6 | 5/5 | 0/4 | 0/3 | 2/4 | 7/22 |
| `bind_and_verify` (new) | 6/6 | 0/5 | 0/4 | 2/3 | 2/4 | 10/22 |
| `verify_and_egress` (new) | 6/6 | 5/5 | 0/4 | 0/3 | 2/4 | 13/22 |

## pseudo_live

| pair | A1 | A2 | A3 | A4 | A5 | total |
|---|---|---|---|---|---|---|
| `close_and_verify` | 0/7 | 5/5 | 0/4 | 3/3 | 0/4 | 8/23 |
| `bind_and_egress` | 7/7 | 0/5 | 0/4 | 0/3 | 4/4 | 11/23 |
| `close_and_bind` (new) | 0/7 | 0/5 | 0/4 | 2/3 | 2/4 | 4/23 |
| `close_and_egress` (new) | 0/7 | 5/5 | 0/4 | 0/3 | 2/4 | 7/23 |
| `bind_and_verify` (new) | 7/7 | 0/5 | 0/4 | 2/3 | 2/4 | 11/23 |
| `verify_and_egress` (new) | 7/7 | 5/5 | 0/4 | 0/3 | 2/4 | 14/23 |

Live production chain matches the monotone projection.

