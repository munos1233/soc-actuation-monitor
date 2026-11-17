# Actuation-integrity evaluation

## Suite B: boundary injection through the real chain

### vendor column: sangfor_stub

| configuration | A1 | A2 | A4 | total |
|---|---|---|---|---|
| naive | 2/2 | 2/2 | 3/3 | 7/7 |
| full | 0/2 | 0/2 | 0/3 | 0/7 |

### harm still reachable with every mediator loaded

None.

### leave-one-out: marginal harm of removing one mediator

| configuration | mediator removed | harm | marginal |
|---|---|---|---|
| full | — | 0/7 | — |

## Appendix: predicate-level checks (not mediation evidence)

- `binding_rejects_content_drift`: {"rejected": true, "reason": "action_content_drift"}
- `binding_switch_unloads`: {"unloaded": true}
- `guard_blocks_narrative`: {"blocked": true, "rules": ["no_analysis_content_outbound"]}
- `guard_blocks_foreign_locator`: {"blocked": true, "rules": ["disposition_source_match"]}
- `verify_switch_flips_deferred_accounting`: {"with_phase_split": false, "without_phase_split": true}
