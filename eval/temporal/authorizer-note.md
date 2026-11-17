# Y1 — Temporal authorizer on the lab plane

Survey date: 2026-09-18. Lab instance: Temporal Python SDK
`WorkflowEnvironment.start_local()` with the bundled single-binary
dev server (Server 1.32.0 in the frozen run
`eval/results/temporal/run-20260916T120721Z.json`). Never pooled
with the 57. No new 0/N.

## Question

Can the lab plane enforce an analogue of the SOC planner / actuation
role split: the planner must not be able to call the analyst-seat
`approve` update or the worker activity path?

## What a deployment would use

Self-hosted Temporal exposes two **frontend** plugins
([self-hosted security](https://docs.temporal.io/self-hosted-guide/security)):

- `ClaimMapper` — identity → roles / permissions
- `Authorizer` — `Authorize` on every incoming API call

They are registered on the Go server:

```go
temporal.NewServer(
    temporal.WithAuthorizer(newCustomAuthorizer()),
    temporal.WithClaimMapper(...),
)
```

That is the production counterpart of PostgreSQL `GRANT` on
`CLOSED` / the outbox: a privilege the proposer login cannot issue.

## What `start_local` actually exposes

`temporalio.testing.WorkflowEnvironment.start_local` starts the
downloaded **dev server** and returns a Client. Its knobs are
namespace, TLS, `rpc_metadata`, **client** interceptors, UI, and
`dev_server_extra_args`. There is no `WithAuthorizer` /
`WithClaimMapper` hook. The default server authorizer is
`noopAuthorizer` unless those Go options are set, and this lab
binary is not started through `temporal.NewServer`.

SDK **worker interceptors** (`Worker(..., interceptors=[...])`,
including `handle_update_handler`) can observe or reject an update
*inside the worker process*. That is still the workflow TCB — the
same address space as the handlers — not a database-style privilege
on a different login. A planner that holds the same Client the test
uses can still issue `approve`.

## Verdict

**Not testable on the lab server.** The declared boundary in
`eval/temporal/README.md` and `paper/main.tex` §eval-temporal
stands: the planner cannot call `approve` in the threat model the
way A0 forbids planner SQL on privileged columns; enforcing that in
a deployment is the Temporal authorizer's job. We did not invent a
0/N for an intercept we cannot install.

No change to Table `tab:temporal`. No Temporal re-run.
