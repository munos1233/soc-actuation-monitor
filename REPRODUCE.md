# Reproducing the actuation-integrity evaluation

Everything the paper reports comes from two suites driven through the production
service chain against a real PostgreSQL and a vendor stub. This document is the
whole recipe: three commands for the results, one for the PDF.

## What you need

- Docker with Compose v2 (for PostgreSQL 16 and Redis)
- Python 3.12 and [`uv`](https://docs.astral.sh/uv/) (the lockfile is committed;
  every command below runs `--frozen`)
- A LaTeX distribution with `latexmk` and the `acmart` class, only if you want
  to rebuild the PDF
- No network access, no API key, and no LLM provider. The evaluation reported in
  the paper uses a deterministic scripted planner, not a language model.

## One warning that matters

The suite writes to whatever database and Redis it is given, and it deliberately
weakens database constraints in the substrate arms. **Never point it at a
deployment you care about.** The Make targets below use a dedicated Compose
project (`shadowtrace-evalchain`) on non-default ports (PostgreSQL 55432, Redis
56379) precisely so it cannot collide with a development stack on 5432/6379.

## Three commands

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

- **Suite B**, adversaries A1–A5 injected at the system boundary — rows a planner
  writes, receipts and observation answers a vendor returns, repeated dispatch.
  Harm is scored afterwards from database and vendor-side facts, never from a
  mediator's return value.
- **Suite A**, the golden path under the same `full` configuration, reporting
  closure rate, over-block, extra manual steps and extra worker passes.
  `force_close` is forbidden there: a golden path that fails, fails.
- Fifteen configurations: `naive`, four single-gate, `full`, four leave-one-out,
  five substrate arms. Two vendor columns (`mock`, `pseudo_live`). Two planners
  (`untrusted_planner`, and `dead_playbook` as the no-adaptive-planner baseline).

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
| `eval/harness/run_suite.py` | CLI entry point |
| `eval/cases/adversary_set.json` | generated case registry (`make paper-eval-cases`) |
| `eval/results/latest.md` | most recent full run, human readable |
| `backend/app/eval_suite/` | the harness itself |
| `backend/app/eval_suite/substrate.py` | harness-only substrate weakening; production imports nothing from it |
| `backend/app/eval_monitor.py` | the four mediator switches, refused outside a declared harness build |
| `backend/tests/eval/` | structural guards for the harness |

## Known rough edges

- Twenty-nine tests in the wider backend suite fail on a clean checkout for a
  reason unrelated to this work: their fixtures pair `DISPOSITION_MODE=live_xdr`
  with the default mock adapter kind, which `Settings` correctly refuses as a
  fail-closed violation. `make paper-eval-test` is unaffected.
- The matrix is sequential by design, so wall-clock time scales with the number
  of configurations rather than with available cores.
