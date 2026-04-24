---
name: autopilot-temporal
description: Use when running full-lifecycle autonomous execution from a vague idea to working verified code via a durable Temporal-backed workflow that survives session crashes. Trigger phrases include "autopilot temporal", "sagaflow autopilot", "durable autopilot", "temporal-backed end-to-end build". Idea → battle-tested design → consensus plan → executed code → audited defects → three independent judge verdicts → honest completion report. Iron-law phase gates; no coordinator self-approval. Fire-and-forget for long-running builds.
user_invocable: true
argument: |
  Initial idea (one sentence is enough; the workflow will refine it).
  Example: /autopilot-temporal "cli tool that summarizes git log by author for the last N days"
---

# autopilot-temporal (deprecation shim)

This skill has been unified with [`autopilot`](../autopilot/SKILL.md) — see its `## Durable execution` section for the sagaflow launch recipe.

The `-temporal` directory is preserved because sagaflow's worker discovers skill packages by directory name (see `_DIR_TO_LEGACY` in `/Users/npow/code/skillflow/sagaflow/worker.py`). Do not rename or move `__init__.py`, `workflow.py`, `state.py`, or `prompts/` in this directory without a coordinated worker-restart + code update.
