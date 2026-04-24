---
name: deep-debug-temporal
description: Use when a bug, test failure, or unexpected behavior needs diagnosing on a durable Temporal-backed workflow that survives session crashes. Trigger phrases include "deep-debug temporal", "sagaflow debug", "durable debug", "temporal-backed debugging". Hypothesis generation with 2-pass blind judges + rebuttal + probes + fix/verify + Opus architectural escalation after 3 failed fix attempts. Fire-and-forget; find the root cause while you do other work.
user_invocable: true
argument: |
  Symptom text (one sentence is fine) and optionally:
    --arg reproduction=<command>   exact command that triggers the symptom
    --arg num_hypotheses=N         default 4 (max 6)
  Example: /deep-debug-temporal "test_auth intermittently fails with 500" --arg reproduction="pytest tests/auth"
---

# deep-debug-temporal (deprecation shim)

This skill has been unified with [`deep-debug`](../deep-debug/SKILL.md) — see its `## Durable execution` section for the sagaflow launch recipe.

The `-temporal` directory is preserved because sagaflow's worker discovers skill packages by directory name (see `_DIR_TO_LEGACY` in `sagaflow/worker.py`). Do not rename or move `__init__.py`, `workflow.py`, `state.py`, or `prompts/` in this directory without a coordinated worker-restart + code update.
