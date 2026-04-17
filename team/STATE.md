# State Management

Pure file-based state. No MCP state tools. All persistence lives in `team-{run_id}/` in the current working directory.

## State File: `team-{run_id}/state.json`

```json
{
  "run_id": "20260416-153022",
  "skill": "team",
  "created_at": "2026-04-16T15:30:22Z",
  "task_text": "<verbatim task text as invoked>",
  "task_text_sha256": "<sha256 hex of task_text>",
  "generation": 0,
  "invocation": {
    "n_workers_requested": null,
    "n_workers_actual": null,
    "agent_type_override": null,
    "cli_args": "<original slash-command args>"
  },
  "integrations": {
    "deep_design_available": true,
    "deep_qa_available": true,
    "degraded_mode_active": false,
    "degraded_mode_reasons": []
  },
  "budget": {
    "fix_budget_max_iterations": 3,
    "fix_budget_current_iteration": 0,
    "prd_revision_cap": 2,
    "prd_revision_current": 0,
    "token_spent_estimate_usd": 0.0
  },
  "current_stage": "team-plan",
  "stages": [
    {
      "name": "team-plan",
      "status": "not_started",
      "started_at": null,
      "completed_at": null,
      "evidence_files": [],
      "agent_spawns": [],
      "exit_gate_checked_at": null,
      "exit_gate_verdict": null
    },
    {
      "name": "team-prd",
      "status": "not_started",
      "started_at": null,
      "completed_at": null,
      "evidence_files": [],
      "agent_spawns": [],
      "exit_gate_checked_at": null,
      "exit_gate_verdict": null
    },
    {
      "name": "team-exec",
      "status": "not_started",
      "started_at": null,
      "completed_at": null,
      "evidence_files": [],
      "agent_spawns": [],
      "workers": {},
      "team_name": null,
      "task_ids": [],
      "exit_gate_checked_at": null,
      "exit_gate_verdict": null
    },
    {
      "name": "team-verify",
      "status": "not_started",
      "started_at": null,
      "completed_at": null,
      "evidence_files": [],
      "agent_spawns": [],
      "iteration": 0,
      "verdict": null,
      "exit_gate_checked_at": null,
      "exit_gate_verdict": null
    },
    {
      "name": "team-fix",
      "status": "not_started",
      "started_at": null,
      "completed_at": null,
      "evidence_files": [],
      "agent_spawns": [],
      "iterations": [],
      "defects": {},
      "exit_gate_checked_at": null,
      "exit_gate_verdict": null
    }
  ],
  "prd": {
    "final_path": null,
    "ac_ids": [],
    "revision_count": 0
  },
  "invariants": {
    "coordinator_never_evaluated": true,
    "all_evidence_fresh_this_session": true,
    "two_stage_review_enforced": true,
    "every_worker_received_tdd_preamble": true
  },
  "handoffs": {
    "plan": null,
    "prd": null,
    "exec": null,
    "verify": null,
    "fix": null
  },
  "termination": null,
  "cancel_time_iso": null,
  "resume_from_stage": null
}
```

## Enums

### Stage status
- `not_started` — stage hasn't begun.
- `in_progress` — agents spawned or exit-gate not yet checked.
- `gate_checking` — all agents returned, exit-gate evaluation in progress.
- `complete` — exit-gate passed, handoff written.
- `failed_rework` — exit-gate rejected; retry loop under cap.
- `failed_terminal` — exit-gate rejected, no rework path; triggers run termination.
- `cancelled` — user cancelled mid-stage.

### Worker status (inside `stages[team-exec].workers[worker_name]`)
```json
{
  "worker_name": "worker-1",
  "agent_id": "worker-1@team-{run_id}-exec",
  "agent_type": "executor",
  "model_tier": "sonnet",
  "spawn_time_iso": "<ISO or null>",
  "status": "not_spawned|spawned|working|task_complete_pending_review|task_complete_approved|task_complete_rejected|spawn_failed|shutdown_confirmed|shutdown_timeout",
  "assigned_task_ids": [],
  "completion_time_iso": null,
  "evidence_files": [],
  "failure_reason": null
}
```

