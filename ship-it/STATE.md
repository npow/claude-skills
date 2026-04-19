# State Management

## State File: `ship-it-{run_id}/state.json`

```json
{
  "run_id": "20260416-153022",
  "skill": "ship-it",
  "created_at": "2026-04-16T15:30:22Z",
  "updated_at": "2026-04-16T16:12:05Z",
  "generation": 34,
  "initial_idea": "verbatim user input",
  "project_root": "/absolute/path/to/project",
  "tech_stack": {
    "language": "typescript|python|node",
    "build_tool": "npm|pip|uv|etc",
    "test_runner": "jest|vitest|pytest|etc"
  },
  "current_phase": "spec|design|build|test|integrate|package|cleanup|complete",
  "phases": {
    "spec": {
      "status": "pending|in_progress|complete|delegation_failed|blocked",
      "spawn_time_iso": null,
      "completed_at": null,
      "evidence_files": [
        "ship-it-{run_id}/spec/SPEC.md",
        "ship-it-{run_id}/spec/user-approval.md",
        "ship-it-{run_id}/spec/phase-gate.md"
      ],
      "user_approved": null,
      "approval_scope": null,
      "conditions": [],
      "phase_gate": { "advance": null }
    },
    "design": {
      "status": "pending",
      "delegate": "deep-plan",
      "spawn_time_iso": null,
      "completed_at": null,
      "evidence_files": [
        "ship-it-{run_id}/design/DESIGN.md",
        "ship-it-{run_id}/design/adr.md",
        "ship-it-{run_id}/design/consensus-termination.md",
        "ship-it-{run_id}/design/phase-gate.md"
      ],
      "consensus_label": null,
      "iter_count": null,
      "degraded_mode": false,
      "phase_gate": { "advance": null }
    },
    "build": {
      "status": "pending",
      "delegate": "team",
      "spawn_time_iso": null,
      "completed_at": null,
      "evidence_files": [
        "ship-it-{run_id}/build/team-termination.md",
        "ship-it-{run_id}/build/handoffs/",
        "ship-it-{run_id}/build/modified-files.txt",
        "ship-it-{run_id}/build/build-output.txt",
        "ship-it-{run_id}/build/phase-gate.md"
      ],
      "team_label": null,
      "modified_files_count": null,
      "accepted_unfixed_count": null,
      "degraded_mode": false,
      "phase_gate": { "advance": null }
    },
    "test": {
      "status": "pending",
      "audit": {
        "delegate": "deep-qa --diff",
        "spawn_time_iso": null,
        "completed_at": null,
        "critical_count": null,
        "major_count": null,
        "minor_count": null,
        "disputed_count": null,
        "fix_loop_required": null,
        "structured_verdict_path": "ship-it-{run_id}/test/audit/structured-verdict.md",
        "defects_path": "ship-it-{run_id}/test/audit/defects.md"
      },
      "test_run": {
        "output_path": "ship-it-{run_id}/test/test-output.txt",
        "exit_code": null,
        "tests_passed": null,
        "tests_failed": null
      },
      "fix": {
        "delegate": "loop-until-done",
        "spawn_time_iso": null,
        "completed_at": null,
        "skipped": false,
        "skip_reason": null,
        "loop_label": null,
        "stories_total": null,
        "stories_passed": null,
        "prd_path": "ship-it-{run_id}/test/fix/prd.json",
        "termination_path": "ship-it-{run_id}/test/fix/loop-termination.md"
      },
      "evidence_files": [
        "ship-it-{run_id}/test/audit/defects.md",
        "ship-it-{run_id}/test/audit/structured-verdict.md",
        "ship-it-{run_id}/test/test-output.txt",
        "ship-it-{run_id}/test/fix/loop-termination.md",
        "ship-it-{run_id}/test/phase-gate.md"
      ],
      "degraded_mode": false,
      "phase_gate": { "advance": null }
    },
    "integrate": {
      "status": "pending",
      "spawn_time_iso": null,
      "completed_at": null,
      "evidence_files": [
        "ship-it-{run_id}/integrate/build-output.txt",
        "ship-it-{run_id}/integrate/startup-probe.txt",
        "ship-it-{run_id}/integrate/smoke-output.txt",
        "ship-it-{run_id}/integrate/stub-scan.txt",
        "ship-it-{run_id}/integrate/phase-gate.md"
      ],
      "build_exit_code": null,
      "smoke_pass_count": null,
      "stub_unannotated_count": null,
      "phase_gate": { "advance": null }
    },
    "package": {
      "status": "pending",
      "revalidation_round": 0,
      "max_revalidation_rounds": 2,
      "clean_install": {
        "spawn_time_iso": null,
        "completed_at": null,
        "exit_code": null,
        "output_path": "ship-it-{run_id}/package/clean-install-output.txt"
      },
      "judges": {
        "correctness": {
          "spawn_time_iso": null,
          "completed_at": null,
          "verdict": null,
          "blocking_scenario_count": null,
          "conditional_count": null,
          "cannot_evaluate_count": null,
          "verdict_path": "ship-it-{run_id}/package/correctness-verdict.md"
        },
        "security": {
          "spawn_time_iso": null,
          "completed_at": null,
          "verdict": null,
          "blocking_scenario_count": null,
          "conditional_count": null,
          "cannot_evaluate_count": null,
          "verdict_path": "ship-it-{run_id}/package/security-verdict.md"
        },
        "quality": {
          "spawn_time_iso": null,
          "completed_at": null,
          "verdict": null,
          "blocking_scenario_count": null,
          "conditional_count": null,
          "cannot_evaluate_count": null,
          "verdict_path": "ship-it-{run_id}/package/quality-verdict.md"
        }
      },
      "aggregate": null,
      "aggregation_path": "ship-it-{run_id}/package/aggregation.md",
      "evidence_files": [
        "ship-it-{run_id}/package/clean-install-output.txt",
        "ship-it-{run_id}/package/correctness-verdict.md",
        "ship-it-{run_id}/package/security-verdict.md",
        "ship-it-{run_id}/package/quality-verdict.md",
        "ship-it-{run_id}/package/aggregation.md",
        "ship-it-{run_id}/package/phase-gate.md"
      ],
      "phase_gate": { "advance": null }
    },
    "cleanup": {
      "status": "pending",
      "completion_report_path": "ship-it-{run_id}/completion-report.md",
      "completion_report_written": false,
      "state_deleted": false
    }
  },
  "budget": {
    "max_delegations_per_phase": 3,
    "current_delegation_count": {
      "design": 0,
      "build": 0,
      "test_audit": 0,
      "test_fix": 0,
      "package_revalidation": 0
    },
    "token_spent_estimate_usd": 0.0,
    "hard_cap_usd": 30.0,
    "exhausted": false
  },
  "integrations": {
    "consensus_plan_available": null,
    "team_available": null,
    "deep_qa_available": null,
    "loop_until_done_available": null,
    "availability_checked_at": null
  },
  "invariants": {
    "coordinator_never_evaluated": true,
    "all_evidence_fresh_this_session": true,
    "state_written_before_every_delegation": true,
    "types_ts_immutable_after_design": true
  },
  "termination": null,
  "termination_reason": null
}
```

