---
name: autopilot-temporal
description: Use when running full-lifecycle autonomous execution from a vague idea to working verified code via a durable Temporal-backed workflow that survives session crashes. Trigger phrases include "autopilot temporal", "sagaflow autopilot", "durable autopilot", "temporal-backed end-to-end build". Idea → battle-tested design → consensus plan → executed code → audited defects → three independent judge verdicts → honest completion report. Iron-law phase gates; no coordinator self-approval. Fire-and-forget for long-running builds.
user_invocable: true
argument: |
  Initial idea (one sentence is enough; the workflow will refine it).
  Example: /autopilot-temporal "cli tool that summarizes git log by author for the last N days"
---

# autopilot-temporal

Launches the `autopilot` workflow on sagaflow. Full-lifecycle autonomous pipeline — design, plan, execute, audit, judge — with iron-law phase gates and three independent judge verdicts before the report emits a completion verdict.

## How to invoke

```
Bash(
  run_in_background=true,
  command="sagaflow launch autopilot --arg idea='<IDEA>' --await"
)
```

Substitute `<IDEA>` with the initial concept. Quote strings with spaces.

Tell the user: "Launched autopilot on <idea>. This is a long-running workflow (design → plan → execute → audit → judge) — running in the background; I'll surface the judge verdicts + report when it completes."

## Termination labels

`Judges unanimous — complete` · `Judges split — complete with caveats` · `Judges rejected — execution failed audit` · `Design phase blocked — idea insufficient` · `Plan phase blocked — scope unclear` · `Execution phase hard-stop` · `User-stopped at phase N` · `Hard stop at phase N`

## Result surfacing

Report at `~/.sagaflow/runs/<run_id>/autopilot-report.md` with design doc, plan, per-stage artifacts, audit findings, three judge verdicts, and final termination label. Surface unanimous/split status + summary of what was built to the user.
