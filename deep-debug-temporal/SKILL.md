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

# deep-debug-temporal

Launches the `deep-debug` workflow on sagaflow. Generates parallel hypotheses across orthogonal dimensions (correctness / concurrency / environment / resource / ordering / dependency / outside-frame), independent blind+informed judges, discriminating probes, fix-and-verify cycle, and Opus architectural escalation if 3 fix attempts fail.

## How to invoke

```
Bash(
  run_in_background=true,
  command="sagaflow launch deep-debug --arg symptom='<SYMPTOM>' --arg reproduction='<REPRO>' --arg num_hypotheses=<N> --await"
)
```

Substitute:
- `<SYMPTOM>` — one-line description of the failure.
- `<REPRO>` — the exact command to trigger it (e.g., `pytest tests/test_thing.py -v`). Pass empty string if unknown.
- `<N>` — 3–6. Default 4.

Tell the user: "Launched deep-debug on <symptom>. I'll surface the diagnosis + fix proposal when the workflow completes."

## Termination labels (exhaustive)

`Fixed — reproducing test now passes` · `Environmental — requires retry/monitoring, not fix` · `Architectural escalation required — 3 fix attempts failed across distinct hypotheses` · `Hypothesis space saturated — no plausible hypothesis survives judge` · `Cannot reproduce — investigation blocked` · `User-stopped at phase N` · `Hard stop at cycle N`

## Result surfacing

Report file at `~/.sagaflow/runs/<run_id>/debug-report.md`. Surface the termination label, leading hypothesis, and proposed fix (or escalation rationale) to the user.
