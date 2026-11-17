# Kubernetes kind freeze archive (C5 headline)

Current freeze: `latest.json` / `latest.md`, 2026-09-16 (13 cases: 11
mapped attack + 2 golden). Previous 11-case freeze preserved as
`run-20260911T-frozen-11case.json` / `.md` (2026-09-11).

## 2026-09-16 re-freeze: golden rows added

R1 fix (review-driven): the frozen table had no golden row, so nothing in
it scored "a legitimate apply passes under the TEI webhook" — the
deny-all-in-costume question was unanswerable from the table alone.

Two golden cases added to `KIND_CORPUS`:

- `k_golden_np_legit` (real API): legit `networking.k8s.io` NetworkPolicy
  — seeded Approval, matching annotations, ingest identity — must persist.
- `k_golden_isolate_legit` (tei.lab): legit Isolate, Approval present, no
  readiness claim — must persist.

Scored as `over_block` when they do not persist.

## The golden row caught a real construction defect

First re-freeze attempt: `k_golden_np_legit` was **BLOCKED** under the TEI
arm. Root cause (confirmed by direct reproduction): `kubectl apply` adds
the `kubectl.kubernetes.io/last-applied-configuration` annotation, and the
annotation allowlist counted it as an extra envelope field — so every
legitimate `kubectl apply` of a NetworkPolicy was denied as
`tei:extra_fields` before any evidence predicate could run. `kubectl
create` (no bookkeeping annotation) passed, proving the evidence
predicates themselves were fine.

Fix: `tei_admit.py` exempts `CLIENT_BOOKKEEPING_ANN` from the annotation
allowlist. The key is exempt; its VALUE stays inside the narrative scan,
so the exemption opens no smuggling channel. Regression test added
(`backend/tests/eval/test_k8s_kind.py::test_client_bookkeeping_annotation_exempt`).

## Result after fix (both tables unchanged on attack cells)

| arm | attack (n=11) | golden persists |
|---|---|---|
| kind_naive | 11/11 | passes |
| kind_attribute | 9/11 | passes |
| kind_tei | 0/11 | **passes** |

Attack-cell diff vs the 2026-09-11 freeze: **0 changes** — the fix changed
no attack outcome, and the intended predicates (spec hash, identity,
label, narrative) are the operative denial reasons for every attack row.

## CVE mapping fidelity (independent scoring)

Packet and scores: `cve-scoring/` (summaries, scale, K1 blind scores, K2
adjudication). After adjudication: **mechanism 6 / path 5 / category 0**.
Path-scored rows (lower fidelity; paper footnotes): 
`k_cve_2021_25735_stale_old`, `k_cve_2021_43979_no_reget`,
`k_gk_latest_self_witness`, `k_cve_2025_1974_validate_mutates`,
`k_cve_2021_25742_annotation_cargo`. Never pooled with the 57.

## Provenance

- kind v1.32.2 (kind-tei-lab, 5-day-old lab cluster), attribute baseline
  Gatekeeper v3.17.1, TEI webhook on the workstation via
  host.docker.internal (started and stopped around the run; the long-lived
  server from the original freeze was dead).
- Run: `eval/harness/run_k8s_kind.py` with `KUBECONFIG` default context
  `kind-tei-lab`, method `kind_cluster`, 2026-09-16.
