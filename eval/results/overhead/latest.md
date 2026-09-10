# Mediator overhead

Every applicable case, 8 repeats, vendor column `mock`. The naive row is not zero: it is the cost of asking whether each mediator is loaded.

| arm | cases | wall p50 (ms) | wall p95 (ms) | SQL statements/case | worker passes |
|---|---|---|---|---|---|
| naive | 32 | 938 | 995 | 188.5 | 1.50 |
| full | 32 | 1089 | 1168 | 239.5 | 1.50 |

| mediator | arm | p50 (ms) | p95 (ms) | decisions |
|---|---|---|---|---|
| close | naive | 0.00 | 0.00 | 32 |
| close | full | 0.01 | 0.01 | 32 |
| bind | naive | 0.01 | 0.01 | 24 |
| bind | full | 0.02 | 0.03 | 24 |
| verify | naive | 40.85 | 49.89 | 32 |
| verify | full | 158.00 | 168.25 | 32 |
| egress | naive | 0.01 | 0.02 | 48 |
| egress | full | 0.09 | 0.12 | 112 |
