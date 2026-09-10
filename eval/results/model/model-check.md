## Model check: terminal-head activation

### `shared_action`, K = 2

| mechanisms | states | I3 | I5 | I6 | I2a |
|---|---|---|---|---|---|
| `full` | 29 | holds | holds | holds | holds |
| `minus_claim_cas` | 164 | holds | violated (17) | holds | violated (4) |
| `minus_head_index` | 29 | holds | holds | holds | holds |
| `minus_head_supersede` | 29 | holds | holds | holds | holds |
| `minus_head_uniqueness` | 29 | holds | holds | holds | holds |
| `minus_head_uniqueness_and_assertion` | 29 | holds | holds | holds | holds |
| `naive` | 234 | violated (8) | violated (16) | violated (12) | violated (4) |

### `shared_action`, K = 3

| mechanisms | states | I3 | I5 | I6 | I2a |
|---|---|---|---|---|---|
| `full` | 85 | holds | holds | holds | holds |
| `minus_claim_cas` | 4033 | holds | violated (17) | holds | violated (4) |
| `minus_head_index` | 85 | holds | holds | holds | holds |
| `minus_head_supersede` | 85 | holds | holds | holds | holds |
| `minus_head_uniqueness` | 85 | holds | holds | holds | holds |
| `minus_head_uniqueness_and_assertion` | 85 | holds | holds | holds | holds |
| `naive` | 12478 | violated (8) | violated (16) | violated (12) | violated (4) |

### `shared_action`, K = 4

| mechanisms | states | I3 | I5 | I6 | I2a |
|---|---|---|---|---|---|
| `full` | 225 | holds | holds | holds | holds |
| `minus_claim_cas` | 128748 | holds | violated (17) | holds | violated (4) |
| `minus_head_index` | 225 | holds | holds | holds | holds |
| `minus_head_supersede` | 225 | holds | holds | holds | holds |
| `minus_head_uniqueness` | 225 | holds | holds | holds | holds |
| `minus_head_uniqueness_and_assertion` | 225 | holds | holds | holds | holds |
| `naive` | 1190752 | violated (8) | violated (16) | violated (12) | violated (4) |

### `distinct_actions`, K = 2

| mechanisms | states | I3 | I5 | I6 | I2a |
|---|---|---|---|---|---|
| `full` | 119 | holds | holds | holds | holds |
| `minus_claim_cas` | 136 | holds | holds | holds | holds |
| `minus_head_index` | 179 | violated (6) | holds | violated (10) | holds |
| `minus_head_supersede` | 81 | holds | holds | holds | holds |
| `minus_head_uniqueness` | 189 | violated (6) | holds | violated (10) | holds |
| `minus_head_uniqueness_and_assertion` | 189 | violated (6) | holds | violated (10) | holds |
| `naive` | 206 | violated (8) | holds | violated (12) | holds |

### `distinct_actions`, K = 3

| mechanisms | states | I3 | I5 | I6 | I2a |
|---|---|---|---|---|---|
| `full` | 2775 | holds | holds | holds | holds |
| `minus_claim_cas` | 3157 | holds | holds | holds | holds |
| `minus_head_index` | 9870 | violated (6) | holds | violated (10) | holds |
| `minus_head_supersede` | 789 | holds | holds | holds | holds |
| `minus_head_uniqueness` | 10980 | violated (6) | holds | violated (10) | holds |
| `minus_head_uniqueness_and_assertion` | 10590 | violated (6) | holds | violated (10) | holds |
| `naive` | 11182 | violated (8) | holds | violated (12) | holds |

### `distinct_actions`, K = 4

| mechanisms | states | I3 | I5 | I6 | I2a |
|---|---|---|---|---|---|
| `full` | 88317 | holds | holds | holds | holds |
| `minus_claim_cas` | 100164 | holds | holds | holds | holds |
| `minus_head_index` | 1004749 | violated (6) | holds | violated (10) | holds |
| `minus_head_supersede` | 7113 | holds | holds | holds | holds |
| `minus_head_uniqueness` | 1160881 | violated (6) | holds | violated (10) | holds |
| `minus_head_uniqueness_and_assertion` | 1052761 | violated (6) | holds | violated (10) | holds |
| `naive` | 1096288 | violated (8) | holds | violated (12) | holds |

