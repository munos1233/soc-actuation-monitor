# Eval: actuation integrity under an untrusted planner

Two suites, both driven through the production service chain against a real
PostgreSQL and a vendor stub:

- **Suite B** injects adversaries A0–A5 at the system boundary — rows a planner
  writes, receipts and observation answers a vendor returns, repeated dispatch,
  and planner-login SQL — and scores harm from database and vendor-side facts
  afterwards.
- **Suite A** runs the golden path under exactly the same `full` configuration
  and reports closure rate, over-block, extra manual steps, and extra worker
  passes. `force_close` is forbidden there (`gold.py::FORCE_CLOSE_FORBIDDEN`):
  a golden path that fails, fails.

The harness never calls a mediator directly and never reads a mediator's return
value. Predicate-level checks still exist (`app/eval_suite/component.py`) but
they are an appendix: they show a check is wired to the switch it claims, which
is not evidence of mediation on the actuation path.

## Layout

| Path | Role |
|---|---|
| `backend/app/eval_suite/chain.py` | one case, end to end: plan → dispatch → verify → activate → close |
| `backend/app/eval_suite/cases.py` | the adversary set, with the mediator each case is a claim about |
| `backend/app/eval_suite/gold.py` | suite A substrate (g1–g4, frozen 2026-09-10) |
| `backend/app/eval_suite/gold_ext.py` | suite A extension (g5–g11); never pooled with g1–g4 |
| `backend/app/eval_suite/b2_cases.py` | construction-closure attacks; never pooled with the 57 |
| `backend/app/eval_suite/mutants.py` | 18 harness-only mediator mutants; production imports nothing |
| `backend/app/eval_suite/world.py` | isolated world: migrations, services, vendor, observation surface |
| `backend/app/eval_suite/vendor.py` | vendor stub: receipt profiles, writeback records, readback |
| `backend/app/eval_suite/observation.py` | what a verification query is allowed to learn, and how it can lie |
| `backend/app/eval_suite/runner.py` | matrix, harm rates, leave-one-out, markdown |
| `eval/harness/run_suite.py` | CLI |
| `eval/cases/adversary_set.json` | generated case registry (`--export-cases`) |
| `eval/results/` | recorded runs (`latest.json`, `latest.md`) |
| `backend/app/eval_suite/backlog.py` | mixed gold / fail-closed arrivals; global READY depth |
| `backend/app/eval_suite/search.py` | coverage search over implemented Injection knobs |
| `backend/app/eval_suite/process_split.py` | planner child / actuation parent: writer factory refused |
| `eval/taxonomy/tei_threats.md` | TEI definition and published threat grid |
| `eval/model/TEI.tla` | TEI specification; `tei_engine.py` is the same `Next` |
| `eval/model/TEIPair.tla` | Twin spec for AttrView / CloseOK; `view_lemma.md` |
| `eval/k8s/` | Kubernetes lab + kind/Gatekeeper/TEI webhook |
| `eval/taxonomy/sampling.md` | external-sample protocol (written before cases) |
| `eval/taxonomy/external_sample.json` | frozen retrieval log + mappings |
| `backend/app/eval_suite/k8s_chain.py` | fixture 22/22 CI path; not pooled with the 57 |
| `backend/app/eval_suite/heldout_cases.py` | SOC held-out from the sample; not in 57 |
| `backend/app/eval_suite/kind_corpus.py` | kind C5 corpus from the sample; not fixture 22 |

## Switches (production default: every mediator loaded)

| Environment variable | What is unloaded |
|---|---|
| `EVAL_DISABLE_CLOSED_GATE` | closure evidence predicate |
| `EVAL_DISABLE_FINGERPRINT_RECHECK` | approval binding recheck at dispatch |
| `EVAL_DISABLE_VERIFY_PHASE_SPLIT` | observation/actuation split |
| `EVAL_DISABLE_OUTBOUND_GUARD` | outbound field allowlist and locator check |

Setting any of them is rejected when `Settings` is constructed unless
`EVAL_HARNESS_MODE=true` is also set, so a process that unloads a mediator by
accident fails to start rather than serving traffic with a gate missing. That is
a guard against operator error, not tamper-proofness: these switches are not a
security mechanism and are excluded from the trusted boundary the paper claims.

Configurations: `naive`, the four single-gate configurations, `full`, the
four leave-one-out configurations `full_minus_{close,bind,verify,egress}`,
and the two interaction pairs `close_and_verify` and `bind_and_egress`.
Four further 2-gate cells (`close_and_bind`, `close_and_egress`,
`bind_and_verify`, `verify_and_egress`) are `LATTICE_CONFIGS` and
`make paper-eval-lattice`; they are not in the frozen 17-config matrix.
A third vendor envelope (`envelope_b`) is a separate target and is never
merged into the headline mock/pseudo-live denominator.

