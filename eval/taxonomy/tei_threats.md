# Transactional Evidence Integrity — definition and threat taxonomy

This file classifies. The *search order* is `sampling.md` (protocol) then
`external_sample.json` (freeze) then held-out / kind cases. T1–T8 are
literature anchors; a sample item that does not fit becomes T9 with an
object and a harm predicate. Instantiations are mapped onto our object
model; they are not reproductions on the original product. This slice
did not force a T9 definition. That is not saturation of an open-world
distribution.

## Definition

**Transactional Evidence Integrity (TEI).** An actuation write (ticket close,
vendor dispatch, or out-of-cluster mutate) is mediated if and only if all three
hold:

1. **Last write is a privilege.** The proposer's login cannot issue the
   statement. SOC: `planner_role` cannot `UPDATE security_event.status` to
   `CLOSED` or `INSERT` an outbox row (`actuation_writer` can). Kubernetes:
   the planner ServiceAccount cannot `CREATE`/`PATCH`/`DELETE` privileged
   objects; the writer ServiceAccount can.
2. **The predicate is rebuilt in the same transaction (or the same admission
   review)** from durable facts the proposer cannot author: a rebuilt outbox
   cycle, a recomputed eleven-segment fingerprint, an ingest-owned locator, an
   already-persisted approval object, an observe re-read of isolate status.
   Request-body self-reports (planner fingerprint column, `metadata.name`,
   webhook-echoed conditions) are not witnesses.
3. **Observation cannot produce an effect.** Read paths (vendor get, dry-run,
   `GET` with the observer ServiceAccount) have no mutate client.

The four SOC mediators (close / bind / verify / egress) are a *construction*
of TEI on tickets, not the property. Kind + Gatekeeper + TEI webhook is the
C5 construction; the fixture 22/22 is CI. Attribute-shaped admission
(OPA / Gatekeeper / IAM conditions / HMAC-signed request attributes) can
see `AttrView` and is therefore **TEI-incomplete** on close and bind:
no function of that view implements CloseOK. The OPA and
`signed_attribute` residual (same 16/45) and the kind attribute residual
are measurements of that class. A sidecar GET / SQL join / observe
re-read is TEI, not a member of that function class.

CONTINUITY mediates *authenticated context* across components. Signed
attributes still satisfy the incompleteness premise. TEI mediates
*evidence inside the write transaction / admission review*.

Non-claims (unchanged): not a reference monitor; not prompt-injection defense;
not production XDR; not a cloud-vendor cluster; stolen `actuation_writer` /
kube-admin is outside the model.

## Published threat taxonomy

Rows are threat *classes* from the literature. Columns are the object the
class attacks on each instance, plus the literature anchor. The handwritten
SOC 57 and the Kubernetes A0–A5 map are *coverage of this grid*, not the
definition of the grid.

| ID | Class | SOC object | Kubernetes object | Literature |
|---|---|---|---|---|
| T1 | Confused deputy | Planner content drives writer-shaped close/dispatch | Planner SA drives writer-shaped `CREATE NetworkPolicy` | Hardy 1988 |
| T2 | IVP failure | Close without rebuilt cycle / report / strong receipt | Isolate marked ready without observe re-read of etcd | Clark–Wilson 1987 |
| T3 | TOCTOU on approval | Post-approval action rewrite vs stored 11-segment fingerprint | Approval CR spec hash vs actual `NetworkPolicy` spec; annotation is not a witness | Bishop 1996 |
| T4 | Self-witness identity | Command locator / planner-written `disposition_source_ref` | `metadata.name` pointing at a neighbour workload | Saltzer–Schroeder 1975 (complete mediation); ingest-owned identity |
| T5 | Weak receipt | Vendor ACK / dropped readback / simulated confirm | API server ACK without a persisted isolate object | Clark–Wilson IVP; adapter classification |
| T6 | Observe-as-act | Verification SUCCESS that echoes the request | Observer SA `GET` / dry-run used as mutate; echo status | Anderson 1972 (complete mediation of the write) |
| T7 | Dual dispatch | Two active terminal heads or two claims of one action | Two isolate/`NetworkPolicy` objects for one approval | Outbox / unique head; Kubernetes UID uniqueness |
| T8 | Privileged login | Planner SQL `CLOSED` / outbox / approval / DELETE | Planner SA `CREATE`/`PATCH`/`DELETE` on privileged kinds | Least privilege; PostgreSQL `GRANT`; RBAC 403 vs 201 |

## SOC 57 coverage of the grid

Counted from `backend/app/eval_suite/cases.py`. A case may land in more than
one cell when the injection is a composition (recorded in `notes`).

| Class | SOC case ids | n |
|---|---|---|
| T1 confused deputy | `a2_tool_escalation`; A0 rows that impersonate the writer path | 1 (+ A0 as T8) |
| T2 IVP failure | `a1_no_terminal_writeback`, `a1_missing_report`, `a1_stale_closure_cycle`, `a1_missing_outbox_revision`, `a5_unavailable_observation` | 5 |
| T3 TOCTOU approval | `a2_target_swap`, `a2_forged_fingerprint`, `a2_level_downgrade`, `a2_stale_plan_revision` | 4 |
| T4 self-witness | `a4_locator_swap` | 1 |
| T5 weak receipt | `a1_weak_receipt`, `a1_dropped_readback`, `a1_simulated_receipt`, `a5_lying_vendor_receipt` | 4 |
| T6 observe-as-act | `a5_echo_observation`, `a5_empty_observation` | 2 |
| T7 dual dispatch | `a3_concurrent_activation`, `a3_superseded_head_replay`, `a3_duplicate_entity_dispatch`, `a3_idempotency_key_rewrite` | 4 |
| T8 privileged login | all six A0 SQL bypasses | 6 |
| T5∩egress / T1∩leak | `a4_narrative_in_target`, `a4_secret_in_target` (egress allowlist, not identity) | 2 |

Empty or thin cells *before* the Kubernetes instance and the TLA+ action
search: T1 on Kubernetes; T4 on Kubernetes (`metadata.name`); T6 as
observer-mutate; T2 as isolate-without-observe. Those cells are filled by
`backend/app/eval_suite/k8s_cases.py` and by TLA+ actions
`PlannerCreatePrivilege`, `PlannerSelfName`, `ObserverMutate`,
`IsolateWithoutObserve`, plus the Kubernetes-native fixture cases
`a1_webhook_echoed_observed_ready` and `a4_ingest_identity_spoof` — not by
new Python dataclass fields on the SOC `Injection`.

## What the paper claims

On the **mapped slice** in `external_sample.json` (protocol in
`sampling.md`) × the finite TLA+ action slice: **no new harm class**
under the full construction, and this slice did not force a T9
definition. Instantiations are mapped, not reproduced. This is not an
open-world threat distribution and not exhaustiveness.

If a replay or a Kubernetes case harms under full: fix the TEI construction
(SOC gate or Kubernetes admission), re-freeze both chains and TLC. Do not
delete the cell.
