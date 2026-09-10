# Eval: actuation integrity under an untrusted planner

Two suites, both driven through the production service chain against a real
PostgreSQL and a vendor stub:

- **Suite B** injects adversaries A1–A5 at the system boundary — rows a planner
  writes, receipts and observation answers a vendor returns, repeated dispatch —
  and scores harm from database and vendor-side facts afterwards.
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
| `backend/app/eval_suite/gold.py` | suite A |
| `backend/app/eval_suite/world.py` | isolated world: migrations, services, vendor, observation surface |
| `backend/app/eval_suite/vendor.py` | vendor stub: receipt profiles, writeback records, readback |
| `backend/app/eval_suite/observation.py` | what a verification query is allowed to learn, and how it can lie |
| `backend/app/eval_suite/runner.py` | matrix, harm rates, leave-one-out, markdown |
| `eval/harness/run_suite.py` | CLI |
| `eval/cases/adversary_set.json` | generated case registry (`--export-cases`) |
| `eval/results/` | recorded runs (`latest.json`, `latest.md`) |

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

Configurations: `naive`, the four single-gate configurations, `full`, and the
four leave-one-out configurations `full_minus_{close,bind,verify,egress}`.

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

The suite writes to the database and Redis it is given. Never point it at
anything you care about.

```bash
docker compose -p shadowtrace-eval up -d postgres redis
export DATABASE_URL=postgresql+asyncpg://shadowtrace:shadowtrace@localhost:55432/shadowtrace
export REDIS_URL=redis://localhost:56379/0

python eval/harness/run_suite.py --out eval/results
python eval/harness/run_suite.py --configs naive,full --columns mock --skip-gold   # quick signal
python eval/harness/run_suite.py --export-cases eval/cases/adversary_set.json
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
