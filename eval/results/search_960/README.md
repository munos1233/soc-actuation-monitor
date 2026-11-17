# Full-space coverage search archive (960 of 960)

One-time full-space sweep of the implemented-knob coverage search,
2026-09-16. The frozen 512-budget run stays in `eval/results/search/`
(run-20260911T023429Z); this run is the complete-space completion and is
**never pooled** with it — both are standalone sweeps over the same
deterministic space, so the full-space result supersedes the budgeted one
for reporting purposes while the freeze remains as provenance.

## Command

```bash
make paper-eval-search PAPER_SEARCH_BUDGET=960   # directed here with --out
# equivalent direct form:
# run_search.py --budget 960 --out eval/results/search_960
```

## Result (run-20260916T130843Z.json)

| sweep | attempted | space | coverage cells | bypass | new harm class |
|---|---|---|---|---|---|
| frozen 512 (2026-09-11) | 512 | 960 | 5 | no | no |
| **full 960 (this run)** | **960** | **960** | **6** | **no** | **no** |

- The extra 448 points found one additional coverage cell: the
  `mutate_after_approval: level_downgrade` combination
  (the a2_level_downgrade shape). No bypass, no new harm class, and zero
  harmed traces under `full` across all 960 points.
- This closes review question Q5 ("is the search effort sufficient?"):
  the sweep now covers the entire implemented-knob space, not a budgeted
  subset. The honest boundary is unchanged and still stated: this is the
  mapped slice × implemented knobs, not an open-world threat distribution
  and not "T1–T8 × every conceivable knob".

## Paper updates driven by this run

- §7 Spec-driven search: "budget 512 of a 960-point space; five coverage
  cells" → "the full 960-point implemented-knob space; six coverage cells;
  no bypass and no new harm class".
- Discussion, "What this paper did not measure": same update.
