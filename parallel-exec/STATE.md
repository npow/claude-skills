# State Management

## State File: `parallel-exec-{run_id}/state.json`

Authoritative runtime state. Written before every Task tool call; `generation` counter incremented on every write.

```json
{
  "run_id": "parallel-exec-20260416-153022",
  "skill": "parallel-exec",
  "created_at": "2026-04-16T15:30:22Z",
  "generation": 0,
  "current_phase": "dispatching | pending_convergence_check | complete",
  "budget": {
    "max_wave_count": 32,
    "current_wave": 0,
    "per_task_timeout_default_seconds": 600
  },
  "dependency_graph_path": "parallel-exec-{run_id}/logs/dependency_graph.json",
  "dispatch_log_path": "parallel-exec-{run_id}/logs/dispatch_log.jsonl",
  "tasks": {
    "t_001": {
      "spec_path": "parallel-exec-{run_id}/specs/t_001.json",
      "model_tier": "haiku",
      "verification_command": "npx tsc --noEmit",
      "expected_output_pattern": "^$",
      "depends_on": [],
      "touches_paths": ["src/types.ts"],
      "run_in_background": false,
      "timeout_seconds": 120,
      "status": "pending | in_progress | pending_convergence_check | spawn_failed | timed_out | passed_with_evidence | failed_with_error | conflicted_with_sibling | unverified | blocked_on_dependency",
      "spawn_time_iso": null,
      "completion_time_iso": null,
      "wave": null,
      "result_path": null,
      "verify_paths": {
        "stdout": null,
        "stderr": null,
        "exit": null
      },
      "subagent_self_report": {
        "claim": null,
        "verification_exit_code": null,
        "files_modified": [],
        "notes": null
      },
      "convergence_label": null,
      "convergence_label_reason": null,
      "failure_reason": null
    }
  },
  "convergence_check": {
    "status": "not_started | in_progress | completed | failed_unparseable",
    "output_path": "parallel-exec-{run_id}/convergence/convergence-check.md",
    "started_at": null,
    "completed_at": null,
    "structured_block_parsed": false
  },
  "aggregate_status": null,
  "invariants": {
    "coordinator_never_graded": true,
    "every_task_has_verification_command": true,
    "state_written_before_spawn": true,
    "no_aggregate_claim_without_convergence": true
  },
  "termination": null
}
```

---

## Task Registry Fields

| Field | Lifecycle | Who writes |
|---|---|---|
| `spec_path` | Written at Step 2 | Coordinator, before dispatch |
| `status` | See state transitions below | Coordinator + convergence checker (at Step 6) |
| `spawn_time_iso` | Written BEFORE Task tool call | Coordinator |
| `completion_time_iso` | Written after subagent produces `results/{task_id}.md` | Coordinator (detected by file presence) |
| `wave` | Set at dispatch | Coordinator |
| `result_path` | Set when result file detected | Coordinator |
| `verify_paths.*` | Set when verify files detected | Coordinator |
| `subagent_self_report` | Parsed from structured block in result file | Coordinator (verbatim extraction only — NOT evaluation) |
| `convergence_label` | One of four labels | Convergence checker — the ONLY writer of this field |
| `convergence_label_reason` | One-line reason | Convergence checker |
| `failure_reason` | Set on `spawn_failed` or `timed_out` | Coordinator |

The coordinator may NEVER write `convergence_label` directly. Any coordinator code path that sets this field is a violation of the independence invariant.

---

## Generation Counter

Before any write:
1. Read current `generation` from state file.
2. Write new state with `generation + 1`.
3. After writing, re-read and verify `generation == N+1`.
4. Mismatch → log conflict, retry with fresh read.

This is conflict-detectable, not truly atomic. Sufficient for single-coordinator use.

Do NOT claim atomic writes — the Write tool has no rename primitive. Use the generation counter for conflict detection instead.

---

## State Transitions

```
pending
  ├─ dispatch → in_progress       (coordinator sets spawn_time_iso, increments generation, calls Task tool)
  │   ├─ result file appears  → pending_convergence_check  (result_path + verify_paths set)
  │   ├─ timeout elapsed      → timed_out                  (no result file)
  │   └─ Task tool returned error (spawn refused) → spawn_failed
  │                             (resume retries spawn)
  ├─ dependency failed → blocked_on_dependency              (never dispatched)
  └─ (convergence check at Step 6):
        pending_convergence_check
         ├─ passed_with_evidence       (convergence checker verdict)
         ├─ failed_with_error          (convergence checker verdict)
         ├─ conflicted_with_sibling    (convergence checker verdict)
         └─ unverified                 (convergence checker verdict)
```

