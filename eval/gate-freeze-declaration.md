# Gate-freeze declaration (Phase 1 acceptance)

**Date: 2026-09-17.** This is the acceptance record that
`protocol-independent-authors.md` §0 names as the execution prerequisite
for the independent author track: authoring sessions begin only after
Phase 1 is accepted and the four mediators are frozen, so that no author
can be influenced — even indirectly — by knowledge of gate changes still
in flight.

## What is frozen

The four mediator predicates (`close`, `bind`, `egress`, `verify`), the
head protocol, and the role split are frozen as of this date. From here
on, a change to any of them is not a routine edit: it is a §2.3 event
(fix, re-freeze every affected table, disclose the change and the
before/after numbers). The construction layers below are the evidence
that the freeze is earned rather than declared.

## Phase 1 evidence (all times UTC; local = UTC+8)

| layer | result | artifact | frozen at |
|---|---|---|---|
| Main ablation (Suite B + Suite A) | naive 49/57, full **0/57** | `results/latest.json` | 04:58:47Z |
| TLA+ / TLC | full slice exhausted, counterexamples enumerated | `results/tla/latest.json` | 04:52:26Z |
| Gold-path extension g5–g11 | 6/6 closed, **0 over-block** | `results/gold_ext/latest.json` | 06:51:42Z |
| B2 construction closure | naive 12/12, full **0/12** | `results/b2/latest.json` | 06:54:45Z |
| Predicate mutation kill-rate | **17/18 killed**, 1 declared survivor, 0 unexpected | `results/mutation/latest.json` | 08:14:46Z |
| Mediator lattice projection | 4 new pairs, projection consistent | `results/lattice/latest.json` | 08:20:25Z |
| Structural guards | `make paper-eval-test` green (98 passed, 1 skipped) | `backend/tests/eval/` | re-verified this date |

The last construction layer to go green was the mutation kill-rate at
08:14:46Z (16:14 local). The declaration takes effect from that point.

## The one declared survivor

Mutation reports 17/18, not 18/18. The surviving mutant is declared in
`results/mutation/latest.md` rather than hidden or removed from the
denominator. A kill-rate with a disclosed survivor is the honest form of
this measurement; a 18/18 obtained by deleting the inconvenient mutant
would not be.

## Sequencing, stated plainly

The independent authoring sessions ran at 11:26–11:28Z (19:26–19:28
local), after the last Phase 1 layer froze at 08:14:46Z. The
prerequisite ordering therefore holds on the evidence.

What does **not** hold is the ordering of this document against the
sessions: the underlying Phase 1 green state preceded the sessions, but
this written declaration was produced later the same day, after them.
It is a record of a state, not a contemporaneous signature. Anyone
auditing the protocol should read it that way, and the correct reading
of the prerequisite is satisfied by the artifact timestamps above rather
than by this file's own creation time.

## Scope

This declaration covers the SOC instance's four mediators and head
protocol. It does not freeze: the Kubernetes instance corpus
(`results/k8s-kind/`), the Temporal portability instance
(`results/temporal/`), the comparator arm (`results/comparator/`, whose
freeze predates the A2 level-fix and is labelled as such), or the
language-model planner arms, each of which carries its own freeze date
and is never pooled with the 57.
