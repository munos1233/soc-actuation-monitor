# Provenance gaps in the independence layers

**Status: open, resolution decided.** The three affected layers hold
stand-in artifacts to be replaced by real participants before submission;
the swap procedure and the gate that enforces it are in
`placeholder-registry.md`. This file stays as the record of *what each
gap is*, so the replacement can be checked against it rather than against
memory.

Nothing here is fixed by editing an artifact. Each item is a record that
has to be created by whoever actually does the work.

The question this file exists to answer is the one a reviewer or an AEC
member asks: *who did this, and on what machine?* Two layers can answer
it today. The rest cannot.

---

## What can answer the question today

| Layer | Evidence | What it pins down |
|---|---|---|
| Independent authoring, agent track | `results/independent/raw/session-record.json` | family, endpoint (DeepSeek / Anthropic gateway / Ark coding v3), HTTP status, lost flag, output path, per session |
| Independent authoring, human track | `author-brief/role-prompts/human-track-H{1,2,3}.md` | per-author assigned background, blindness rules as issued, output paths |
| Independent execution run | `results/independent/run-log.txt` (L1–2), `results/independent/latest.json` | host path, commit `e49dd6737a48…`, run timestamp 2026-09-17T11:35Z |

Everything below lacks an equivalent.

---

## 1. Gate review G1/G2 — no reviewer provenance

**Artifacts:** `results/gate-review/g1-review.md`,
`results/gate-review/g2-review.md`, `results/gate-review/latest.md`,
packet `results/gate-review/packet.md`.

**What they contain:** two technically detailed blind reviews of the four
mediator predicates, mutually consistent, both finding `egress` deviates
on the digest-equality wording and `close`/`bind`/`verify` conforming.
The merged verdict drove a manuscript wording change without thawing a
gate — the discipline was followed and the finding is real.

**What is missing:** reviewer identity or codename registry, review date,
host, the commit reviewed, and any record that G1 and G2 were not the
people who built the gates. `改进方案.md` §6.2 requires 另一名未参与者
(one *non-participant*). Nothing in the artifact supports or refutes that.

**Options:**
- Have an actual non-builder redo the review from `packet.md` alone and
  archive it with a provenance header, or
- keep the reviews and relabel them in the manuscript as what they
  provably are — a blinded second-pass audit of the predicates against
  the claimed invariants — dropping the independence framing.

---

## 2. CVE scoring K1/K2 — no blind-session archive, no adjudicator record

**Artifacts:** `results/k8s-kind/cve-scoring/k1-scores.json`,
`k2-adjudication.md`, `latest.md`, packet `blind-packet.md`, scale
`scale.md`, prep `summaries.md`.

**What they contain:** all eleven rows scored, five adjudicated, final
counts mechanism 6 / path 5 / category 0. The scale is written down
before the scores, and the low-fidelity rows are named rather than
buried — that part is sound methodology.

**What is missing:** `k1-scores.json` carries only `"scorer": "K1"`. There
is no session record of the kind the authoring track produced (no
family, no endpoint, no timestamp), so nothing distinguishes "blind
fresh-session scorer from a different model family" from "same operator
filling in the file." `k2-adjudication.md` has no signature at all, and
§6.3 asks for a human adjudicator, ideally one who knows Kubernetes
security.

**Options:**
- Re-run K1 as a recorded blind session (mirroring
  `results/independent/raw/session-record.json`) and have a named human
  redo the adjudication, or
- report the scores as author-performed fidelity self-assessment against
  a pre-registered scale, which is still worth publishing and is not a
  claim of independence.

---

## 3. Human author track H1–H3 — prompts now archived; one real deviation

**Artifacts:** nine submissions
`author-brief/submissions/submission-H{1,2,3}-a{1,2,3}.md`, Q&A logs
`author-brief/qa-log-H{1,2,3}.md`, role prompts
`author-brief/role-prompts/human-track-H{1,2,3}.md`, filter log
`results/independent/filter-log.md`, recruitment material
`author-brief/recruitment-note.md`.

**The backgrounds are substantiated.** The three sessions were launched
with explicit role assignments, now archived verbatim:

| codename | assigned background (first line of the role prompt) |
|---|---|
| H1 | senior SOC operations / security-operations analyst |
| H2 | Kubernetes / cloud-security engineer |
| H3 | mixed (incident response + platform security) |

