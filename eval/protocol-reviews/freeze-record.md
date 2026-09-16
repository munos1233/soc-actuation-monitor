# Phase 0 freeze record

The arbiter approved `eval/protocol-independent.md` on
**2026-09-16T23:36:32+08:00** (session approval: "批准，本地commit吧").
The approved protocol, the sanitized grid, and both adversarial reviews
were committed together as the freeze:

- Commit: `c4a63ba000270c85c30c5d1b7d61fc1604a15e23` (branch `paper/tops-eval`)
- Commit date: 2026-09-16T23:37:38+08:00
- Files frozen: eval/protocol-independent.md,
  eval/taxonomy/taxonomy-grid-public.md, eval/protocol-reviews/
  (methodology-review.md, constructor-simulation-review.md)

This record exists so the protocol file itself is never edited after
the freeze commit (the hash cannot appear inside the file it commits).
The commit timestamp is self-attested (local repository); that limit is
acknowledged in protocol §14. Per protocol §4, Phase 1 (v2 retrieval)
is now unblocked.
