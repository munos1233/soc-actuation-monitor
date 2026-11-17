# Mutation set: independent selection review

Judged from `backend/app/eval_suite/mutants.py` (18), the bind and close
predicates, the terminal activate path, B2, gold_ext, and the close-gate
projector. The constructors' README is treated as a claim, not as evidence.

Kill is the mutation runner's definition: relative to an unmutated FULL pass,
an attack FULL prevents that becomes harmed, or a golden FULL closes that is
refused. Frozen 57 means the Suite B cells (29 case ids × mock/pseudo-live,
minus inapplicable columns), not B2 and not g5–g11.

---

## A. Selection rationale a paper can print

The mutant set is a convenience sample of *switchable-mediator* predicates,
not a covering design of TEI. It has two families:

- **M1 (12, `kind=harm`)** — weaken a loaded gate so a FULL-prevented attack
  is predicted to land. Completeness mutants.
- **M4 (6, `kind=over_strict`)** — tighten a loaded gate so a FULL-closed
  golden is predicted to refuse. Precision mutants. Every named killer is in
  gold_ext (g5–g11), which is the only reason those six exist: g1–g4 never
  retarget, never re-approve, never dispatch a second immediate action, and
  never take the operator writeback-retry path.

The numbering is a gap. The file contains M1 and M4 only. If M2/M3 were
meant to be substrate uniqueness (A3) and role separation (A0), omitting
them from this experiment is consistent with those already having their own
tables. Printing “18 mutants of TEI” without that caveat overstates what
was mutated.

**Why these 18, as a defensible sentence:** they poke the four production
switches the main table already ablates (close, bind, verify, egress), plus
six over-strict shapes the frozen goldens do not exercise. That is a
reasonable *second* experiment after leave-one-out. It is not a mutant of
every TEI conjunct (closure_cycle, side-effect convergence, playbook hash,
level-vs-fingerprint, observation target mismatch, CAS/claim).

**Why M1 vs M4.** Leave-one-out already answers “unload the gate.” M1 asks
the stricter question: a plausible *weaker witness* inside a still-loaded
gate. M4 is the dual that Suite B cannot see. Splitting the families is
correct. Padding them to 12+6 for a round 18 is visible in M1: three
verify-branch patches of one function, and one equivalent mutant of a dead
close conjunct (C).

**Why A3 substrate is absent.** Justified, if stated as a scope limit rather
than as coverage. Dual-dispatch is mediated by mechanisms with no production
switch (`head_index`, in-transaction supersede, delivery re-read, claim
CAS). The substrate ladder already shows they fail only in combination.
Repeating those weakenings as `unittest.mock.patch` mutants would mix two
methods and still not be a first-order mutant of a gate. The cost of the
exclusion: the mutation headline cannot be read as “TEI predicates, 17/18
killed.” A3 is part of the TEI write path.

**Why two historical fail-open shapes are duplicated.** The README lists
four sites as two shapes × two boundaries:

| shape | site A | site B |
|---|---|---|
| compare a planner-authored stored label to itself | bind: approval `action_fingerprint` vs action `action_fingerprint` (`m1_bind_planner_fingerprint`) | close: view `plan_revision` vs `current_plan_revision` (`m1_close_planner_cycle`) |
| treat a local check over planner-writable fields as integrity | egress: `_trusted_event_locator` falls back to `command.source_locator` (`m1_egress_self_witness`) | terminal activate: `_template_unchanged` hashes two planner columns against each other (`m1_template_unchanged_revert`) |

Duplicating a *shape* across bind/close and egress/activate is a legitimate
paper point (the same mistake is cheap at every boundary). It is not
legitimate if one of the four sites is an equivalent mutant. Bind-column
and egress-self-witness are live fail-opens. Close-planner-cycle is not
(C). Terminal `_template_unchanged` is live as a *consistency* check of two
planner columns, but the shipped mutant also no-ops bind, so it does not
isolate that shape (D).

