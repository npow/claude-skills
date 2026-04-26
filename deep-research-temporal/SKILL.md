---
name: deep-research-temporal
description: Use when researching, investigating, or exploring a topic systematically via a durable Temporal-backed workflow. Trigger phrases include "deep-research temporal", "sagaflow research", "durable research", "temporal research". Spawns parallel researchers across WHO/WHAT/HOW/WHERE/WHEN/WHY/LIMITS plus cross-cut dimensions (PRIOR-FAILURE, BASELINE, ADJACENT-EFFORTS, STRATEGIC-TIMING, ACTUAL-USAGE). Fact-verification, novelty classification, vocabulary bootstrap for cold-start topics. Fire-and-forget while you do other work.
user_invocable: true
argument: |
  Research seed (a question or topic). Optional flags:
    --arg max_directions=N       number of research directions (default 5, max ~15)
    --arg topic_velocity=fast_moving|stable   recency threshold
  Example: /deep-research-temporal "How are teams adopting Temporal for LLM orchestration?" --arg max_directions=8
---

# deep-research-temporal (deprecation shim)

This skill has been unified with [`deep-research`](../deep-research/SKILL.md) — see its `## Execution routing` section for the sagaflow launch recipe.

The `-temporal` directory is preserved because sagaflow's worker discovers skill packages by directory name (see `_DIR_TO_LEGACY` in `sagaflow/worker.py`). Do not rename or move `__init__.py`, `workflow.py`, `state.py`, or `prompts/` in this directory without a coordinated worker-restart + code update.
