# Criteria-Poll-with-Hold-Window (Shared)

An **observational termination primitive**: a workflow finishes when a set of shell-command success criteria pass **continuously** for a hold window, then an anticheat gate confirms the pass wasn't gamed. Distinct from evidentiary termination (the primitive in [`prd-story-criteria-loop.md`](prd-story-criteria-loop.md)), which asks "did we produce the right artifacts on this iteration?"

**Used by:** `/swarm` mission workflows. Available to any durable workflow that wants observational termination.

**Origin:** implemented in both `swarmd.durable.workflow.MissionWorkflow` (standalone) and `sagaflow.missions.workflow.MissionWorkflow` (absorbed copy — sagaflow registers it alongside skill workflows). See [`ADR-001-single-substrate.md`](ADR-001-single-substrate.md) for the remaining decommission steps.

---

## Contract

A mission specifies N `success_criteria`, each with:
- `id` — snake_case identifier
- `description` — human-readable
- `check` — shell command, exit code 0 = pass
- `timeout_sec` — per-invocation timeout
- `idempotent` — bool; if false, the poll loop must respect `run_every_sec` even if criterion is cheap

And a `verification` block:
- `run_every_sec` — poll period (default 30s)
- `hold_window_sec` — required continuous-green duration before pass-transition gate (default 60s)
- `path_add` — PATH prefix additions for criterion shells
- `env_passthrough` — whitelisted env vars visible to criterion shells

---

## State machine

```
  CREATED → RUNNING → CRITERIA_GREEN → HOLDING → PASS_TRANSITION_GATE → COMPLETE
                                             ↘                       ↘
                                              RUNNING (criterion flipped)  → rejected, back to RUNNING
                                                                             (if anticheat rejects)

  any state → aborting (on user `swarm abort`) → aborted
```

Transitions:

- **RUNNING → CRITERIA_GREEN**: every criterion returned exit 0 on the most recent poll
- **CRITERIA_GREEN → HOLDING**: begin tracking hold timer at time of first full-green poll
- **HOLDING → RUNNING**: any criterion flipped to non-zero during the hold window → reset hold timer, back to RUNNING
- **HOLDING → PASS_TRANSITION_GATE**: criteria stayed green continuously for `hold_window_sec`
- **PASS_TRANSITION_GATE → COMPLETE**: anticheat critic panel approved (see [`anticheat-critic-panel.md`](anticheat-critic-panel.md))
- **PASS_TRANSITION_GATE → RUNNING**: anticheat rejected; findings surfaced, execution continues

---

## Failure modes and required handling

### 1. Flaky criterion
A criterion that passes sometimes and fails sometimes during the hold window blocks transition indefinitely.

**Handling:** track per-criterion `consecutive_pass_count` and `consecutive_fail_count`. If a criterion flips ≥ 3 times within one hold window, emit a `CRITERION_FLAKY` finding to `findings.jsonl` and switch that criterion to `flaky` state. The coordinator's next poll logs the flakiness; the workflow continues. It is the user's responsibility (via `swarm abort` or amending the mission) to decide. Never silently-auto-degrade (that's a rubber-stamp failure mode).

### 2. Unreachable criterion
A criterion's shell errors before returning an exit code (timeout, missing binary, PATH misconfiguration).

**Handling:** treat `timeout` or `execution_error` as non-pass (reset any hold timer). Emit a `CRITERION_UNREACHABLE` finding on every N-th consecutive unreachable poll (N=5 by default) so the user can diagnose.

### 3. Criterion reflects coordinator output (trivially-satisfiable)
A criterion like `test -f app.py` passes the moment an empty file exists. This is a criterion-rigor bug, not a runtime bug.

**Handling:** pre-flight linter (see the existing `lint_criteria.py` in swarm) runs BEFORE workflow launch. Runtime does not re-validate rigor — the linter is authoritative. Workflows accept user-overridden weak criteria if the `user-overridden weak criteria:` marker appears in the mission prose.

### 4. Criterion requires mutating state to pass
A mission whose criterion is "the database has 5 rows" can pass because a subagent wrote rows, OR because the subagent seeded them without running the code. The anticheat panel catches this — that's exactly what it's for. See `anticheat-critic-panel.md`.

---

## Inputs and outputs

**Input contract** (mission.yaml, validated by sagaflow's MissionInput schema):
```yaml
success_criteria:
  - id: string (snake_case)
    description: string
    check: string (shell command)
    timeout_sec: int (default 120)
    idempotent: bool (default true)
verification:
  run_every_sec: int (default 30)
  hold_window_sec: int (default 60)
  path_add: [string]
  env_passthrough: [string]
```

**Output contract** (state per-poll, written to `~/.sagaflow/state/<run_id>/criteria_history.jsonl`):
```jsonl
{"ts":"2026-04-23T12:00:00Z","poll_n":1,"criteria":[{"id":"pytest","exit":0,"duration_ms":1240},{"id":"no_todos","exit":0,"duration_ms":54}],"all_green":true}
{"ts":"2026-04-23T12:00:30Z","poll_n":2,"criteria":[{"id":"pytest","exit":1,"duration_ms":2030},{"id":"no_todos","exit":0,"duration_ms":48}],"all_green":false,"hold_reset_reason":"pytest flipped"}
```

**Findings emitted** (to `~/.sagaflow/state/<run_id>/findings.jsonl`):
- `CRITERIA_GREEN` when entering hold window
- `HOLD_WINDOW_MET` when hold completes
- `HOLD_WINDOW_BROKEN` when criterion flips mid-hold
- `CRITERION_FLAKY` per flake detection
- `CRITERION_UNREACHABLE` per persistent unreachable criterion
- `PASS_TRANSITION_APPROVED` / `PASS_TRANSITION_REJECTED` from anticheat

---

## When to choose this primitive

Use criteria-poll-with-hold-window when:
- The mission's "done" is observable from outside (shell commands can prove it)
- The algorithm is allowed to take arbitrarily long
- The user prefers an observational check over the workflow's self-assessment

Use PRD-story-criteria-loop (the other termination primitive) when:
- The algorithm has pre-defined user stories with acceptance criteria
- Evidence files (test outputs, verification command outputs) are the termination signal
- The workflow has an iteration budget (bounded, not open-ended)

Many skills benefit from **both**: the algorithm iterates on evidentiary PRD-story completion, and the final pass goes through criteria-poll-with-hold-window as a secondary observational gate. This is the ideal composition for high-stakes missions.

---

## Integration checklist

- [ ] Skill's `## Durable execution` section references this primitive
- [ ] Mission YAML schema enforces `success_criteria` + `verification` fields
- [ ] Pre-flight linter runs before workflow launch
- [ ] `criteria_history.jsonl` is written per-poll for postmortem
- [ ] `findings.jsonl` events match the vocabulary above
- [ ] Hold-window reset logic is symmetric (any non-pass resets, including timeouts and errors)
- [ ] Flakiness detection emits `CRITERION_FLAKY` without auto-degrading the criterion
- [ ] Pass-transition invokes anticheat per `anticheat-critic-panel.md` before marking complete
