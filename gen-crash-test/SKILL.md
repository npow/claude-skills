---
name: gen-crash-test
description: Crash-recovery test for the sagaflow generic interpreter. Multiple sequential tool calls with a sleep in the middle.
user_invocable: true
argument: |
  --arg name=<someone>
---

# gen-crash-test

Crash-recovery test for the sagaflow generic interpreter. Execute these three steps IN ORDER, one at a time, waiting for each tool result before the next:

1. Use `write_artifact` with path `step1.md` content `Step 1 complete for $name`.
2. Use `bash` with command `sleep 6 && echo 'slept 6s'` and a 30s timeout.
3. Use `write_artifact` with path `step3.md` content `Step 3 complete for $name — all steps survived!`.

After step 3, end your turn. One text summary, no more tool calls.
