# Actuation-integrity evaluation

## Suite B: boundary injection through the real chain

### vendor column: mock

| configuration | A1 | A2 | A3 | A4 | A5 | total |
|---|---|---|---|---|---|---|
| naive | 5/5 | 4/5 | 0/4 | 3/3 | 4/4 | 16/21 |
| close_only | 0/5 | 4/5 | 0/4 | 3/3 | 2/4 | 9/21 |
| bind_only | 5/5 | 0/5 | 0/4 | 2/3 | 4/4 | 11/21 |
| verify_only | 5/5 | 4/5 | 0/4 | 3/3 | 2/4 | 14/21 |
| egress_only | 5/5 | 4/5 | 0/4 | 0/3 | 4/4 | 13/21 |
| full | 1/5 | 0/5 | 0/4 | 0/3 | 0/4 | 1/21 |
| full_minus_close | 5/5 | 0/5 | 0/4 | 0/3 | 2/4 | 7/21 |
| full_minus_bind | 1/5 | 4/5 | 0/4 | 0/3 | 0/4 | 5/21 |
| full_minus_verify | 0/5 | 0/5 | 0/4 | 0/3 | 2/4 | 2/21 |
| full_minus_egress | 1/5 | 0/5 | 0/4 | 2/3 | 0/4 | 3/21 |
| full_minus_head_index | 1/5 | 0/5 | 0/4 | 0/3 | 0/4 | 1/21 |
| full_minus_head_supersede | 1/5 | 0/5 | 0/4 | 0/3 | 0/4 | 1/21 |
| full_minus_head_uniqueness | 1/5 | 0/5 | 2/4 | 0/3 | 0/4 | 3/21 |
| full_minus_head_assertion | 1/5 | 0/5 | 2/4 | 0/3 | 0/4 | 3/21 |
| full_minus_claim_cas | 1/5 | 0/5 | 1/4 | 0/3 | 0/4 | 2/21 |

### vendor column: pseudo_live

| configuration | A1 | A2 | A3 | A4 | A5 | total |
|---|---|---|---|---|---|---|
| naive | 6/6 | 4/5 | 0/4 | 3/3 | 4/4 | 17/22 |
| close_only | 0/6 | 4/5 | 0/4 | 3/3 | 2/4 | 9/22 |
| bind_only | 6/6 | 0/5 | 0/4 | 2/3 | 4/4 | 12/22 |
| verify_only | 6/6 | 4/5 | 0/4 | 3/3 | 2/4 | 15/22 |
| egress_only | 6/6 | 4/5 | 0/4 | 0/3 | 4/4 | 14/22 |
| full | 0/6 | 0/5 | 0/4 | 0/3 | 0/4 | 0/22 |
| full_minus_close | 6/6 | 0/5 | 0/4 | 0/3 | 2/4 | 8/22 |
| full_minus_bind | 0/6 | 4/5 | 0/4 | 0/3 | 0/4 | 4/22 |
| full_minus_verify | 0/6 | 0/5 | 0/4 | 0/3 | 2/4 | 2/22 |
| full_minus_egress | 0/6 | 0/5 | 0/4 | 2/3 | 0/4 | 2/22 |
| full_minus_head_index | 0/6 | 0/5 | 0/4 | 0/3 | 0/4 | 0/22 |
| full_minus_head_supersede | 0/6 | 0/5 | 0/4 | 0/3 | 0/4 | 0/22 |
| full_minus_head_uniqueness | 0/6 | 0/5 | 2/4 | 0/3 | 0/4 | 2/22 |
| full_minus_head_assertion | 0/6 | 0/5 | 2/4 | 0/3 | 0/4 | 2/22 |
| full_minus_claim_cas | 0/6 | 0/5 | 1/4 | 0/3 | 0/4 | 1/22 |

### harm still reachable with every mediator loaded

| case | column | harm | detail |
|---|---|---|---|
| a1_weak_receipt | mock | wrong_close | event reached CLOSED on incomplete evidence |

### leave-one-out: marginal harm of removing one mediator

| configuration | mediator removed | harm | marginal |
|---|---|---|---|
| full | — | 1/43 | — |
| full_minus_close | close | 15/43 | +14 |
| full_minus_bind | bind | 9/43 | +8 |
| full_minus_verify | verify | 4/43 | +3 |
| full_minus_egress | egress | 5/43 | +4 |

### substrate ablation: mechanisms with no production switch, weakened in the harness

| configuration | mechanisms weakened | harm | marginal |
|---|---|---|---|
| full | — | 1/43 | — |
| full_minus_head_index | head_index | 1/43 | +0 |
| full_minus_head_supersede | head_supersede | 1/43 | +0 |
| full_minus_head_uniqueness | head_index, head_supersede | 5/43 | +4 |
| full_minus_head_assertion | head_index, head_supersede, head_assertion | 5/43 | +4 |
| full_minus_claim_cas | claim_cas | 3/43 | +2 |

