---
name: monitor-temporal
description: "Durable Temporal-backed monitoring workflow that survives session crashes. Use when monitoring health, metrics, or system state via sagaflow."
user-invocable: true
---

# monitor-temporal (sagaflow routing shim)

This directory contains the Temporal workflow implementation for the `monitor` skill. The skill's documentation and in-session logic lives in [`monitor/SKILL.md`](../monitor/SKILL.md).

This directory is preserved because sagaflow's worker discovers skill packages by directory name. Do not rename or move `__init__.py`, `state.py`, or `workflow.py` in this directory without a coordinated worker-restart + code update.