### Agent spawn record (used in every stage's `agent_spawns[]`)
```json
{
  "agent_role": "planner|analyst|critic|falsifiability_judge|plan_validator|code_reviewer|verify_judge|per_fix_verifier|deep_qa|deep_design|worker",
  "agent_id": "<if assigned>",
  "model_tier": "haiku|sonnet|opus",
  "spawn_time_iso": "<ISO>",
  "completion_time_iso": "<ISO or null>",
  "input_files": ["<path>", "<path>"],
  "output_file": "<path>",
  "status": "spawned|completed|spawn_failed|timed_out|unparseable_output",
  "structured_output_markers_present": true
}
```

## Generation Counter

Optimistic-concurrency version counter. Every write of `state.json` increments `generation`. On read:
1. Parse JSON.
2. Compare `generation` against the value from the last read in the same coordinator turn. Must be strictly greater.
3. If not: a concurrent write happened → re-read and retry the intended update.

## Lock File

On run start: write `team-{run_id}.lock` in CWD with coordinator timestamp + PID. On clean exit: delete it. On startup: if a lock file from the same `run_id` exists < 15 min old, surface: `Another team run appears active. Resume (r) / abort (a) / force (f)?` — require explicit user response. No silent takeover.

## Pre-Transition Gate (Iron Law)

Before advancing `current_stage` from X to Y:

```
Step 1. Read state.json; confirm stages[X].status in {"gate_checking"}.
Step 2. Confirm stages[X].evidence_files is a non-empty list.
Step 3. For every path p in stages[X].evidence_files:
          - Confirm p exists on disk (os.stat) and is non-empty.
          - If p is a structured-output file, confirm it contains
            STRUCTURED_OUTPUT_START and STRUCTURED_OUTPUT_END markers.
Step 4. Confirm stages[X].exit_gate_verdict == "approved".
Step 5. Confirm stages[X].exit_gate_verdict was written by an independent
          agent (agent_role != "coordinator"); read the linked verdict file.
Step 6. Only if 1-5 all pass: set stages[X].status = "complete",
          set current_stage = Y, stages[Y].status = "in_progress",
          stages[Y].started_at = <ISO>, generation += 1, write state.json.
```

Any failing check: do NOT advance; log to `logs/gate_decisions.jsonl` with `{verdict: rejected, reason}`. Fire a rework loop if the stage supports it (team-plan: re-spawn planner with validator rejection; team-prd: re-spawn analyst with critic + falsifiability issues; team-verify: loop to team-fix). Stages without rework paths terminate with `blocked_unresolved`.

## Worker Registry

Lives at `state.stages[team-exec].workers`. Each entry updated by the lead (never by the worker itself). Worker self-reports via `SendMessage`; the lead translates messages into registry updates:

| Event | Registry update |
|---|---|
| Before `Task` spawn | `status: "not_spawned" → "spawned"`, `spawn_time_iso: <ISO>` |
| `Task` returned spawn error | `status: "spawn_failed"`, `failure_reason: <error>` |
| Worker `SendMessage` "task #X complete" | `status: "task_complete_pending_review"`, evidence_files populated |
| Per-worker two-stage review `VERDICT: passed` | `status: "task_complete_approved"` |
| Per-worker two-stage review `VERDICT: failed_*` | `status: "task_complete_rejected"`, worker re-sent to work via SendMessage |
| Worker `shutdown_response` approve=true | `status: "shutdown_confirmed"`, `completion_time_iso: <ISO>` |
| Shutdown 30s timeout (2x) | `status: "shutdown_timeout"` |

## Handoff File Registry

Lives at `state.handoffs`. One path per stage after its handoff is written. Plain strings (not objects):

```json
"handoffs": {
  "plan": "team-{run_id}/handoffs/plan.md",
  "prd": "team-{run_id}/handoffs/prd.md",
  "exec": "team-{run_id}/handoffs/exec.md",
  "verify": "team-{run_id}/handoffs/verify.md",
  "fix": null
}
```

A handoff path entry is written only after the handoff file exists on disk with valid structured markers. Setting a handoff path without the file present is an invariant violation.

## Resume Protocol

On re-invocation in the same CWD:

