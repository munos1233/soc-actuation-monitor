# Independent author track (Phase 2)

Never pooled with Suite B 57, held-out, gold_ext, B2, or mutation.

## Freeze

- Protocol: `eval/protocol-independent-authors.md` (APPROVED 2026-09-17; DeepSeek 2026-09-17b; Claude 2026-09-17c; Ark recovery 2026-09-18a)
- Filter log: `filter-log.md` (agent families all 9/9 admitted; translation deferred)
- Out-of-knob: `out-of-knob.md` (H3-a1 only; agent translation still pending)
- Raw agent archive: scored `raw/{deepseek-flash,claude-opus-5,kimi-k3,glm-5.3,glm-5.3-flash}-session{1,2,3}.md`; earlier Ark/SSL/reasoning misses under `raw/lost-*`
- Runner: `make paper-eval-independent` → `latest.md` / `latest.json` (do not re-run until human-track swap)

## Manuscript lines (this freeze)

| line | cases | naive harmed | full harmed |
|---|---|---|---|
| human-authored | 8 (16 cells) | 10/16 | **0/16** |
| agent-authored | 9 (18 cells) | 12/18 | **0/18** |

Naive idle cells are mostly duplicate-dispatch shapes (substrate, same reading as Suite B A3). Zero full breakthroughs.
