---
name: flaky-test-diagnoser-temporal
description: Use when a test is flaky, intermittent, non-deterministic, or randomly failing via a durable Temporal-backed workflow that survives session crashes. Trigger phrases include "flaky-test-diagnoser temporal", "sagaflow flaky test", "durable flakiness diagnosis", "temporal-backed flaky-test investigation". Multi-run experiments, isolation tests, ordering permutations, timing analysis. Fire-and-forget — let the workflow grind while you do other work.
user_invocable: true
argument: |
  Test identifier (pytest nodeid or equivalent) and the exact run command. Required:
    --arg test='<test identifier>'    the test (e.g. tests/test_foo.py::test_bar)
    --arg command='<run command>'     exact shell command that runs it
    --arg n_runs=N                     number of stability runs (default 10)
  Example: /flaky-test-diagnoser-temporal --arg test='tests/test_auth.py::test_login' --arg command='pytest tests/test_auth.py::test_login -q' --arg n_runs=20
---

# flaky-test-diagnoser-temporal

Launches the `flaky-test-diagnoser` workflow on sagaflow. Runs the test N times, isolates per-run state, tries ordering permutations, analyzes timing variance. Emits a diagnosis with confidence and suspected root cause.

## How to invoke

Both `test` and `command` are REQUIRED — workflow rejects input without them.

```
Bash(
  run_in_background=true,
  command="sagaflow launch flaky-test-diagnoser --arg test='<TEST_ID>' --arg command='<RUN_CMD>' --arg n_runs=<N> --await"
)
```

Substitute:
- `<TEST_ID>` — the test identifier (e.g. `tests/test_foo.py::test_bar`).
- `<RUN_CMD>` — the exact shell command that runs that test.
- `<N>` — stability runs to perform (default 10).

Tell the user: "Launched flaky-test-diagnoser on <test>. Running in the background (N stability runs + isolation + ordering + timing) — I'll surface the diagnosis when the workflow completes."

## Termination labels

`Root cause identified` · `Strong hypothesis — insufficient discriminators` · `Cannot reproduce — test stable in N runs` · `Environmental — platform/resource factor` · `Hard stop at phase N` · `User-stopped at phase N`

## Result surfacing

Report at `~/.sagaflow/runs/<run_id>/report.md` with pass/fail table, isolation+ordering results, timing analysis, top hypothesis with evidence, and proposed fix or mitigation. Surface pass rate + leading root cause to the user.
