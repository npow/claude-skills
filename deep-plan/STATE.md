# State Management

State is fully file-based. The coordinator is the only writer of `state.json`. Agents read it for reference but never mutate it. Every write increments `generation` for optimistic concurrency; resume relies on on-disk state, never in-memory reconstruction.

## State File: `deep-plan-{run_id}/state.json`

```json
{
  "run_id": "20260416-153022",
  "skill": "deep-plan",
  "generation": 0,
  "created_at": "2026-04-16T15:30:22Z",
  "task_file": "deep-plan-{run_id}/task.md",
  "task_sha256": "sha256-hex-of-task-text",
  "mode": "short | deliberate",
  "flags": {
    "interactive": false,
    "deliberate": false,
    "architect_provider": "claude | codex",
    "critic_provider": "claude | codex | gemini",
    "max_iterations": 5
  },
  "status": "planner_pending | planner_in_progress | planner_complete | architect_pending | architect_in_progress | architect_complete | critic_pending | critic_in_progress | critic_complete | feedback_pending | adr_pending | adr_in_progress | complete | aborted",
  "current_iteration": 0,
  "iterations": {
    "1": {
      "status": "in_progress | complete | failed",
      "planner": {
        "status": "pending | in_progress | complete | spawn_failed | unparseable | timed_out",
        "spawn_time_iso": "2026-04-16T15:31:05Z",
        "completion_time_iso": null,
        "plan_path": "deep-plan-{run_id}/iterations/iter-1/plan.md",
        "structured_output_parsed": false,
        "acceptance_criteria_ids": [],
        "principle_ids": [],
        "driver_ids": [],
        "option_ids": [],
        "chosen_option_id": null,
        "premortem_ids": [],
        "failure_reason": null
      },
      "architect": {
        "status": "pending | in_progress | complete | spawn_failed | unparseable | timed_out",
        "spawn_time_iso": null,
        "completion_time_iso": null,
        "verdict_path": "deep-plan-{run_id}/iterations/iter-1/architect-verdict.md",
        "architect_mode": "claude | codex | degraded",
        "verdict": null,
        "concerns": [],
        "tradeoffs": [],
        "synthesis_present": false,
        "principle_violations": [],
        "structured_output_parsed": false,
        "failure_reason": null
      },
      "critic": {
        "status": "pending | in_progress | complete | spawn_failed | unparseable | timed_out | blocked_architect_not_complete",
        "spawn_time_iso": null,
        "completion_time_iso": null,
        "verdict_path": "deep-plan-{run_id}/iterations/iter-1/critic-verdict.md",
        "critic_mode": "claude | codex | gemini | degraded",
        "verdict": null,
        "verdict_promoted": false,
        "verdict_promotion_reason": null,
        "rejections_total": 0,
        "rejections_surviving": 0,
        "rejections_dropped": 0,
        "dropped_rejection_ids": [],
        "dropped_rejections_path": null,
        "approval_evidence": [],
        "structured_output_parsed": false,
        "failure_reason": null
      },
      "feedback_bundle_path": null
    }
  },
  "agent_verdict_registry": {
    "planner": {
      "total_spawns": 0,
      "spawn_failures": 0,
      "unparseable_count": 0
    },
    "architect": {
      "total_spawns": 0,
      "spawn_failures": 0,
      "unparseable_count": 0,
      "verdict_counts": {"ARCHITECT_OK": 0, "ARCHITECT_CONCERNS": 0},
      "degraded_mode_count": 0
    },
    "critic": {
      "total_spawns": 0,
      "spawn_failures": 0,
      "unparseable_count": 0,
      "verdict_counts": {"APPROVE": 0, "ITERATE": 0, "REJECT": 0, "APPROVE_AFTER_RUBBER_STAMP_FILTER": 0},
      "degraded_mode_count": 0,
      "total_rejections_filed": 0,
      "total_rejections_dropped": 0
    },
    "adr_scribe": {
      "total_spawns": 0,
      "spawn_failures": 0
    }
  },
  "termination": {
    "label": null,
    "iteration_at_termination": null,
    "ts": null,
    "reason_detail": null
  },
  "final_plan_path": null,
  "adr_path": null,
  "invariants": {
    "coordinator_never_evaluated": true,
    "architect_always_before_critic": true,
    "state_written_before_spawn": true
  }
}
```

## Iteration Status Enum

Per-iteration status lifecycle (monotonic — never regresses):

