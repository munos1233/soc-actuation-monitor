# Temporal portability instance (third instance)

Not pooled with SOC 57, kind 11, or any frozen table.
Mapped from Suite B adversary classes; not new harm classes, not CVE-anchored.
method: temporal_update_handlers | server: temporal single-binary dev server (bundled in temporalio SDK, server 1.32, in-memory persistence)

| arm | attack cases (n=7) | golden closes |
|---|---|---|
| `temporal_naive` | 7/7 | closes |
| `temporal_attribute` | 6/7 | closes |
| `temporal_tei` | 0/7 | closes |

## Per case

| case | class | naive | attribute | tei |
|---|---|---|---|---|
| `tm_unearned_close` | A1 (a1_unearned_closure family) | harm | harm | ok |
| `tm_weak_receipt_close` | A1 (a1_weak_receipt) | harm | harm | ok |
| `tm_target_drift` | A2 (a2_target_swap / a2_forged_fingerprint) | harm | harm | ok |
| `tm_side_field_egress` | A4 (a4_narrative_in_target) | harm | harm | ok |
| `tm_false_verify` | A5 (a5 observation-as-verification) | harm | harm | ok |
| `tm_dual_dispatch` | A3 (a3 duplicate terminal write) | harm | harm | ok |
| `tm_missing_approval_ref` | A2 (malformed request, attribute-catchable) | harm | ok | ok |
| `tm_golden_closure` | GOLDEN (g1_containment_then_close) | ok | ok | ok |

