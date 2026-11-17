# Stand-in registry and swap procedure

Three layers currently hold **stand-in artifacts**: output produced to fix
the shape of each layer — the packet, the form, the scale, the file paths,
the downstream wiring — so that a real participant's work drops into the
same paths without redesigning anything. The stand-ins are scaffolding.
They are not the evidence the manuscript will ship.

`make paper-artifact` refuses to run while any stand-in remains
(`scripts/check_placeholders.py`). The block is not a flag: each stand-in
carries the token `STAND-IN-PENDING-REPLACEMENT` inside the file, so a
real submission overwriting the path clears it and nothing else does.

Run `make paper-placeholder-check` at any time to see what is outstanding.

---

## Do this before recruiting anyone

**Fix the brief so every participant gets the identical input.** The three
current human-track prompts carry three different paraphrases of
`author-brief/threat-model-brief.md` (5518 / 3834 / 2725 bytes against a
4121-byte brief; H3 received the five harms as one line where the brief
defines each). The agent track did it correctly — its twelve prompts are
byte-identical per family because the brief is pasted verbatim, which is
what `protocol-independent-authors.md` §1 requires.

If real authors receive paraphrases the way the stand-ins did, the track
is not a controlled comparison and the defect is permanent: you cannot
re-issue a brief to someone who has already read a different one. Paste
`threat-model-brief.md` verbatim into every packet.

**What a participant may see:** the threat-model brief, the submission
form, and their own role assignment. Nothing else.

**What a participant must not see:** any existing submission (including
the stand-ins), the case registry, the mediator source, the gate names,
`out-of-knob.md`, or this file. A participant who reads
`submission-H1-a1.md` before writing will anchor on it, and the track's
value is that they did not.

---

## Layer 1 — independent authors, human track

| stand-in path | replaced by |
|---|---|
| `author-brief/role-prompts/human-track-H{1,2,3}.md` | the recruitment packet actually issued to each author |
| `author-brief/submissions/submission-H{1,2,3}-a{1,2,3}.md` | their submissions, verbatim, unedited |
| `author-brief/qa-log-H{1,2,3}.md` | the real Q&A, including "no questions" if that is true |

Role assignments the stand-ins used, kept so the manuscript sentence
stays true if you recruit to the same profile
(`paper/main.tex:2508-2509`, "SOC / Kubernetes / mixed backgrounds"):

- H1 — senior SOC operations / security-operations analyst
- H2 — Kubernetes / cloud-security engineer
- H3 — mixed (incident response + platform security)

If the people you find do not match these profiles, change the manuscript
sentence rather than the profiles. Three authors is the plan's minimum
(`改进方案.md` §5.2 asks for 2–3, at least one SOC and one Kubernetes);
fewer is reportable, but say so.

**Also needed, and not producible by a swap:** an arbiter-held roster of
real identities (`protocol-independent-authors.md` §0 promises one for
camera-stage acknowledgment) and a one-line non-involvement statement per
author. Neither has to be public; both have to exist.

### After the swap

1. Re-run the filter and rewrite `results/independent/filter-log.md` from
   the real submissions.
2. Re-translate to knobs in `backend/app/eval_suite/independent_cases.py`
   (`HUMAN_CASES`), and remove that file's stand-in marker.
3. List anything unrunnable in `results/independent/out-of-knob.md`.
4. `make paper-eval-independent` → new `results/independent/latest.{json,md}`.
5. Update the two never-merged lines in `paper/main.tex`
   (`tab:independent`, currently human 0/16).

**Schedule risk worth naming now:** real authors write different attacks,
so the human line *will* change, and a full-arm harm is a live
possibility. That is the track's best possible outcome scientifically and
its worst outcome for your calendar — per the standing §2.3 discipline it
means fix the gate, re-freeze every affected table, and disclose. Leave
room for it rather than discovering it a week before the deadline.

---

## Layer 2 — gate review (G1/G2)

| stand-in path | replaced by |
|---|---|
| `results/gate-review/g1-review.md` | reviewer 1's verdict |
| `results/gate-review/g2-review.md` | reviewer 2's verdict |
| `results/gate-review/latest.md` | the merged verdict you write from the two |

The packet (`results/gate-review/packet.md`) is reusable as-is: it holds
the claimed invariants and the four mediator source paths, and nothing
from the case registry. `改进方案.md` §6.2 asks for one non-participant,
budget about two person-days, reading source against claimed invariants
with the cases withheld.

Each review needs a provenance header the stand-ins never had: reviewer
codename, date, host, and the commit reviewed.

**Carry forward regardless of who reviews:** the egress finding. Both
stand-in reviewers found the `inv:mediate` wording claimed a
digest-equality check the implementation does not perform, and the
manuscript wording was tightened rather than the gate thawed. If real
reviewers do not independently reach it, the finding still stands on its
own merits — but do not present it as their finding.

---

## Layer 3 — CVE mapping fidelity (K1/K2)

| stand-in path | replaced by |
|---|---|
| `k8s-kind/cve-scoring/k1-scores.json` | the blind scorer's output |
| `k8s-kind/cve-scoring/k2-adjudication.md` | the human adjudicator's ruling on low/ambiguous rows |
| `k8s-kind/cve-scoring/latest.md` | the count summary you write from the two |

`summaries.md`, `scale.md` and `blind-packet.md` are reusable: the scale
was fixed before any scoring, which is the part that makes this layer
worth publishing at all. K1 needs a session record of the kind the author
track produced (family, endpoint, timestamp) — `results/independent/raw/
session-record.json` is the format to copy. K2 should be a named human,
ideally the same person as the §6.2 reviewer.

### After the swap

Rewrite the CVE section of `results/k8s-kind/README.md` and the two
mapping-table footnotes in `paper/main.tex` (`tab:k8s-real`,
`tab:k8s-mapped`) with the new mechanism/path/category counts and the new
list of path-scored rows.

---

## Where this sits in the schedule

The swap has to come **before** the joint freeze, not after. Real authors
produce different cases, so `results/independent/` is regenerated by the
swap; freezing first means freezing twice. The order that holds:

1. Fix the brief; recruit; issue packets.
2. Collect submissions, reviews, scores. Swap them in.
3. Regenerate the derived artifacts listed above.
4. Commit the eval tree, then run the joint freeze (main matrix, kind,
   comparator, planner arms), then R1's diff on top of it.
5. Update the paper's numbers, then cut to 35 pages, then pack.

`make paper-placeholder-check` is green only after step 3. `make
paper-artifact` cannot complete before then.

---

## The one thing this registry cannot enforce

The AI-disclosure paragraph (`paper/main.tex`, §7.3 of the plan) and the
independence claims have to be consistent with each other, and no script
can check that. If the stand-ins are still in place at submission time,
the manuscript's description of these three layers is false regardless of
what the disclosure paragraph says. The placeholder gate exists to make
that failure mode loud instead of silent, but it only guards the artifact
pack — it cannot guard a PDF uploaded by hand.
