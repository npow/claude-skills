---
name: hello-world-temporal
description: Use when the user wants to run the sagaflow framework smoke test — the minimum-viable skill that proves the Temporal-backed runtime is healthy end-to-end. Trigger phrases include "sagaflow smoke", "hello-world temporal", "test sagaflow", "check sagaflow works". Greets a named recipient and emits a DONE finding to ~/.sagaflow/INBOX.md via a Temporal workflow.
user_invocable: true
argument: |
  Name to greet. Optional; defaults to "world".
  Example: /hello-world-temporal alice
---

# hello-world-temporal

Launches the `hello-world` sagaflow workflow. Greets the named recipient via an Anthropic SDK call; writes a finding to `~/.sagaflow/INBOX.md`.

## How to invoke

Run a single non-blocking bash task that invokes `sagaflow launch`. The workflow survives session crashes — you can do other work while it runs.

```
Bash(
  run_in_background=true,
  command="sagaflow launch hello-world --name '<NAME>' --await"
)
```

Substitute `<NAME>` with the argument the user provided (default "world" if absent).

Then report to the user: "Launched hello-world sagaflow workflow for <NAME>. Running in the background on the sagaflow worker; I'll surface the result when it completes."

## What happens

1. sagaflow preflights Temporal (localhost:7233) + SessionStart hook.
2. Auto-spawns the worker daemon if none is polling.
3. Submits `HelloWorldWorkflow` to the `sagaflow` task queue with run id `hello-world-<YYYYMMDD-HHMMSS>`.
4. `--await` blocks until completion (seconds).
5. `~/.sagaflow/INBOX.md` gets a DONE entry; desktop notification fires; the background bash task completes.

## Result surfacing

When the background task completes Claude Code fires a `<task-notification>`; read `~/.sagaflow/INBOX.md` and surface the greeting + run_id to the user.

## Preflight diagnostics

If the user reports the workflow never completes, run `sagaflow doctor` to probe Temporal, transport, worker, and hook. The workflow is durable — if the worker crashed mid-run, a second `sagaflow launch` auto-spawns a fresh worker and Temporal resumes from the last completed activity.
