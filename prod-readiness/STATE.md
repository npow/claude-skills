# State Management

Pure file-based state. No MCP state tools. All persistence lives in `prod-readiness-{run_id}/` in the current working directory.

## Contents
- [Directory layout](#directory-layout)
- [state.json schema](#statejson-schema)
- [Generation counter](#generation-counter)
- [Lock file](#lock-file)
- [Iron-law evidence gate](#iron-law-evidence-gate)
- [Resume protocol](#resume-protocol)
- [State invariants](#state-invariants-checked-at-every-read)
- [Reference patterns](#state-updates--reference-patterns)

---

## Directory layout

```
prod-readiness-{run_id}/
├── state.json                    # authoritative state, generation-versioned
├── stack.json                    # detected stack + patterns, written once
├── scorecard.md                  # final report, written at Phase 4
├── risks.md                      # user-authored accept-rationale (optional)
├── evidence/
│   ├── 1/
│   │   ├── input.md              # judge input (written before spawn)
│   │   ├── manifest.md           # candidate files (coordinator-compiled)
│   │   ├── verdict.md            # judge output
│   │   └── applicability-verdict.md  # optional — only if contested
│   ├── 2/
│   │   └── ...
│   ├── ...
│   └── 24/
│       └── ...
└── logs/
    ├── judge_spawns.jsonl        # one line per spawn event
    └── gate_decisions.jsonl      # one line per evidence-gate evaluation
```

---

## state.json schema

```json
{
  "run_id": "20260416-153022",
  "skill": "prod-readiness",
  "created_at": "2026-04-16T15:30:22Z",
  "cwd": "/absolute/path/to/project",
  "invocation": {
    "cli_args": "<original args if any>",
    "diff_mode": false,
    "diff_ref": null
  },
  "generation": 0,
  "stack": {
    "detected_at": "2026-04-16T15:30:25Z",
    "language": "typescript",
    "framework": "express",
    "package_manager": "npm",
    "container_tooling": "docker",
    "k8s_present": true,
    "ci_present": true,
    "project_type": "http_service"
  },
  "current_phase": "detect | compile | spawn_judges | verify_evidence | score | complete",
  "items": {
    "1": {
      "name": "Health Check Endpoints",
      "severity": "critical",
      "category": "Reliability",
      "status": "not_started | spawned | completed | spawn_failed | timed_out | scan_incomplete",
      "judge_id": "judge-1-health",
      "model_tier": "haiku",
      "spawn_time_iso": null,
      "completion_time_iso": null,
      "spawn_input_files": ["evidence/1/input.md", "evidence/1/manifest.md"],
      "output_file": "evidence/1/verdict.md",
      "structured_output_markers_present": false,
      "searches_attempted": [],
      "verdict": null,
      "evidence_path": null,
      "evidence_excerpt": null,
      "evidence_excerpt_verified": false,
      "reason_code": null,
      "applicability_judge_id": null,
      "applicability_verdict": null,
      "retry_count": 0,
      "written_by": null
    },
    "2": { "... same shape" },
    "...": "... through item 24"
  },
  "applicability_flags": {
    "20": "contested",
    "22": "contested"
  },
  "invariants": {
    "coordinator_never_assigned_pass_fail": true,
    "every_pass_has_verified_excerpt": true,
    "every_fail_ran_three_searches": true,
    "no_critical_accepted_without_signer": true
  },
  "score": {
    "pass_count": 0,
    "warn_count": 0,
    "fail_count": 0,
    "na_count": 0,
    "scan_incomplete_count": 0,
    "applicable_checks": null,
    "percentage": null,
    "grade": null
  },
  "termination": null,
  "termination_time_iso": null,
  "resume_from_phase": null,
  "lock_file": "prod-readiness-{run_id}.lock"
}
```

## Enums

### `current_phase`
- `detect` — detecting stack (Phase 0 in SKILL.md)
- `compile` — writing judge inputs (Phase 1)
- `spawn_judges` — spawning all 24 item judges in parallel (Phase 2)
- `verify_evidence` — coordinator verifying every `pass`/`warn` excerpt exists verbatim in the cited file (Phase 3)
- `score` — computing score + drafting scorecard (Phase 4)
- `complete` — final report delivered

### `items[<id>].status`
- `not_started` — judge not yet spawned
- `spawned` — judge spawned, no output yet
- `completed` — judge produced output; verdict may or may not have passed evidence verification
- `spawn_failed` — Agent call errored; retry once
- `timed_out` — 120s elapsed with no output file; does NOT auto-retry silently
- `scan_incomplete` — output received but did not pass verification (missing markers, missing excerpt, hallucinated excerpt, etc.)

### `items[<id>].verdict`
- `null` — not yet assigned
- `pass` | `warn` | `fail` | `na` — the four real verdicts (assigned by judge, verified by coordinator)
- `scan_incomplete` — verdict absent after retries

### `termination`
- `ready_for_prod`
- `partial_with_accepted_risks`
- `blocked`
- `scan_incomplete`
- `scan_inconclusive`

---

## Generation counter

Optimistic-concurrency version counter. Every write of `state.json` increments `generation`. On read:
1. Parse JSON.
2. Compare `generation` against the value from the last read in the same coordinator turn. Must be strictly greater.
3. If not: a concurrent write happened → re-read and retry the intended update.

Atomic writes only: write to `state.json.tmp`, then `rename` to `state.json`. Partial writes are undefined behavior; on resume, a `.tmp` file older than 5 seconds is unlinked and the last good `state.json` is reused.

---

## Lock file

On run start: write `prod-readiness-{run_id}.lock` in CWD with coordinator timestamp + PID. On clean exit: delete it. On startup, if a lock file from the same `run_id` exists < 15 min old, surface:

```
Another prod-readiness run appears active. Resume (r) / abort (a) / force (f)?
```

Require explicit user response. No silent takeover.

---

## Iron-law evidence gate

Before assigning any `pass` or `warn` verdict to `state.items[<id>].verdict`, the coordinator MUST run this gate:

```
Step 1. Read evidence/{item_id}/verdict.md.
Step 2. Confirm STRUCTURED_OUTPUT_START and STRUCTURED_OUTPUT_END markers exist.
Step 3. Parse the ITEM line; extract evidence_path and evidence_excerpt.
Step 4. Confirm evidence_path is formatted as `relative/path:line`. If not: reject.
Step 5. Open the file at evidence_path. Confirm it exists and line number is within the file length.
Step 6. Read ±1 line around the cited line. Confirm evidence_excerpt substring is present
        (after newline escape normalization).
Step 7. Parse the SEARCHES line. Confirm exactly 3 patterns were listed. If fewer: reject.
Step 8. Only if 1-7 all pass: set items[<id>].verdict, items[<id>].evidence_excerpt_verified = true,
        generation += 1, write state.json.
```

Any failing step → set `status: "scan_incomplete"`, log to `logs/gate_decisions.jsonl`, re-spawn the judge ONCE. On second failure, lock in `scan_incomplete`.

For `fail` verdicts: the gate verifies the SEARCHES line shows three patterns attempted; if not, downgrade to `scan_incomplete`.

For `na` verdicts: the gate requires a companion `applicability-verdict.md` whose `APPLICABILITY` line is `does_not_apply`. Absent → downgrade to `scan_incomplete`.

---

## Resume protocol

On re-invocation in the same CWD:

1. Check for `prod-readiness-*.lock` files; if one matches an existing `prod-readiness-{run_id}/` directory, prompt: `Resume run {run_id} from phase {current_phase}? [y/N]`
2. If user confirms:
   - Read `state.json`.
   - For `current_phase`:
     - `detect` → restart Phase 0.
     - `compile` → restart Phase 1 (writing judge inputs is idempotent; overwrite).
     - `spawn_judges` → for each item with `status: "spawned"` and no output file on disk:
       - If spawn was < 120s ago: wait (file may still arrive).
       - Else: mark `timed_out`; do NOT auto-respawn. Let the operator decide.
     - For each item with `status: "spawned"` and output file present: mark `completed` and re-run the evidence gate.
     - For each item with `status: "completed"` but `evidence_excerpt_verified: false`: re-run the evidence gate.
     - Re-spawn any items with `status: "spawn_failed"` and `retry_count < 1`.
     - `verify_evidence` → re-run the gate for every `pass`/`warn` item.
     - `score` → re-compute score from current verdicts and re-draft scorecard.
3. If user declines: offer `rm -rf prod-readiness-{run_id}/` (explicit, not default) or start a new run with a fresh `run_id`.

---

## State invariants (checked at every read)

1. `generation` strictly monotonic across writes in the same session.
2. `items` has exactly 24 entries keyed `"1"`..`"24"`.
3. `current_phase` is one of the enum values.
4. Every `items[<id>].verdict` is either `null` or one of the five values.
5. Every `items[<id>]` with `verdict: "pass"` or `"warn"` has `evidence_excerpt_verified: true`.
6. Every `items[<id>]` with `verdict: "fail"` has `len(searches_attempted) >= 3`.
7. Every `items[<id>]` with `verdict: "na"` has `applicability_verdict: "does_not_apply"`.
8. `invariants.coordinator_never_assigned_pass_fail`: every items[<id>] non-null verdict was set from a parsed judge ITEM line. If the coordinator wrote a verdict without reading a verdict.md file: invariant violated, halt.
9. `termination` is either null or one of the five enum values.
10. If `termination == "ready_for_prod"`: zero `fail` verdicts on Critical/High items AND zero `scan_incomplete` entries.
11. If `termination == "partial_with_accepted_risks"`: every `warn`/`fail` has a matching ACCEPT line in `risks.md` OR the item severity is Medium/Low. Critical FAILs never permit this termination.

Any invariant violation: log to `logs/gate_decisions.jsonl` with `event: invariant_violation`; halt run pending operator input; surface a human-readable summary.

---

## State updates — reference patterns

### Before spawning a judge

```json
"items.<id>.spawn_time_iso": "<ISO>",
"items.<id>.status": "spawned",
"items.<id>.judge_id": "judge-<id>-<slug>",
"items.<id>.spawn_input_files": ["evidence/<id>/input.md", "evidence/<id>/manifest.md"],
"items.<id>.output_file": "evidence/<id>/verdict.md",
"generation": += 1
```

Write state.json, THEN call Agent. If the call errors: update the entry to `status: "spawn_failed"`, increment `retry_count`. If `retry_count >= 1`: leave as `spawn_failed` and let the coordinator surface it.

### After judge completes (output file on disk)

```json
"items.<id>.completion_time_iso": "<ISO>",
"items.<id>.status": "completed",
"items.<id>.structured_output_markers_present": true,
"items.<id>.searches_attempted": ["primary", "framework", "fallback"],
"generation": += 1
```

### After evidence-gate verification passes

```json
"items.<id>.verdict": "pass|warn|fail|na",
"items.<id>.evidence_path": "src/server/routes/health.ts:14",
"items.<id>.evidence_excerpt": "router.get('/healthz', healthCheck);",
"items.<id>.evidence_excerpt_verified": true,
"items.<id>.reason_code": "full_impl_detected",
"items.<id>.written_by": "judge-1-health",
"generation": += 1
```

### After evidence-gate verification fails

```json
"items.<id>.status": "scan_incomplete",
"items.<id>.reason_code": "hallucinated_excerpt|missing_evidence_excerpt|...",
"items.<id>.retry_count": += 1,
"generation": += 1
```

Then re-spawn the judge once (resetting `status: "not_started"`). On second failure, lock in `scan_incomplete`.

### On termination

```json
"termination": "ready_for_prod|partial_with_accepted_risks|blocked|scan_incomplete|scan_inconclusive",
"termination_time_iso": "<ISO>",
"current_phase": "complete",
"score.pass_count": <n>,
"score.warn_count": <n>,
"score.fail_count": <n>,
"score.na_count": <n>,
"score.scan_incomplete_count": <n>,
"score.applicable_checks": 24 - na_count - scan_incomplete_count,
"score.percentage": <int>,
"score.grade": "A|B|C|D|F",
"generation": += 1
```

## State never written by judges

Judges communicate via their output files in `evidence/{item_id}/verdict.md`. The coordinator reads those files and translates them into state writes. This keeps state-write authority in one process and avoids lock races on `state.json`. Judge output files ARE written by judges to disk — but the coordinator parses them before registering anything in `state.items[<id>]`.
