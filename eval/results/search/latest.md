# Coverage search over implemented Injection knobs

Budget 512; space 960; attempted 512; coverage cells 5.

No new harm class within the implemented-knob space under the full configuration. This is not a claim that the threat distribution is exhausted.

| closed | harmed | entity_submit | blocked |
|---|---|---|---|
| False | False | True | — |
| False | False | False | validation_error |
| True | False | True | — |
| True | False | True | invalid_state_transition |
| False | False | True | invalid_state_transition |
