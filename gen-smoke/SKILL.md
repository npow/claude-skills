---
name: gen-smoke
description: Smoke test for the sagaflow generic interpreter. Writes a greeting to report.md and ends turn. Use only for testing the interpreter round-trip.
user_invocable: true
argument: |
  --arg name=<someone>
---

# gen-smoke

This is a smoke test for the sagaflow generic interpreter. Your job is trivial:

1. Use the `write_artifact` tool with path `report.md` and content `Hello from the generic interpreter, $name!`.
2. End your turn. Do NOT call any other tools. Do NOT spawn subagents.

That's it. One tool call, then stop.
