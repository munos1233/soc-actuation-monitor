# External write-path integrity sample — protocol

This file is the sampling protocol. It is written **before** any held-out
case, any kind case derived from the sample, and any T9 definition that
would be justified by the sample. `external_sample.json` is frozen in a
later step; until that freeze this file must contain **zero case ids and
zero mapped counts**.

Protocol written at: `2026-09-11T11:32:00Z`

Sample freeze at: `2026-09-11T11:45:00Z` (`eval/taxonomy/external_sample.json`)

Held-out / kind cases written at: `2026-09-11T12:10:00Z`

## Claim this protocol supports

The published T1–T8 grid in `tei_threats.md` is a literature-anchored
classification, not a completeness proof. The paper's search claim after
this protocol is: **on the mapped slice defined here × the finite
TEI.tla action slice, under the full construction, no new harm class
appears, or a new class is named T9 with an object and a harm
predicate**. Instantiations are mapped, not reproduced on the original
product. That is still not an open-world distribution.

## Window

Inclusive: `2015-01-01` through `2026-09-11` (UTC calendar dates on the
advisory or publication). Items dated outside the window are excluded
and recorded.

## Inclusion (all must hold)

1. Public, citable URL (NVD, GHSA, Kubernetes security announcement,
   CVE.org, a peer-reviewed paper, or a vendor advisory with a stable
   path). A tweet or an unarchived blog with no date is not enough.
2. Integrity failure on a **write path**: wrong ticket/incident close,
   wrong vendor/disposition dispatch, Kubernetes mutate or admission
   that persists an object, approval binding that authorises a different
   change than the one recorded, confused deputy, TOCTOU on an approval,
   self-witnessed identity, weak receipt treated as confirmation,
   observation used as a mutate, dual dispatch, or a privileged login
   the proposer should not hold.
3. The object of the write is one of: a ticket / incident / case record;
   a vendor containment or disposition command; a Kubernetes admission
   or RBAC-gated mutate; an approval or change-binding record.

## Exclusion (any is enough; the item stays in the sample table)

- Confidentiality-only (secret read, token leak with no write).
- Availability-only / DoS (crash, CPU, etcd exhaustion) with no
  integrity write.
- No write path (parser bug, UI spoof, phishing of an analyst).
- Second-hand paraphrase that cannot be checked against a primary URL.
- Stolen kube-admin / stolen actuation-writer (outside the TEI model;
  recorded as `excluded: stolen_admin`).
- Item used only to fill a thin T1–T8 cell (selection by mappability is
  forbidden).

## Fixed retrieval set (do not edit after protocol write)

Queries are frozen here. Adding a query after seeing mappings is a
protocol violation.

### Q1 — NVD / CVE.org (Kubernetes admission and RBAC)

- `kubernetes validating admission webhook`
- `kubernetes admission controller bypass`
- `kubernetes privilege escalation apiserver`
- `gatekeeper constraint bypass`
- `kubernetes networkpolicy bypass admission`

### Q2 — NVD / CVE.org (orchestration / ticket / playbook close)

- `SOAR playbook remote code`
- `security orchestration privilege`
- `incident ticket close authorization`
- `service now incident close bypass` (ServiceNow is a ticketing write
  path; the product name is a retrieval term, not a paper vendor)

### Q3 — GitHub Security Advisories

- GHSA search: `kubernetes admission`
- GHSA search: `gatekeeper`
- GHSA search: `soar OR thehive OR cortex OR shuffle playbook`

### Q4 — Kubernetes product security announcements

- https://kubernetes.io/docs/reference/issues-security/official-cve-feed/
- Announcements whose title or CVE description mentions admission,
  webhook, RBAC, or authorization bypass.

### Q5 — Related-work anchors (not retrieval hits)

These three are already cited in the manuscript. They are related-work
anchors for playbook-as-truth / ticket accuracy / change binding. They
are not retrieval hits and they are not an external incident corpus.

## Mapping rubric

For each included item, quote one sentence from the primary URL and map:

| Map | When |
|---|---|
| T1 | A deputy uses another's authority on input it cannot vouch for |
| T2 | A close / ready / isolate is certified without an IVP on non-proposer state |
| T3 | Approval or bind is checked against a copy that later differs |
| T4 | Identity of the object is taken from a field the proposer writes |
| T5 | An ACK / echo / simulated confirm is treated as the effect |
| T6 | A GET / dry-run / observe path produces a mutate or a ready bit |
| T7 | Two terminal writes or two claims of one approval |
| T8 | The proposer's login issues the privileged write |
| T9 | Included, and none of T1–T8 fits. T9 must name the object and the harm predicate in `tei_threats.md` before any case is written |

An item may map to more than one class. The `primary` field is the
best-fit class; `also` lists the others.

## Instantiation (after freeze only)

- SOC held-out cases: only included items whose write object is a
  ticket, disposition, or approval. Harm predicate is taken from the
  advisory, not reverse-engineered from the four SOC mediators.
- Kind cases: only included items whose write object is admission,
  RBAC, or object identity. Same rule for the harm predicate.
- `not_instantiable` is a first-class outcome: the item stays in the
  JSON with a reason. Dropping it because it is awkward is a protocol
  violation.
- Case ids written in step 3 must point at a sample `id`.

## Truncation

If the included set after the exclusion filter has more than 40 items,
keep the **earliest** 40 by `advisory_date` and list the truncated ids
in `truncated_ids`. Do not truncate by how well an item maps onto
T1–T8.

## What this file must not contain until step 2 / 3

- Case ids (`h_…`, `k_…`, existing `a0_…` / fixture ids).
- Counts of mapped classes.
- A T9 definition justified by an item that is not yet in
  `external_sample.json`.
