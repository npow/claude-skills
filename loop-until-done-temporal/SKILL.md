---
name: loop-until-done-temporal
description: Use when a task must be driven to guaranteed completion via a durable Temporal-backed workflow that survives session crashes. Trigger phrases include "loop-until-done temporal", "sagaflow loop-until-done", "durable loop until complete", "temporal-backed persistence loop". PRD-driven execution — breaking work into user stories with structured acceptance criteria, iterating story-by-story with independent verification, terminating only when every criterion has fresh passing evidence. Fire-and-forget for guaranteed completion.
user_invocable: true
argument: |
  Task to drive to completion. Optional flags:
    --arg max_iter=N             iteration cap per story (default 5)
  Example: /loop-until-done-temporal "all tests pass and coverage >= 80%" --arg max_iter=8
---

# loop-until-done-temporal (deprecation shim)

This skill has been absorbed into [`autopilot`](../autopilot/SKILL.md) (Phase 3 verify loop). See autopilot's `## Execution routing` section for the sagaflow launch recipe.

The `-temporal` directory is preserved because sagaflow's worker discovers skill packages by directory name (see `_DIR_TO_LEGACY` in `sagaflow/worker.py`). Do not rename or move `__init__.py`, `workflow.py`, `state.py`, or `prompts/` in this directory without a coordinated worker-restart + code update.
