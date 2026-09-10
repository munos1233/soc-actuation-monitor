# Multi-process contention probe

4 concurrent OS processes, 5 rounds per configuration per contention point, vendor column `mock`.

| configuration | contention | rounds with a duplicate | max entity effects | max terminal effects | max active heads | late workers |
|---|---|---|---|---|---|---|
| full | deliver | 0/5 | 1 | 0 | 0 | 0 |
| full | dispatch | 0/5 | 1 | 0 | 0 | 0 |
| full | head | 0/5 | 0 | 1 | 1 | 0 |
| full | rekey | 0/5 | 1 | 0 | 0 | 0 |
| full_minus_claim_cas | deliver | 0/5 | 1 | 0 | 0 | 0 |
| full_minus_claim_cas | dispatch | 0/5 | 0 | 0 | 0 | 0 |
| full_minus_claim_cas | head | 0/5 | 0 | 1 | 1 | 0 |
| full_minus_claim_cas | rekey | 0/5 | 0 | 0 | 0 | 0 |
| full_minus_head_uniqueness | deliver | 0/5 | 1 | 0 | 0 | 0 |
| full_minus_head_uniqueness | dispatch | 0/5 | 1 | 0 | 0 | 0 |
| full_minus_head_uniqueness | head | 5/5 | 0 | 1 | 4 | 0 |
| full_minus_head_uniqueness | rekey | 0/5 | 1 | 0 | 0 | 0 |
