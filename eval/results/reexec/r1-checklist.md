# R1 checklist — independent table re-execution

Codename R1. You re-run frozen tables on your own machine and cell-diff against
committed baselines. You do not invent results. Numeric `0/N` (or any
`cell_diffs` count) claims are written only after a real re-run fills
`suite-b-diff` / `kind-diff`. Do not invent cell-diff numbers.

Blindness (from `protocol.md`): you may read `REPRODUCE.md`, this checklist,
`protocol.md`, and `eval/harness/diff_freeze.py`. You may read frozen baselines
under `eval/results/latest.json` and `eval/results/k8s-kind/latest.json` for
comparison **after** your run. You do not modify production gate code or the
case registry to make diffs go away.

---

## 1. Environment checklist

Fill `eval/results/reexec/env.json` from `env.example.json` on the re-run host
before (or with) each `paper-eval-diff-freeze` invocation. Pass it as
`DIFF_ENV=eval/results/reexec/env.json`.

| Field | What to record | Why it matters |
|---|---|---|
| `postgres` | Exact PostgreSQL version string (Compose eval stack is **PostgreSQL 16**; e.g. `PostgreSQL 16.x`) | Suite B writes to a real DB; version skew can change SQLSTATE / constraint behaviour (notably A0) |
| `timezone` | Host timezone (protocol: record host timezone; `diff_freeze` default if unset is `UTC`) | Timestamped run paths and any TZ-sensitive scoring/logging |
| `docker_images` | Digests (not just tags) for images used by the eval Compose project and, for kind, kind / Gatekeeper / VAP / TEI webhook images | Mirror or tag drift looks like cell diffs |
| `commit` | `git rev-parse HEAD` of the tree you ran | Baseline vs re-run must be attributable to the same (or known) revision |
| `host` | Machine identity (hostname / OS) | Reproducibility provenance for the joint freeze |
| `notes` | Anything else material (Compose project name, ports, kind cluster name) | Audit trail |

Also confirm before Suite B:

- Docker with Compose v2; isolated project `actuation-evalchain` on non-default ports (PostgreSQL **55432**, Redis **56379**) via `make paper-eval-up` — never a deployment you care about.
- Python 3.11+ and `uv` with `--frozen` (lockfile committed).
- **No API key** for `make paper-eval-matrix` (offline).

Also confirm before kind:

- Local Docker + kind as documented in `eval/k8s/README.md`.
- Same `env.json` fields as above, plus kind-related image digests in `docker_images`.

Do **not** run `make paper-eval-matrix` or `make paper-eval-k8s-kind` from this checklist alone until the joint freeze; this file defines what to check when you do.

---

## 2. Exact cell definitions (`diff_freeze.py`)

`make paper-eval-diff-freeze` runs the offline harness `eval/harness/diff_freeze.py`
(no database). A **cell_diff** is any of: value mismatch on shared keys, key
only in baseline, or key only in re-run. Total:

`cell_diffs = |mismatches| + |only_in_baseline| + |only_in_rerun|`.

### Suite B cell

**Detection:** freeze JSON has top-level `rows` or `suite_b_rows` (a list). If
top-level `arms` (a dict) is present, kind extraction wins and Suite B path is
not used.

**Key** (one cell = one key):

```text
(case_id, config_or_arm, column, planner, trial)
```

Implemented as `_cell_key_suite`:

- `case_id` ← `row["case_id"]`
- `config` ← `row["config"]` or, if missing, `row["arm"]`
- `column` ← `row["column"]`
- `planner` ← `row["planner"]`
- `trial` ← `row.get("trial", 0)`

**Compared fields:**

- `applicable` ← `bool(row.get("applicable", True))`
- `harmed` ← `bool(row.get("harmed"))` if applicable, else forced to `False`

A shared-key mismatch is any difference in `(applicable, harmed)`.

**Protocol label:** `DIFF_LABEL=suite_b`. Baseline: `eval/results/latest.json`.
Output prefix: `eval/results/reexec/suite-b-diff`.

### Kind cell

**Detection:** freeze JSON has top-level `arms` as a **dict** mapping arm name →
list of row objects. Extraction returns immediately after walking `arms`.

**Key** (one cell = one key):

```text
(case_id, arm, None, None, 0)
```

Implemented as `_cell_key_kind` after `enriched.setdefault("arm", arm_name)` from
the dict key:

- `case_id` ← row `case_id`
- `arm` ← row `arm` (defaulted from the `arms` map key)
- third/fourth tuple slots are always `None`; `trial` slot is always `0`

**Compared fields:**

- `harmed` ← `bool(enriched.get("harmed"))`
- `applicable` ← always `True` (kind cells do not carry an applicable flag in the
  normalized map)

