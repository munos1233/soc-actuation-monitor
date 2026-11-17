# Mixed-load backlog archive (fail-closed cost)

Frozen run: `run-20260911T015644Z.json` (2026-09-11), 120 arrivals,
fail_closed_fraction=0.30, Poisson λ=1.0 clock, seed 7, mock column.

Headline (also in `latest.md`):

| arm | closed_ok | harmed | stuck | READY mean | stuck age p50 | stuck age p95 |
|---|---|---|---|---|---|---|
| naive | 80/120 | 40 | 0 | 0.00 | — | — |
| full | 80/120 | 0 | 40 | 0.00 | 56.80 | 109.14 |

## Typed refusals (cited in §7, "What one stuck ticket costs a human")

All 40 stuck tickets under `full` carry a machine-readable `close_error`;
across the forty there are exactly three distinct values:

| close_error | count | source templates |
|---|---|---|
| closed_side_effects_pending | 17 | a1_dropped_readback (4), a2_target_swap (7), a5_lying_vendor_receipt (6) |
| closed_weak_confirmation_evidence | 12 | a1_weak_receipt (12) |
| closed_requires_report | 11 | a1_missing_report (11) |

This is the basis for the paper's claim that triage of a stuck ticket is a
lookup (which evidence predicate failed, from the retained transaction
snapshot) rather than a forensic reconstruction. The `t_h` cost per ticket in
the paper is stated as an assumption, not a measurement; 40·t_h at an assumed
5 min/ticket ≈ 3.3 analyst-hours per 120 arrivals.

Queue properties: stuck count equals the injected refuse fraction (30% of
120), READY outbox depth stays 0 (refusals never become undelivered
commands), and all 80 golden events close under both arms.

## Human-attention flag (cited in §7 alongside the typed refusals)

The harness flags a ticket as needing a human when it is stuck, manually
resolved, or blocked (`human = stuck or verify.overall == manual_resolution
or blocked_errors`, `backend/app/eval_suite/backlog.py`):

| arm | human-flagged | breakdown |
|---|---|---|
| naive | 120/120 | 80/80 gold + 40/40 injected — without the verify split nothing auto-resolves |
| full | 40/120 | 0/80 gold + 40/40 injected — human attention concentrates on exactly the stuck tickets |

This is the basis for the paper's claim that the comparison is not "40
tickets of human work against none": naive flags every arrival and still
lets 40 close wrong, while full concentrates human work on the 40 typed
stuck tickets only.
