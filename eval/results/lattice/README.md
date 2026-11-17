# Mediator lattice (missing 2-gate cells)

Frozen 2026-09-17 after the A2 level-fix (A2 5/5). Live
`$4\times 57$` production-chain run matches the monotone projection on
every adversary cell: mock `close+egress` 7/22, `verify+egress` 13/22,
`close+bind` 4/22, `bind+verify` 10/22 (and the two frozen pairs).

Never pooled into 49/57. Reproduce: `make paper-eval-lattice`.