1. Check for `team-*.lock` files; if one matches an existing `team-{run_id}/` directory, prompt: `Resume run {run_id} from stage {current_stage}? [y/N]`
2. If user confirms:
   - Read `state.json`.
   - Verify `task_text_sha256` matches stored `task_text` (tamper check).
   - Set `resume_from_stage = current_stage`.
   - Check `stages[current_stage].status`:
     - `not_started` → begin stage from Step N in SKILL.md.
     - `in_progress` → for each agent in `agent_spawns` with `status: spawned` and no completion time:
       - Check if output file exists on disk:
         - Exists + has structured markers → mark `completed`, re-run any downstream coordinator work (parsing, dedup).
         - Missing → mark `timed_out` (do NOT re-spawn — agents are one-shot; spawn a fresh replacement if the stage requires it).
     - `gate_checking` → re-run pre-transition gate from Step 1.
     - `failed_rework` → continue rework loop from where it left off.
   - For `team-exec`: re-read `TaskList` for the persisted `team_name`; reconcile worker registry with live `config.json` members (missing workers → `spawn_failed` or `shutdown_timeout` depending on `spawn_time_iso`).
3. If user declines: offer `rm -rf team-{run_id}/` (explicit, not default) or start a new run with a fresh `run_id`.

## State Invariants (Checked At Every Read)

1. `generation` strictly monotonic across writes in the same session.
2. `task_text_sha256` matches SHA256 of `task_text`. Mismatch → halt with `TASK_TAMPERED`.
3. `stages[]` has exactly 5 entries in order: plan, prd, exec, verify, fix.
4. `current_stage` matches the only stage with `status: "in_progress"` (unless `termination` is set).
5. Every `handoffs[<stage>]` non-null path exists on disk.
6. Every `stages[<stage>].evidence_files` path exists on disk and is non-empty.
7. `invariants.coordinator_never_evaluated`: every verdict file has `written_by != "coordinator"` in its metadata.
8. `invariants.two_stage_review_enforced`: in `team-exec` and `team-verify`, for every reviewed diff, there are TWO independent verdict files (spec-compliance + code-quality) with distinct `agent_id` and distinct `spawn_time_iso`.
9. `termination` is either null or one of the five enum values.

Any invariant violation: log to `logs/gate_decisions.jsonl` with `event: invariant_violation`; halt run pending operator input; surface a human-readable summary.

## State Updates — Reference Patterns

### Before spawning any agent

```json
"stages[<idx>].agent_spawns": [
  ...existing,
  {
    "agent_role": "planner",
    "spawn_time_iso": "<ISO>",
    "input_files": ["handoffs/plan-input.md"],
    "output_file": "handoffs/plan.md",
    "status": "spawned",
    "structured_output_markers_present": false
  }
],
"generation": += 1
```
Then call `Task` / `Agent` / `TeamCreate`. If the call errors: update the just-added record to `status: "spawn_failed"`, `spawn_time_iso: null`, `failure_reason: <error>`.

### After agent completes

```json
"stages[<idx>].agent_spawns[<i>].completion_time_iso": "<ISO>",
"stages[<idx>].agent_spawns[<i>].status": "completed",
"stages[<idx>].agent_spawns[<i>].structured_output_markers_present": true,
"generation": += 1
```

### On stage exit gate approved

```json
"stages[<idx>].exit_gate_checked_at": "<ISO>",
"stages[<idx>].exit_gate_verdict": "approved",
"stages[<idx>].evidence_files": ["...", "..."],
"stages[<idx>].status": "complete",
"stages[<idx>].completed_at": "<ISO>",
"current_stage": "<next_stage_name>",
"stages[<next_idx>].status": "in_progress",
"stages[<next_idx>].started_at": "<ISO>",
"generation": += 1
```

### On termination

```json
"termination": "complete|partial_with_accepted_unfixed|blocked_unresolved|budget_exhausted|cancelled",
"stages[<current_idx>].status": "complete" | "cancelled" | "failed_terminal",
"current_stage": null,
"generation": += 1
```

## State Never Written By Workers

Workers communicate via `SendMessage` to the lead. The lead translates messages into state writes. This keeps the state-write authority in one process and avoids lock races on `state.json`. Worker output files (TDD evidence, diffs) ARE written by workers to disk — but the lead reads them before registering them in `state.stages[].evidence_files`.
