# Vendor-latency sensitivity scan (Experiment 4b)

One-screen answer: **where does a slow vendor read API land?** An artificial
delay was injected into the vendor stub's confirmation read-back endpoint
(`RecordingVendor.confirm_readback`) at five levels, and the golden-path
overhead probe was re-run at each level. The verification phase split absorbs
essentially all of it (slope ≈ 1.0); the unmediated arm never waits for the
read and is flat, as are the other three mediators.

## Run identity

- Date: 2026-09-16 (single session, ~22 minutes, levels run ascending 0 → 5000).
- Command per level (level substituted for `$D`):

  ```bash
  DATABASE_URL=postgresql+asyncpg://shadowtrace:shadowtrace@localhost:55432/shadowtrace \
  REDIS_URL=redis://localhost:56379/0 \
  uv run --frozen --directory backend python eval/harness/run_overhead.py \
      --repeats 8 --vendor-readback-delay-ms $D \
      --out eval/results/vendor_latency/delay_${D}ms
  ```

- Stack: isolated paper-eval postgres :55432 / redis :56379 (`shadowtrace-evalchain`).
- Harness: Suite A golden path, 8 repeats × 4 cases × {naive, full}, mock column.
  No LLM anywhere in this experiment — the measurement design requires a
  deterministic proposer (both arms run the same case to the same close).
- Levels: 0 / 100 / 500 / 1000 / 5000 ms injected into the read-back surface only;
  the submit path keeps its normal cost.
- Mechanism (new code, this experiment):
  - `backend/app/eval_suite/vendor.py`: `RecordingVendor(readback_delay_ms=...)`,
    `asyncio.sleep` at the top of `confirm_readback`.
  - `backend/app/eval_suite/world.py`: `_build_vendor` reads
    `EVAL_VENDOR_READBACK_DELAY_MS` (default 0).
  - `eval/harness/run_overhead.py`: `--vendor-readback-delay-ms` flag, recorded in
    the report JSON as `vendor_readback_delay_ms`.
  - Default is 0 everywhere; the frozen headline table
    (`eval/results/overhead/`, 2026-09-10) is untouched and unaffected.

## Data (p50, ms; 32 case runs per arm per level)

| injected delay | verify naive | verify full | E2E naive | E2E full |
|---|---|---|---|---|
| 0 | 43.4 | 178.7 | 3583 | 3721 |
| 100 | 49.8 | 317.7 | 3730 | 3948 |
| 500 | 37.4 | 731.9 | 3137 | 3186 |
| 1000 | 37.4 | 1244.4 | 2467 | 3436 |
| 5000 | 37.5 | 5255.5 | 2320 | 7458 |

- verify full − verify full@0ms: +139 / +553 / +1066 / +5077.
  Least-squares slope vs injected delay: **≈ 1.02**.
- close / bind / egress: p50 ≤ 0.12 ms, p95 ≤ 0.21 ms at every level in both
  arms (flat).
- SQL statements/case: 146.6–146.8 naive, 168.5–168.6 full at every level.
- Worker passes: 1.50 at every level. All golden cases still closed at 5000 ms.

## Findings (as written into the paper, §7 overhead)

1. The verify split absorbs the injected vendor-read latency with slope ≈ 1.0 —
   it is the only mediator that moves.
2. The unmediated arm is flat (both its verify timer and its E2E wall): it
   closes without waiting for the confirmed receipt, so the delay never enters
   its measured path. The asymmetry is the trade in one table: naive is
   insensitive because it does not check; full pays exactly what the check costs.
3. No hidden amplification: subtracting the injected delay from the full arm's
   E2E p50 lands within (or below) the naive arm's own band at every level
   (3848 vs 3730; 2686 vs 3137; 2436 vs 2467; 2458 vs 2320). Raw E2E growth
   does not track the verify growth at the small levels — session drift moves
   wall p50 by ±500 ms between levels, which is exactly why the verify-split
   timer, not wall time, is the measurement. Audit note: an earlier draft of
   this file claimed "E2E growth equals verify growth at every level"; the
   500 ms level falsifies that (E2E −535 vs verify +553) and it was corrected.
4. Every level's median rises by slightly more than the injected value (excess
   39–77 ms, roughly constant across levels). Part is structural: the
   transient-outage golden case (g3) pays the delay twice — once on the failed
   read-back, once on the protocol's own retry. The excess is reported, not
   fully explained; audit corrected an earlier draft that attributed the 100 ms
   level's +139 entirely to g3.
5. At 5000 ms — far beyond any honest read of a local stub — every case still
   closes: within this range a slow vendor means a slower close, not a stuck
   ticket.
6. Absolute wall times sit above `tab:overhead`'s frozen values because this
   scan ran against a database holding all evaluation state accumulated since
   2026-09-10. Each level is compared against the scan's own 0 ms arm; the
   slope is the finding, not the intercept. The naive arm's wall drifts
   downward across the session (levels ran ascending); at no level does it grow
   with the delay.

## Provenance caveat

Per-level directories contain `run-<stamp>.json` (full per-mediator
distributions) and `latest.{json,md}`. The smoke test that validated the
injection mechanism (100 ms, repeats=1) is not archived; it was a mechanism
check, not data.
