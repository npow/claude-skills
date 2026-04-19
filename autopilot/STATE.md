# State Management

## State File: `autopilot-{run_id}/state.json`

```json
{
  "run_id": "20260416-153022",
  "skill": "autopilot",
  "created_at": "2026-04-16T15:30:22Z",
  "updated_at": "2026-04-16T15:42:11Z",
  "generation": 17,
  "initial_idea": "verbatim user input",
  "ambiguity": {
    "score": 0.72,
    "class": "high",
    "concrete_anchors_count": 0,
    "classifier_verdict_path": "autopilot-{run_id}/expand/ambiguity-verdict.md",
    "routed_to": "deep-interview|spec|deep-design",
    "deep_interview_available": true
  },
  "current_phase": "expand|plan|exec|qa_audit|qa_fix|validate|cleanup|complete",
  "phases": {
    "expand": {
      "status": "pending|in_progress|complete|delegation_failed|blocked",
      "delegate": "deep-interview|spec|deep-design",
      "spawn_time_iso": "2026-04-16T15:30:25Z",
      "completed_at": null,
      "evidence_files": [
        "autopilot-{run_id}/expand/ambiguity-verdict.md",
        "autopilot-{run_id}/expand/spec.md",
        "autopilot-{run_id}/expand/phase-gate.md"
      ],
      "phase_gate": {
        "evidence_present": true,
        "evidence_parseable": true,
        "evidence_fresh_this_session": true,
        "advance": true,
        "blocking_reason": null
      },
      "degraded_mode": false,
      "degraded_reasons": []
    },
    "plan": {
      "status": "pending",
      "delegate": "deep-plan",
      "spawn_time_iso": null,
      "completed_at": null,
      "evidence_files": [
        "autopilot-{run_id}/plan/plan.md",
        "autopilot-{run_id}/plan/adr.md",
        "autopilot-{run_id}/plan/consensus-termination.md",
        "autopilot-{run_id}/plan/phase-gate.md"
      ],
      "consensus_label": null,
      "iter_count": null,
      "phase_gate": { "advance": null }
    },
    "exec": {
      "status": "pending",
      "delegate": "team",
      "spawn_time_iso": null,
      "completed_at": null,
      "evidence_files": [
        "autopilot-{run_id}/exec/team-termination.md",
        "autopilot-{run_id}/exec/handoffs/",
        "autopilot-{run_id}/exec/modified-files.txt",
        "autopilot-{run_id}/exec/build-output.txt",
        "autopilot-{run_id}/exec/phase-gate.md"
      ],
      "team_label": null,
      "modified_files_count": null,
      "accepted_unfixed_count": null,
      "phase_gate": { "advance": null }
    },
    "qa": {
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
        "structured_verdict_path": "autopilot-{run_id}/qa/audit/structured-verdict.md",
        "defects_path": "autopilot-{run_id}/qa/audit/defects.md"
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
        "prd_path": "autopilot-{run_id}/qa/fix/prd.json",
        "termination_path": "autopilot-{run_id}/qa/fix/loop-termination.md"
      },
      "evidence_files": [
        "autopilot-{run_id}/qa/audit/defects.md",
        "autopilot-{run_id}/qa/audit/structured-verdict.md",
        "autopilot-{run_id}/qa/fix/loop-termination.md",
        "autopilot-{run_id}/qa/phase-gate.md"
      ],
      "phase_gate": { "advance": null }
    },
    "validate": {
      "status": "pending",
      "revalidation_round": 0,
      "max_revalidation_rounds": 2,
      "judges": {
        "correctness": {
          "spawn_time_iso": null,
          "completed_at": null,
          "verdict": null,
          "blocking_scenario_count": null,
          "conditional_count": null,
          "cannot_evaluate_count": null,
          "verdict_path": "autopilot-{run_id}/validate/correctness-verdict.md"
        },
        "security": {
          "spawn_time_iso": null,
          "completed_at": null,
          "verdict": null,
          "blocking_scenario_count": null,
          "conditional_count": null,
          "cannot_evaluate_count": null,
          "verdict_path": "autopilot-{run_id}/validate/security-verdict.md"
        },
        "quality": {
          "spawn_time_iso": null,
          "completed_at": null,
          "verdict": null,
          "blocking_scenario_count": null,
          "conditional_count": null,
          "cannot_evaluate_count": null,
          "verdict_path": "autopilot-{run_id}/validate/quality-verdict.md"
        }
      },
      "aggregate": null,
      "aggregation_path": "autopilot-{run_id}/validate/aggregation.md",
      "evidence_files": [
        "autopilot-{run_id}/validate/correctness-verdict.md",
        "autopilot-{run_id}/validate/security-verdict.md",
        "autopilot-{run_id}/validate/quality-verdict.md",
        "autopilot-{run_id}/validate/aggregation.md",
        "autopilot-{run_id}/validate/phase-gate.md"
      ],
      "phase_gate": { "advance": null }
    },
    "cleanup": {
      "status": "pending",
      "completion_report_path": "autopilot-{run_id}/completion-report.md",
      "completion_report_written": false,
      "state_deleted": false
    }
  },
  "budget": {
    "max_delegations_per_phase": 3,
    "current_delegation_count": {
      "expand": 0,
      "plan": 0,
      "exec": 0,
      "qa_audit": 0,
      "qa_fix": 0,
      "validate": 0
    },
    "token_spent_estimate_usd": 0.0,
    "hard_cap_usd": 25.0,
    "exhausted": false
  },
  "integrations": {
    "deep_interview_available": null,
    "deep_design_available": null,
    "deep_qa_available": null,
    "consensus_plan_available": null,
    "team_available": null,
    "loop_until_done_available": null,
    "availability_checked_at": null
  },
  "invariants": {
    "coordinator_never_evaluated": true,
    "all_evidence_fresh_this_session": true,
    "state_written_before_every_delegation": true
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
| `in_progress` | Delegation is running; `spawn_time_iso` is set, no evidence yet |
| `complete` | Evidence written AND phase-gate returned `ADVANCE=true` |
| `delegation_failed` | Delegate subagent/skill returned an error or never wrote evidence; `spawn_time_iso` is set, `completed_at` is null |
| `blocked` | Phase-gate returned `ADVANCE=false` with a blocking reason; evidence exists but is insufficient |

Transitions:
- `pending → in_progress` — when coordinator writes `spawn_time_iso` before invoking delegate
- `in_progress → complete` — when evidence written AND phase-gate passes
- `in_progress → delegation_failed` — when delegate errors or times out
- `in_progress → blocked` — when evidence written but phase-gate fails
- `delegation_failed → in_progress` — on re-delegation (within budget)
- `blocked → in_progress` — if user requests re-try (e.g., after manual fix)

No other transitions are legal. Coordinator must refuse invalid transitions.

## Phase Evidence File Registry

The iron-law gate validates these files exist, contain required markers, and have mtimes after `state.json.created_at`.

### Phase 0 — Expand

| File | Required? | Producer |
|---|---|---|
| `expand/ambiguity-verdict.md` | yes | ambiguity classifier subagent |
| `expand/spec.md` OR `expand/design.md` | yes (one of) | `/spec` or `deep-design` delegate |
| `expand/phase-gate.md` | yes | fresh phase-gate subagent |

### Phase 1 — Plan

| File | Required? | Producer |
|---|---|---|
| `plan/plan.md` | yes | `/deep-plan` |
| `plan/adr.md` | yes | `/deep-plan` |
| `plan/consensus-termination.md` | yes | `/deep-plan` |
| `plan/phase-gate.md` | yes | fresh phase-gate subagent |

### Phase 2 — Exec

| File | Required? | Producer |
|---|---|---|
| `exec/team-termination.md` | yes | `/team` |
| `exec/handoffs/` (directory, non-empty) | yes | `/team` |
| `exec/modified-files.txt` | yes | `/team` |
| `exec/build-output.txt` | yes | `/team` final verify run |
| `exec/phase-gate.md` | yes | fresh phase-gate subagent |

### Phase 3 — QA

| File | Required? | Producer |
|---|---|---|
| `qa/audit/defects.md` | yes | `deep-qa --diff` |
| `qa/audit/structured-verdict.md` | yes | `deep-qa` summary wrapper |
| `qa/fix/loop-termination.md` | if `FIX_LOOP_REQUIRED=true` | `/loop-until-done` |
| `qa/skipped-fix-loop.md` | if `FIX_LOOP_REQUIRED=false` | coordinator |
| `qa/phase-gate.md` | yes | fresh phase-gate subagent |

Exactly one of `loop-termination.md` or `skipped-fix-loop.md` must be present. Both present → gate fails.

### Phase 4 — Validate

| File | Required? | Producer |
|---|---|---|
| `validate/judge-input.md` | yes | coordinator (paths only) |
| `validate/correctness-verdict.md` | yes | correctness judge (fresh spawn) |
| `validate/security-verdict.md` | yes | security judge (fresh spawn) |
| `validate/quality-verdict.md` | yes | quality judge (fresh spawn) |
| `validate/aggregation.md` | yes | coordinator (mechanical) |
| `validate/phase-gate.md` | yes | fresh phase-gate subagent |

On re-validation (up to 2 rounds): judge verdicts from the prior round remain on disk (as `correctness-verdict.v1.md` etc.) but the current-round files must be the freshly-produced ones from re-spawned judges. Aggregation uses current-round only.

### Phase 5 — Cleanup

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
Resume/retry behavior: if `current_delegation_count.{phase} < max_delegations_per_phase`, re-spawn. Else mark `blocked_at_phase_{N}`.

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

### After Phase 4 judge completes
```json
"phases.validate.judges.{dimension}.completed_at": "<ISO>",
"phases.validate.judges.{dimension}.verdict": "approved|rejected|conditional",
"phases.validate.judges.{dimension}.blocking_scenario_count": <int>,
"phases.validate.judges.{dimension}.cannot_evaluate_count": <int>,
"generation": += 1
```

### After Phase 4 re-validation round
```json
"phases.validate.revalidation_round": += 1,
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
3. `current_phase` matches the phase with `status: "in_progress"` OR the most recently completed phase (when between phases).
4. Every phase in `phases` with `status: "complete"` has all required `evidence_files` existing on disk.
5. `termination` is non-null iff `current_phase == "complete"` OR `current_phase == "cleanup"` OR some phase has `status: "blocked"` OR `budget.exhausted == true`.
6. `termination` value is from the exhaustive label table in SKILL.md — no other values allowed.
7. `invariants.coordinator_never_evaluated == true` — flips to `false` if any Phase 4 judge verdict or phase-gate verdict was authored by the coordinator context. This is a kill-switch: once false, the run is invalid.
8. `invariants.all_evidence_fresh_this_session == true` — flips to `false` if any evidence file's mtime precedes `created_at`. Resume must re-produce stale evidence, not consume it.
9. For each phase with `status == "complete"`, `phase_gate.advance == true`.
10. Total `budget.current_delegation_count` across phases ≤ 15 (hard cap).