Cells give the length of the shortest counterexample in steps.

- **I3**: at most one active terminal head per (event, closure cycle, intent, slot)
- **I5**: one approved action produces at most one external effect
- **I6**: no superseded head is ever delivered
- **I2a**: at most one worker writes an action's execution status

### Shortest counterexamples

**I5 under `minus_claim_cas`, `shared_action`, K=2** — one approved action produces at most one external effect

1. w0: read action 0 status (approved)
2. w1: read action 0 status (approved)
3. w0: write action 0 EXECUTING on the strength of an earlier read
4. w0: SELECT prior head FOR UPDATE returns nothing
5. w0: insert head 0
6. w0: lease head 0 for delivery
7. w0: head 0 carries no supersede pointer
8. w0: head 0 is still the active head, proceed to deliver
9. w0: submit head 0 to the vendor
10. w1: write action 0 EXECUTING on the strength of an earlier read
11. w1: lock prior head 0
12. w1: head 0 is still active, adopt it as prior
13. w1: insert head 1, superseding 0
14. w1: lease head 1 for delivery
15. w1: head 1 carries no supersede pointer
16. w1: head 1 is still the active head, proceed to deliver
17. w1: submit head 1 to the vendor

**I2a under `minus_claim_cas`, `shared_action`, K=2** — at most one worker writes an action's execution status

1. w0: read action 0 status (approved)
2. w1: read action 0 status (approved)
3. w0: write action 0 EXECUTING on the strength of an earlier read
4. w1: write action 0 EXECUTING on the strength of an earlier read

**I3 under `naive`, `shared_action`, K=2** — at most one active terminal head per (event, closure cycle, intent, slot)

1. w0: read action 0 status (approved)
2. w1: read action 0 status (approved)
3. w0: write action 0 EXECUTING on the strength of an earlier read
4. w0: SELECT prior head FOR UPDATE returns nothing
5. w1: write action 0 EXECUTING on the strength of an earlier read
6. w1: SELECT prior head FOR UPDATE returns nothing
7. w0: insert head 0
8. w1: insert head 1

**I5 under `naive`, `shared_action`, K=2** — one approved action produces at most one external effect

1. w0: read action 0 status (approved)
2. w1: read action 0 status (approved)
3. w0: write action 0 EXECUTING on the strength of an earlier read
4. w0: SELECT prior head FOR UPDATE returns nothing
5. w1: write action 0 EXECUTING on the strength of an earlier read
6. w1: SELECT prior head FOR UPDATE returns nothing
7. w0: insert head 0
8. w0: lease head 0 for delivery
9. w0: head 0 carries no supersede pointer
10. w0: deliver head 0 without re-reading the active head
11. w0: submit head 0 to the vendor
12. w1: insert head 1
13. w1: lease head 1 for delivery
14. w1: head 1 carries no supersede pointer
15. w1: deliver head 1 without re-reading the active head
16. w1: submit head 1 to the vendor

**I6 under `naive`, `shared_action`, K=2** — no superseded head is ever delivered

1. w0: read action 0 status (approved)
2. w1: read action 0 status (approved)
3. w0: write action 0 EXECUTING on the strength of an earlier read
4. w0: SELECT prior head FOR UPDATE returns nothing
5. w1: write action 0 EXECUTING on the strength of an earlier read
6. w1: SELECT prior head FOR UPDATE returns nothing
7. w0: insert head 0
8. w0: lease head 0 for delivery
9. w0: head 0 carries no supersede pointer
10. w0: deliver head 0 without re-reading the active head
11. w1: insert head 1
12. w0: submit head 0 to the vendor

**I2a under `naive`, `shared_action`, K=2** — at most one worker writes an action's execution status

1. w0: read action 0 status (approved)
2. w1: read action 0 status (approved)
3. w0: write action 0 EXECUTING on the strength of an earlier read
4. w1: write action 0 EXECUTING on the strength of an earlier read

**I3 under `minus_head_index`, `distinct_actions`, K=2** — at most one active terminal head per (event, closure cycle, intent, slot)

