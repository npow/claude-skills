---
name: build-temporal
description: "Durable Temporal-backed build workflow that survives session crashes. Use when building, scaffolding, or implementing a spec via sagaflow."
user-invocable: true
---

# build-temporal (sagaflow routing shim)

The `build` skill has been absorbed into [`autopilot`](../autopilot/SKILL.md). This directory contains the standalone Temporal workflow implementation that sagaflow's worker discovers by directory name (see `_DIR_TO_LEGACY` in `sagaflow/worker.py`). Do not rename or move `__init__.py`, `state.py`, or `workflow.py` in this directory without a coordinated worker-restart + code update.
