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

# team-temporal (deprecation shim)

This skill has been unified with [`team`](../team/SKILL.md) — see its `## Durable execution` section for the sagaflow launch recipe.

The `-temporal` directory is preserved because sagaflow's worker discovers skill packages by directory name (see `_DIR_TO_LEGACY` in `sagaflow/worker.py`). Do not rename or move `__init__.py`, `workflow.py`, `state.py`, or `prompts/` in this directory without a coordinated worker-restart + code update.