### Status rules

- `pending` tasks have not been dispatched; `depends_on` may still be blocking.
- `in_progress` MUST carry `spawn_time_iso`. Any `in_progress` task without this field is a state corruption and must be treated as `unverified` on resume.
- `spawn_failed` is distinct from `timed_out`: spawn was refused by the tool, not attempted. Resume retries spawn.
- `timed_out` is NOT re-queued. It surfaces in the aggregate report as `unverified` via the convergence checker.
- `pending_convergence_check` is the terminal status for successful dispatches; the final label is assigned at Step 6.

---

## Dependency Graph Representation

Persisted at `parallel-exec-{run_id}/logs/dependency_graph.json`. Built from the `depends_on` fields of every task spec.

```json
{
  "nodes": ["t_001", "t_002", "t_003", "t_004", "t_005"],
  "edges": [
    {"from": "t_001", "to": "t_003", "basis": "t_003.depends_on includes t_001"},
    {"from": "t_002", "to": "t_004", "basis": "t_004.depends_on includes t_002"}
  ],
  "topological_order": ["t_001", "t_002", "t_003", "t_004", "t_005"],
  "waves": [
    {"wave": 1, "tasks": ["t_001", "t_002", "t_005"]},
    {"wave": 2, "tasks": ["t_003", "t_004"]}
  ],
  "cycles_detected": [],
  "built_at": "2026-04-16T15:30:22Z"
}
```

### Rules

- Edges are directed `from: prerequisite → to: dependent`.
- A task is in wave `N+1` if all of its prerequisites are in waves `≤ N`. Tasks with no prerequisites are in wave 1.
- Cycles are detected at graph-build time. Any cycle → reject the batch at input validation (Step 0). Print the cycle to the user.
- A task in wave `N` may NOT be dispatched until every task in waves `1..N-1` that it depends on has `convergence_label: passed_with_evidence`. `failed_with_error` on a prerequisite blocks every dependent task — they are marked `blocked_on_dependency` without dispatch.
- Dispatch within a single wave is always parallel (single tool-call block). Serializing a wave is a bug.

### Wave blocking semantics

| Prerequisite outcome | Dependent task action |
|---|---|
| `passed_with_evidence` | Prerequisite satisfied; dispatch when its wave is reached. |
| `failed_with_error` | Dependent task status set to `blocked_on_dependency`; never dispatched. |
| `conflicted_with_sibling` | Dependent task status set to `blocked_on_dependency`; user intervention required before proceeding. |
| `unverified` | Dependent task status set to `blocked_on_dependency`; user intervention required. |

Prerequisite labels are known only after the convergence check for the wave completes. This skill runs the convergence check **once** at Step 6, after all waves have run, not per-wave — this is intentional: the convergence checker sees the full batch context and can detect cross-wave conflicts.

For cases where a failed prerequisite must block subsequent waves, the coordinator performs a lightweight per-wave check against the subagent self-report (`VERIFICATION_EXIT_CODE`); a nonzero self-reported exit code blocks dependents pre-convergence. The convergence checker may later escalate other tasks to `blocked_on_dependency` if its verdict differs.

---

## Dispatch Log: `logs/dispatch_log.jsonl`

One line per dispatch attempt:

```json
{"task_id": "t_001", "wave": 1, "tier": "haiku", "spawn_time_iso": "2026-04-16T15:30:23Z", "outcome": "spawned"}
{"task_id": "t_002", "wave": 1, "tier": "sonnet", "spawn_time_iso": "2026-04-16T15:30:23Z", "outcome": "spawned"}
{"task_id": "t_099", "wave": 1, "tier": "sonnet", "spawn_time_iso": "2026-04-16T15:30:23Z", "outcome": "spawn_failed", "failure_reason": "concurrency limit exceeded"}
```

`outcome` ∈ {`spawned`, `spawn_failed`}. The log is append-only; failed spawns that are retried on resume produce a second line with a new `spawn_time_iso`.

---

## State Invariants (verified before aggregate report)

After the convergence check completes, verify:

