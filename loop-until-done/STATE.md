# State Management

## State File: `loop-{run_id}/state.json`

Authoritative run state. Written before every agent spawn; `generation` incremented on every write.

```json
{
  "run_id": "20260416-153022",
  "skill": "loop-until-done",
  "generation": 42,
  "created_at": "2026-04-16T15:30:22Z",
  "last_write_at": "2026-04-16T16:32:10Z",
  "task": "Original task description",
  "config": {
    "no_prd": false,
    "no_deslop": false,
    "critic": "architect",
    "max_iterations": 25,
    "resume_of": null
  },
  "prd_locked": true,
  "prd_sha256": "sha256-hex-of-canonicalized-stories-array",
  "prd_lock_iteration": 1,
  "budget": {
    "max_iterations": 25,
    "current_iteration": 9,
    "iteration_started_at": "2026-04-16T16:28:00Z",
    "iterations_per_story": {
      "US-001": 2,
      "US-002": 1,
      "US-003": 3,
      "US-004": 0,
      "US-005": 1
    }
  },
  "current_phase": "deslop_regression | story_implement | story_verify | reviewer_gate | complete | blocked",
  "current_story_id": "US-003",
  "verification_mode": "basic | deep-qa",
  "deslop_mode": "standard | skipped_no_deslop | skipped_unavailable",
  "reviewer_rejection_count": 1,
  "reviewer_approval_rate": {
    "total_reviews": 2,
    "approved": 1,
    "rejected": 1,
    "warning_threshold_approaching_rubber_stamp": false
  },
  "invariants": {
    "coordinator_never_evaluated": true,
    "every_passes_true_has_fresh_evidence": true,
    "both_reviewer_files_structured": true,
    "prd_locked_criteria_not_mutated": true
  },
  "spawns": {
    "falsifiability_judge_iter1_attempt1": {
      "spawn_time_iso": "2026-04-16T15:30:48Z",
      "status": "complete | spawn_failed | timed_out | in_progress",
      "output_file": "judge/falsifiability-2026-04-16T15-30-48Z.md",
      "failure_reason": null
    },
    "executor_US-001_iter2": {
      "spawn_time_iso": "2026-04-16T15:32:30Z",
      "status": "complete",
      "output_file": null,
      "tier": "sonnet"
    },
    "reviewer_spec_compliance_iter8": {
      "spawn_time_iso": "2026-04-16T16:12:00Z",
      "status": "complete",
      "output_file": "reviews/spec-compliance-8.md",
      "critic": "architect"
    },
    "reviewer_code_quality_iter8": {
      "spawn_time_iso": "2026-04-16T16:12:02Z",
      "status": "complete",
      "output_file": "reviews/code-quality-8.md",
      "critic": "architect"
    }
  },
  "termination": null,
  "termination_at": null,
  "termination_evidence": null
}
```

## Story Status Enum

Stored in `prd.json.stories[].status`, not in `state.json` — but mirrored here for reference.

| Value | Meaning | Transitions allowed |
|---|---|---|
| `pending` | Not yet selected for an iteration | → `in_progress` |
| `in_progress` | Currently being worked on | → `passed` (when iron-law passes), `pending` (when reviewer rejects a passed story), `blocked` |
| `passed` | Every criterion `passes: true` with fresh evidence | → `in_progress` (reviewer rejection re-queues it), `passed` (idempotent) |
| `blocked` | `STORY_INFEASIBLE` note filed OR ≥ 3 consecutive failing iterations | Terminal for the run; triggers `blocked_on_story_{id}` label |

## Generation Counter (optimistic concurrency)

- Before any write: read current generation from state file
- Increment generation in the write
- After writing, re-read and verify generation is N+1
- If generation is not N+1: a concurrent write occurred → log conflict, retry with fresh read
- Strictly monotonically increasing — any decrease is a corruption signal

## Iteration Budget Tracking

`budget.current_iteration` is incremented once at Step 3 when a new story iteration starts (NOT on every substep).

