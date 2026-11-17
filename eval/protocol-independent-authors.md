# Independent author track (Phase 2) — protocol

Status: **APPROVED — frozen 2026-09-17** (Phase 2 launch is the
arbiter approval). Later changes are dated amendments that never rewrite
history. This protocol governs the author track (independent attack
authors, human and agent). It is a sibling of
`eval/protocol-independent.md`, which governs the retrieval track
(Suite C). The two tracks never merge and are reported separately.

## 0. Decision record (5.0, arbiter — 2026-09-17)

- **Track design: dual track.** Human authors AND blind agent sessions
  run in parallel. The manuscript reports two lines — "human-authored
  (n)" and "agent-authored sessions (k)" — never merged into one number.
- **Author identity: anonymous codenames** (author-H1…H3 for humans;
  family-session ids for agents) in the artifact and manuscript. Real
  identities are held by the arbiter for camera-stage acknowledgment.
- **Execution prerequisite:** authoring sessions begin only after Phase 1
  acceptance (the gate-freeze declaration, `eval/gate-freeze-declaration.md`).
  Preparation — this brief, recruitment, prompt freeze — proceeds now. The
  prerequisite exists so that no author, human or agent, can be influenced
  (even indirectly) by knowledge of gate changes still in flight. The
  declaration records the evidence and the timing, including the respect in
  which it is a retrospective record rather than a contemporaneous signature.

## 1. Author inputs (the blindness boundary)

The ONLY system documentation any author receives is
`eval/author-brief/threat-model-brief.md`: the pipeline description, the
adversary may/may-not lists, and the five harm definitions. The brief
contains no case ids, no case registry, no knob catalog, no gate or
mediator names, no implementation details, no results. It was drafted
from the manuscript's threat-model section (§2) and adversarially
leak-checked (§6) before issue. The submission form is
`submission-template.md`.

Q&A (human track) is limited to threat-model-level questions; all Q&A is
archived per author codename. Agent track has no Q&A (ambiguities are
stated and resolved by the author in-field). The operator may not
confirm or deny the existence of any existing case.

## 2. Human track

- 2–3 authors with SOC/security-operations and Kubernetes/cloud-security
  backgrounds (at least one each), none involved in building this system
  or its evaluation. Recruited with `recruitment-note.md`.
- Each author submits 2–3 attacks on the form. Submissions archived
  verbatim, unedited.

## 3. Agent track

- Four families (glm / deepseek / kimi / claude), 3 fresh sessions each,
  3 attacks per session. Prompt frozen verbatim
  (`authoring-prompt-agent-track.md`) before the first session runs.
- No session sees conversation history, other sessions' outputs, the
  repository, or any tool. Raw outputs archived verbatim in full —
  including duplicates, malformed submissions, and refusals. Provider
  failures are recorded as lost sessions, never retried with rewording.

## 4. Filter and translation

- **Filter (syntactic only, applied per submission, counts and reasons
  logged):** a submission is admitted iff (a) the narrative is complete
  enough to follow step-by-step; (b) every step rides may-list
  capabilities only (may-not-dependent submissions are discarded with the
  specific boundary named); (c) an expected harm is chosen. The filter
  does NOT judge novelty, quality, likely success, or similarity to
  anything.
- **Translation:** each admitted submission becomes a case in
  `backend/app/eval_suite/independent_cases.py`, `adversary="I"`, with
  the author's original narrative preserved verbatim in the case
  annotation alongside the knob mapping. The translator may not alter a
  narrative; disagreements between narrative and harness capability are
  recorded, and shape the out-of-knob list.
- **Out-of-knob proposals** (attacks the harness cannot express): listed
  separately, assessed manually. If one stands up, it is a potential new
  harm class or a harness gap: extend per the standing §2.3 discipline
  (fix, re-freeze, disclose). This is a finding, not a failure.

## 5. Execution and reporting

- Runner: `eval/harness/run_independent.py` (naive vs full, both vendor
  columns, scripted planner), output `eval/results/independent/`,
  **never pooled** with the 57, held-out, kind, Suite C, or any frozen
  table. Make target mirrors `run_heldout.py`.
- Every admitted case runs; every cell is reported (harm / prevented /
  idle / not-applicable), with the same cell semantics as the main suite.
- **A full-arm harm is handled per the standing discipline** (fix the
  gate, re-freeze, disclose) and is the headline outcome of this track:
  an independent author found a real gap.
- Zero breakthroughs is the strongest independence evidence and is
  reported as such — with the author counts, filter counts, and session
  counts alongside, so the reader can weigh it.

## 6. Leak check (pre-issue audit)

Before the brief was issued, an adversarial review was run by an agent
with full access to the case registry, knob catalog, and gate
implementation, tasked with finding any content in the brief that would
channel authors toward existing cases or defenses. The review and its
resolution are archived under `eval/author-brief/leak-check.md`.

## Amendments

### Amendment 2026-09-17b — DeepSeek endpoint for agent track

Ark coding endpoint timed out or returned reasoning-only empties for
authoring sessions. Agent track smoke ran on
`https://api.deepseek.com` with model `deepseek-flash` (3 sessions × 3
attacks, same frozen BRIEF prompt): 3/3 sessions scored, 0 lost.
Ark families previously probed remain in
`eval/results/independent/raw/lost-*` as lost/timeout; they are not
padded. Filter and freeze: `eval/results/independent/`.

### Amendment 2026-09-17c — Claude Opus on Anthropic Messages API

The same gateway (`https://sub2api.52ai.pro`) that served the planner
arm's OpenAI-compat `/v1/chat/completions` path returned SSL errors or
empty replies for authoring-length generations. Those three attempts are
archived under `raw/lost-ssl-20260917/` and are not padded. A second
pass, **same frozen BRIEF prompts**, used the Anthropic Messages API
(`ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`, `POST /v1/messages`,
model `claude-opus-5`): 3/3 sessions scored, 0 lost. Session 2 needed
one same-prompt transport retry (status 0 → 200). glm and kimi remain
lost as of this amendment. Translation into `independent_cases.py` and
the independent freeze wait for the human-track swap so that layer is
frozen once.

### Amendment 2026-09-18a — Ark glm-5.3 / glm-5.3-flash / kimi-k3 recovered

Same frozen BRIEF prompts as the lost Ark probes. OpenAI-compat
`POST /v1/chat/completions` on
`https://ark.cn-beijing.volces.com/api/coding/v3` with
`INDEPENDENT_AUTHOR_API_STYLE=openai`, `enable_thinking=false`,
`max_tokens=32768`. Wire id for flash: `glm-5-3-flash-260828`.

Scored, 0 lost this pass:

- `kimi-k3` sessions 1–3 (2026-09-17)
- `glm-5.3` sessions 1–2 (2026-09-17); session 3 (2026-09-18, after a
  curl-60 SSL miss archived under `raw/lost-ssl-20260918/`)
- `glm-5.3-flash` sessions 1–3 (2026-09-18)

Earlier Ark failures stay in `raw/lost-ark-20260917/`,
`lost-timeout-20260917/`, `lost-reasoning-20260917/`, and
`lost-ssl-20260918/` and are not padded. No prompt was reworded.
Translation into `independent_cases.py` and the independent freeze still
wait for the human-track swap.
