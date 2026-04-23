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

# deep-qa-temporal

Launches the `deep-qa` workflow on sagaflow. Multi-round parallel critics + two-pass independent severity judges + rationalization auditor. Emits a qa-report.md to `~/.sagaflow/runs/<run_id>/`.

## How to invoke

Resolve the user's artifact path to an absolute path, then fire a non-blocking bash task:

```
Bash(
  run_in_background=true,
  command="sagaflow launch deep-qa --path '<ABS_PATH>' --arg type=<TYPE> --arg max_rounds=<N> --await"
)
```

Where:
- `<ABS_PATH>` is the absolute path to the artifact (if user gave a relative path, convert it using the current working directory).
- `<TYPE>` is one of `doc` / `code` / `research` / `skill`. Default to `doc` if the user didn't say.
- `<N>` is the max rounds (default 3).

Tell the user: "Launched deep-qa on <artifact>. It's running on the sagaflow worker in the background — you can do other work. I'll surface findings when the workflow completes."

## What happens

1. Artifact snapshot to `~/.sagaflow/runs/<run_id>/artifact.txt`.
2. Dimension discovery (Sonnet) produces QA angles.
3. Up to `max_rounds` × up to 6 parallel Haiku critics per round.
4. Two-pass severity judges (pass-1 blind + pass-2 informed; pass-2 is authoritative).
5. Rationalization auditor (max 2 attempts; compromised twice → report assembled from verdicts only).
6. For `--type research`: fact verifier (claude -p + WebFetch).
7. Synthesis → qa-report.md.
8. INBOX entry + desktop notification.

## Result surfacing

When the background task completes: read `~/.sagaflow/runs/<run_id>/qa-report.md` and post the key findings (critical/major/minor counts, top 3 defects, termination label) to the user. Full report path appears in the background task's stdout.

## Termination labels (exhaustive)

`Conditions Met` · `Coverage plateau — frontier saturated` · `Max Rounds Reached — user stopped` · `Max Rounds Reached` · `User-stopped at round N` · `Convergence — frontier exhausted before full coverage` · `Hard stop at round N` · `Audit compromised — report re-assembled from verdicts only`

Never "no defects remain" — if every angle came back clean, termination is `Conditions Met` and the report says so honestly.
