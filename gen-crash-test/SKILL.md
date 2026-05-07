---
name: gen-crash-test
description: Crash-recovery test for the sagaflow generic interpreter. Multiple sequential tool calls with a sleep in the middle.
user_invocable: true
argument: |
  --arg name=<someone>

category: meta
capabilities: [temporal-workflow]
sagaflow_only: true
input_types: [git-diff]
output_types: [report, code]
complexity: moderate
cost_profile: low
maturity: beta
metadata_source: inferred
---

# gen-crash-test

Crash-recovery test for the sagaflow generic interpreter's crash-recovery and
sequential tool execution. It **requires sagaflow** — there is no in-session
fallback because the test target is the sagaflow interpreter itself.

## Pre-flight check

Run `sagaflow doctor`. If Temporal is unreachable, stop immediately and report:

> gen-crash-test requires a running sagaflow worker (Temporal backend). Run `temporal server start-dev` and `sagaflow worker run`, then retry.

Do NOT attempt an in-session workaround — this skill tests sagaflow, not Claude Code tools.

## Steps (sagaflow only)

Execute these three steps IN ORDER, one at a time, waiting for each tool result before the next:

1. Use `write_artifact` with path `step1.md` content `Step 1 complete for $name`.
2. Use `bash` with command `sleep 6 && echo 'slept 6s'` and a 30s timeout.
3. Use `write_artifact` with path `step3.md` content `Step 3 complete for $name — all steps survived!`.

After step 3, end your turn. One text summary, no more tool calls.