A shared-key mismatch is any difference in `(applicable, harmed)` (for kind,
effectively `harmed`).

**Protocol label:** `DIFF_LABEL=k8s_kind`. Baseline:
`eval/results/k8s-kind/latest.json`. Output prefix:
`eval/results/reexec/kind-diff`.

---

## 3. Failure modes that look like cell diffs but are env skew

Check environment **first** (protocol: “Environment first: PG version, timezone,
mirror/image skew”).

| Symptom in diff report | Likely env skew, not a true gate/case change |
|---|---|
| Many `only_in_baseline` / `only_in_rerun` keys | Different commit, different matrix/kind corpus, wrong baseline/rerun paths, or kind `arms` vs Suite B `rows` shape mismatch |
| `harmed` / `applicable` mismatches concentrated on A0 or DB-touching cases | PostgreSQL major/minor skew vs recorded `postgres` (Compose expects 16) |
| Systematic timestamp or path confusion; hard-to-reconcile run archives | Host timezone not recorded / not matching what you believe you ran |
| Kind arm disagreements or missing arms | Docker image digest drift (Gatekeeper / VAP / TEI webhook / kind node images) vs freeze host |
| Suite B blow-ups or partial matrices | Pointed at wrong DB/Redis (not the isolated `actuation-evalchain` stack on 55432/56379); residual volumes; skipped `paper-eval-up` / incomplete `paper-eval-down` |
| Diff vs “expected” numbers without files | Inventing `0/N` before `suite-b-diff` / `kind-diff` exist — refuse; fill only after joint freeze |

Every discrepancy is logged, including missing/extra cells. Do not clear diffs by
editing gates or cases; re-check env and re-run if skew is confirmed.

---

## 4. Order of operations for the joint freeze

From `PENDING_JOINT_FREEZE.md` and `protocol.md`. Numeric diffs stay empty until
this sequence completes. Do not invent `0/N`.

1. **Record env** — copy `env.example.json` → `env.json`; fill `commit`,
   `timezone`, `postgres`, `docker_images`, `host`, `notes`.
2. **Suite B re-run**
   - `make paper-eval-up`
   - `make paper-eval-matrix`
   - Archive that run’s `latest.json` / `latest.md` under a timestamped path
     (do not silently overwrite provenance).
   - `make paper-eval-diff-freeze` with  
     `BASELINE=eval/results/latest.json`,  
     `RERUN=<your-run>/latest.json`,  
     `DIFF_OUT=eval/results/reexec/suite-b-diff`,  
     `DIFF_LABEL=suite_b`,  
     `DIFF_ENV=eval/results/reexec/env.json`
   - `make paper-eval-down` (stop and delete volumes).
3. **Kind re-run** (requires local Docker + kind)
   - `make paper-eval-k8s-kind`
   - `make paper-eval-diff-freeze` with  
     `BASELINE=eval/results/k8s-kind/latest.json`,  
     `RERUN=<your-kind-run>/latest.json`,  
     `DIFF_OUT=eval/results/reexec/kind-diff`,  
     `DIFF_LABEL=k8s_kind`,  
     `DIFF_ENV=eval/results/reexec/env.json`
4. **Artifacts expected after joint freeze**
   - `suite-b-diff.json` / `suite-b-diff.md`
   - `kind-diff.json` / `kind-diff.md`
   - filled `env.json`
   - optional `latest-diff.md` roll-up pointing at both diffs and `cell_diffs` totals
5. **Paper sentence** — only then fill  
   `\<suite-b cell_diffs\>/N` and `\<kind cell_diffs\>/M` from those files.
   Until then, the manuscript only cites that the protocol and diff harness are
   frozen under `eval/results/reexec/`.

Re-execution archive is **never pooled** with Suite B 57, kind headline,
independent-author, or mutation tables.

---

## 5. What R1 refuses to do

- Invent cell-diff counts, `0/N`, or paper numeric claims before
  `suite-b-diff` / `kind-diff` exist.
- Edit production **gate** / mediator code to make diffs go away.
- Edit the **case registry** (or other case definitions) to clear diffs.
- Modify `diff_freeze.py` comparison semantics to hide mismatches.
- Point Suite B at a non-isolated or production database to “get a clean run.”
- Pool reexec results with Suite B 57, kind headline, independent-author, or
  mutation denominators.
- Treat env skew (PG version, timezone, image digests, wrong commit, wrong
  baseline path) as evidence against the frozen table without first correcting
  the environment and re-running.

R1’s job is: same recipe, own machine, offline cell-diff, honest env header,
honest report of every discrepancy.