- `budget.max_iterations` defaults to 25; overridden by `--budget=N` in config
- `budget.iteration_started_at` is the ISO timestamp at the moment Step 3 incremented `current_iteration` — this is the reference for the iron-law fresh-evidence check (`last_verified_at > iteration_started_at`)
- `budget.iterations_per_story[story_id]` tracks how many times a story has been the focus; ≥ 3 without `passed` triggers the blocked path
- Step 3 checks `current_iteration > max_iterations` BEFORE incrementing; if true, abort with label `budget_exhausted` and do not start the iteration

Reviewer rejections do NOT cost a story iteration — they cost a reviewer rejection slot (`reviewer_rejection_count`). But the subsequent fix-and-re-verify cycle does increment `current_iteration` when it re-enters Step 3.

## Resume Protocol (invoked via `--resume=<run_id>`)

Each skill's STATE.md must document how to replay from the last completed stage. Here it is:

1. Read `loop-{run_id}/state.json`
2. Verify `prd_sha256` matches SHA256 of canonicalized `stories` array in `prd.json`. If mismatch: halt with label `prd_tampered_since_lock` (a diagnostic subcase); do not resume.
3. Re-read `progress.jsonl` and compute the last known state:
   - `last_iteration` = max `iteration` across all events
   - `last_completed_story` = last `story_passed` event's `story_id`
   - `last_event` = last line's `event`
4. Reconcile `spawns` with output files:
   - For each entry with `status: "in_progress"`:
     - If output file exists and contains `STRUCTURED_OUTPUT_START`/`END` markers → mark `status: "complete"`, process normally
     - If output file exists but malformed → mark `status: "timed_out"`, file a diagnostic note, move on
     - If output file missing → mark `status: "timed_out"` (spawn never produced); do NOT re-spawn silently
   - For each entry with `status: "spawn_failed"`:
     - Retry spawn on resume (spawn_failed = call was refused, not produced)
5. Route to the appropriate step based on `current_phase`:
   - `prd_draft` → restart from Step 2a (PRD is not yet locked)
   - `prd_falsifiability` → re-spawn judge if its output is missing; otherwise read verdict and proceed
   - `story_implement` → re-read the current story's criteria and verify any that were not completed; execute Step 5 on the current story
   - `story_verify` → continue Step 5 from the next unverified criterion
   - `reviewer_gate` → re-spawn any missing reviewer pass; read existing verdicts
   - `deslop_regression` → re-run post-deslop verification
   - `complete` or `blocked` → resume is a no-op; print the stored termination label
6. Print: `Resumed loop-until-done: {run_id} at iteration {current_iteration} phase {current_phase}`

Resume does NOT:
- Re-run the falsifiability judge on already-locked criteria (PRD is immutable post-lock)
- Re-run `verification_command` for criteria that were `passes: true` with `last_verified_at > iteration_started_at` of the CURRENT iteration (if resuming mid-iteration, already-fresh evidence counts)
- Re-run the deslop pass if post-deslop regression already passed

Resume DOES:
- Retry any `spawn_failed` agents
- Re-spawn any `in_progress` agent whose output is missing or malformed
- Re-verify criteria whose `last_verified_at` is stale (< `iteration_started_at`)

## State Updates

### Before spawning each agent (CRITICAL: state written BEFORE Agent tool call)

```json
"spawns.{spawn_id}": {
  "spawn_time_iso": "<ISO timestamp>",
  "status": "in_progress",
  "output_file": "<expected output file path>",
  "failure_reason": null
},
"generation": += 1
```

### If Agent tool returns a spawn error

```json
"spawns.{spawn_id}.status": "spawn_failed",
"spawns.{spawn_id}.spawn_time_iso": null,
"spawns.{spawn_id}.failure_reason": "<error message>",
"generation": += 1
```

Resume behavior: retry spawn (different from `timed_out` → do not retry, leave as diagnostic).

### After agent completes successfully

