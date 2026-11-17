# Reproducing the actuation-integrity evaluation

Everything the paper reports comes from two suites driven through the production
service chain against a real PostgreSQL and a vendor stub. This document is the
whole recipe: three commands for the main ablation table, one extra command per
language-model planner arm, one for the PDF.

## What you need

- Docker with Compose v2 (for PostgreSQL 16 and Redis)
- Python 3.11+ and [`uv`](https://docs.astral.sh/uv/) (the lockfile is committed;
  `backend/pyproject.toml` requires `>=3.11`; every command below runs `--frozen`)
- A LaTeX distribution with `latexmk` and the `acmart` class, only if you want
  to rebuild the PDF
- **No API key for the main table.** `make paper-eval-matrix` and
  `make paper-eval-quick` are offline. The language-model planner arms are
  separate commands and need OpenAI-compatible endpoints.

## One warning that matters

The suite writes to whatever database and Redis it is given, and it deliberately
weakens database constraints in the substrate arms. **Never point it at a
deployment you care about.** The Make targets below use a dedicated Compose
project (`actuation-evalchain`) on non-default ports (PostgreSQL 55432, Redis
56379) precisely so it cannot collide with a development stack on 5432/6379.

## Three commands (main ablation, offline)

```bash
make paper-eval-up        # isolated PostgreSQL + Redis, ~20 s
make paper-eval-matrix    # the full matrix, ~20 min
make paper-eval-down      # stop and delete the volumes
```

`paper-eval-matrix` writes four files into `eval/results/`: a timestamped
`run-<UTC>.json` and `run-<UTC>.md`, plus `latest.json` and `latest.md` copies.
The timestamped JSON is deliberately not versioned (see `eval/.gitignore`); the
markdown summaries and `latest.json` are.

For a signal in minutes rather than tens of minutes, the two arms that carry the
main claim:

```bash
make paper-eval-quick     # naive vs full, mock column, suite B only
```

## What the matrix covers

- **Suite B**, adversaries A0–A5 injected at the system boundary — rows a planner
  writes, receipts and observation answers a vendor returns, repeated dispatch,
  and (A0) `UPDATE`/`INSERT` issued as the planner database login. Harm is
  scored afterwards from database and vendor-side facts, never from a mediator's
  return value. A0 scores from SQLSTATE and stored rows.
- **Suite A**, the golden path under the same `full` configuration, reporting
  closure rate, over-block, extra manual steps and extra worker passes.
  `force_close` is forbidden there: a golden path that fails, fails.
- Seventeen configurations: `naive` (gates off **and** role split off), four
  single-gate, `full`, four leave-one-out, two interaction arms
  (`close_and_verify`, `bind_and_egress`), five substrate arms. Two vendor
  columns in the headline matrix (`mock`, `pseudo_live`). A third envelope
  column (`envelope_b`) is `make paper-eval-sangfor` and is not merged into
  the  headline denominator. Two planners (`untrusted_planner`, and
  `dead_playbook` as the no-adaptive-planner baseline).

`eval/README.md` explains each arm, why the substrate arms are a ladder rather
than four independent rows, and what the appendix predicate checks are and are
not evidence of.

## Structural test gate

```bash
make paper-eval-test
```

These assert that every adversary is covered, that every case perturbs
something, that golden cases carry no adversary, that the configuration matrix
contains the single-gate, leave-one-out and substrate arms and that the substrate
arms nest, and that the scorer can produce a one for each harm kind. There is
deliberately no test asserting an ablation table from mediator return values —
that table is what the boundary run produces, and asserting it from predicates
is how an earlier version of this suite fooled itself.

`make paper-eval-test` is the paper artifact's test command. Unrelated failures
in the wider backend suite (fixture combinations such as `DISPOSITION_MODE`
paired with a mock adapter kind) are **out of scope** for this artifact and are
not required to be green.

## The paper

```bash
make paper-pdf            # paper/main.pdf
make paper-pages          # rebuild and fail if over the 35-page TOPS limit
```

## Where things live

| Path | Role |
|---|---|
| `paper/main.tex` | the manuscript |
| `paper/references.bib` | bibliography |
| `paper/cover-letter.md` | TOPS cover letter |
| `eval/harness/run_suite.py` | CLI entry point |
| `eval/cases/adversary_set.json` | generated case registry (`make paper-eval-cases`) |
| `eval/results/latest.md` | most recent full run, human readable |
| `backend/app/eval_suite/` | the harness itself |
| `backend/app/eval_suite/substrate.py` | harness-only substrate weakening; production imports nothing from it |
| `backend/app/eval_monitor.py` | the four mediator switches, refused outside a declared harness build |
| `backend/migrations/versions/0040_actuation_roles.py` | planner / actuation roles (0040--0045) |
| `backend/tests/eval/` | structural guards for the harness |

## Additional experiments the paper reports

These are not required to reproduce the main ablation table.

