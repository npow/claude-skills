---
name: deep-plan-temporal
description: Use before touching code for any multi-step task via a durable Temporal-backed workflow that survives session crashes. Trigger phrases include "deep-plan temporal", "sagaflow plan", "durable plan", "temporal planning". Produces an ADR-backed plan with verification-backed acceptance criteria via a Planner → Architect → Critic consensus loop. Fire-and-forget — refine the plan while you do other work.
user_invocable: true
argument: |
  Task to plan (a feature, refactor, migration, architectural decision). Optional flags:
    --arg max_iter=N            Planner↔Critic iteration cap (default 5)
  Example: /deep-plan-temporal "migrate auth from sessions to JWT" --arg max_iter=6
---

# deep-plan-temporal (deprecation shim)

This skill has been unified with [`deep-plan`](../deep-plan/SKILL.md) — see its `## Durable execution` section for the sagaflow launch recipe.

The `-temporal` directory is preserved because sagaflow's worker discovers skill packages by directory name (see `_DIR_TO_LEGACY` in `sagaflow/worker.py`). Do not rename or move `__init__.py`, `workflow.py`, `state.py`, or `prompts/` in this directory without a coordinated worker-restart + code update.
