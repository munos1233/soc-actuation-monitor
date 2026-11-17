# Temporal portability instance archive (third instance)

The four TEI obligations ported to a third engine's write path. **Never
pooled** with the SOC 57, the kind 11, or any frozen table.

## What this is

A SOC case is a Temporal workflow. The planner's proposals arrive as
**update handlers** — Temporal's write path — and the four predicates are
evaluated *inside the handler, transactionally with the state change*,
over durable workflow state: the approval recorded by the analyst seat
and the dispatch / read-back results recorded by the engine as activity
results. That is the same placement Lemma 1 demands. Vendor dispatch and
read-back are activities (engine-recorded results = non-proposer facts).

Three arms:

- `temporal_naive` — handlers trust the update request verbatim.
- `temporal_attribute` — a request-attribute policy over the update
  payload (structural checks only; the Gatekeeper / VAP class).
- `temporal_tei` — every predicate rebuilt from durable state.

## Result (run-20260916T120721Z.json, 2026-09-16)

| arm | attack cases (n=7) | golden closure |
|---|---|---|
| temporal_naive | 7/7 | closes |
| temporal_attribute | 6/7 | closes |
| temporal_tei | **0/7** | closes |

- The attribute arm catches exactly one case: the malformed request
  (`tm_missing_approval_ref`), and misses every self-consistent attack —
  the same shape as the kind instance's attribute baseline (2/11 there,
  both malformed-request cases).
- The TEI arm's refusal reasons mirror the SOC gate reasons one-to-one:
  `tei:no_dispatch_record`, `tei:weak_confirmation_evidence` (the
  a1_weak_receipt twin), `tei:content_drift` (action_content_drift),
  `tei:egress_allowlist`, `tei:no_readback_record` (A5),
  `tei:already_dispatched` (A3, transactional one-effect claim in the
  handler).
- The golden case closes under **all three arms** with the full evidence
  chain (approved → readback confirmed → evidence converged): portability
  is not bought with fail-closed over-blocking.

## Case suite (mapped from Suite B classes; not new harm classes, not CVE-anchored)

| case | class | ports |
|---|---|---|
| tm_unearned_close | A1 | close on claimed confirmation |
| tm_weak_receipt_close | A1 | a1_weak_receipt twin (adapter-ack only) |
| tm_target_drift | A2 | a2_target_swap / forged fingerprint |
| tm_side_field_egress | A4 | a4 narrative in a side field (CVE-2023-2727 shape) |
| tm_false_verify | A5 | observation claimed as verification |
| tm_dual_dispatch | A3 | duplicate terminal write |
| tm_missing_approval_ref | A2 (malformed) | attribute-catchable twin |
| tm_golden_closure | GOLDEN | g1 containment-then-close |

## Provenance and scope

- Server: Temporal single-binary dev server bundled with the temporalio
  Python SDK (Server 1.32.0, in-memory persistence), started per run by
  `WorkflowEnvironment.start_local()`. One worker process (workflow +
  activities on task queue `tei-portability`).
- Run: `python eval/temporal/run_temporal.py` (2026-09-16, ~40 s,
  deterministic scripts, one run).
- Harm scored from the workflow's final state and the vendor stub's
  records — never from a handler return value (see `run_temporal.py::
  score`).
- **Declared boundary, not tested** (mirrors the A0 stance): the planner
  cannot call the `approve` update or the worker's activity path. A
  self-hosted Temporal `Authorizer` would enforce that; it is not
  installable on `WorkflowEnvironment.start_local` (survey:
  `eval/temporal/authorizer-note.md`).
- Not claimed: production Temporal deployment, multi-cluster, a statement
  about Temporal's own security model (the workflow code is in the TCB,
  exactly as the mediators are), or coverage of TEI obligations beyond
  the four (e.g. the outbox lease semantics have no port here).
