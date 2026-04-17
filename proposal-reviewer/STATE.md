# State Management

Pure file-based state. No MCP state tools. All persistence lives in `proposal-review-{run_id}/` in the current working directory.

## Contents

- state.json schema
- Stage enums
- Agent spawn record schema
- Generation counter
- Lock file
- Iron-law gate (pre-final-report)
- Resume protocol
- State invariants (checked at every read)
- State update patterns

## State File: `proposal-review-{run_id}/state.json`

```json
{
  "run_id": "20260416-153022",
  "skill": "proposal-reviewer",
  "created_at": "2026-04-16T15:30:22Z",
  "proposal_text": "<verbatim proposal text>",
  "proposal_text_sha256": "<sha256 hex of proposal_text>",
  "core_claim": "<locked 1-2 sentence core claim>",
  "core_claim_sha256": "<sha256 hex>",
  "generation": 0,
  "invocation": {
    "rewrite_requested": false,
    "cli_args": "<original invocation string>"
  },
  "integrations": {
    "deep_qa_available": true,
    "degraded_mode_active": false,
    "degraded_mode_reasons": []
  },
  "budget": {
    "max_critic_weaknesses_per_dimension": 5,
    "fact_check_timeout_seconds_per_claim": 180,
    "token_spent_estimate_usd": 0.0
  },
  "current_stage": "claim-extraction",
  "stages": [
    {
      "name": "claim-extraction",
      "status": "not_started",
      "started_at": null,
      "completed_at": null,
      "evidence_files": [],
      "agent_spawns": [],
      "exit_gate_checked_at": null,
      "exit_gate_verdict": null
    },
    {
      "name": "parallel-critique",
      "status": "not_started",
      "started_at": null,
      "completed_at": null,
      "evidence_files": [],
      "agent_spawns": [],
      "dimensions_returned_parseable": [],
      "quorum_met": null,
      "exit_gate_checked_at": null,
      "exit_gate_verdict": null
    },
    {
      "name": "fact-check",
      "status": "not_started",
      "started_at": null,
      "completed_at": null,
      "evidence_files": [],
      "agent_spawns": [],
      "claims_checked": [],
      "exit_gate_checked_at": null,
      "exit_gate_verdict": null
    },
    {
      "name": "independent-judges",
      "status": "not_started",
      "started_at": null,
      "completed_at": null,
      "evidence_files": [],
      "agent_spawns": [],
      "credibility_verdicts": [],
      "severity_verdicts": [],
      "weaknesses_dropped_unfalsifiable": [],
      "landscape_verdict_path": null,
      "exit_gate_checked_at": null,
      "exit_gate_verdict": null
    },
    {
      "name": "rationalization-audit",
      "status": "not_started",
      "started_at": null,
      "completed_at": null,
      "evidence_files": [],
      "agent_spawns": [],
      "report_fidelity": null,
      "reassembly_attempts": 0,
      "exit_gate_checked_at": null,
      "exit_gate_verdict": null
    },
    {
      "name": "assembly",
      "status": "not_started",
      "started_at": null,
      "completed_at": null,
      "evidence_files": [],
      "agent_spawns": [],
      "exit_gate_checked_at": null,
      "exit_gate_verdict": null
    }
  ],
  "claims": {
    "registry_path": null,
    "claim_ids": [],
    "count": 0
  },
  "weaknesses": {
    "filed_ids": [],
    "falsifiable_ids": [],
    "dropped_unfalsifiable_ids": []
  },
  "invariants": {
    "coordinator_never_evaluated": true,
    "all_evidence_fresh_this_session": true,
    "every_claim_has_credibility_verdict": false,
    "every_weakness_has_severity_verdict": false,
    "every_unfalsifiable_weakness_dropped_from_report": true
  },
  "termination": null,
  "cancel_time_iso": null,
  "resume_from_stage": null
}
```

## Stage Status Enum

- `not_started` — stage hasn't begun.
- `in_progress` — agents spawned or exit-gate not yet checked.
- `gate_checking` — all agents returned; exit-gate evaluation in progress.
- `complete` — exit-gate passed.
- `failed_quorum` — parallel-critique stage only: < 3/4 dimensions returned parseable output; triggers `insufficient_evidence_to_review` termination.
- `failed_rework` — rationalization-audit only: `REPORT_FIDELITY|compromised`; triggers re-assembly loop.
- `cancelled` — user cancelled mid-stage.