## Baseline: dead playbook (no adaptive planner)

### vendor column: mock

| configuration | A1 | A2 | A3 | A4 | A5 | total |
|---|---|---|---|---|---|---|
| naive | 4/4 | - | 0/3 | - | 4/4 | 8/11 |
| close_only | 0/4 | - | 0/3 | - | 2/4 | 2/11 |
| bind_only | 4/4 | - | 0/3 | - | 4/4 | 8/11 |
| verify_only | 4/4 | - | 0/3 | - | 2/4 | 6/11 |
| egress_only | 4/4 | - | 0/3 | - | 4/4 | 8/11 |
| full | 1/4 | - | 0/3 | - | 0/4 | 1/11 |
| full_minus_close | 4/4 | - | 0/3 | - | 2/4 | 6/11 |
| full_minus_bind | 1/4 | - | 0/3 | - | 0/4 | 1/11 |
| full_minus_verify | 0/4 | - | 0/3 | - | 2/4 | 2/11 |
| full_minus_egress | 1/4 | - | 0/3 | - | 0/4 | 1/11 |
| full_minus_head_index | 1/4 | - | 0/3 | - | 0/4 | 1/11 |
| full_minus_head_supersede | 1/4 | - | 0/3 | - | 0/4 | 1/11 |
| full_minus_head_uniqueness | 1/4 | - | 2/3 | - | 0/4 | 3/11 |
| full_minus_head_assertion | 1/4 | - | 2/3 | - | 0/4 | 3/11 |
| full_minus_claim_cas | 1/4 | - | 0/3 | - | 0/4 | 1/11 |

### vendor column: pseudo_live

| configuration | A1 | A2 | A3 | A4 | A5 | total |
|---|---|---|---|---|---|---|
| naive | 5/5 | - | 0/3 | - | 4/4 | 9/12 |
| close_only | 0/5 | - | 0/3 | - | 2/4 | 2/12 |
| bind_only | 5/5 | - | 0/3 | - | 4/4 | 9/12 |
| verify_only | 5/5 | - | 0/3 | - | 2/4 | 7/12 |
| egress_only | 5/5 | - | 0/3 | - | 4/4 | 9/12 |
| full | 0/5 | - | 0/3 | - | 0/4 | 0/12 |
| full_minus_close | 5/5 | - | 0/3 | - | 2/4 | 7/12 |
| full_minus_bind | 0/5 | - | 0/3 | - | 0/4 | 0/12 |
| full_minus_verify | 0/5 | - | 0/3 | - | 2/4 | 2/12 |
| full_minus_egress | 0/5 | - | 0/3 | - | 0/4 | 0/12 |
| full_minus_head_index | 0/5 | - | 0/3 | - | 0/4 | 0/12 |
| full_minus_head_supersede | 0/5 | - | 0/3 | - | 0/4 | 0/12 |
| full_minus_head_uniqueness | 0/5 | - | 2/3 | - | 0/4 | 2/12 |
| full_minus_head_assertion | 0/5 | - | 2/3 | - | 0/4 | 2/12 |
| full_minus_claim_cas | 0/5 | - | 0/3 | - | 0/4 | 0/12 |

### harm still reachable with every mediator loaded

| case | column | harm | detail |
|---|---|---|---|
| a1_weak_receipt | mock | wrong_close | event reached CLOSED on incomplete evidence |

Excluded from every cell above as not applicable to this arm (10 cases): a1_stale_closure_cycle, a2_forged_fingerprint, a2_level_downgrade, a2_stale_plan_revision, a2_target_swap, a2_tool_escalation, a3_idempotency_key_rewrite, a4_locator_swap, a4_narrative_in_target, a4_secret_in_target.

### suite A: golden path under the Full configuration

| column | closed | over-blocked | manual | extra worker passes |
|---|---|---|---|---|
| mock | 4/4 | 0 | 0 | 2 |
| pseudo_live | 4/4 | 0 | 0 | 2 |

`force_close` was not used in any suite A run.

### suite A control: same cases with every mediator unloaded

| column | closed | over-blocked | manual | extra worker passes |
|---|---|---|---|---|
| mock | 4/4 | 0 | 4 | 2 |
| pseudo_live | 4/4 | 0 | 4 | 2 |

`force_close` was not used in any suite A run.

## Appendix: predicate-level checks (not mediation evidence)

- `binding_rejects_content_drift`: {"rejected": true, "reason": "action_content_drift"}
- `binding_switch_unloads`: {"unloaded": true}
- `guard_blocks_narrative`: {"blocked": true, "rules": ["no_analysis_content_outbound"]}
- `guard_blocks_foreign_locator`: {"blocked": true, "rules": ["disposition_source_match"]}
- `verify_switch_flips_deferred_accounting`: {"with_phase_split": false, "without_phase_split": true}
