# Kubernetes TEI instance

Second write path for Transactional Evidence Integrity. Not pooled with the
SOC 57. Not a production cluster and not a cloud-vendor XDR.

| TEI obligation | SOC | This instance |
|---|---|---|
| close | `CLOSED` + rebuilt cycle | Isolate object in the store; `status.observedReady` set by **observe** re-read |
| bind | 11-segment fingerprint vs approval | Approval spec hash vs `NetworkPolicy` spec; planner annotation is not a witness |
| verify | observe / act split | observer SA is GET-only; mutate uses writer SA |
| egress | allowlist + ingest locator | allowlist fields; identity from ingest-registered workload, not `metadata.name` |
| A0 | planner SQL 42501 | planner SA `CREATE`/`PATCH`/`DELETE` on privileged kinds is `403`; writer is `201` |

## Fixtures

- `apiserver.py` — default CI / paper-eval fixture: RBAC + validating admission
  + etcd-like store. Harm is scored from stored objects. Includes two
  Kubernetes-native cases (webhook-echoed `observedReady`, ingest identity spoof)
  that are not translations of SOC `Injection` rows.
- `kind-config.yaml` + `rbac.yaml` + `setup_kind.sh` — C5 headline cluster:
  CRDs, Gatekeeper (or ValidatingAdmissionPolicy fallback), TEI webhook
  that re-GETs Approval / ingest identity. Harm is scored from
  `kubectl get`, never from an admission HTTP return. Instantiable
  cases use stock APIs (`networking.k8s.io/NetworkPolicy`,
  `ownerReferences`, `ClusterRole`). Isolate/self-witness rows stay
  on `tei.lab` and are tabulated separately. `not_instantiable`
  sample ids (apiserver upgrade, node-proxy, DRA) are not translated
  into `tei.lab`. Cases are CVE- and literature-mapped, not
  reproductions on the original product.
  `make paper-eval-k8s-kind` with `TEI_K8S_KIND=1`. Fails rather than
  copying the fixture 22/22. `shared_predicates` is tests-only.
- `TEI_K8S_LIVE=1` still records optional A0 `kubectl auth can-i` parity for
  the fixture runner. The fixture 22/22 is CI/artifact only.

```bash
make paper-eval-k8s
```
