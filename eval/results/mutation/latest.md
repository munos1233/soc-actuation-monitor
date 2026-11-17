# Mutation kill rate (FULL only)

Never pooled with Suite B 57. Production code does not import these
mutants. Kill is relative to an unmutated FULL pass: harm-kill is an
attack FULL prevents that the mutant lets through; over-strict-kill is
a golden FULL closes that the mutant refuses.

killed 17/18  survivors 1  unexpected 0

| mutant | family | status | harm-kills | over-strict | named hit |
|---|---|---|---|---|---|
| `m1_bind_planner_fingerprint` | M1 | killed | `a2_level_downgrade`, `a2_stale_plan_revision`, `a2_target_swap`, `a2_tool_escalation`, `b2_t1a_terminal_template_rewrite`, `b2_t1b_execution_owner_rewrite` | — | `a2_target_swap`, `a2_tool_escalation`, `a2_stale_plan_revision`, `a2_level_downgrade` |
| `m1_bind_partial_fingerprint` | M1 | killed | `b2_t1b_execution_owner_rewrite` | — | `b2_t1b_execution_owner_rewrite` |
| `m1_close_planner_cycle` | M1 | survivor | — | — | — |
| `m1_close_skip_report` | M1 | killed | `a1_missing_report` | — | `a1_missing_report` |
| `m1_close_weak_evidence_ok` | M1 | killed | `a1_weak_receipt`, `a5_lying_vendor_receipt` | — | `a1_weak_receipt` |
| `m1_simulated_receipt_ok` | M1 | killed | `a1_simulated_receipt` | — | `a1_simulated_receipt` |
| `m1_verify_echo_verified` | M1 | killed | `a5_echo_observation` | — | `a5_echo_observation` |
| `m1_verify_missing_field_verified` | M1 | killed | `a5_echo_observation`, `a5_empty_observation` | — | `a5_empty_observation` |
| `m1_verify_false_negative` | M1 | killed | `b2_t6b_honest_negative_observation` | — | `b2_t6b_honest_negative_observation` |
| `m1_egress_self_witness` | M1 | killed | `b2_t4b_pre_approval_locator_swap` | — | `b2_t4b_pre_approval_locator_swap` |
| `m1_egress_no_content_scan` | M1 | killed | `a4_narrative_in_target`, `a4_secret_in_target` | — | `a4_narrative_in_target` |
| `m1_template_unchanged_revert` | M1 | killed | `b2_t1a_terminal_template_rewrite` | — | `b2_t1a_terminal_template_rewrite` |
| `m4_locator_creation_source` | M4 | killed | — | `g5_compensating_retarget` | `g5_compensating_retarget` |
| `m4_bind_first_approval` | M4 | killed | — | `g11_level_raise_reapproval`, `g6_retarget_with_reapproval` | `g6_retarget_with_reapproval` |
| `m4_level_first_approval` | M4 | killed | — | `g11_level_raise_reapproval` | `g11_level_raise_reapproval` |
| `m4_one_immediate_action_per_event` | M4 | killed | — | `g7_multi_stage_disposition` | `g7_multi_stage_disposition` |
| `m4_verify_no_recovery` | M4 | killed | — | `g10_writeback_operator_retry` | `g10_writeback_operator_retry` |
| `m4_outbox_no_retry` | M4 | killed | — | `g9_retry_after_timeout` | `g9_retry_after_timeout` |

