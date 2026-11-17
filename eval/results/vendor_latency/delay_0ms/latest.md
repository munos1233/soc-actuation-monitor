# Mediator overhead

Every applicable case, 8 repeats, vendor column `mock`. The naive row is not zero: it is the cost of asking whether each mediator is loaded.

| arm | cases | wall p50 (ms) | wall p95 (ms) | SQL statements/case | worker passes |
|---|---|---|---|---|---|
| naive | 32 | 3583 | 4428 | 146.6 | 1.50 |
| full | 32 | 3721 | 5323 | 168.5 | 1.50 |

| mediator | arm | p50 (ms) | p95 (ms) | decisions |
|---|---|---|---|---|
| close | naive | 0.00 | 0.01 | 32 |
| close | full | 0.01 | 0.03 | 32 |
| bind | naive | 0.01 | 0.02 | 24 |
| bind | full | 0.03 | 0.05 | 24 |
| verify | naive | 43.36 | 65.37 | 32 |
| verify | full | 178.68 | 313.17 | 32 |
| egress | naive | 0.02 | 0.03 | 48 |
| egress | full | 0.11 | 0.18 | 112 |
