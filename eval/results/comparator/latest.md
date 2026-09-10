# Actuation-integrity evaluation

## Suite B: boundary injection through the real chain

### vendor column: mock

| configuration | A1 | A2 | A3 | A4 | A5 | total |
|---|---|---|---|---|---|---|
| naive | 5/5 | 4/5 | 0/4 | 3/3 | 4/4 | 16/21 |
| full | 1/5 | 0/5 | 0/4 | 0/3 | 0/4 | 1/21 |

### vendor column: pseudo_live

| configuration | A1 | A2 | A3 | A4 | A5 | total |
|---|---|---|---|---|---|---|
| naive | 6/6 | 4/5 | 0/4 | 3/3 | 4/4 | 17/22 |
| full | 0/6 | 0/5 | 0/4 | 0/3 | 0/4 | 0/22 |

### harm still reachable with every mediator loaded

| case | column | harm | detail |
|---|---|---|---|
| a1_weak_receipt | mock | wrong_close | event reached CLOSED on incomplete evidence |

### leave-one-out: marginal harm of removing one mediator

| configuration | mediator removed | harm | marginal |
|---|---|---|---|
| full | — | 1/43 | — |

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

### suite A comparator: same cases with an external policy engine in place of the mediators

| column | closed | over-blocked | manual | extra worker passes |
|---|---|---|---|---|
| mock | 4/4 | 0 | 4 | 2 |
| pseudo_live | 4/4 | 0 | 4 | 2 |

`force_close` was not used in any suite A run.

### where each arm sits: benign closure against harm

| arm | benign closed (Suite A) | harm (Suite B) | harm rate | 95% Wilson |
|---|---|---|---|---|
| external_opa | 8/8 | 14/43 | 0.33 | [0.20, 0.47] |
| full | 8/8 | 1/43 | 0.02 | [0.00, 0.12] |
| naive | 8/8 | 33/43 | 0.77 | [0.62, 0.87] |

## Appendix: predicate-level checks (not mediation evidence)

- `binding_rejects_content_drift`: {"rejected": true, "reason": "action_content_drift"}
- `binding_switch_unloads`: {"unloaded": true}
- `guard_blocks_narrative`: {"blocked": true, "rules": ["no_analysis_content_outbound"]}
- `guard_blocks_foreign_locator`: {"blocked": true, "rules": ["disposition_source_match"]}
- `verify_switch_flips_deferred_accounting`: {"with_phase_split": false, "without_phase_split": true}
