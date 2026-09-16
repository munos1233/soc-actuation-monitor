# Independent verification suite (Suite C) — pre-registered protocol

Status: **APPROVED (FROZEN) — 2026-09-16.** This file is frozen; any
later change is a dated entry under §16 (Amendments) that must not
rewrite history. It was written and approved **before** any v2
retrieval, any Suite C narrative, any harm predicate, and any case.

| | |
|---|---|
| Protocol drafted at | `2026-09-16T15:20:00Z` (agent, v1 draft) |
| Revised at | `2026-09-16T15:55:00Z` (agent, v2: incorporates two independent adversarial reviews — a methodology review and a constructor-simulation review — both archived under `eval/protocol-reviews/`) |
| Arbiter approval | **2026-09-16T23:36:32+08:00** — approved by the arbiter (manuscript author) in session: "批准，本地commit吧" |
| Freeze evidence | local git commit (self-attested timestamp; limit acknowledged in §14). Commit hash recorded in `eval/protocol-reviews/freeze-record.md`, created immediately after the approval commit so this file itself is never edited post-freeze. |

The arbiter's approval is the **sole basis** for any "pre-registered"
claim about Suite C in the manuscript. Without a dated approval above,
no such claim may be made.

## 1. Purpose and the claim this protocol supports

The main suite (57) and the existing held-out (14) were constructed by
the paper's authors against the authors' own object model, and
`heldout_cases.py` says so in its header: those rows retag implemented
`Injection` knobs. A reviewer is entitled to ask whether the evaluation
can say anything about cases whose construction did not start from the
implemented knobs. Suite C exists to answer that question.

The claim this protocol supports, and the only claim it supports:

> Under the pre-registered rules below, within the retrieval space the
> frozen queries of §5 define, a suite whose narratives and harm
> predicates were authored from primary sources — by agents that did not
> see the implementation, the implemented knobs, or the v1 mappings — is
> run in full on the production chain; every well-formed case and every
> cell is reported; and any full-configuration harm is handled by the
> standing discipline (§11), not by deletion.

This is not a claim of organizational independence (§13), not a claim of
open-world coverage, and not a claim about any product named in a
primary source.

## 2. Scope and non-goals

**In scope**: SOC-side mapped cases (Suite C) over ticket / disposition /
approval write objects, run on the production chain (mock and pseudo-live
columns where the case is expressible), scripted planner, `naive` vs
`full`.

**Out of scope (non-goals, each governed elsewhere)**:

- The Kubernetes independent slice (kind Suite C) — separate phase; if
  run, it requires a dated amendment (§16) with its own queries.
- Language-model planner arms over Suite C — **explicitly deferred**;
  cases are built now, LLM runs happen later under a single consolidated
  execution, and nothing in this protocol licenses an LLM-arm claim.
- The seventeen-configuration grid and leave-one-out decomposition over
  Suite C — **excluded** from this protocol; if run later, a dated
  amendment must pre-register which configurations and why.
- The mutation suite, the golden-path expansion, and any change to the
  frozen 57 / held-out 14 / kind 13.

Suite C cases live in their own table
(`backend/app/eval_suite/suite_c_cases.py`), are **never pooled** with
the 57, the held-out 14, the kind 13, or any frozen headline, and are
reported in their own table in the manuscript.

## 3. Roles, inputs, and auditable separation

Four roles. Roles 1–3 are executed by agents; **the complete prompt given
to each role agent is itself a frozen artifact** (`eval/protocol-reviews/
role-prompts/`, one file per role per phase), so a reviewer can verify
exactly what each agent was and was not given. Role separation is
enforced by prompt content and verified by the freeze trail (each
phase's outputs are timestamped before the next phase's inputs are
prepared). This is process separation, not organizational isolation —
§13 states the limit.