```bash
make paper-eval-model         # head protocol + write-path invariants, no database
make paper-eval-concurrency   # K=4 OS processes on one row, ~15 min
make paper-eval-overhead      # mediator p50/p95 and statement counts, ~5 min
make paper-eval-scale         # 120 golden events, p50/p95/p99 and gold-path READY
make paper-eval-backlog       # mixed fail-closed arrivals, naive vs full
make paper-eval-adaptive      # rejection-then-mutate search, budget 24
make paper-eval-search        # coverage search over implemented knobs; full space: PAPER_SEARCH_BUDGET=960
make paper-eval-process-split # planner child, actuation parent: no writer factory, A0 still 42501
make paper-eval-tla           # TEI.tla + TEIPair; requires JVM + tla2tools.jar
make paper-eval-k8s           # Kubernetes TEI fixture (22 cases); CI / artifact only
make paper-eval-k8s-kind      # C5 headline: kind + Gatekeeper/VAP + TEI webhook
make paper-eval-lattice       # 2^4 live 4×57 plus projection; not in ALL_CONFIGS
make paper-eval-heldout       # mapped SOC cases (not reproduced); not pooled with 57
make paper-eval-independent   # dual-track independent authors; two never-merged lines; not pooled with 57
make paper-eval-diff-freeze   # offline cell-diff of two freeze JSONs (Suite B or kind); no DB
make paper-eval-gold-ext      # golden g5-g11; never pooled with g1-g4
make paper-eval-b2            # construction-closure attacks; never pooled with 57
make paper-eval-mutation      # 18 mutants, FULL only, 57+B2+golden 10
make paper-eval-playbook-semantic  # playbook-as-truth closer; not a product eval
make paper-eval-replay        # spec-trace replay on SOC + Kubernetes chains
make paper-eval-repeat        # N=20 wall-clock/harm variance; artifact only
make paper-eval-sangfor       # second vendor envelope (envelope_b), naive vs full
```

Independent re-execution protocol (codename R1), env template, and pending
joint-freeze checklist: `eval/results/reexec/`. Numeric cell-diff claims
are written only after a real re-run fills `suite-b-diff` / `kind-diff`.

### Portability instance (Temporal, third instance)

```bash
pip install temporalio   # SDK bundles the single-binary dev server
python eval/temporal/run_temporal.py          # ~1 min, no external server
```

Seven mapped attack cases + one golden closure, three arms
(`temporal_naive` / `temporal_attribute` / `temporal_tei`), scored from
workflow final state + vendor records. Never pooled with the 57, the kind
11, or any frozen table (`eval/results/temporal/`).

### Hosted-cluster replication (one-time, C5 slice)

The 11-case C5 slice was replicated once on a hosted two-node Alibaba Cloud
ACK cluster (v1.36-aliyun, cn-hangzhou): all 33 cells match the kind freeze
(`eval/results/k8s-aliyun/`, rows labelled `hosted_ack_2node`, never pooled).
This needs a hosted cluster you control; it is not part of the offline
recipe. The webhook runs in-cluster there
(`eval/k8s/webhook/deploy-incluster.yaml`, `TEI_WEBHOOK_INCLUSTER=1`) and
the attribute baseline is ValidatingAdmissionPolicy because Gatekeeper's
images were unreachable from cn-hangzhou. Re-run command and full
provenance: `eval/results/k8s-aliyun/README.md`.


The vendor-latency sensitivity scan (Table `tab:vendor-latency`) is the
overhead probe with an artificial delay injected into the vendor stub's
confirmation read-back endpoint, one run per level:

```bash
for D in 0 100 500 1000 5000; do
  uv run --frozen --directory backend python eval/harness/run_overhead.py \
    --repeats 8 --vendor-readback-delay-ms $D \
    --out eval/results/vendor_latency/delay_${D}ms
done
```

Frozen per-level outputs live in `eval/results/vendor_latency/` with a README
recording the mechanism and the run date. The flag defaults to 0 and must stay
0 for the headline overhead table.

Eval-only role passwords (`planner_role` / `actuation_role`) are for this
Compose project. A production deployment must set explicit planner and
actuation DSNs and rotate those passwords; `Settings` refuses the defaults
when `APP_ENV=production`.

The real-planner arms need provider credentials in `backend/.env` (never
committed); each arm takes roughly 30--75 minutes at N=5 depending on the
provider's latency. They are **not** covered by the three
offline commands above. The paper reports five model arms from four
families (`glm-5.3`, `glm-5.3-flash`, `deepseek-flash`, `kimi-k3`,
`claude-opus-5`):

```bash
make paper-eval-planner   # the frozen glm-5.3 arm
```

Each additional arm is the same harness with the endpoint overridden on the
command line and a separate output directory, e.g.:

```bash
LLM_MODE=openai_compatible LLM_API_BASE_URL=<endpoint> LLM_API_KEY=<key> \
  uv run --frozen --directory backend python eval/harness/run_suite.py \
  --configs naive,full --columns mock --planners untrusted_planner,llm_planner \
  --skip-gold --trials 5 --llm-token-budget 1200000 \
  --llm-model <endpoint-model-id> --out eval/results/planner_arm_<name>
```

The frozen per-arm outputs live in `eval/results/planner_arm*/` with a
README per arm recording the endpoint identifier and freeze date.

## Without Make (anonymous zip)

The artifact zip does not include Compose. Point `DATABASE_URL` and
`REDIS_URL` at an isolated PostgreSQL 16 and Redis you are allowed to
wipe, then:

```bash
export DATABASE_URL='postgresql+asyncpg://<eval-owner>:<eval-owner>@localhost:55432/<eval-db>'
export REDIS_URL=redis://localhost:56379/0
# main table (offline):
python eval/harness/run_suite.py --out eval/results
# finite TEI.tla slice (fetch the TLC jar first if you want Java TLC):
python eval/harness/run_tla.py --out eval/results/tla
python eval/harness/run_k8s.py --out eval/results/k8s
```

## Anonymous artifact

```bash
scripts/pack_paper_artifact.sh
```

The zip is `paper/main.pdf`, this file, `eval/`, the frozen `latest.json`, the
model-check results, and the harness sources. It does not include the frontend,
challenge-cup slides, vendor contracts, or product demo matrices.
