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

# flaky-test-diagnoser-temporal (deprecation shim)

This skill has been unified with [`flaky-test-diagnoser`](../flaky-test-diagnoser/SKILL.md) — see its `## Durable execution` section for the sagaflow launch recipe.

The `-temporal` directory is preserved because sagaflow's worker discovers skill packages by directory name (see `_DIR_TO_LEGACY` in `/Users/npow/code/skillflow/sagaflow/worker.py`). Do not rename or move `__init__.py`, `workflow.py`, `state.py`, or `prompts/` in this directory without a coordinated worker-restart + code update.