## Agent Spawn Record Schema

Used inside every stage's `agent_spawns[]`:

```json
{
  "agent_role": "claim_extractor | viability_critic | competition_critic | structural_critic | evidence_critic | fact_check_research | credibility_judge | severity_judge | landscape_judge | rationalization_auditor",
  "agent_id": "<assigned by Task spawn>",
  "model_tier": "haiku|sonnet|opus",
  "spawn_time_iso": "<ISO>",
  "completion_time_iso": "<ISO or null>",
  "input_files": ["<path>", "<path>"],
  "output_file": "<path>",
  "status": "spawned | completed | spawn_failed | timed_out | unparseable_output",
  "structured_output_markers_present": true,
  "blind_verdict_protocol": {
    "severity_claim_stripped": true | null,
    "fact_check_proposed_verdict_stripped": true | null
  }
}
```

## Generation Counter

Optimistic-concurrency version counter. Every write of `state.json` increments `generation`. On read:
1. Parse JSON.
2. Compare `generation` against the value from the last read in the same coordinator turn. Must be strictly greater.
3. If not: a concurrent write happened → re-read and retry the intended update.

## Lock File

On run start: write `proposal-review-{run_id}.lock` in CWD with coordinator timestamp + PID. On clean exit: delete. On startup: if a lock file from the same `run_id` exists < 15 min old, prompt: `Another proposal-review run appears active. Resume (r) / abort (a) / force (f)?` — require explicit user response. No silent takeover.

## Iron-Law Gate (Pre-Final-Report)

Before writing `REPORT.md` and setting `termination`:

```
Step 1. Read state.json; confirm current_stage == "assembly" and status in {"gate_checking"}.
Step 2. Confirm every prior stage has status in {"complete", "failed_quorum"}.
Step 3. For every claim in claims.claim_ids:
          - Confirm judges/credibility/claim-{NNN}-verdict.md exists on disk.
          - Confirm file contains STRUCTURED_OUTPUT_START/END markers.
          - Confirm VERDICT_FINAL line is present.
Step 4. For every weakness in weaknesses.filed_ids:
          - Confirm judges/severity/weakness-{dim}-{NNN}-verdict.md exists on disk.
          - Confirm file has markers + FALSIFIABLE + SEVERITY_FINAL lines.
Step 5. Confirm judges/landscape-verdict.md exists with markers.
Step 6. Confirm judges/rationalization-audit.md exists with REPORT_FIDELITY|clean.
          If REPORT_FIDELITY|compromised and reassembly_attempts < 2: loop back to assembly.
          If reassembly_attempts >= 2: terminate with insufficient_evidence_to_review.
Step 7. Confirm every weakness with FALSIFIABLE|no is listed in weaknesses.dropped_unfalsifiable_ids
         and NOT listed in the draft REPORT.md's Weaknesses section.
Step 8. Only if 1-7 all pass: write REPORT.md, set termination, current_stage = null,
         generation += 1, write state.json.
```

Any failing check: do NOT write the final report. Log to `logs/judge_decisions.jsonl` with `{verdict: rejected, reason}` and halt with an operator-visible summary of what is missing.

## Resume Protocol

On re-invocation in the same CWD:

1. Check for `proposal-review-*.lock` files; if one matches an existing `proposal-review-{run_id}/` directory, prompt: `Resume run {run_id} from stage {current_stage}? [y/N]`
2. If user confirms:
   - Read `state.json`.
   - Verify `proposal_text_sha256` matches SHA256 of stored `proposal_text` (tamper check). Mismatch → `TASK_TAMPERED`, halt.
   - Verify `core_claim_sha256` matches. Mismatch → `CORE_CLAIM_TAMPERED`, halt.
   - Set `resume_from_stage = current_stage`.
   - For the current stage, examine `agent_spawns[]`:
     - Entries with `status: spawned` and no `completion_time_iso`: check if `output_file` exists on disk.
       - Exists + has markers → mark `completed`; re-run any coordinator bookkeeping that depended on this output.
       - Missing → mark `timed_out` (do NOT re-spawn silently — agents are one-shot; spawn a fresh replacement if the stage requires it).
     - Entries with `status: spawn_failed`: re-spawn (fresh `spawn_time_iso`).
