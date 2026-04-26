---
name: proposal-reviewer-temporal
description: Use when reviewing, critiquing, evaluating, or assessing a proposal, pitch, grant application, or business plan via a durable Temporal-backed workflow that survives session crashes. Trigger phrases include "proposal-reviewer temporal", "sagaflow proposal review", "durable proposal review", "temporal-backed proposal critique". Fact-checks claims, maps competitive landscape, identifies structural problems, produces an honest recommendation. Fire-and-forget while you do other work.
user_invocable: true
argument: |
  Path to the proposal file (absolute or workspace-relative). Minimum 200 words.
    --path <proposal.md>         the proposal file to review
  Example: /proposal-reviewer-temporal --path ./docs/grant-proposal.md
---

# proposal-reviewer-temporal (deprecation shim)

This skill has been unified with [`proposal-reviewer`](../proposal-reviewer/SKILL.md) — see its `## Execution routing` section for the sagaflow launch recipe.

The `-temporal` directory is preserved because sagaflow's worker discovers skill packages by directory name (see `_DIR_TO_LEGACY` in `sagaflow/worker.py`). Do not rename or move `__init__.py`, `workflow.py`, `state.py`, or `prompts/` in this directory without a coordinated worker-restart + code update.