## Substrate arms

Four mechanisms have no production switch and never will: the partial unique
index on active writeback heads, the in-transaction supersede that retires the
prior head, the re-read of the active head at delivery time, and the
compare-and-set on action status under `FOR UPDATE`. They are ablated by
weakening the substrate in the harness instead — `app/eval_suite/substrate.py`
drops the index in the evaluation database and substitutes the naive shape of
each code-level mechanism. Production code is unchanged and imports nothing from
that module.

| Configuration | Weakened |
|---|---|
| `full_minus_head_index` | index dropped |
| `full_minus_head_supersede` | enqueue appends without retiring the prior head |
| `full_minus_head_uniqueness` | both of the above |
| `full_minus_head_assertion` | both of the above, plus the delivery-time re-read |
| `full_minus_claim_cas` | claim re-reads without the lock and without the status CAS |

The head arms are a ladder because the mechanisms are layered, and reporting them
independently would have said that none of them matters. Dropping the index alone
changes nothing (the supersede already retired the loser); weakening the
supersede alone changes nothing (the index rejects the second insert, visible as
an `IntegrityError` in the case notes); only with both gone do two rows both claim
to be the current head. The delivery-time re-read sits under both, so the arm that
ablates it has to remove them first.

These arms answer a different question from the gate ablation — not "was the gate
loaded" but "would a plausible naive implementation of this step have let the harm
through" — and the two tables are kept apart so nobody reads the system as having
nine switches. It has four.

## Vendor columns

| Column | Mode | Adapter | Writeback |
|---|---|---|---|
| `mock` | `mock_xdr` | `mock` | disabled |
| `pseudo_live` | `pseudo_live_xdr` | `http` | enabled |

The pseudo-live stub can acknowledge without confirming, report `SUCCESS` with
nothing behind it, drop the readback channel, and echo a verification query back
as an observation. The two columns are never merged, and a case that only closes
in the mock column is reported in the mock column.

## Baseline

`--planners untrusted_planner,dead_playbook`. The dead-playbook arm runs the
same actions with no adaptive planner, so vendor-side and multiplicity
adversaries still apply to it while post-approval drift and egress injection do
not. Cases it cannot mount are reported as not applicable rather than as
prevented harm (`Injection.applies_to`).

## Running it

The suite writes to the database and Redis it is given, and the substrate arms
deliberately drop a uniqueness constraint. Never point it at anything you care
about. `REPRODUCE.md` is the full recipe; the short version:

```bash
make paper-eval-up        # isolated postgres :55432 / redis :56379
make paper-eval-matrix    # every configuration, both columns, both planners
make paper-eval-quick     # naive vs full, mock column only — minutes
make paper-eval-heldout   # sample-derived SOC cases; not pooled with 57
make paper-eval-playbook-semantic  # closer assumption; not a product eval
make paper-eval-lattice   # 2^4 live 4×57 (needs the eval DB)
make paper-eval-k8s       # fixture 22/22 CI
make paper-eval-k8s-kind  # C5 headline; fails if kind cannot start
make paper-eval-cases     # regenerate eval/cases/adversary_set.json
make paper-eval-down
```

Equivalently, by hand:

```bash
# Prefer the Make targets. They point at the isolated Compose project.
# Hand-export only if you already have that project's owner DSN.
export DATABASE_URL='postgresql+asyncpg://<eval-owner>:<eval-owner>@localhost:55432/<eval-db>'
export REDIS_URL=redis://localhost:56379/0
python eval/harness/run_suite.py --out eval/results
```

## What the pytest gate does and does not do

```bash
cd backend && pytest tests/eval -q
```

These are structural guards: every adversary is covered, every case perturbs
something, golden cases carry no adversary, the configuration matrix contains
the single-gate, leave-one-out and substrate arms (and the substrate arms nest),
and the appendix predicates hold. There
is deliberately no test that asserts an ablation table from mediator return
values — that table is what the boundary run produces, and asserting it from
predicates is how the previous version of this suite fooled itself.

They also include positive controls for the scorer. Most reported cells are
zeros, and a zero means nothing unless the instrument can produce a one, so one
test per harm kind hands the scorer a world state that is harm by construction
and checks that it says so. One control covers the vendor stub itself: a replayed
idempotency key must collapse onto one external effect, and a fresh key must not.
Getting that wrong is what made A3 flicker before the stub honoured the
idempotency contract it advertises.
