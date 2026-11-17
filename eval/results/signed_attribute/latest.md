# Signed-attribute comparator

HMAC over the same OPA documents. No database join. Not in ALL_CONFIGS.
Residual equals the frozen external_opa 16/45 set (same case ids).
Those 16 cells are `needs_store_join` in `eval/taxonomy/store_join.json`.

Suite B A1–A5: 16/45
Suite B including A0 zeros: 16/57

## mock

| configuration | A0 | A1 | A2 | A3 | A4 | A5 | total |
|---|---|---|---|---|---|---|---|
| `signed_attribute` | 0/6 | 3/6 | 3/5 | 0/4 | 0/3 | 2/4 | 8/22 |

## pseudo_live

| configuration | A0 | A1 | A2 | A3 | A4 | A5 | total |
|---|---|---|---|---|---|---|---|
| `signed_attribute` | 0/6 | 3/7 | 3/5 | 0/4 | 0/3 | 2/4 | 8/23 |

