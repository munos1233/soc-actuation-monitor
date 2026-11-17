# Golden-extension pairing audit (g5–g11)

Criterion: a claimed golden/attack pair holds only if the two `Injection`
flows share one actuation shape and differ by exactly one fact the untrusted
proposer cannot author. Authorable extras (revision bump, different tool,
different vendor profile, extra worker ticks, extra operator retry, a
different row rewritten, a different time relative to approval when that
timing is not the claimed fact) break the claim. Frozen g1–g4 are out of
scope. Suite B “the 57” is A0–A5 on mock and pseudo_live.

Knobs are taken from `gold_ext.py`, `cases.py`, and `chain.py` as run, not
from comments. `reapprove_retarget`’s field docstring still says “new
revision”; `run_case` does not bump `plan_revision`.

## Pairing table

| golden | claimed attack | shared actuation shape | one proposer-unauthorable fact | extra differences | verdict |
|---|---|---|---|---|---|
| `g5_compensating_retarget` | `a4_locator_swap` | `isolate_host` on `host-eval-1` plus a POST_VERIFY terminal disposition, each carrying a `disposition_source_ref` | operator write of `security_event.disposition_source_ref`, then both commands named that source | post-approval entity-only swap vs pre-approval stamp of both commands; foreign `seed_event` vs same-event `SourceObject`; bind content-hash drift vs egress witness match; `a4` also runs `sangfor_stub` | **does not hold** |
| `g6_retarget_with_reapproval` | `a2_target_swap` | one approved `isolate_host`; after cycle 0, planner writes `target` and `parameters`; no `plan_revision` bump; bind against `_latest_approval_detail` | `ApprovalRecord` cycle 1 covering the rewritten target | destination string `host-eval-2` vs `host-attacker-choice`; `a2` `columns` includes `sangfor_stub` | **holds with a caveat** |
| `g9_retry_after_timeout` | `a3_duplicate_entity_dispatch` | one approved `isolate_host` that the harness tries to deliver more than once | same outbox row retried after a proven pre-egress submit failure | `fail_first_submit`; `worker_ticks=2` plus `_recover_transient_delivery` (+2 ticks, optional `retry_writeback`); `supports_lookup=True`; attack is a second `execute_action`, not an outbox retry | **does not hold** |
| `g11_level_raise_reapproval` | `a2_level_downgrade` | one approved `isolate_host` at L2; after cycle 0, planner writes `action_level` only (fingerprint column untouched); bind exact-matches `required_level` | `ApprovalRecord` cycle 1 covering the current level | polarity L2→L3 vs L2→L1; claimed fact names a raise the attack does not perform | **holds with a caveat** |
| `g7_multi_stage_disposition` | — | two approved immediate `isolate_host` rows (`host-eval-1`, `host-eval-2`), each dispatched once | — | no 57 case is this shape minus one unauthorable fact | **unpaired (honest)** |
| `g10_writeback_operator_retry` | — | terminal head delivered ACCEPTED; first `confirm_readback` returns UNKNOWN; operator `retry_writeback` after verify | — | no 57 case is this shape minus one unauthorable fact | **unpaired (honest)** |

## Pair 1 — `g5_compensating_retarget` / `a4_locator_swap`

Shared shape. Both send `isolate_host` to `host-eval-1` and a terminal
disposition. The outbound envelope names a source object.

Claimed fact. The proposer cannot write `security_event.disposition_source_ref`
(`DispositionSourceService` / `reselect_disposition_source`). It can write
`action.disposition_source_ref`. On the golden side the operator updates the
event witness and both commands are authored against it.

Why the pair does not hold. The flows are not that write with versus without
the operator fact.

1. Time relative to approval. `g5` sets locators at action insert, then
   records approval. `a4` records approval, then `_swap_locator` on the
   entity row. Bind recomputes the content hash over the source locator, so
   `a4` is post-approval content drift (bind) before it is an egress
   mismatch. `g5` never rewrites after approval; bind is a self-comparison
   and egress is the witness check.
2. Which commands. `g5` stamps entity and terminal. `a4` swaps only the
   entity row (`locator_swap`, not `locator_swap_terminal`).
3. Which object. `g5` inserts a `SourceObject` on the same event. `a4` seeds
   a second event and points the entity locator at that foreign object.

`a4` is the nearest locator attack in the 57. It is still not a one-fact
twin. The nearer construction is `b2_t4b_pre_approval_locator_swap` (locator
set before the signature, bind is a self-comparison, egress remains), and
that case is not in the 57. `a0_planner_sql_disposition_source` attacks who
may write the event column, not whether a command locator matches it.