## Phase Status Enum

Valid values for `phases.{phase}.status`:

| Value | Meaning |
|---|---|
| `pending` | Not yet reached |
| `in_progress` | Delegation running; `spawn_time_iso` set, no evidence yet |
| `complete` | Evidence written AND phase-gate returned `ADVANCE=true` |
| `delegation_failed` | Delegate skill returned error or never wrote evidence; `spawn_time_iso` set, `completed_at` null |
| `blocked` | Phase-gate returned `ADVANCE=false` with a blocking reason; evidence exists but insufficient |

Transitions:
- `pending → in_progress` — coordinator writes `spawn_time_iso` before invoking delegate
- `in_progress → complete` — evidence written AND phase-gate passes
- `in_progress → delegation_failed` — delegate errors or times out
- `in_progress → blocked` — evidence written but phase-gate fails
- `delegation_failed → in_progress` — on re-delegation within budget
- `blocked → in_progress` — if user requests retry after manual fix

No other transitions legal. Coordinator must refuse invalid transitions.

## Phase Evidence File Registry

The iron-law gate validates these files exist, contain required markers, and have mtimes after `state.json.created_at`.

### Phase 1 — Spec

| File | Required? | Producer |
|---|---|---|
| `spec/SPEC.md` | yes | coordinator with user approval |
| `spec/user-approval.md` | yes | coordinator records user response |
| `spec/phase-gate.md` | yes | fresh phase-gate subagent |

### Phase 2 — Design

