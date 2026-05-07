---
name: gen-smoke
description: Smoke test for the sagaflow generic interpreter. Writes a greeting to report.md and ends turn. Use only for testing the interpreter round-trip.
user_invocable: true
argument: |
  --arg name=<someone>

category: meta
capabilities: [temporal-workflow]
sagaflow_only: true
input_types: [git-diff, repo]
output_types: [report, code]
complexity: moderate
cost_profile: low
maturity: beta
metadata_source: inferred
---

# gen-smoke

This is a smoke test for the sagaflow generic interpreter's `write_artifact` tool.
It **requires sagaflow** — there is no in-session fallback because the test target
is the sagaflow interpreter itself.

## Pre-flight check

Run `sagaflow doctor`. If Temporal is unreachable, stop immediately and report:

> gen-smoke requires a running sagaflow worker (Temporal backend). Run `temporal server start-dev` and `sagaflow worker run`, then retry.

Do NOT attempt an in-session workaround — this skill tests sagaflow, not Claude Code tools.

## Steps (sagaflow only)

1. Use the `write_artifact` tool with path `report.md` and content `Hello from the generic interpreter, $name!`.
2. End your turn. Do NOT call any other tools. Do NOT spawn subagents.