| Status | Meaning | Allowed next transitions |
|---|---|---|
| `pending` | iteration slot created, planner not yet spawned | `in_progress` |
| `in_progress` | any of planner/architect/critic running | `complete`, `failed` |
| `complete` | all three agents done, verdict recorded (APPROVE or ITERATE/REJECT with feedback bundle) | terminal for this iteration; next iteration starts fresh |
| `failed` | iteration unrecoverable (e.g., planner unparseable twice) | terminal; termination label written |

Per-agent status enum (`planner.status`, `architect.status`, `critic.status`):

| Status | Meaning |
|---|---|
| `pending` | not yet spawned |
| `in_progress` | `spawn_time_iso` set, awaiting output |
| `complete` | output file exists AND structured block parsed |
| `spawn_failed` | Agent tool returned error; `spawn_time_iso` reverted to null; retried on resume |
| `unparseable` | output file exists but STRUCTURED_OUTPUT block missing or malformed |
| `timed_out` | output file missing after deadline; not retried |
| `blocked_architect_not_complete` | critic-only; set if coordinator attempts to spawn Critic before Architect is complete (should never occur; indicates bug) |

## Termination Labels

Authoritative set. No other label may appear in `termination.label`:

| Label | Trigger |
|---|---|
| `consensus_reached_at_iter_N` | Critic verdict in iter-N was `APPROVE` (including promoted `APPROVE_AFTER_RUBBER_STAMP_FILTER`) |
| `max_iter_no_consensus` | N == max_iterations and verdict still `ITERATE`/`REJECT` |
| `user_stopped` | User said stop/cancel at interactive gate before final approval |
| `user_rejected` | User chose "reject" at interactive approval gate |
| `planner_unparseable_at_iter_N` | Planner produced unparseable output twice in iter-N |
| `architect_unparseable_at_iter_N` | Architect produced unparseable output twice in iter-N |
| `critic_unparseable_at_iter_N` | Critic produced unparseable output twice in iter-N |
| `planner_spawn_failed_at_iter_N_after_retries` | Planner spawn failed after all retry attempts |
| `architect_spawn_failed_at_iter_N_after_retries` | Same for architect |
| `critic_spawn_failed_at_iter_N_after_retries` | Same for critic |
| `adr_scribe_failed` | Terminal agent spawn failed; last-iteration plan still output but ADR missing (flagged in summary) |
| `aborted_by_error` | Unrecoverable state corruption or invariant violation |

Label is written into `state.json.termination.label` AND the final plan header. Coordinator NEVER writes `approved`, `done`, or other vocabulary.

## Generation Counter

Optimistic concurrency:

1. Read `state.json`; capture current `generation`.
2. Apply in-memory mutation.
3. Write back with `generation += 1`.
4. Re-read; if new generation != expected, a concurrent writer existed → log `generation_conflict_detected` and retry the full read-mutate-write cycle.

Since `deep-plan` is single-coordinator per run, concurrency conflicts should not occur; the counter is a correctness check, not primary synchronization.

## Lock File

On startup: write `deep-plan-{run_id}.lock` with process timestamp. If a lock file <15 minutes old exists with a different process id, print:

```
Another deep-plan session appears active on this run_id. Continue anyway? [y/N]
```

On clean exit: delete lock file. On unclean exit: stale lock is overwritten after 15 minutes.

## State Write Invariants

After every state write, verify:

1. `state.json` is valid JSON.
2. `generation` strictly monotonically increased from the pre-write value.
3. `task_sha256` matches SHA256 of task.md content (halt with `aborted_by_error` if tampered).
4. `current_iteration <= flags.max_iterations`.
5. For every iteration I: `iterations[I].architect.status != "in_progress"` OR `iterations[I].critic.status == "pending"`. Put plainly: Critic never spawned before Architect is complete.
6. For every iteration I with `status == "complete"`: `iterations[I].planner.status == "complete"` AND `iterations[I].architect.status == "complete"` AND `iterations[I].critic.status in {"complete"}`.
7. No agent has both `spawn_time_iso` set AND `status == "spawn_failed"` — spawn_failed reverts `spawn_time_iso` to null.
8. `termination.label`, if non-null, belongs to the authoritative label set above.

Violations halt the run with `aborted_by_error` and write the violation detail to `logs/decisions.jsonl`.

## State-Write-Before-Spawn Protocol

For every agent spawn (Planner, Architect, Critic, ADR Scribe):