---

## Resume Protocol

1. On autopilot invocation, look for `autopilot-*/state.json` in CWD. If one or more exist:
   - Parse `state.json`. If multiple: list and prompt user to select (do NOT auto-pick most recent).
   - Verify all invariants. If any invariant violates: halt with `resume_invalid_state` and print which invariant failed.
2. If `termination` is set: run is complete. Display completion report path. Offer to start a new run.
3. Else identify resume point:
   - For each phase in order (expand, plan, exec, qa, validate, cleanup):
     - If `status == "complete"`: skip.
     - If `status == "in_progress"` or `status == "delegation_failed"`: resume here.
     - If `status == "pending"`: resume here.
     - If `status == "blocked"`: prompt user — manual fix, re-try, or abandon.
4. On resume at a phase:
   - Check evidence files. If complete and mtimes are after `created_at`: just run phase-gate.
   - If evidence partial or missing: re-delegate (increments `current_delegation_count.{phase}`).
   - If `current_delegation_count.{phase} >= max_delegations_per_phase`: mark `blocked_at_phase_{N}` without re-delegating.
5. Resume NEVER re-runs completed phases. Resume NEVER consumes stale evidence.

---

## Session Restart Recovery

1. Read `state.json`.
2. Verify invariants.
3. For each phase with `status: "in_progress"`:
   - Evidence files complete? → Mark `complete`, run gate.
   - Evidence partial? → Mark `delegation_failed`, re-delegate on next tick.
   - No evidence and `spawn_time_iso` set but very stale? → Mark `delegation_failed`, re-delegate.
4. For each phase with `status: "delegation_failed"`:
   - Re-delegate if under budget; else block.
5. Continue from current phase.

---

## Lock File

On startup: write `autopilot-{run_id}.lock` with timestamp. If a lock from a different run_id is present and < 15 min old: prompt "Another autopilot session appears active. Continue anyway? [y/N]". On clean exit: delete lock file.

Lock file is advisory — generation counter is the actual concurrency control.
