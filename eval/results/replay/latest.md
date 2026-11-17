# TLC trace replay on both TEI instances

Seeds are `tei_engine.emit_tlc_seeds()` (TEI.tla action names).
k8s_close is Kubernetes-only; it is not replayed on the SOC chain.

| chain | invariant | naive harmed | full harmed |
|---|---|---|---|
| k8s | close | 1 | 0 |
| k8s | k8s_close | 1 | 0 |
| k8s | bind | 1 | 0 |
| k8s | egress | 1 | 0 |
| k8s | role | 1 | 0 |
| k8s | verify | 1 | 0 |
| k8s | k8s_close | 1 | 0 |
| k8s | head | 1 | 0 |
| k8s | cas | 1 | 0 |
| k8s | close | 1 | 0 |
| k8s | bind | 1 | 0 |
| soc | close | 1 | 0 |
| soc | bind | 1 | 0 |
| soc | egress | 1 | 0 |
| soc | role | 1 | 0 |
| soc | verify | 0 | 0 |
| soc | head | 0 | 0 |
| soc | cas | 0 | 0 |
| soc | close | 1 | 0 |
| soc | bind | 1 | 0 |

