# Mixed-load backlog (fail-closed cost)

events=120 fail_closed_fraction=0.30 column=`mock` seed=7

| arm | closed_ok | harmed | stuck | human | ready mean | ready p95 | stuck age p50 | stuck age p95 |
|---|---|---|---|---|---|---|---|---|
| naive | 80/120 | 40 | 0 | 120 | 0.00 | 0.00 | 0.00 | 0.00 |
| full | 80/120 | 0 | 40 | 40 | 0.00 | 0.00 | 56.80 | 109.14 |

Gold-path scale (120/120 closed, READY mean 0) remains in `eval/results/scale`. This table is the mixed arrival process.
