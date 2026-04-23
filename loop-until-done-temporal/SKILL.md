---
name: loop-until-done-temporal
description: Use when a task must be driven to guaranteed completion via a durable Temporal-backed workflow that survives session crashes. Trigger phrases include "loop-until-done temporal", "sagaflow loop-until-done", "durable loop until complete", "temporal-backed persistence loop". PRD-driven execution — breaking work into user stories with structured acceptance criteria, iterating story-by-story with independent verification, terminating only when every criterion has fresh passing evidence. Fire-and-forget for guaranteed completion.
user_invocable: true
argument: |
  Task to drive to completion. Optional flags:
    --arg max_iter=N             iteration cap per story (default 5)
  Example: /loop-until-done-temporal "all tests pass and coverage >= 80%" --arg max_iter=8
---

# loop-until-done-temporal

Launches the `loop-until-done` workflow on sagaflow. PRD-driven persistence loop: story → acceptance criteria → iterate → independent verification → next story. Honest termination labels; no self-approval.

## How to invoke

```
Bash(
  run_in_background=true,
  command="sagaflow launch loop-until-done --arg task='<TASK>' --arg max_iter=<N> --await"
)
```

Substitute:
- `<TASK>` — the task or goal to drive to completion.
- `<N>` — max iterations per story (default 5).

Tell the user: "Launched loop-until-done on <task>. Running in the background — I'll surface the per-story verdicts + final report when the workflow completes."

## Termination labels

`All stories verified complete` · `Some stories unverified — loop exhausted` · `PRD blocked — task under-specified` · `Reviewer rejected — criteria unmet` · `User-stopped at story N` · `Hard stop at story N`

## Result surfacing

Report at `~/.sagaflow/runs/<run_id>/summary.md`. The same directory also contains `prd-prompt.txt`, per-story `executor-sN.txt`, `reviewer-prompt.txt`, and `falsifiability-prompt.txt`. Surface the verified/unverified split + unresolved criteria to the user.
