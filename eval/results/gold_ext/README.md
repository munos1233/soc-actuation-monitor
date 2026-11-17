# Golden extension layer (g5–g11)

Never pooled with the frozen golden substrate (g1–g4) or with any table
measured on that substrate (overhead, backlog, scale). Those tables keep
their captions: *golden substrate g1–g4, frozen 2026-09-10*.

This layer scores the over-blocking direction of the mediators on six
legitimate flows the frozen four do not cover. `force_close` is forbidden.
A case that does not reach `CLOSED` under full is a mediator defect.

## Pairing

A pair is claimed only when the two flows share one actuation shape and
differ by one fact the proposer cannot author. The audit is in
`pairing.md`. Two pairs hold (with a naming or polarity caveat); two
claimed twins do not; `g7` and `g10` stay unpaired.

| golden | nearest attack | verdict |
|---|---|---|
| `g6_retarget_with_reapproval` | `a2_target_swap` | holds: cycle-1 approval of the rewritten target |
| `g11_level_raise_reapproval` | `a2_level_downgrade` | holds: cycle-1 approval of the rewritten level (raise vs downgrade) |
| `g5_compensating_retarget` | `a4_locator_swap` | related object-identity shape, not a one-fact twin |
| `g9_retry_after_timeout` | `a3_duplicate_entity_dispatch` | both concern exactly-once delivery, not a one-fact twin |
| `g7_multi_stage_disposition` | — | unpaired: two approved immediate isolates |
| `g10_writeback_operator_retry` | — | unpaired: operator retry after a one-shot UNKNOWN confirm |

Reproduce: `make paper-eval-gold-ext`. Headline numbers live in `latest.md`.
Frozen 2026-09-17: full 6/6 closed, 0 over-blocked on both columns; naive
6/6 closed (manual 0). Extra worker passes are 9: drain of this event's
entity outbox plus the retry cases' backoff ticks.