| Role | Allowed inputs | Barred inputs (until the role's own phase ends) |
|---|---|---|
| 1. Retriever | §5 queries, `taxonomy-grid-public.md` (§3.1) | `external_sample.json` (the v1 sample and its mappings), `cases.py`, `heldout_cases.py`, `chain.py`, any case or result file |
| 2. Constructor | the primary-source URLs of included items, `taxonomy-grid-public.md`, this protocol | everything in the implementation (`chain.py`, `cases.py`, `heldout_cases.py`, `suite_c_cases.py`), the v1 sample's class mappings, the implementer's output, the SOC-object and Kubernetes-object columns of the full taxonomy |
| 3. Implementer | the frozen constructor output, the implementation, this protocol | primary sources beyond the frozen narrative (it binds what the constructor wrote; it does not re-research) |
| 4. Arbiter (human) | everything; all arbiter feedback is recorded verbatim in `arbiter_log.md` | — |

An agent that has already acted in one role on a given item does not act
in another role on that item. The implementer may **not** alter a
narrative or a harm predicate; disagreements are recorded (§8), not
resolved by editing the constructor's text. Arbiter review of Phase 2
happens **after** the phase-2 freeze is on disk, so feedback cannot
alter frozen narratives (it can only reject the phase, which is logged).

### 3.1 The sanitized public grid

`eval/taxonomy/taxonomy-grid-public.md` is the class table with
**class name, generic definition, and literature anchor only** — no
SOC-object column, no Kubernetes-object column, no mediator names, no
implementation vocabulary. It is frozen with this protocol and is the
only taxonomy the retriever and constructor receive. The full
`tei_threats.md` remains the paper's document; the constructor sees the
sanitized grid because the full grid's object columns describe the
implementation's expression surface, which is exactly what the
constructor must not start from.

## 4. Phase order and freeze gates

Each phase ends in a freeze with a UTC timestamp; the next phase may not
begin before the previous freeze exists on disk. The JSON freeze
(`external_sample_v2.json`) is **append-only across phases**: Phase 2
adds fields to Phase-1 rows but never edits a Phase-1 field; Phase 3
likewise adds and never edits. Every phase's freeze layer is
machine-checkable (fields carry `phase{n}_frozen_at` timestamps).

| Phase | Output | Frozen as | Gate |
|---|---|---|---|
| 0 | This protocol + sanitized grid + role prompts | these files | **arbiter approval (human)** |
| 1 | v2 retrieval log | `external_sample_v2.json` (retrieval fields) | agent freeze, logged |
| 2 | Narratives + expected harm predicates + class guesses (every included item, no exceptions) | same file, `suite_c` fields | agent freeze, then **arbiter review** (T9 dispositions decided here, per item) |
| 3 | Case table (bound, boundary-recorded, or not-instantiable) | `suite_c_cases.py` | agent freeze, then arbiter review |
| 4 | Evaluation run | `eval/results/suite_c/` | never pooled; every result row records the code commit hash |

Phase 2 output for **every** included item is mandatory — including
items the implementer will later mark `not_instantiable`. Writing
narratives only for items that look easy to bind is a protocol violation
(the constructor cannot see the implementation, so "easy to bind" is not
a thing the constructor could know anyway).

## 5. Retrieval (v2): window, frozen queries, execution rules

**Window**: `2015-01-01` through `2026-09-16` (UTC date of publication
of the primary source; for NVD, the CVE **published** date, not the
modified date). Items dated outside are excluded and recorded.

Every query below is a frozen triple: **engine, exact query string,
depth**. A query is executed exactly once, as written. Adding, rewording,
or dropping a query after retrieval begins is a protocol violation. A
query that returns nothing is a result, not a reason to reword.

**Execution rule (all engines)**: examine the first **50** results in
the engine's default relevance order (for index pages: the index page
plus up to **3** pages of its pagination); each examined result goes to
the §6 filter and is logged with its verdict. Results beyond the depth
cut are not examined and are not logged.

### R1 — NVD keyword search (engine: https://nvd.nist.gov/vuln/search)

- `service desk automation close ticket`
- `ITSM change request approval bypass`
- `workflow engine authorization bypass ticket`
- `remediation playbook unauthorized action`

### R2 — Vendor advisory indexes (engine: each vendor's official security-advisory index page, by URL)

Scan the advisory list at each URL (index page + up to 3 pagination
pages); an advisory is a **hit** iff its title or summary contains any
of the terms `automation`, `playbook`, `workflow`, `approval`, or
`authorization`:

- https://advisory.splunk.com/ (SOAR advisories)
- https://security.paloaltonetworks.com/ (Cortex XSOAR advisories)
- https://msrc.microsoft.com/update-guide (Sentinel / Defender
  automation rules; filter view: Microsoft Sentinel)
- https://trust.servicenow.com/security-advisories (workflow / approval)

### R3 — Public incident retrospectives (engine: a general web search engine; first-party postmortems only — the hit must link the operator's own domain or an archival copy)

- `automation outage retrospective postmortem unauthorized change`
- `maintenance command outage postmortem audit tool`
- `automated runbook wrong target incident report`
- `configuration deployment validator bug postmortem`

### R4 — Academic literature (engine: ACM Digital Library for all four strings, chosen for stable indexing and open abstracts)

- `SOAR case study failure`
- `security automation incident case study`
- `playbook misexecution report`
- `security orchestration empirical study`

### R5 — GitHub Security Advisories (engine: https://github.com/advisories search)

- `ticket authorization`
- `workflow approval`
- `thehive`
- `socless`
- `demisto`

### R6 — Non-security-vocabulary write-path integrity (engine: NVD
keyword search + a general web search engine, one pass each; these probe
whether write-path integrity failures exist outside the security domain
— ITSM, enterprise workflow, business-process records — so the query
space is not pre-baked onto security vocabulary)

- `change request closed without approval`
- `workflow record integrity violation audit`
- `business process authorization bypass state change`

**Item cap**: after filtering (§6), if more than **12** items qualify,
keep the earliest 12 by `advisory_date` (ties: lexicographic by `id`)
and list the remainder in `overflow_ids`. Twelve is the labor bound this
protocol pre-registers for the phased, role-separated pipeline; it is
**not** a power calculation and the manuscript may not present it as
one. Selection by apparent mappability is forbidden. If fewer than 12
qualify, run all and record the shortfall — padding is a violation.

## 6. Filter (source-form gate, write-object gate, event-shape gate; counts logged)

Applied by the retriever to each logged hit, **in this order**, stopping
at the first failed gate. The filter never looks at which class an item
might fit; the event-shape gate is stated structurally, without class
vocabulary. Every hit stays in the log with the gate that excluded it.

**Gate A — source form** (all must hold):

1. A public, citable URL with a publication date: NVD / CVE.org / GHSA,
   a vendor advisory with a stable path, a first-party retrospective on
   the operator's own domain, or a peer-reviewed paper (an open abstract
   containing the relevant event detail is sufficient; the full text
   need not be accessible).
2. Not a tweet, forum post, or undated blog.

**Gate B — write object** (hard gate, checked before the event shape;
an item whose write object is not one of these three is excluded as
`excluded: write_object_out_of_scope` and stays in the log — including
Kubernetes-cluster objects, which are reserved for the kind phase):

1. A ticket / incident / case / change-request record; or
2. A vendor or external disposition / containment command; or
3. An approval or change-binding record.

**Gate C — event shape** (structural, no class vocabulary):

The source describes a **persistent record being created, modified, or
closed** whose outcome was wrong, because the modifier relied on a fact
that it could have authored itself, or that was never independently
established by the party the record's meaning depends on.

Both vulnerability reports and retrospective incident reports qualify.

**Duplicates**: if two items describe the same underlying event, keep
the more primary source by this priority: first-party retrospective >
vendor PSIRT > NVD/CVE.org > GHSA > news/reporting; mark the other
`excluded: duplicate` and record both.

The filter is judged from the source's own text. It does **not** assess
interest, severity, novelty, or how well the item might map onto any
classification.

## 7. Construction: narratives and harm predicates first

For each included item the constructor writes, **from the primary source
alone**, using only `taxonomy-grid-public.md` as classification
vocabulary:

1. A verbatim quote establishing the write-path event — up to **two
   sentences or 40 words**, whichever is shorter, from the primary
   source's own text.
2. An attack narrative in the constructor's own words. Vocabulary rule:
   the narrative may use the primary source's terms, ordinary English,
   and the sanitized grid's class names and generic definitions. It may
   not use implementation vocabulary (`Injection` fields, gate or
   mediator names, object-model field names). **Required elements** —
   the narrative must state: (a) which role proposed the write;
   (b) what record the write changed; (c) what the write should have
   depended on; (d) which fact made the actual outcome wrong;
   (e) the order of events. A narrative missing an element is returned
   by the arbiter review once, with the missing element named; the
   constructor completes it without seeing the implementation.
