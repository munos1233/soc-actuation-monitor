# Coverage search over implemented Injection knobs

Budget 960; space 960; attempted 960; coverage cells 6.

No new harm class within the implemented-knob space under the full configuration. This is not a claim that the threat distribution is exhausted.

| closed | harmed | entity_submit | blocked |
|---|---|---|---|
| False | False | True | — |
| False | False | False | validation_error |
| True | False | True | — |
| True | False | True | invalid_state_transition |
| False | False | True | invalid_state_transition |
| False | False | False | ValidationError |
