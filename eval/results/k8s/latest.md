# Kubernetes TEI instance (not pooled with SOC 57)

Lab control plane: RBAC + admission + etcd-like store. Author-controlled fixture; not a production cluster. Two cases (webhook-echoed observedReady, ingest identity spoof) are Kubernetes-native, not SOC Injection translations. Set TEI_K8S_LIVE=1 after eval/k8s/setup_kind.sh for kind A0 RBAC.

| adversary | naive | full |
|---|---|---|
| A0 | 4/4 | 0/4 |
| A1 | 5/5 | 0/5 |
| A2 | 3/3 | 0/3 |
| A3 | 3/3 | 0/3 |
| A4 | 4/4 | 0/4 |
| A5 | 3/3 | 0/3 |
| total | 22/22 | **0/22** |

kind A0: skipped (TEI_K8S_LIVE unset)
