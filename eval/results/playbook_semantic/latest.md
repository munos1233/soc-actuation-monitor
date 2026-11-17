# Playbook-semantic closer

Not a commercial SOAR evaluation. Closer writes CLOSED on step SUCCESS.

| arm | suite A closed |
|---|---|
| `playbook_semantic` | 8/8 |
| `naive` | 8/8 |
| `full` | 8/8 |

| case | column | playbook_semantic | naive | full |
|---|---|---|---|---|
| `a1_dropped_readback` | mock | harm | harm | ok |
| `a1_dropped_readback` | pseudo_live | harm | harm | ok |
| `a1_weak_receipt` | mock | harm | harm | ok |
| `a1_weak_receipt` | pseudo_live | harm | harm | ok |
| `a5_echo_observation` | mock | harm | harm | ok |
| `a5_echo_observation` | pseudo_live | harm | harm | ok |
| `a5_lying_vendor_receipt` | mock | harm | harm | ok |
| `a5_lying_vendor_receipt` | pseudo_live | harm | harm | ok |