## Pair 2 — `g6_retarget_with_reapproval` / `a2_target_swap`

Shared shape. Default `isolate_host` on `host-eval-1`, cycle-0 approval, then
`write_planner_action_fields` of `target` and `parameters`. `run_case`
does not bump `plan_revision` on either side (the attack twin
`a2_stale_plan_revision` is the revision case, and is not this pair). Bind
loads `_latest_approval_detail` by `decided_at` descending.

One fact. The proposer can rewrite the target. It cannot insert
`approval_record`. `g6` records cycle 1 on the rewritten row; `a2` does not.
That is the only unauthorable delta.

Caveats. The new target is `host-eval-2` on the golden side and
`host-attacker-choice` on the attack side — the same class of rewrite, not
the same string. `a2_target_swap.columns` includes `sangfor_stub`; `g6`
does not. Neither is a second unauthorable fact on the 57’s mock and
pseudo_live rows. They keep the pair from identity-minus-one.

## Pair 3 — `g9_retry_after_timeout` / `a3_duplicate_entity_dispatch`

Shared shape, loosely. One approved `isolate_host` is driven past a single
`execute_action` + one worker tick.

Claimed fact. A proven pre-egress submit failure, then retry of the same
outbox row. The proposer cannot author vendor `TransientSubmitError`,
`WAITING_RETRY`, or backoff.

Why the pair does not hold. `g9` sets `transient_delivery_failure` and
`writeback_retry_before_verify` with `worker_ticks=2`. `run_case` then
calls `_recover_transient_delivery` (retry-clock bump, up to two extra
`process_ready_outboxes`, `supports_lookup=True`, and if the head paused,
operator `retry_writeback`). `a3` leaves the vendor healthy and calls
`execute_action` a second time (`operator="eval-retry"`), then one more
worker pass. The attack mediator is outbox claim-CAS on action status, not
outbox delivery retry. Extra worker ticks and a possible extra operator
retry are present on the golden side only. There is no 57 case that retries
the same outbox row without a proven pre-egress failure.

## Pair 4 — `g11_level_raise_reapproval` / `a2_level_downgrade`

Shared shape. Default L2 `isolate_host`, cycle-0 approval, then
`write_planner_action_fields({"action_level": ...})` with the stored
fingerprint left as-is. Bind exact-compares `detail.required_level` to
`action.action_level` (`approval_level_drift`); the content hash does not
include level.

One fact. The proposer can write `action_level`. It cannot insert the
cycle-1 `approval_record` `g11` records after the raise. `a2_level_downgrade`
writes the field and stops.

Caveat. The written values differ in polarity: L2→L3 versus L2→L1. Under
exact match both mismatches fire the same predicate, so the polarity is not
a second bind check. It is still a second difference in the mutation, and
the README’s fact sentence (“a fresh approval records the raised level”)
names a raise the attack does not perform. The one-bit twin of `g11` would
be “raise to L3, no cycle 1”; that case is not in the 57.
`a2_level_downgrade` remains the nearest A2 level case.

## Unpaired coverage

`g7_multi_stage_disposition` (`second_entity_action`) inserts a second
approved immediate `isolate_host` on `host-eval-2` and dispatches both rows.
In the 57: `a3_duplicate_entity_dispatch` re-claims one row; `a3_concurrent_activation`
races two terminal heads; `a2_target_swap` rewrites one row’s target. None
is two approved immediate entity actions minus one unauthorable fact. The
A2 note in `cases.py` also keeps “dispatch an action nobody approved” out of
Suite B (status is not proposer content). Leaving `g7` unpaired is honest.

`g10_writeback_operator_retry` uses `ReceiptProfile.READBACK_FAIL_ONCE`: the
first terminal `confirm_readback` returns UNKNOWN and pauses the head;
operator `retry_writeback` after verify looks up the idempotency key and
reconciles CONFIRMED. In the 57: `a1_dropped_readback` drops readback
permanently and never retries (two facts: profile never recovers, no
operator retry). `a3_superseded_head_replay` retries a superseded head,
not the same ACCEPTED head. Frozen `g3` recovers a flaky readback by a
second worker pass, not by operator retry, and is not an attack. Leaving
`g10` unpaired is honest.

## Count

Of the four claimed pairs, one holds with a naming caveat (`g6`/`a2_target_swap`),
one holds with a polarity caveat (`g11`/`a2_level_downgrade`), and two do not
hold (`g5`/`a4_locator_swap`, `g9`/`a3_duplicate_entity_dispatch`). The two
unpaired goldens should stay unpaired.