**Padded or incomplete.** Both. Padded by `m1_close_planner_cycle` (equivalent
mutant) and by `m1_verify_echo_verified` largely overlapping
`m1_verify_missing_field_verified` on the actual a5_echo payload. Incomplete
relative to a skeptical mutation-testing reading: no first-order drop of
the `required_level` conjunct; no mutant of the verify target-mismatch
branch (B2 T6a has a case and no mutant); no first-order
`_template_unchanged := True` with bind left on; no projector-level cycle
mutant; A0/A3 out of scope.

A printable rationale that does not overclaim:

> The mutant set weakens or tightens predicates of the four switchable
> mediators under FULL. Completeness mutants (M1) target stored-label
> comparison, dropped fingerprint segments, skipped close facts, observation
> classified as effect, and locator/content witnesses. Precision mutants
> (M4) target the six legitimate flows g1–g4 do not cover. Substrate
> uniqueness and SQL role separation are excluded because they are not
> unloadable gates and already have ablation tables. The set is not a
> covering of TEI conjuncts; one declared survivor is an equivalent mutant
> of an unreachable close conjunct.

---

## B. Per-mutant predicted kill

Notation: **harm-kill** / **over-strict-kill** / **survivor**. Named killer
is the id in `Mutant.killers`. “Also frozen 57” means the same patch would
be killed by a Suite B / g1–g4 case even if B2 and gold_ext were omitted.

### M1 — completeness

**`m1_bind_planner_fingerprint`** — predicted **harm-kill**.
Replaces `_validate_approval_binding` with a comparison of the stored
`action_fingerprint` column only. Drops plan_revision, `required_level`,
playbook hash, and the recomputed content hash. `a2_target_swap` /
`a2_tool_escalation` / `a2_stale_plan_revision` rewrite content and leave
the stub column untouched, so the remaining comparison is identity.
Named killers hit. Additional frozen-57 harm-kill: **`a2_level_downgrade`**
(level is not a fingerprint segment; the dropped `required_level` conjunct
is what FULL uses). `a2_forged_fingerprint` rewrites the column to
`fp-forged-…`, so the naive comparison still refuses; it will not kill
this mutant. Killers are already in the frozen 57. Not a B2-only result.

**`m1_bind_partial_fingerprint`** — predicted **harm-kill**, B2-only.
Patches `recompute_action_content_fingerprint` to drop `execution_owner`
and parameters. Column comparison, plan_revision, and `required_level`
remain. Frozen A2 still hashes target/tool/revision, so a2_* stay refused.
Named killer `b2_t1b_execution_owner_rewrite` is the case that only the
dropped segment covers. **Not** also killed by the frozen 57. This is one
of the few mutants that justifies B2 in the mutation matrix.

**`m1_close_planner_cycle`** — predicted **survivor**, and equivalent (C).
Named killers `()`. Aligning `terminal.plan_revision` to
`ctx.current_plan_revision` is the identity of the production projector.
No A1 case becomes harmed; no golden is refused. Declaring a survivor is
honest as a *measurement* and padded as a *result*.

**`m1_close_skip_report`** — predicted **harm-kill**.
Forces `report_exists=True` into the gate. Named killer `a1_missing_report`
is in the frozen 57 and is the load-bearing conjunct. Other A1 cases still
carry a report, so they will not extra-kill.

**`m1_close_weak_evidence_ok`** — predicted **harm-kill**.
Rewrites the view’s `confirmation_evidence` to `READBACK_VERIFIED`.
`a1_weak_receipt` is CONFIRMED + `ADAPTER_ACKNOWLEDGED`; the evidence
conjunct is what FULL uses. Additional frozen-57 harm-kill:
**`a5_lying_vendor_receipt`** (same evidence tier, CONFIRMED from submit).
`a1_dropped_readback` stays ACCEPTED, so `receipt_status is CONFIRMED`
still refuses. Named killer is in the frozen 57.

**`m1_simulated_receipt_ok`** — predicted **harm-kill** (pseudo-live only).
Rewrites view `simulated` to `False`. Named killer `a1_simulated_receipt`
is pseudo-live only in the frozen 57; on mock, `disposition_is_mock=True`
already accepts simulated receipts, so the cell is inapplicable. Distinct
from the evidence mutant: `SIMULATED_CONFIRM` already carries
`READBACK_VERIFIED`.

