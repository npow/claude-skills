---
name: deep-qa-temporal
description: Use when reviewing, auditing, QAing, critiquing, or assessing any artifact — a spec, code change, diff, PR, research report, skill, prompt, or document — via a durable Temporal-backed workflow that survives session crashes and surfaces findings when you return. Trigger phrases include "deep-qa temporal", "QA this with sagaflow", "run durable QA", "temporal-backed review". Produces a severity-sorted qa-report.md with two-pass independent judges, rationalization auditor, and canonical termination label. Fire-and-forget — you do other work while the workflow runs.
user_invocable: true
argument: |
  Path to the artifact file (absolute or workspace-relative), optionally followed by flags:
    --type doc|code|research|skill   override artifact-type auto-detection
    --max-rounds N                   override max QA rounds (default 3)
  Example: /deep-qa-temporal ./docs/spec.md --type doc --max-rounds 3
---

# deep-qa-temporal (deprecation shim)

This skill has been unified with [`deep-qa`](../deep-qa/SKILL.md) — see its `## Durable execution` section for the sagaflow launch recipe.

The `-temporal` directory is preserved because sagaflow's worker discovers skill packages by directory name (see `_DIR_TO_LEGACY` in `/Users/npow/code/skillflow/sagaflow/worker.py`). Do not rename or move `__init__.py`, `workflow.py`, `state.py`, or `prompts/` in this directory without a coordinated worker-restart + code update.
