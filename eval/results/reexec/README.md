# Independent table re-execution archive

Never pooled with Suite B 57, kind headline, independent-author, or mutation.

## Contents

| file | role |
|---|---|
| `protocol.md` | Re-runner (R1) instructions |
| `PENDING_JOINT_FREEZE.md` | Commands + artifact names for the joint freeze |
| `r1-checklist.md` | R1 environment / cell-definition checklist |
| `env.example.json` | Env header template for `diff_freeze.py --env-json` |
| `*-diff.{json,md}` | Filled after joint re-run (not invented here) |

## Diff harness

Offline (no database):

```bash
make paper-eval-diff-freeze \
  BASELINE=eval/results/latest.json \
  RERUN=/path/to/rerun/latest.json \
  DIFF_OUT=eval/results/reexec/suite-b-diff \
  DIFF_LABEL=suite_b
```

Kind:

```bash
make paper-eval-diff-freeze \
  BASELINE=eval/results/k8s-kind/latest.json \
  RERUN=/path/to/kind-rerun/latest.json \
  DIFF_OUT=eval/results/reexec/kind-diff \
  DIFF_LABEL=k8s_kind
```

Numeric `0/N cell diffs` claims are written only after those files exist.