```json
"spawns.{spawn_id}.status": "complete",
"spawns.{spawn_id}.output_file": "<actual output file path>",
"generation": += 1
```

### After iteration start (Step 3)

```json
"budget.current_iteration": += 1,
"budget.iteration_started_at": "<ISO>",
"budget.iterations_per_story.{story_id}": += 1,
"current_story_id": "<story_id>",
"current_phase": "story_implement",
"generation": += 1
```

### After criterion verification (Step 5, per criterion)

Writes to `prd.json`, not `state.json` directly — but mirrored in `progress.jsonl`:

```json
// in prd.json
"stories[i].acceptance_criteria[j].passes": true | false,
"stories[i].acceptance_criteria[j].last_verified_at": "<ISO>"
```

### After story passes (Step 6)

```json
// in prd.json
"stories[i].status": "passed",
"stories[i].last_modified_iteration": <current_iteration>,
"stories[i].files_modified": [<list from executor>]

// in state.json
"current_story_id": null,
"current_phase": "story_implement",
"generation": += 1
```

### After reviewer verdicts (Step 7c)

```json
"reviewer_approval_rate.total_reviews": += 1,
"reviewer_approval_rate.approved": += 1 | 0,
"reviewer_approval_rate.rejected": += 1 | 0,
"reviewer_rejection_count": += 1 if rejected, else unchanged,
"current_phase": "deslop_regression" if approved, else "story_implement",
"generation": += 1
```

### On termination

```json
"termination": "all_stories_passed | blocked_on_story_{id} | budget_exhausted | reviewer_rejected_{count}_times",
"termination_at": "<ISO>",
"termination_evidence": "<path to the file that establishes the label>",
"current_phase": "complete" | "blocked",
"generation": += 1
```

## State Invariants

After every write, verify:

1. `generation` is strictly monotonically increasing across writes (no decrease allowed)
2. `prd_sha256` matches SHA256 of canonicalized `prd.json.stories` array, if `prd_locked: true`
3. Every criterion with `passes: true` has `last_verified_at` not null AND (when current iteration is in progress) `last_verified_at > budget.iteration_started_at` for whichever iteration most recently claimed it
4. `spawns.{id}.status` is one of `in_progress | complete | spawn_failed | timed_out`
5. No spawn has `status: "in_progress"` once `current_phase: "complete"` or `"blocked"`
6. `reviewer_rejection_count <= 5` (or termination label = `reviewer_rejected_{count}_times`)
7. `budget.current_iteration <= budget.max_iterations` (or termination label = `budget_exhausted`)
8. `termination` is either null (run in progress) or one of the four defined labels
9. `config.critic` is one of `architect | critic | deep-qa | codex`
10. Every story in `prd.json` has status one of `pending | in_progress | passed | blocked`

## Rubber-Stamp Detection (adversarial invariant)

`reviewer_approval_rate` tracks a running count of reviewer verdicts. If `approved / total_reviews > 0.95` AND `total_reviews >= 10`:

- Set `reviewer_approval_rate.warning_threshold_approaching_rubber_stamp: true`
- Emit a `note` event in `progress.jsonl`: `"REVIEWER_POSSIBLY_BROKEN: approval rate {x}% over {n} reviews exceeds rubber-stamp threshold"`
- On the next completion attempt, spawn a SECOND reviewer with a different `--critic` value (e.g., if original was `architect`, secondary is `critic`) and require both to approve. A rubber-stamping reviewer is as broken as a rubber-stamping critic.

This invariant mirrors deep-design's judge rubber-stamp check and is enforced by the coordinator at Step 7c.

## Concurrency

- On startup: write `loop-{run_id}.lock` with timestamp
- If a lock file from a different run_id exists and is < 15 min old: "Another loop-until-done session appears active. Continue anyway? [y/N]"
- On clean exit: delete lock file
- Resume from `--resume=<run_id>` is exempt from the lock check — resume is idempotent

Do NOT claim atomic writes. Use the `generation` counter for conflict detection.