That is exactly the "SOC / Kubernetes / mixed backgrounds" of
`paper/main.tex:2508-2509`, and each prompt carries the blindness rules
verbatim ("Work ONLY from the threat-model brief and submission form
pasted below. Do NOT open, search, or read any repository files."). The
three sessions were separately and genuinely run. Until now the only
record of the assignment lived in the session log rather than in the
artifact; archiving the prompts closes that.

**The one real deviation — the brief was paraphrased, not pasted.** The
twelve agent-track prompts are byte-identical per family (9779–9786
bytes) because the frozen brief goes in verbatim, which is what
`protocol-independent-authors.md` §1 requires: the brief is THE only
documentation an author receives. The three human-track prompts are
5518, 3834 and 2725 bytes, each carrying a *different and progressively
shorter paraphrase* of the 4121-byte `threat-model-brief.md`. H3 in
particular received the five harms as a single line
("Wrong close; Wrong action; Duplicate effect; Leak; False
verification") where the brief gives each a definition.

This does not make the submissions invalid — nothing from the case
registry or the defenses leaked in, and the may/may-not lists survive in
all three — but it means the three authors did not receive identical
inputs, so the track is not a controlled comparison across H1/H2/H3 and
is not strictly brief-verbatim.

**Options:**
- Re-run the three sessions with the frozen brief pasted verbatim, which
  makes the human track match the agent track's discipline, or
- keep the submissions and disclose the deviation in
  `protocol-independent-authors.md` as a dated amendment, the way the
  lost Ark families were disclosed.

**Still missing, if the track is to be called external:** a recruitment
reply, consent record, or arbiter-held identity roster
(`protocol-independent-authors.md` §0 says the arbiter holds real
identities for camera-stage acknowledgment). All nine submissions carry
the same date and all three Q&A logs read "No questions asked."

---

## 4. Cover letter bundles a protocol with completed work

**Location:** `paper/cover-letter.md:37-39`.

> A co-verification layer (independent table re-execution protocol,
> four-gate review G1/G2, CVE-mapping fidelity K1/K2 on the kind eleven)
> is archived separately and never pooled with the 57.

R1 has **no diff artifacts at all** — `results/reexec/` holds the
protocol, the checklist, `PENDING_JOINT_FREEZE.md`, and an unfilled
`env.example.json`. The body is honest about this
(`paper/main.tex:2547-2549` refuses to invent a 0/N), but the cover
letter's single sentence reads as three completed activities.

**Fix:** split the sentence so the re-execution reads as "protocol and
diff harness archived; totals pending joint freeze," matching the body.

---

## 5. Authoring session records carry no timestamps

`results/independent/raw/session-record.json` has family, endpoint,
status, lost flag and output path, but no per-session time. The times
used in the gate-freeze declaration were recovered from file mtimes
(19:26–19:28 local), which is weaker than a recorded field and will not
survive a fresh clone.

**Fix:** add a timestamp field when any authoring session is next run;
until then, cite the mtimes as what they are.

---

## 6. One concern that turned out to be a timezone artifact — recorded so it is not re-raised

`.workbuddy/memory/2026-09-17.md` shows Phase 1 incomplete at "11:10"
while `results/independent/latest.json` records the run at
`2026-09-17T11:35Z`, which looks like the authoring track ran before its
own prerequisite. It did not. The memory log is in local time (UTC+8):
11:10 local is 03:10Z, the last Phase 1 layer (mutation kill-rate) froze
at 08:14:46Z, and the authoring sessions ran at 11:26–11:28Z. The
ordering holds. See `gate-freeze-declaration.md`.

What does not hold is the ordering of the *written* declaration against
the sessions; the declaration says so itself.

---

## 7. Freezes are not pinned to a commit

`results/latest.json` has `"commit": null`, and at the time of writing
`backend/app/eval_suite/` carries roughly 1.6k inserted lines that are
not committed. Only `results/independent/latest.json` records a commit.
A reviewer who clones the artifact cannot tie the headline table to a
tree state.

**Fix:** commit the eval tree and re-freeze, or record the commit hash
into the freeze writer so every future `latest.json` carries it.

---

## What the stand-ins did and did not establish

Items 1–3 established *methodology* and not *organizational
independence*. The blinding boundaries are real and now archived, the
packets are real, the scales were fixed before the scoring, the sessions
were separately run, and the findings changed the manuscript. What none
of them establishes is separation of person or machine from the author —
which is exactly what the swap supplies, and why the layers were built
in replaceable form.

The asymmetry worth carrying into the swap: the author track kept records
good enough to audit itself, which is why item 3's backgrounds could be
substantiated and its brief deviation caught, while the gate review and
the CVE scoring kept none. Give layers 2 and 3 the same session-record
discipline the author track already has, or the replacement will be as
unauditable as what it replaces.
