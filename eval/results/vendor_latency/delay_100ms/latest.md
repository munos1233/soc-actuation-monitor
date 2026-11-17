# Mediator overhead

Every applicable case, 8 repeats, vendor column `mock`. The naive row is not zero: it is the cost of asking whether each mediator is loaded. Vendor read-back delay injected: 100 ms.

| arm | cases | wall p50 (ms) | wall p95 (ms) | SQL statements/case | worker passes |
|---|---|---|---|---|---|
| naive | 32 | 3730 | 5499 | 146.8 | 1.50 |
| full | 32 | 3948 | 5989 | 168.6 | 1.50 |

| mediator | arm | p50 (ms) | p95 (ms) | decisions |
|---|---|---|---|---|
| close | naive | 0.00 | 0.01 | 32 |
| close | full | 0.01 | 0.03 | 32 |
| bind | naive | 0.01 | 0.01 | 24 |
| bind | full | 0.03 | 0.05 | 24 |
| verify | naive | 49.80 | 79.69 | 32 |
| verify | full | 317.69 | 415.63 | 32 |
| egress | naive | 0.02 | 0.03 | 48 |
| egress | full | 0.12 | 0.20 | 112 |
