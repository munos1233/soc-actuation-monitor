# Defensive writing inventory

## What real ACM TOPS papers do

Checked against Ceragioli et al., *Specifying and Verifying Information Flow
Control in SELinux Configurations*, ACM TOPS 27(4), 2024 (Basin group; a
systems-security TOPS paper in the same neighbourhood as ours).

- Limitations live in **one short Discussion / Future Work block at the end**.
- Related work contrasts neighbours with a factual delta, not a repeated
  “Difference: we do not claim …”.
- Contribution bullets state what was done. They do **not** append
  “not a proof / not a model evaluation / not the headline” on every item.
- There is **no** multi-sentence Non-claims paragraph that lists seven
  things the paper is not.
- Scope is stated once in the threat model or evaluation setup, then assumed.

Normal density: a few limitation sentences, not a running apology.

## What our manuscript was doing (before this cut)

Defensive prose was appearing in **every layer**: abstract, intro, contribution
bullets, Non-claims, TCB, every eval subsection caption, Discussion (eight
paragraphs), Related Work (“each paragraph ends with why it does not”), and
Conclusion. Same hedge often appeared three or more times.

Reviewers read that density as either insecurity or LLM self-exculpation.

## Patterns cut or demoted (2026-09-18)

| Pattern | Action |
|---|---|
| “These are not claims that the construction would have prevented…” | Deleted from intro |
| “we do not pretend otherwise” | Deleted |
| “We do not claim X” × 7 Non-claims paragraph | Replaced by a short **Scope** paragraph |
| “not a proof of the implementation / lemma” | Removed from abstract/conclusion; left implicit in TLC numbers |
| “not a model evaluation / existence check” thrice | Once in Discussion Limitations |
| “never pooled / not the headline” body echoes | Softened to “reported separately”; captions keep the pooling note where needed |
| “honest version / keep the table honest / honest reading” | Deleted |
| “Difference: we do not …” on every RW paragraph | Rewritten as positive deltas |
| “Each group … ends with why it does not” | Deleted |
| Eight Discussion paragraphs | Collapsed to one **Limitations** paragraph |
| Generative-AI authorship paragraph in Discussion | Removed (ACM checkbox + camera-ready policy) |
| “manuscript does not invent a 0/N” | Dropped the lecture; R1 still says totals fill at joint freeze |
| “A reader who takes only one number…” | Deleted |

## What stays (load-bearing, stated once)

- Threat model / Scope: host root and stolen actuation login out; mock ≠ live;
  `force_close` bypass; mapped kind rows; harm-unreachable cells separate.
- Discussion Limitations: author-constructed 57; layers reported separately;
  model arms $N{=}5$; not a protection domain.
- Table captions that would otherwise invite pooling (independent, B2, temporal).

## Edit rule

State the fact. State the scope once. Do not narrate the reviewer’s possible
misreading. Do not apologize for what the paper is.

## Status

`make paper-pages` → **34 pages** after the cut (was 35; headroom for human-swap
table growth).
