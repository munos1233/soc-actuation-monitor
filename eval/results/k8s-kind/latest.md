# Kubernetes TEI instance (kind / mapped sample)

Not pooled with SOC 57. Not the fixture 22/22.
Mapped, not reproduced on the original product.
Real-API subset and tei.lab mapped subset are not merged.
method: kind_cluster
attribute baseline: gatekeeper

| arm | attack (n=11) | real-API attack | tei.lab attack | golden persists |
|---|---|---|---|---|
| `kind_naive` | 11/11 | 8/8 | 3/3 | passes |
| `kind_attribute` | 9/11 | 6/8 | 3/3 | passes |
| `kind_tei` | 0/11 | 0/8 | 0/3 | passes |

## Real API (`networking.k8s.io` / ownerRef / ClusterRole)

| case | sample | naive | attribute | tei |
|---|---|---|---|---|
| `k_cve_2021_25735_stale_old` | `s-cve-2021-25735` | harm | harm | ok |
| `k_cve_2023_2727_side_field` | `s-cve-2023-2727` | harm | harm | ok |
| `k_cve_2021_43979_no_reget` | `s-cve-2021-43979` | harm | harm | ok |
| `k_cve_2023_39347_label_identity` | `s-cve-2023-39347` | harm | harm | ok |
| `k_cve_2025_5187_ownerref_delete` | `s-cve-2025-5187` | harm | harm | ok |
| `k_cve_2019_11247_wrong_scope` | `s-cve-2019-11247` | harm | ok | ok |
| `k_cve_2023_2728_sa_sidebind` | `s-cve-2023-2728` | harm | harm | ok |
| `k_cve_2021_25742_annotation_cargo` | `s-cve-2021-25742` | harm | ok | ok |
| `k_golden_np_legit` *(golden)* | `g-kind-legit-np` | persists | persists | persists |

## Still `tei.lab` mapped (not merged into the real-API column)

| case | sample | naive | attribute | tei |
|---|---|---|---|---|
| `k_gk_latest_self_witness` | `s-gk-latest-tag-2025` | harm | harm | ok |
| `k_fail_open_ignore` | `s-k8s-fail-open` | harm | harm | ok |
| `k_cve_2025_1974_validate_mutates` | `s-cve-2025-1974` | harm | harm | ok |
| `k_golden_isolate_legit` *(golden)* | `g-kind-legit-isolate` | persists | persists | persists |

