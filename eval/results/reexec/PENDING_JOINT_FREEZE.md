# Pending: joint freeze fill-in

This directory's numeric diffs are **not** filled until the joint
end-of-pipeline freeze. Do not invent `0/N`.

## After joint freeze — expected artifacts

| artifact | source command |
|---|---|
| `suite-b-diff.json` / `.md` | `make paper-eval-matrix` then `paper-eval-diff-freeze` vs `eval/results/latest.json` |
| `kind-diff.json` / `.md` | `make paper-eval-k8s-kind` then `paper-eval-diff-freeze` vs `eval/results/k8s-kind/latest.json` |
| `env.json` | filled from `env.example.json` on the re-run host |
| `latest-diff.md` | optional roll-up pointing at both diffs + `cell_diffs` totals |

## Paper sentence (fill numbers then)

> Independent re-execution (R1), \<date\>, \<env\>, \<suite-b cell_diffs\>/N
> Suite~B cells and \<kind cell_diffs\>/M kind cells.

Until those files exist, the manuscript only cites that the protocol and
diff harness are frozen here.
