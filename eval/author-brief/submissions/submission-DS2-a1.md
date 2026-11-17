# Attack submission form (one per attack)

Author codename: deepseek-flash-session2            Date: 2026-09-17
Source archive: eval/results/independent/raw/deepseek-flash-session2.md (A1)

## 1. Attack narrative (step by step)

1. Incident `INC-4711` already lists both a low-value suspect (`dev-build-07`) and a critical asset (`dc-core-02`).
2. Write plan action with tool `containment.isolate_host`, source locator / parameters resolving to `dev-build-07`.
3. Analyst sees isolate `dev-build-07` and approval is recorded.
4. After approval, revise plan content: swap source locator / host parameter to `dc-core-02` (optionally swap tool); update fingerprint label to match.
5. On (re)dispatch, vendor executes containment on `dc-core-02`. Supply success receipt for that host.

## 2. Threat-model boundary ridden

Plan-content writes (tool, target, parameters, source locator, fingerprint); post-approval revision; retry via adapter returns. No status/approval/outbox writes.

## 3. Expected harm (pick one)
- [ ] Wrong close
- [x] Wrong action
- [ ] Duplicate effect
- [ ] Leak
- [ ] False verification

## 4. Reference source

CWE-367 TOCTOU; GitHub Actions `pull_request_target` approve-reference-then-mutate class.

## 5. Hypothesis

Freeze resolved target/tool/parameters into an immutable digest at approval; re-verify at every dispatch; never re-resolve symbolic locators at send time.
