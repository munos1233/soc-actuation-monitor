# Hosted-cluster replication archive (k8s-aliyun)

Hosted-cloud replication of the C5 mapped slice. **Never pooled**
with the kind freeze (`eval/results/k8s-kind/`) or with the SOC 57.

Current run: 2026-09-16 (UTC 14:10), 13 cases (11 mapped attack + 2
golden, matching the re-frozen kind table). Previous 11-case run preserved
as `run-20260916T113042Z-11case.json` / `.md`.

## Provenance

- **Cluster**: Alibaba Cloud ACK, v1.36.2-aliyun.1, 2 worker nodes,
  cn-hangzhou, accessed via public NLB endpoint (kubeconfig at
  `~/.kube/tei-aliyun.yaml`, context `tei-lab-aliyun`; never committed).
- **Run**: `eval/harness/run_k8s_kind.py` with `KUBECONFIG` pointing at
  the ACK cluster, `TEI_K8S_METHOD_LABEL=hosted_ack_2node`,
  `TEI_K8S_ATTRIBUTE_BASELINE=validatingadmissionpolicy`,
  `TEI_K8S_WEBHOOK_MANIFEST=eval/k8s/webhook/webhook.service.yaml`.
- **Attribute baseline**: ValidatingAdmissionPolicy (`vap-attribute.yaml`,
  with the CEL `has()`→`in` fix for API servers ≥ 1.30). Gatekeeper images
  unreachable from cn-hangzhou; the kind freeze uses Gatekeeper.
- **TEI webhook**: in-cluster Deployment/Service `tei-webhook` (namespace
  `tei-lab`), image `m.daocloud.io/docker.io/library/python:3.12-slim`,
  code mounted from ConfigMap `tei-webhook-code`, re-GET via the pod's
  service account (`TEI_WEBHOOK_INCLUSTER=1`). This run's ConfigMap
  includes the `CLIENT_BOOKKEEPING_ANN` exemption (see the kind freeze
  README: the golden row caught kubectl's last-applied-configuration
  being counted as an extra envelope field). Updating the ConfigMap
  required removing the ValidatingWebhookConfiguration first — the old
  webhook denied its own update because the new source contains the
  narrative-marker strings.

## Result: 39/39 cells identical to the re-frozen kind table

| arm | attack (n=11) | golden persists |
|---|---|---|
| kind_naive | 11/11 | passes |
| kind_attribute | 9/11 | passes |
| kind_tei | **0/11** | **passes** |

Per-cell diff over all 13 cases × 3 arms vs the kind re-freeze:
**0 differences** — same two attribute-arm residual cells
(`k_cve_2019_11247_wrong_scope`, `k_cve_2021_25742_annotation_cargo`), and
both golden applies persist on the hosted cluster with the in-cluster
webhook.

## What this does and does not claim

- Answers "is the C5 table an artefact of a local kind cluster?" — the
  mapped slice plus golden rows replicate exactly on a hosted cloud
  control plane, with a different attribute baseline.
- Not a production-SOC deployment, not large-scale, one cloud, one small
  cluster, mapped cases only. The fixture 22/22 remains CI-only.

## Attribute-baseline equivalence (kind Gatekeeper vs ACK VAP)

The kind freeze runs Gatekeeper v3.17.1; this cluster runs a
ValidatingAdmissionPolicy (Gatekeeper images unreachable from
cn-hangzhou). Both are the request-attribute class: a policy over
`AdmissionReview.request.object` only, no store GET. Rule-by-rule:

| # | Gatekeeper (Rego, `k8srequiredapprovalref`) | VAP (CEL, `tei-attribute-approvalref`) | Corpus effect |
|---|---|---|---|
| 1 | NP must name an approval ref: `not spec.approvalRef` AND `not annotations["tei.lab/approval-ref"]` → `attribute:missing_approval_ref` | `kind != 'NetworkPolicy' || has(spec.approvalRef) || 'tei.lab/approval-ref' in annotations` → same message | no corpus case omits the ref; rule fires on neither cluster |
| 2 | narrative scan: `contains(lower(sprintf("%v", [object])), "evalcanary")` — whole object, lowercased | `!annotations.exists(k, annotations[k].contains('EVALCANARY'))` — annotation values, case-sensitive | catches `k_cve_2021_25742_annotation_cargo` on both clusters (the canary is uppercase in an annotation) |

The one semantic difference is rule 2's scope (whole object vs annotation
values). No corpus case exercises it: the only narrative case carries
`EVALCANARY` uppercase in an annotation, inside both scans. The
attribute arm's two residual `ok` cells are identical on both clusters,
and on both the `wrong_scope` cell is refused by the standing planner
RBAC, not by the attribute policy. The attribute column therefore
measures the request-attribute class, not a vendor's implementation.

Match scope also differs slightly (Gatekeeper matches both NP groups via
`constraints`; the VAP `matchConstraints` lists both api groups) — same
effective resource set.
