---
name: deep-design-temporal
description: Use when designing, specifying, architecting, or drafting a design via a durable Temporal-backed workflow that survives session crashes. Trigger phrases include "deep-design temporal", "sagaflow design", "durable design", "temporal design review". DFS-based flaw-finding with parallel critic agents that stress-test until coverage saturates. Output is a battle-tested design document with an honest coverage report. Fire-and-forget while you do other work.
user_invocable: true
argument: |
  Concept to design (a product, system, feature, protocol, workflow). Optional flags:
    --arg max_rounds=N          iteration cap for stress-test loop (default 2)
  Example: /deep-design-temporal "multi-tenant rate limiter with per-tenant quotas" --arg max_rounds=3
---

# deep-design-temporal (deprecation shim)

This skill has been unified with [`deep-design`](../deep-design/SKILL.md) — see its `## Durable execution` section for the sagaflow launch recipe.

The `-temporal` directory is preserved because sagaflow's worker discovers skill packages by directory name (see `_DIR_TO_LEGACY` in `sagaflow/worker.py`). Do not rename or move `__init__.py`, `workflow.py`, `state.py`, or `prompts/` in this directory without a coordinated worker-restart + code update.