**`m1_verify_echo_verified`** — predicted **harm-kill**.
Short-circuits payloads with an `echo` key or `detail == "observation complete"`.
Named killer `a5_echo_observation` matches that shape. Frozen 57.
`a5_empty_observation` has neither cue, so the original missing-field
branch still returns UNVERIFIABLE. Production `classify_verification_observation`
has no echo predicate; a5_echo is already refused as missing `is_verified`.
This mutant *adds* a fail-open rather than deleting a live conjunct. Overlaps
the next mutant on the actual echo payload.

**`m1_verify_missing_field_verified`** — predicted **harm-kill**.
Treats absence of `is_verified` as VERIFIED. Named killer
`a5_empty_observation`. Additional frozen-57 harm-kill: **`a5_echo_observation`**,
whose payload also lacks `is_verified`. Both killers are in the frozen 57.
The echo mutant is then mostly redundant for kill-rate.

**`m1_verify_false_negative`** — predicted **harm-kill**, B2-only.
Maps `is_verified is False` to VERIFIED. Echo/empty do not carry that key,
so a5_* stay on the missing-field branch. Named killer
`b2_t6b_honest_negative_observation`. **Not** also killed by the frozen 57.
B2 T6a (wrong-target SUCCESS) is unaffected: `is_verified` is True and
target-mismatch still runs. No mutant of that branch exists.

**`m1_egress_self_witness`** — predicted **harm-kill**, B2-only.
`_trusted_event_locator` returns `None`; enqueue/delivery then use
`command.source_locator` as the “trusted” locator, so
`disposition_source_match` is a self-comparison. Named killer
`b2_t4b_pre_approval_locator_swap`: bind hashes the foreign locator against
the approval of that same locator; egress is the remaining object-identity
witness. Frozen `a4_locator_swap` is *post*-approval, so bind still refuses
and the case never reaches the patched witness. **Not** also killed by the
frozen 57.

**`m1_egress_no_content_scan`** — predicted **harm-kill**.
`_scan_analysis_content` returns `[]`. Named killer `a4_narrative_in_target`.
Additional frozen-57 harm-kill: **`a4_secret_in_target`** (same scanner,
`bearer ` marker). Both in the frozen 57.

**`m1_template_unchanged_revert`** — predicted **harm-kill**, second-order.
Patches *two* names in `event_disposition_service`: `_template_unchanged`
always True, and `validate_approval_binding` to no-op. Entity dispatch still
binds through `action_execution_service`, so frozen A2 stays refused.

- Named killer `b2_t1a_terminal_template_rewrite`: predicted **hit**.
  Consistent rewrite of list + hash column; bind on terminal activate is
  what FULL uses; both patches remove it; resolver then prefers COMPLETED
  once CONTAINED is gone from the approved set.
- Named killer `b2_t4a_terminal_locator_swap`: predicted **miss**.
  Bind is skipped, but FULL egress still compares the operator-selected
  event locator to the command locator. T4a is a post-approval swap of the
  action row only. The case stays unharmed; the named killer does not
  isolate this mutant.

**Not** also killed by the frozen 57 (no frozen case is mediated only by
terminal-activate bind). The kill, when it happens, is from T1a and from
disabling bind, not from `_template_unchanged` becoming a tautology. See D.

B2/gold_ext vs frozen 57: three M1 mutants with B2 named killers are
genuinely not killed by the frozen 57 — `m1_bind_partial_fingerprint`,
`m1_verify_false_negative`, `m1_egress_self_witness`.
`m1_template_unchanged_revert` is also not killed by the frozen 57; T1a
kills it, T4a will miss. No M4 mutant is over-strict-killed by g1–g4; that
is the point of gold_ext and it holds under the predictions below.

### M4 — precision

**`m4_locator_creation_source`** — predicted **over-strict-kill**. Witness becomes ingest `creation_source_ref`. Eval
seeds that field equal to `disposition_source_ref`, so g1–g4 still close.
`g5_compensating_retarget` re-selects the event source and leaves creation
source on the first object; commands that follow the operator will fail
`disposition_source_match`. Named killer hits. Frozen 57 / g1–g4 will not
over-strict-kill.