| File | Required? | Producer |
|---|---|---|
| `design/DESIGN.md` | yes | `/deep-plan` output adapted by coordinator |
| `design/adr.md` | yes | `/deep-plan` |
| `design/consensus-termination.md` | yes | `/deep-plan` |
| `design/phase-gate.md` | yes | fresh phase-gate subagent |

Plus: `types.ts` (or equivalent) written to project root. Immutability enforced via `invariants.types_ts_immutable_after_design`.

### Phase 3 — Build

| File | Required? | Producer |
|---|---|---|
| `build/team-termination.md` | yes | `/team` |
| `build/handoffs/` (directory, non-empty) | yes | `/team` |
| `build/modified-files.txt` | yes | `/team` |
| `build/build-output.txt` | yes | `/team` final verify run |
| `build/phase-gate.md` | yes | fresh phase-gate subagent |

### Phase 4 — Test

| File | Required? | Producer |
|---|---|---|
| `test/audit/defects.md` | yes | `deep-qa --diff` |
| `test/audit/structured-verdict.md` | yes | `deep-qa` summary wrapper |
| `test/test-output.txt` | yes | coordinator runs `npm test` / `pytest` |
| `test/fix/loop-termination.md` | if `FIX_LOOP_REQUIRED=true` | `/loop-until-done` |
| `test/skipped-fix-loop.md` | if `FIX_LOOP_REQUIRED=false` | coordinator |
| `test/phase-gate.md` | yes | fresh phase-gate subagent |

Exactly one of `loop-termination.md` or `skipped-fix-loop.md` must be present. Both present → gate fails.

### Phase 5 — Integrate

| File | Required? | Producer |
|---|---|---|
| `integrate/build-output.txt` | yes | coordinator runs `npm run build` |
| `integrate/startup-probe.txt` | yes | coordinator probes entry point |
| `integrate/smoke-output.txt` | yes | coordinator runs smoke tests |
| `integrate/stub-scan.txt` | yes | coordinator greps source |
| `integrate/phase-gate.md` | yes | fresh phase-gate subagent |

Any sub-step failure → fix delegated to `/loop-until-done`; re-run phase from the failing step. No coordinator-authored code fixes.

### Phase 6 — Package

| File | Required? | Producer |
|---|---|---|
| `package/clean-install-output.txt` | yes | coordinator runs clean-install cycle |
| `package/judge-input.md` | yes | coordinator (paths only) |
| `package/correctness-verdict.md` | yes | correctness judge (fresh spawn) |
| `package/security-verdict.md` | yes | security judge (fresh spawn) |
| `package/quality-verdict.md` | yes | quality judge (fresh spawn) |
| `package/aggregation.md` | yes | coordinator (mechanical aggregation) |
| `package/phase-gate.md` | yes | fresh phase-gate subagent |

On re-validation (up to 2 rounds): prior round verdicts remain on disk (as `{dimension}-verdict.v1.md` etc.) but current-round files must be freshly-produced from re-spawned judges. Aggregation uses current-round only.

### Completion Report

| File | Required? | Producer |
|---|---|---|
| `completion-report.md` | yes | completion-report subagent |

Report must be written BEFORE any state deletion. Deletion is optional and gated by termination label.

---

## Generation Counter

Before any state write:
1. Read current `generation` from `state.json`
2. Write with `generation: current + 1`, update `updated_at`
3. Re-read; verify new `generation == current + 1`
4. If mismatch: log conflict, retry with fresh read

This is conflict-detectable, not atomic. Sufficient for single-coordinator use. Never claim atomic writes — the Write tool has no rename primitive.

---

## State Updates

### Before delegating to any phase skill (CRITICAL: state written BEFORE delegation call)
```json
"phases.{phase}.status": "in_progress",
"phases.{phase}.spawn_time_iso": "<ISO>",
"current_phase": "{phase}",
"generation": += 1,
"updated_at": "<ISO>"
```

### If delegate returns an error (no evidence produced)
```json
"phases.{phase}.status": "delegation_failed",
"phases.{phase}.completed_at": null,
"budget.current_delegation_count.{phase}": += 1,
"generation": += 1
```

Resume/retry: if `current_delegation_count.{phase} < max_delegations_per_phase`, re-spawn. Else mark `blocked_at_phase_{N}`.

### After delegate produces evidence (but before gate)
```json
"phases.{phase}.completed_at": "<ISO>",
"generation": += 1
```

### After phase-gate passes
```json
"phases.{phase}.status": "complete",
"phases.{phase}.phase_gate": { ... },
"current_phase": "<next_phase>",
"generation": += 1
```

