---
name: deep-plan-temporal
description: Use before touching code for any multi-step task via a durable Temporal-backed workflow that survives session crashes. Trigger phrases include "deep-plan temporal", "sagaflow plan", "durable plan", "temporal planning". Produces an ADR-backed plan with verification-backed acceptance criteria via a Planner → Architect → Critic consensus loop. Fire-and-forget — refine the plan while you do other work.
user_invocable: true
argument: |
  Task to plan (a feature, refactor, migration, architectural decision). Optional flags:
    --arg max_iter=N            Planner↔Critic iteration cap (default 5)
  Example: /deep-plan-temporal "migrate auth from sessions to JWT" --arg max_iter=6
---

# deep-plan-temporal

Launches the `deep-plan` workflow on sagaflow. Planner proposes → Architect reviews → Critic attacks. Loops until consensus or max_iter; emits an ADR-backed plan with verification-backed acceptance criteria.

## How to invoke

```
Bash(
  run_in_background=true,
  command="sagaflow launch deep-plan --arg task='<TASK>' --arg max_iter=<N> --await"
)
```

Substitute `<TASK>` with the task description and `<N>` with the iteration cap (default 5).

Tell the user: "Launched deep-plan on <task>. Running in the background — I'll surface the ADR-backed plan when the workflow completes."

## Termination labels

`Consensus reached` · `Max iterations reached` · `User-stopped at iteration N` · `Hard stop at iteration N`

## Result surfacing

Report at `~/.sagaflow/runs/<run_id>/plan.md` with the final plan. The same directory also contains `adr.md` (decisions + alternatives + rationale) and per-iteration `planner-iterN.txt` / `architect-iterN.txt` / `critic-iterN.txt` transcripts. Surface the top-level checklist + unresolved open questions to the user.