3. An **expected harm predicate**: one sentence in the constructor's own
   words stating the observable fact that constitutes the harm (shape:
   "the record reached ⟨terminal state⟩ although ⟨the fact the state
   asserts⟩ was never independently established"). Frozen at Phase 2;
   never edited afterwards.
4. A class guess against the sanitized grid: `primary` + optional
   `also`, or an explicit `fits_no_published_class` mark.

The harm predicate is derived from the advisory / retrospective, not
reverse-engineered from what the chain can score.

## 8. Implementation binding and object-model boundaries

The implementer maps each frozen narrative onto the production chain.
For each item the outcome is exactly one of:

- `instantiated` — a Suite C case exists. The implementer encodes the
  expected harm predicate as the scored harm and **records the mapping**
  in the case table (predicate sentence → the specific stored or
  vendor-side fact that scores it). Scoring reads stored and vendor-side
  facts only, never a mediator return value.
- `object_model_boundary` — the narrative names a write or a witness the
  SOC object model cannot express. A **first-class finding**, recorded
  with the specific missing object / field.
- `not_instantiable` — expressible in principle but requires substrate
  the lab plane does not have (e.g. a real vendor API); recorded with
  the reason.

The implementer also records its own `mapped_class` (which sanitized-grid
class the bound case actually exercises), which is compared with — never
substituted for — the constructor's frozen `class_guess`. If the
expected harm predicate and the chain's scoring disagree, the
disagreement is recorded verbatim and surfaced to the arbiter.

## 9. T9 procedure

Every `fits_no_published_class` mark from §7 is adjudicated in the
Phase-2 arbiter review, per item, before Phase 3 begins for that item.
The constructor's reasoning is recorded in `t9_reasoning`. The arbiter
decides either:

- **define T9** — a new class row in the **sanitized grid** (and,
  mirrored, in `tei_threats.md`) with its object and harm predicate,
  written before any case is implemented for it; or
- **classify** — a written reason the item fits an existing class,
  recorded in `t9_dispositions`.

There is no T9 quota. The requirements are: candidates are neither
dropped nor forced into published classes; R6's non-security queries
ensure the query space was not pre-baked onto security vocabulary; and
the count of candidates and their dispositions are part of the freeze
either way.

## 10. Acceptance rules (run all, report all)

1. **Cell semantics are pre-registered and computed, not judged.** For
   each case and each column: `harmed` iff harm is scored from stored or
   vendor-side facts; `idle` iff the **naive** arm produces no harm (the
   harm is unreachable in the chain regardless of configuration —
   determinable from the naive arm alone, before full is examined);
   `prevented` iff naive harms and full does not. Idle is reported as
   idle, never as prevented.
2. **Every** admitted case runs under `naive` and `full` on every column
   it is expressible in; every cell is reported, including idle,
   not-applicable, and boundary rows.
3. **No post-result exclusion.** After results are seen, no case is
   excluded, reworded, or dropped. One exception, fully constrained: a
   case may be declared **malformed by construction** only by the
   **arbiter**, only **before** any fix, only with a written finding
   that the case cannot produce a signal in **any** configuration (the
   naive arm shows no harm and the reason is a construction defect, e.g.
   the injection drives nothing — the same instrument-bug class the
   paper already documents), and the declaration, the finding, the fix,
   and **both** the original and re-run results all stay in the
   artifact, with the re-run marked `v2`. At most one such declaration
   per case.
4. The manuscript table reports all cases in frozen order (by
   `advisory_date`, ties by `id`), with the source column naming the
   primary URL. Summary counts are computed from the full table, never
   the reverse.

## 11. Harm handling under full

Unchanged from the standing discipline in `tei_threats.md` (final
section) and the review plan's §2.3: if a case harms under the full
construction, **fix the TEI construction**, re-freeze both chains and
TLC, and — because a fix changes the construction under test —
**re-run every Suite C case on the fixed construction**. Every result
row records the code commit hash it ran on; mixed-version tables are
forbidden. The finding and the fix are reported in the manuscript. A
harm found by Suite C is the suite working, not the suite failing; the
artifact's precedent is the mock-weak-ACK closure hole (found, fixed in
production code, disclosed in §eval-found).

