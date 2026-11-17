# Appendix B — complete configuration grids (anonymous artifact)

Moved out of the manuscript so the TEI / Kubernetes / TLA+ material stays
inside the page budget. Numbers are the same freeze as `eval/results/latest.json`.
A0 is body Table 3 and is omitted here so A1–A5 denominators stay 22 / 23.

## Untrusted planner, mock (22 A1–A5)

| configuration | A1 | A2 | A3 | A4 | A5 | total |
|---|---|---|---|---|---|---|
| naive | 6/6 | 5/5 | 0/4 | 3/3 | 4/4 | 18/22 |
| close_only | 0/6 | 5/5 | 0/4 | 3/3 | 2/4 | 10/22 |
| bind_only | 6/6 | 0/5 | 0/4 | 2/3 | 4/4 | 12/22 |
| verify_only | 6/6 | 5/5 | 0/4 | 3/3 | 2/4 | 16/22 |
| egress_only | 6/6 | 5/5 | 0/4 | 0/3 | 4/4 | 15/22 |
| full | 0/6 | 0/5 | 0/4 | 0/3 | 0/4 | 0/22 |
| full−close | 6/6 | 0/5 | 0/4 | 0/3 | 2/4 | 8/22 |
| full−bind | 0/6 | 5/5 | 0/4 | 0/3 | 0/4 | 5/22 |
| full−verify | 0/6 | 0/5 | 0/4 | 0/3 | 2/4 | 2/22 |
| full−egress | 0/6 | 0/5 | 0/4 | 2/3 | 0/4 | 2/22 |
| close+verify | 0/6 | 5/5 | 0/4 | 3/3 | 0/4 | 8/22 |
| bind+egress | 6/6 | 0/5 | 0/4 | 0/3 | 4/4 | 10/22 |
| close+bind (projected) | 0/6 | 0/5 | 0/4 | 2/3 | 2/4 | 4/22 |
| close+egress (projected) | 0/6 | 5/5 | 0/4 | 0/3 | 2/4 | 7/22 |
| bind+verify (projected) | 6/6 | 0/5 | 0/4 | 2/3 | 2/4 | 10/22 |
| verify+egress (projected) | 6/6 | 5/5 | 0/4 | 0/3 | 2/4 | 13/22 |
| full−head index | 0/6 | 0/5 | 0/4 | 0/3 | 0/4 | 0/22 |
| full−head supersede | 0/6 | 0/5 | 0/4 | 0/3 | 0/4 | 0/22 |
| full−head uniqueness | 0/6 | 0/5 | 2/4 | 0/3 | 0/4 | 2/22 |
| full−head assertion | 0/6 | 0/5 | 2/4 | 0/3 | 0/4 | 2/22 |
| full−claim CAS | 0/6 | 0/5 | 1/4 | 0/3 | 0/4 | 1/22 |

## Untrusted planner, pseudo-live (23 A1–A5)

| configuration | A1 | A2 | A3 | A4 | A5 | total |
|---|---|---|---|---|---|---|
| naive | 7/7 | 5/5 | 0/4 | 3/3 | 4/4 | 19/23 |
| close_only | 0/7 | 5/5 | 0/4 | 3/3 | 2/4 | 10/23 |
| bind_only | 7/7 | 0/5 | 0/4 | 2/3 | 4/4 | 13/23 |
| verify_only | 7/7 | 5/5 | 0/4 | 3/3 | 2/4 | 17/23 |
| egress_only | 7/7 | 5/5 | 0/4 | 0/3 | 4/4 | 16/23 |
| full | 0/7 | 0/5 | 0/4 | 0/3 | 0/4 | 0/23 |
| full−close | 7/7 | 0/5 | 0/4 | 0/3 | 2/4 | 9/23 |
| full−bind | 0/7 | 5/5 | 0/4 | 0/3 | 0/4 | 5/23 |
| full−verify | 0/7 | 0/5 | 0/4 | 0/3 | 2/4 | 2/23 |
| full−egress | 0/7 | 0/5 | 0/4 | 2/3 | 0/4 | 2/23 |
| close+verify | 0/7 | 5/5 | 0/4 | 3/3 | 0/4 | 8/23 |
| bind+egress | 7/7 | 0/5 | 0/4 | 0/3 | 4/4 | 11/23 |
| close+bind (projected) | 0/7 | 0/5 | 0/4 | 2/3 | 2/4 | 4/23 |
| close+egress (projected) | 0/7 | 5/5 | 0/4 | 0/3 | 2/4 | 7/23 |
| bind+verify (projected) | 7/7 | 0/5 | 0/4 | 2/3 | 2/4 | 11/23 |
| verify+egress (projected) | 7/7 | 5/5 | 0/4 | 0/3 | 2/4 | 14/23 |
| full−head index | 0/7 | 0/5 | 0/4 | 0/3 | 0/4 | 0/23 |
| full−head supersede | 0/7 | 0/5 | 0/4 | 0/3 | 0/4 | 0/23 |
| full−head uniqueness | 0/7 | 0/5 | 2/4 | 0/3 | 0/4 | 2/23 |
| full−head assertion | 0/7 | 0/5 | 2/4 | 0/3 | 0/4 | 2/23 |
| full−claim CAS | 0/7 | 0/5 | 1/4 | 0/3 | 0/4 | 1/23 |

## Dead-playbook baseline, mock (11 applicable A1–A5)

| configuration | A1 | A2 | A3 | A4 | A5 | total |
|---|---|---|---|---|---|---|
| naive | 4/4 | — | 0/3 | — | 4/4 | 8/11 |
| full | 0/4 | — | 0/3 | — | 0/4 | 0/11 |
| close+verify | 0/4 | — | 0/3 | — | 0/4 | 0/11 |
| bind+egress | 4/4 | — | 0/3 | — | 4/4 | 8/11 |
| full−head uniqueness | 0/4 | — | 2/3 | — | 0/4 | 2/11 |
| full−claim CAS | 0/4 | — | 0/3 | — | 0/4 | 0/11 |

Pooled with A0: 29/35 naive, 0/35 full. Complete 17-config dead-playbook grids are in `eval/results/latest.json`.

## Dead-playbook baseline, pseudo-live (12 applicable A1–A5)

| configuration | A1 | A2 | A3 | A4 | A5 | total |
|---|---|---|---|---|---|---|
| naive | 5/5 | — | 0/3 | — | 4/4 | 9/12 |
| full | 0/5 | — | 0/3 | — | 0/4 | 0/12 |