**`m4_bind_first_approval`** — predicted **over-strict-kill**.
`_latest_approval_detail` becomes earliest-by-`decided_at`. g1–g4 have one
cycle. `g6_retarget_with_reapproval` signs new content on cycle 1; bind
against cycle 0’s fingerprint refuses. Named killer hits. Not frozen 57.

**`m4_level_first_approval`** — predicted **over-strict-kill**.
Merges the earliest `required_level` into the latest detail. The
present-then-check conjunct in `_validate_approval_binding` then sees
bound L2 (or whatever cycle 0 recorded) against a raised L3.
`g11_level_raise_reapproval` is the only golden that diverges those fields.
Not frozen 57. There is still no M1 that *drops* this conjunct; A2’s
level-downgrade kill of `m1_bind_planner_fingerprint` is collateral.

**`m4_one_immediate_action_per_event`** — predicted **over-strict-kill**.
Refuses `execute_action` when another IMMEDIATE row on the event is
EXECUTING/SUCCESS. g1 has one entity action; g2 has none; A3 duplicate
dispatch is the *same* `action_id` and is excluded. Named killer
`g7_multi_stage_disposition`. Not frozen 57.

**`m4_verify_no_recovery`** — predicted **over-strict-kill**.
`retry_writeback` always raises. g3 recovers on a second worker pass, not
through the operator retry API. Named killer `g10_writeback_operator_retry`.
Not frozen 57.

**`m4_outbox_no_retry`** — predicted **over-strict-kill**.
Promotes `WAITING_RETRY` to `DEAD_LETTER` after a leased failure. g9 is the
pre-egress `TransientSubmitError` path. g3 is a *readback* outage after
submit (ACCEPTED, then `ReadbackError`); predicted not to take this
promotion. If a mutation run lists `g3_transient_readback_outage` under
over-strict, the mutant is coarser than the name. Named killer
`g9_retry_after_timeout`. Not frozen 57 under the g9/g3 split.

---

## C. `m1_close_planner_cycle` as survivor

The declaration is honest as a measurement and not honest as a TEI claim.

`_validate_closed_gate` contains:

```
ctx.current_plan_revision is not None
and terminal.plan_revision != ctx.current_plan_revision
```

On the production construction path that predicate is **unreachable**.
`StateMachineService._build_terminal_writeback_view`:

1. Returns `None` when `current_revision is None`.
2. Selects the deferred terminal action with
   `plan_revision == current_revision`.
3. Returns `None` when `outbox.plan_revision` is missing or disagrees with
   that action (the ISSUE-092 incomplete-row path).
4. Stamps `TerminalEventWritebackView.plan_revision = current_revision`
   — not `outbox.plan_revision`.

Whenever the view is non-`None`, `terminal.plan_revision` *is*
`ctx.current_plan_revision`. The gate conjunct compares a value to the
definition used to build it. It is a tautology on that path, not a live
witness of store agreement.

The mutant copies `current_plan_revision` onto the view and calls the
original gate: identity. `a1_missing_outbox_revision` still gets `terminal
is None` from step 3; `a1_stale_closure_cycle` bumps every action row, so
the outbox/action revision check fails at step 3 and the view is again
`None`. Remaining A1 conjuncts (report, evidence, simulated) are untouched
and still refuse their own cases. That is why the runner will report a
survivor. It is not because “aligning the planner’s cycle does not open
harm.” It is because the patch does not change any scored path.

The conjunct is also untested as a rejecting case: no unit test in
`test_state_machine.py` constructs a mismatched pair. Hand-built
`TransitionContext` *could* fire it; the projector never will.

A mutant that *should* be reachable, if the paper wants a cycle-binding
result: skip step 3 (always project a view) and stamp
`plan_revision=outbox.plan_revision` (or the action’s pre-bump revision).
Then `a1_missing_outbox_revision` / `a1_stale_closure_cycle` would hit the
gate conjunct instead of the missing-view error, and a weakening that
re-aligns the view to `current_plan_revision` would be a real harm-kill.
That mutant is not in the set. The shipped one is an equivalent mutant of
dead code. Mutation testing treats those as invalid survivors. Leaving the
production conjunct unpatched “rather than a tautology-looking edit” is a
code-hygiene note, not a mutation result.