## 12. Provenance and freeze formats

`external_sample_v2.json`, append-only across phases:

```json
{
  "protocol": "eval/protocol-independent.md",
  "protocol_approved_at": "<arbiter date>",
  "window": ["2015-01-01", "2026-09-16"],
  "queries_used": ["R1 …", "…"],
  "phase1_frozen_at": "<ts>",
  "items": [
    {
      "id": "sc-<slug>",
      "advisory_date": "<publication date of primary source>",
      "url": "<primary>",
      "source_type": "nvd|ghsa|psirt|retrospective|paper",
      "query": "<R# string>",
      "included": true,
      "filter_gate_failed": null,
      "phase2_frozen_at": "<ts>",
      "quote": "<verbatim, ≤2 sentences / 40 words>",
      "narrative": "<constructor's words, required elements a–e>",
      "expected_harm_predicate": "<constructor's words, frozen>",
      "class_guess": {"primary": "<T#|fits_no_published_class>", "also": []},
      "t9_reasoning": "<or null>",
      "constructor_role_id": "<agent run id>",
      "phase3_frozen_at": "<ts>",
      "binding": "instantiated|object_model_boundary|not_instantiable",
      "binding_reason": "<or null>",
      "mapped_class": "<implementer's class, or null>",
      "predicate_mapping": "<predicate sentence -> scored fact, or null>",
      "implementer_role_id": "<agent run id>",
      "case_id": "<sc_… or null>"
    }
  ],
  "included_count": 0, "excluded_count": 0, "overflow_ids": [],
  "t9_dispositions": [], "arbiter_log": "eval/protocol-reviews/arbiter_log.md"
}
```

`suite_c_cases.py` imports nothing from `ALL_CASES`; its rows point at
`sc-` item ids. Results land in `eval/results/suite_c/`, one row per
case × arm × column with the code commit hash, plus a README stating
provenance and the never-pooled rule.

## 13. Pre-registered outcome interpretations

All of these are fixed now, before any case exists:

- **All cases `instantiated`, zero full-arm harm**: the intended
  headline — independently constructed cases do not change the result.
- **A full-arm harm occurs**: §11; the headline becomes "the independent
  suite found a construction defect", reported with the fix.
- **Zero cases `instantiated`** (all boundary / not-instantiable): the
  finding is about the object model's expressiveness, not about TEI —
  the manuscript reports the boundary inventory as the result.
- **Majority idle**: the retrieval surfaced write-path integrity events
  whose harms the chain cannot reach; reported as idle with the
  constructor's predicates, never as prevented.
- **Fewer than 12 included items**: the shortfall is the finding about
  the query space; reported as such.

## 14. What this protocol does and does not claim

**Claims**: the acceptance, filtering, construction, and harm rules
above were fixed and arbiter-approved before any v2 retrieval or Suite C
case existed; the frozen prompts and append-only artifact trail make
post-hoc selection detectable.

**Does not claim**: organizational independence — the constructing
agents and the paper's authors share a repository and a review history;
the mechanism is prompt-level role separation plus the pre-frozen trail,
and §3's prompt freeze is what makes that mechanism auditable rather
than trusted. Not claimed: open-world coverage — Suite C answers whether
cases can be constructed without starting from the implementation
**within the space the frozen queries define**; that space is itself a
design choice, pre-registered here rather than hidden. Not claimed:
reproduction of any primary source (mapped, not reproduced); anything
about products named in primary sources. If the freeze evidence in the
header is a local commit only, its timestamp is self-attested and the
manuscript must say so.

## 15. Deferred work

LLM planner arms over Suite C are deferred to a single consolidated
execution after all case work lands. Nothing in this protocol licenses
an LLM-arm claim, a model comparison, or a ranking. When that run
happens it will be governed by the standing LLM-arm rules in the review
plan (§6.1): pre-specified subset, existence-check framing, provider
failures dropped from denominators and reported.

## 16. Amendments

None. (Any future amendment appends here with a UTC date, the arbiter's
initials, and a statement of what changed and why; nothing above is ever
edited in place.)
