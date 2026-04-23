---
name: proposal-reviewer-temporal
description: Use when reviewing, critiquing, evaluating, or assessing a proposal, pitch, grant application, or business plan via a durable Temporal-backed workflow that survives session crashes. Trigger phrases include "proposal-reviewer temporal", "sagaflow proposal review", "durable proposal review", "temporal-backed proposal critique". Fact-checks claims, maps competitive landscape, identifies structural problems, produces an honest recommendation. Fire-and-forget while you do other work.
user_invocable: true
argument: |
  Path to the proposal file (absolute or workspace-relative). Minimum 200 words.
    --path <proposal.md>         the proposal file to review
  Example: /proposal-reviewer-temporal --path ./docs/grant-proposal.md
---

# proposal-reviewer-temporal

Launches the `proposal-reviewer` workflow on sagaflow. Critically reviews proposals for viability, competitive position, structural flaws. Fact-checks claims; surfaces honest recommendation (proceed/revise/kill).

## How to invoke

Resolve the user's proposal path to an absolute path, then fire a non-blocking bash task:

```
Bash(
  run_in_background=true,
  command="sagaflow launch proposal-reviewer --path '<ABS_PATH>' --await"
)
```

Where `<ABS_PATH>` is the absolute path to the proposal (convert relative paths using the current working directory). Minimum 200 words or the workflow rejects the input.

Tell the user: "Launched proposal-reviewer on <proposal>. Running in the background — I'll surface the verdict + key flaws when the workflow completes."

## Termination labels

`Recommend proceed` · `Recommend revise` · `Recommend kill` · `Audit compromised — verdict from critics only` · `User-stopped at round N`

## Result surfacing

Report at `~/.sagaflow/runs/<run_id>/review.md` with executive verdict, severity-rated flaw inventory, claim extraction, and final recommendation. The same directory contains per-critic `critic-N.txt` transcripts. Surface verdict + top 3 concerns to the user.