---

## D. Terminal-path claim: `_template_unchanged` after bind-on-activate

`_template_unchanged` hashes `approved_terminal_dispositions` and compares
the digest to `approved_operation_template_hash`. Both columns are
planner-writable. A consistent rewrite (`b2_t1a`) makes the local check a
tautology. That observation is correct and is why T1a exists.

Once terminal activate re-runs `validate_approval_binding` against the
latest approval detail, that tautology is **not** a remaining integrity gap
for T1a. Bind’s content hash includes `approved_operation_template_hash` as
a segment. Rewriting the hash column to match the new list is exactly
content drift against the approval record. Bind refuses; the local check
never had to.

What bind does *not* do: re-derive the template segment from the
dispositions list. `recompute_action_content_fingerprint` feeds
`action.approved_operation_template_hash` into the digest, not
`compute_template_hash(_approved_list(action))`. `_template_unchanged` is
the only check that those two planner columns agree with each other. It is
not a check that either column agrees with the approval, except indirectly
when the hash column moves.

So after bind-on-activate:

- Consistent rewrite of list **and** hash column → bind kills (T1a).
  `_template_unchanged` is redundant for that attack.
- List-only rewrite, hash column left as approved → `_template_unchanged`
  is the only refusal. Bind still sees the approved hash column. This case
  is **not in B2**.
- Bind is skipped when `approval_detail` is not a `dict` (the activate path
  is `if isinstance(approval_detail, dict): validate…`). Missing detail is
  not fail-closed. `_template_unchanged` is then the remaining content
  check. Also not in B2.

The shipped mutant patches both the tautological local check *and* bind.
That is a revert of the terminal-path fix, not a probe of whether the local
check is still load-bearing. T1a kills it because bind is gone. T4a will
not, because egress still witnesses object identity.

A stronger mutant, first-order:

1. `_template_unchanged := True`, bind left intact. Predicted **survivor**
   against T1a (bind still kills). Predicted **harm-kill** against a
   list-only rewrite case the suite does not currently have. That is the
   remaining gap.
2. Alternatively, drop only the template-hash segment from
   `recompute_action_content_fingerprint` (keep the column comparison, which
   T1a does not touch). Combined with T1a’s consistent rewrite, bind looks
   loaded and the template drift is invisible. That isolates the “hash the
   planner’s hash column, not the list” hole.

Until one of those exists, the paper should not say that hashing planner
columns against each other is still the terminal integrity problem. Bind-on-
activate closed T1a. What remains is: bind trusts the hash *column*,
activate does not require an approval detail, and `_template_unchanged` is
a consistency predicate over proposer-owned fields.

---

## E. What a skeptical reviewer would demand

The mutation experiment, as designed, cannot support a sentence of the form
“17/18 TEI predicates killed, one documented survivor.” The survivor is an
equivalent mutant of an unreachable close conjunct; A3 uniqueness and A0
roles are out of scope by construction; B2 is required for three real M1
kills (`partial_fingerprint`, `false_negative`, `egress_self_witness`) and
for T1a of a second-order terminal mutant, while several other M1 patches
are already killed by the frozen 57 and should not be billed as
construction-closure results. A reviewer who accepts mutation testing as
evidence for “the gates are not vacuously true” would still ask for: (i) a
first-order drop of the `required_level` present-then-check, which is the
one bind conjunct that is not a fingerprint segment and which A2 only
reaches because `m1_bind_planner_fingerprint` deletes the whole function;
(ii) a mutant of the verify target-mismatch branch, given B2 T6a exists and
none of the three verify mutants touch it; (iii) a first-order
`_template_unchanged` mutant with bind on, plus a list-only rewrite case,
before any remaining-gap claim about the terminal path; (iv) either deletion
of `m1_close_planner_cycle` or a projector-level cycle mutant that can
actually fire. Without those, the table is a useful adjunct to leave-one-out
on the four switches, and a padded kill-rate if it is asked to stand as the
mutation argument for TEI.