1. w0: claim action 0 by compare-and-set, succeeds
2. w0: SELECT prior head FOR UPDATE returns nothing
3. w1: claim action 1 by compare-and-set, succeeds
4. w1: SELECT prior head FOR UPDATE returns nothing
5. w0: insert head 0
6. w1: insert head 1

**I6 under `minus_head_index`, `distinct_actions`, K=2** — no superseded head is ever delivered

1. w0: claim action 0 by compare-and-set, succeeds
2. w0: SELECT prior head FOR UPDATE returns nothing
3. w1: claim action 1 by compare-and-set, succeeds
4. w1: SELECT prior head FOR UPDATE returns nothing
5. w0: insert head 0
6. w0: lease head 0 for delivery
7. w0: head 0 carries no supersede pointer
8. w0: head 0 is still the active head, proceed to deliver
9. w1: insert head 1
10. w0: submit head 0 to the vendor

**I3 under `minus_head_uniqueness`, `distinct_actions`, K=2** — at most one active terminal head per (event, closure cycle, intent, slot)

1. w0: claim action 0 by compare-and-set, succeeds
2. w0: SELECT prior head FOR UPDATE returns nothing
3. w1: claim action 1 by compare-and-set, succeeds
4. w1: SELECT prior head FOR UPDATE returns nothing
5. w0: insert head 0
6. w1: insert head 1

**I6 under `minus_head_uniqueness`, `distinct_actions`, K=2** — no superseded head is ever delivered

1. w0: claim action 0 by compare-and-set, succeeds
2. w0: SELECT prior head FOR UPDATE returns nothing
3. w1: claim action 1 by compare-and-set, succeeds
4. w1: SELECT prior head FOR UPDATE returns nothing
5. w0: insert head 0
6. w0: lease head 0 for delivery
7. w0: head 0 carries no supersede pointer
8. w0: head 0 is still the active head, proceed to deliver
9. w1: insert head 1
10. w0: submit head 0 to the vendor

**I3 under `minus_head_uniqueness_and_assertion`, `distinct_actions`, K=2** — at most one active terminal head per (event, closure cycle, intent, slot)

1. w0: claim action 0 by compare-and-set, succeeds
2. w0: SELECT prior head FOR UPDATE returns nothing
3. w1: claim action 1 by compare-and-set, succeeds
4. w1: SELECT prior head FOR UPDATE returns nothing
5. w0: insert head 0
6. w1: insert head 1

**I6 under `minus_head_uniqueness_and_assertion`, `distinct_actions`, K=2** — no superseded head is ever delivered

1. w0: claim action 0 by compare-and-set, succeeds
2. w0: SELECT prior head FOR UPDATE returns nothing
3. w1: claim action 1 by compare-and-set, succeeds
4. w1: SELECT prior head FOR UPDATE returns nothing
5. w0: insert head 0
6. w0: lease head 0 for delivery
7. w0: head 0 carries no supersede pointer
8. w0: deliver head 0 without re-reading the active head
9. w1: insert head 1
10. w0: submit head 0 to the vendor

**I3 under `naive`, `distinct_actions`, K=2** — at most one active terminal head per (event, closure cycle, intent, slot)

1. w0: read action 0 status (approved)
2. w0: write action 0 EXECUTING on the strength of an earlier read
3. w0: SELECT prior head FOR UPDATE returns nothing
4. w1: read action 1 status (approved)
5. w1: write action 1 EXECUTING on the strength of an earlier read
6. w1: SELECT prior head FOR UPDATE returns nothing
7. w0: insert head 0
8. w1: insert head 1

**I6 under `naive`, `distinct_actions`, K=2** — no superseded head is ever delivered

1. w0: read action 0 status (approved)
2. w0: write action 0 EXECUTING on the strength of an earlier read
3. w0: SELECT prior head FOR UPDATE returns nothing
4. w1: read action 1 status (approved)
5. w1: write action 1 EXECUTING on the strength of an earlier read
6. w1: SELECT prior head FOR UPDATE returns nothing
7. w0: insert head 0
8. w0: lease head 0 for delivery
9. w0: head 0 carries no supersede pointer
10. w0: deliver head 0 without re-reading the active head
11. w1: insert head 1
12. w0: submit head 0 to the vendor