### After phase-gate fails
```json
"phases.{phase}.status": "blocked",
"phases.{phase}.phase_gate": { "advance": false, "blocking_reason": "..." },
"termination": "blocked_at_phase_{N}",
"termination_reason": "<blocking_reason>",
"generation": += 1
```

### After Phase 6 judge completes
```json
"phases.package.judges.{dimension}.completed_at": "<ISO>",
"phases.package.judges.{dimension}.verdict": "approved|rejected|conditional",
"phases.package.judges.{dimension}.blocking_scenario_count": <int>,
"phases.package.judges.{dimension}.cannot_evaluate_count": <int>,
"generation": += 1
```

### After Phase 6 re-validation round
```json
"phases.package.revalidation_round": += 1,
// rename v{N} files to preserve history
// reset judges state to pending for next round
"generation": += 1
```

### After completion report written
```json
"phases.cleanup.completion_report_written": true,
"termination": "complete|partial_with_accepted_tradeoffs|blocked_at_phase_N|budget_exhausted",
"generation": += 1
```

---

## State Invariants (verified after every write)

1. `generation` is strictly monotonically increasing. Regression → halt.
2. At most one phase has `status: "in_progress"` at any time.
3. `current_phase` matches the phase with `status: "in_progress"` OR the most recently completed phase.
4. Every phase with `status: "complete"` has all required `evidence_files` on disk with mtimes after `state.json.created_at`.
5. `termination` is non-null iff `current_phase == "complete"` OR `current_phase == "cleanup"` OR some phase has `status: "blocked"` OR `budget.exhausted == true`.
6. `termination` value is from the exhaustive label table in SKILL.md — no other values allowed.
7. `invariants.coordinator_never_evaluated == true` — flips to `false` if any Phase 6 judge verdict or phase-gate verdict was authored by the coordinator context. Kill-switch: once false, the run is invalid.
8. `invariants.all_evidence_fresh_this_session == true` — flips to `false` if any evidence file's mtime precedes `created_at`. Resume must re-produce stale evidence, not consume it.
9. `invariants.types_ts_immutable_after_design == true` — flips to `false` if `types.ts` mtime changes after Phase 2 completion. If flipped: the build is invalid; some build subagent diverged.
10. For each phase with `status == "complete"`, `phase_gate.advance == true`.
11. Total `budget.current_delegation_count` across phases ≤ 15 (hard cap).

---

## Resume Protocol

1. On ship-it invocation, look for `ship-it-*/state.json` in CWD. If one or more exist:
   - Parse `state.json`. If multiple: list and prompt user to select (do NOT auto-pick most recent).
   - Verify all invariants. If any fails: halt with `resume_invalid_state` and print which invariant failed.
2. If `termination` is set: run is complete. Display completion report path. Offer to start a new run.
3. Else identify resume point:
   - For each phase in order (spec, design, build, test, integrate, package, cleanup):
     - If `status == "complete"`: skip.
     - If `status == "in_progress"` or `status == "delegation_failed"`: resume here.
     - If `status == "pending"`: resume here.
     - If `status == "blocked"`: prompt user — manual fix, retry, or abandon.
4. On resume at a phase:
   - Check evidence files. If complete and mtimes after `created_at`: just run phase-gate.
   - If evidence partial or missing: re-delegate (increments `current_delegation_count.{phase}`).
   - If `current_delegation_count.{phase} >= max_delegations_per_phase`: mark `blocked_at_phase_{N}` without re-delegating.
5. Resume NEVER re-runs completed phases. Resume NEVER consumes stale evidence — every agent reads from disk fresh.

---

## Session Restart Recovery

1. Read `state.json`.
2. Verify invariants.
3. For each phase with `status: "in_progress"`:
   - Evidence files complete? → Mark `complete`, run gate.
   - Evidence partial? → Mark `delegation_failed`, re-delegate on next tick.
   - No evidence and `spawn_time_iso` set but very stale? → Mark `delegation_failed`, re-delegate.
4. For each phase with `status: "delegation_failed"`: re-delegate if under budget; else block.
5. Continue from current phase.

---

## Lock File

On startup: write `ship-it-{run_id}.lock` with timestamp. If a lock from a different run_id is present and < 15 min old: prompt "Another ship-it session appears active. Continue anyway? [y/N]". On clean exit: delete lock file.

Lock file is advisory — generation counter is the actual concurrency control.
