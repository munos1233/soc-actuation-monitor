# Mutation kill-rate (FULL only)

Never pooled with Suite B 57. Production code neither contains nor imports
these mutants (`backend/app/eval_suite/mutants.py`). A3 substrate
mechanisms are absent: the substrate ablation already speaks for them.

Eighteen weakenings, two families:

- **M1 predicate witness** (12): the gate compares a planner-authored label,
  drops a content segment, skips a store fact, or treats an observation as
  an effect. Two historical fail-open shapes each contribute two mutants
  (close gate reading a planner-aligned cycle; bind comparing the action's
  own fingerprint column; egress taking the command's locator as witness;
  terminal activation treating `_template_unchanged` as sufficient).
- **M4 over-strict** (6): a plausible tightening that would refuse a
  legitimate golden. Named killers are g5–g11.

Kill is relative to an unmutated FULL pass, not to a stale freeze. A golden
that already failed under full cannot over-strict-kill a mutant. An attack
that already harmed under full cannot harm-kill a mutant.

`m1_close_planner_cycle` is the declared survivor: aligning the view's plan
revision with the current cycle does not open a scored harm, because the
close gate's remaining conjuncts (report, confirmation evidence, simulated
receipt) still refuse the A1 cases, and no golden is refused. The
`plan_revision` check on the terminal writeback is unreachable as a
standalone hole; it is left unchanged and documented here rather than
patched into a tautology-looking production edit.

Reproduce: `make paper-eval-mutation`. Headline numbers live in `latest.md`.
Frozen 2026-09-17: killed 17/18, declared survivor `m1_close_planner_cycle`,
`m4_verify_no_recovery` over-strict-killed on `g10_writeback_operator_retry`.