1. Pre-spawn state write:
   ```json
   "iterations.{N}.{role}.status": "in_progress",
   "iterations.{N}.{role}.spawn_time_iso": "<ISO timestamp>",
   "generation": += 1
   ```
2. Call `Task(subagent_type="general-purpose", ...)` or external CLI.
3. On successful return: state write marks `complete` + `completion_time_iso` + parsed structured fields.
4. On spawn error (Agent tool error, tool limit, etc.):
   ```json
   "iterations.{N}.{role}.status": "spawn_failed",
   "iterations.{N}.{role}.spawn_time_iso": null,
   "iterations.{N}.{role}.failure_reason": "<error message>",
   "generation": += 1
   ```
   Resume retries spawn (does NOT wait for a ghost output).

## Resume Protocol

On any invocation whose CWD contains a `deep-plan-{run_id}/` directory with a `state.json`:

1. Read `state.json`. Validate invariants. If invariant 3 fails (task_sha256 mismatch), halt with `aborted_by_error`.
2. Determine replay point via `status` field:
   - `planner_pending` / `planner_in_progress`: go to SKILL.md Step 1 at current_iteration. If `planner.status == "in_progress"`, check for existence of `plan.md`:
     - Exists + parseable → mark `complete`, advance to Step 3.
     - Exists + unparseable → mark `unparseable`, re-spawn Planner once.
     - Missing → mark `timed_out`; treat as unparseable → re-spawn once.
   - `planner_complete` / `architect_pending` / `architect_in_progress`: go to Step 3 at current_iteration. Same existence check for architect-verdict.md.
   - `architect_complete` / `critic_pending` / `critic_in_progress`: go to Step 4 at current_iteration. Same existence check for critic-verdict.md.
   - `critic_complete`: go to Step 5 (re-evaluate verdict) at current_iteration.
   - `feedback_pending`: re-assemble `feedback-bundle.md` and go to Step 1 at current_iteration + 1.
   - `adr_pending`: go to Step 6 (ADR Scribe).
   - `complete`: print final summary; no further work.
   - `aborted`: print termination + invariant violation; exit.
3. For any per-agent status == `spawn_failed`: retry spawn. Increment retry count in `agent_verdict_registry.{role}.spawn_failures`. If retry count ≥ 3 for any role in the same iteration: write `{role}_spawn_failed_at_iter_N_after_retries` and go to Step 6 (ADR Scribe on the last parseable plan if any; otherwise skip ADR).
4. Never wait on a ghost output. If `status == "in_progress"` with no output file and no matching running process, treat as `timed_out` and re-spawn once.

## Agent Verdict Registry

The registry tracks cumulative agent behavior across iterations for this run. Purpose: detect rubber-stamping and abnormal spawn failure rates.

**Warnings surfaced to final summary when:**
- `architect.verdict_counts.ARCHITECT_OK / total_spawns > 0.9` → "Architect rubber-stamp suspected"
- `critic.verdict_counts.APPROVE / total_spawns > 0.9 AND total_spawns > 1` → "Critic rubber-stamp suspected"
- `critic.total_rejections_dropped / critic.total_rejections_filed > 0.5 AND total_rejections_filed > 5` → "Critic rejection quality low — many dropped by falsifiability gate"
- any role's `spawn_failures > 2` → "Agent spawn instability"
- any role's `degraded_mode_count > 0` → "External provider unavailable — some passes ran in degraded mode"

These are informational warnings written to the final plan header, not hard failures.

## State File Example After Iteration 1 APPROVE

```json
{
  "run_id": "20260416-153022",
  "skill": "deep-plan",
  "generation": 12,
  "status": "complete",
  "current_iteration": 1,
  "iterations": {
    "1": {
      "status": "complete",
      "planner": {"status": "complete", "structured_output_parsed": true, "acceptance_criteria_ids": ["AC-001", "AC-002", "AC-003"], ...},
      "architect": {"status": "complete", "verdict": "ARCHITECT_CONCERNS", "concerns": [{"id": "C-1", "severity": "minor"}], ...},
      "critic": {"status": "complete", "verdict": "APPROVE", "rejections_total": 0, "rejections_surviving": 0, ...}
    }
  },
  "termination": {
    "label": "consensus_reached_at_iter_1",
    "iteration_at_termination": 1,
    "ts": "2026-04-16T15:42:11Z"
  },
  "final_plan_path": "deep-plan-20260416-153022/plan.md",
  "adr_path": "deep-plan-20260416-153022/adr.md"
}
```