1. State file is valid JSON.
2. `generation` is strictly monotonically increasing across every write.
3. No task has `status: "in_progress"` — all are terminal or `pending_convergence_check`.
4. No task has `status: "pending"` — all are either dispatched (some form), blocked, or terminal.
5. Every task with a non-null `spawn_time_iso` has a line in `dispatch_log.jsonl`.
6. Every task with `convergence_label` set has a matching entry in `convergence/convergence-check.md`'s structured block.
7. No task's `convergence_label` was written by anyone other than the convergence checker (audit via write log or git history if available).
8. `aggregate_status` matches the structured output of the convergence check — not a coordinator-computed value.
9. If any task has `convergence_label` set, `convergence_check.status == "completed"`.
10. `convergence_check.structured_block_parsed == true` before `aggregate_status` is set.

Invariant violations → coordinator sets `aggregate_status: convergence_check_failed` and surfaces paths for manual review.

---

## Resume Protocol (session restart)

1. Locate the most recent `parallel-exec-*/state.json` in CWD.
2. Verify `generation` counter integrity (monotonically increasing).
3. For each task:
   - `status: pending` and `depends_on` satisfied → re-add to dispatch frontier.
   - `status: in_progress` and `results/{task_id}.md` exists → set to `pending_convergence_check`. Parse structured block, populate `subagent_self_report`.
   - `status: in_progress` and `results/{task_id}.md` missing → set to `timed_out`. NOT re-queued.
   - `status: spawn_failed` → re-add to dispatch frontier (spawn was refused, retry is warranted).
   - `status: blocked_on_dependency` → re-evaluate dependency labels; if prerequisite now `passed_with_evidence`, unblock.
   - Any terminal label (`passed_with_evidence`, `failed_with_error`, `conflicted_with_sibling`, `unverified`) → leave as-is.
4. If any task still needs dispatch, resume Step 4 of the main workflow (dispatch next wave).
5. If all tasks are terminal but convergence-check has not run (`convergence_check.status != "completed"`) → resume at Step 6 (spawn convergence checker).
6. If convergence-check output file exists but `structured_block_parsed == false` → re-parse. If still unparseable, mark `aggregate_status: convergence_check_failed` and surface.

Resume NEVER re-dispatches tasks that are already terminal. Resume NEVER re-evaluates tasks that already have a `convergence_label` — the convergence check is one-shot per run.

---

## Updates by Stage

### On task spec validation (Step 0/2)
```json
"tasks.{id}": {
  "spec_path": "specs/{id}.json",
  "status": "pending",
  "depends_on": [...],
  "touches_paths": [...],
  "verification_command": "...",
  ...
}
"generation": += 1
```

### Before calling Task tool (Step 4, per task)
```json
"tasks.{id}.status": "in_progress",
"tasks.{id}.spawn_time_iso": "<now>",
"tasks.{id}.wave": N,
"generation": += 1
```
Write this state BEFORE the Task tool call. Append a line to `dispatch_log.jsonl`.

### On Task tool error (spawn refused)
```json
"tasks.{id}.status": "spawn_failed",
"tasks.{id}.spawn_time_iso": null,
"tasks.{id}.failure_reason": "<error>",
"generation": += 1
```
Resume retries; does not wait.

### On subagent completion (result file detected)
```json
"tasks.{id}.status": "pending_convergence_check",
"tasks.{id}.completion_time_iso": "<now>",
"tasks.{id}.result_path": "results/{id}.md",
"tasks.{id}.verify_paths": {
  "stdout": "verify/{id}.stdout",
  "stderr": "verify/{id}.stderr",
  "exit": "verify/{id}.exit"
},
"tasks.{id}.subagent_self_report": { ...parsed from structured block... },
"generation": += 1
```

### After convergence check completes (Step 6)
```json
"tasks.{id}.status": "passed_with_evidence | failed_with_error | conflicted_with_sibling | unverified",
"tasks.{id}.convergence_label": "<label>",
"tasks.{id}.convergence_label_reason": "<one-line>",
"convergence_check.status": "completed",
"convergence_check.completed_at": "<now>",
"convergence_check.structured_block_parsed": true,
"aggregate_status": "<one of five labels>",
"generation": += 1
```

### On convergence checker failure (output missing or malformed)
```json
"convergence_check.status": "failed_unparseable",
"aggregate_status": "convergence_check_failed",
"generation": += 1
```
No task receives a convergence label. Coordinator prints evidence paths for manual review.
