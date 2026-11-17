# Mediator overhead

Every applicable case, 8 repeats, vendor column `mock`. The naive row is not zero: it is the cost of asking whether each mediator is loaded. Vendor read-back delay injected: 1000 ms.

| arm | cases | wall p50 (ms) | wall p95 (ms) | SQL statements/case | worker passes |
|---|---|---|---|---|---|
| naive | 32 | 2467 | 3503 | 146.8 | 1.50 |
| full | 32 | 3436 | 5016 | 168.5 | 1.50 |

| mediator | arm | p50 (ms) | p95 (ms) | decisions |
|---|---|---|---|---|
| close | naive | 0.00 | 0.01 | 32 |
| close | full | 0.01 | 0.02 | 32 |
| bind | naive | 0.01 | 0.01 | 24 |
| bind | full | 0.03 | 0.03 | 24 |
| verify | naive | 37.42 | 50.76 | 32 |
| verify | full | 1244.37 | 1384.32 | 32 |
| egress | naive | 0.01 | 0.02 | 48 |
| egress | full | 0.09 | 0.13 | 112 |