3. If user declines: offer `rm -rf proposal-review-{run_id}/` (explicit, not default) or start a new run with a fresh `run_id`.

## State Invariants (Checked At Every Read)

1. `generation` is strictly monotonic across writes in the same session.
2. `proposal_text_sha256` matches SHA256 of `proposal_text`. Mismatch → halt with `TASK_TAMPERED`.
3. `core_claim_sha256` matches SHA256 of `core_claim`. Mismatch → halt with `CORE_CLAIM_TAMPERED`.
4. `stages[]` has exactly 6 entries in order: claim-extraction, parallel-critique, fact-check, independent-judges, rationalization-audit, assembly.
5. `current_stage` matches the only stage with `status: "in_progress"` (unless `termination` is set).
6. Every `stages[<i>].evidence_files` path exists on disk AND has structured-output markers (for files that claim them).
7. `invariants.coordinator_never_evaluated` — spot-check: every verdict file must have `agent_role != coordinator` in its spawn record.
8. `invariants.every_claim_has_credibility_verdict` — true iff every `claims.claim_ids` entry has a matching file in `judges/credibility/`.
9. `invariants.every_weakness_has_severity_verdict` — true iff every `weaknesses.filed_ids` entry has a matching file in `judges/severity/`.
10. `invariants.every_unfalsifiable_weakness_dropped_from_report` — any weakness with `FALSIFIABLE|no` in its severity verdict MUST be in `weaknesses.dropped_unfalsifiable_ids` AND absent from REPORT.md. If present in REPORT.md → invariant violation.
11. `termination` is either null or one of the four enum values: `high_conviction_review | mixed_evidence | insufficient_evidence_to_review | declined_unfalsifiable`.

Any invariant violation: log to `logs/judge_decisions.jsonl` with `event: invariant_violation`; halt run pending operator input; surface a human-readable summary.

## State Update Patterns — Reference

### Before spawning any agent

```json
"stages[<idx>].agent_spawns": [
  ...existing,
  {
    "agent_role": "viability_critic",
    "spawn_time_iso": "<ISO>",
    "input_files": ["critiques/viability-angle.md", "proposal.md"],
    "output_file": "critiques/viability-critique.md",
    "status": "spawned",
    "structured_output_markers_present": false,
    "blind_verdict_protocol": { "severity_claim_stripped": null, "fact_check_proposed_verdict_stripped": null }
  }
],
"generation": += 1
```

Then call `Task` / `Agent`. If the call errors: update the just-added record to `status: "spawn_failed"`, `spawn_time_iso: null`, `failure_reason: <error>`.

### After agent completes

```json
"stages[<idx>].agent_spawns[<i>].completion_time_iso": "<ISO>",
"stages[<idx>].agent_spawns[<i>].status": "completed",
"stages[<idx>].agent_spawns[<i>].structured_output_markers_present": true,
"generation": += 1
```

### Before handing a critic's file to Judge B (blind severity protocol)

```json
"stages[<judges_idx>].agent_spawns[<i>].blind_verdict_protocol": {
  "severity_claim_stripped": true,
  "fact_check_proposed_verdict_stripped": null
}
```
The coordinator creates `judges/inputs/weakness-{dim}-{NNN}.md` by copying the critic file and removing the `SEVERITY_CLAIM_BLOCK_START` → `SEVERITY_CLAIM_BLOCK_END` region.

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
"termination": "high_conviction_review | mixed_evidence | insufficient_evidence_to_review | declined_unfalsifiable",
"stages[<current_idx>].status": "complete" | "cancelled" | "failed_quorum",
"current_stage": null,
"generation": += 1
```

## State Never Written By Critics or Judges

Critics and judges write their own output files (critique, verdict, evidence). They do NOT write `state.json`. Only the coordinator updates `state.json`, reading structured outputs from those files and transcribing conclusions into the state invariants. This keeps write authority in one process and avoids races on `state.json`.
