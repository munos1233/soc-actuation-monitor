# Re-execution protocol (codename R1)

You re-run frozen tables on your own machine and cell-diff against the
committed baselines. You do not invent results. You do not edit mediators
or cases.

## Blindness

- You may read `REPRODUCE.md`, this protocol, and `eval/harness/diff_freeze.py`.
- You may read frozen baselines under `eval/results/latest.json` and
  `eval/results/k8s-kind/latest.json` for comparison after your run.
- You do not modify production gate code or the case registry to make
  diffs go away.

## Suite B main table

```bash
make paper-eval-up
make paper-eval-matrix
# archive your run's latest.json / latest.md under a timestamped path
make paper-eval-diff-freeze \
  BASELINE=eval/results/latest.json \
  RERUN=<your-run>/latest.json \
  DIFF_OUT=eval/results/reexec/suite-b-diff \
  DIFF_LABEL=suite_b \
  DIFF_ENV=eval/results/reexec/env.json
make paper-eval-down
```

Record PostgreSQL version, host timezone, Docker image digests, and git
commit in `env.json` (see `env.example.json`).

## Kind headline table

Requires local Docker + kind (see `eval/k8s/README.md`).

```bash
make paper-eval-k8s-kind
make paper-eval-diff-freeze \
  BASELINE=eval/results/k8s-kind/latest.json \
  RERUN=<your-kind-run>/latest.json \
  DIFF_OUT=eval/results/reexec/kind-diff \
  DIFF_LABEL=k8s_kind \
  DIFF_ENV=eval/results/reexec/env.json
```

## What counts as a cell

- Suite B: one `(case_id, config, column, planner, trial)` row; compared
  fields are `applicable` and `harmed`.
- Kind: one `(case_id, arm)` row; compared field is `harmed`.

Every discrepancy is logged, including missing/extra cells. Environment
first: PG version, timezone, mirror/image skew.
