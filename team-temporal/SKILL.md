---
name: team-temporal
description: Use when coordinating multiple agents on a staged pipeline — plan → PRD → exec → verify → fix — via a durable Temporal-backed workflow that survives session crashes. Trigger phrases include "team temporal", "sagaflow team", "durable team", "temporal-backed agent team". File-based state, independent critic/verifier gates, two-stage review on every source modification, honest termination labels. Fire-and-forget while you do other work.
user_invocable: true
argument: |
  Task the team should complete. Optional flags:
    --arg n_workers=N            parallel executor agents (1-8; default 2)
    --arg max_fix_iters=N        fix-loop iteration cap (default 3)
  Example: /team-temporal "add oauth login flow with tests" --arg n_workers=3 --arg max_fix_iters=4
---

# team-temporal

Launches the `team` workflow on sagaflow. Staged pipeline: planner → PRD writer → N parallel executors → verifier → fixer. Each source modification gets two-stage review (critic + verifier). Honest termination labels; no coordinator self-approval.

## How to invoke

```
Bash(
  run_in_background=true,
  command="sagaflow launch team --arg task='<TASK>' --arg n_workers=<N> --arg max_fix_iters=<M> --await"
)
```

Substitute:
- `<TASK>` — the task the team should complete (one sentence is fine).
- `<N>` — executors in parallel (1-8, clamped; default 2).
- `<M>` — fix-loop iteration cap (default 3).

Tell the user: "Launched team on <task>. Running in the background — I'll surface the verifier verdict + diff when the workflow completes."

## Termination labels

`Verified complete` · `Verified with caveats` · `Fix loop exhausted` · `Planner blocked — insufficient information` · `User-stopped at stage N` · `Hard stop at stage N`

## Result surfacing

Report at `~/.sagaflow/runs/<run_id>/SUMMARY.md`. The same directory also contains `handoffs/plan.md`, `handoffs/plan-verdict.md`, `exec/codebase-context.md`, and per-stage prompt transcripts. Surface the termination label + summary of changes to the user.
