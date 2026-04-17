# Output Formats

## Task Spec JSON Schema

Each task submitted to `/parallel-exec` MUST conform to this schema. Specs are written to `parallel-exec-{run_id}/specs/{task_id}.json` before dispatch. Missing required fields → spec rejected at input validation.

```json
{
  "task_id": "t_001",
  "prompt": "Full instructions for the subagent. Include target files, acceptance criteria, and 'do not modify' boundaries. The subagent MUST be told to run the verification_command and write output to verify/{task_id}.{stdout,stderr,exit}.",
  "model_tier": "haiku | sonnet | opus",
  "verification_command": "npm test -- path/to/affected.test.ts",
  "expected_output_pattern": "tests: \\d+ passed",
  "depends_on": ["t_000"],
  "touches_paths": ["src/auth/login.ts", "src/auth/session.ts"],
  "run_in_background": false,
  "timeout_seconds": 600
}
```

### Field reference

| Field | Type | Required | Meaning |
|---|---|---|---|
| `task_id` | string, `^t_\d{3}$` | yes | Stable ID within this run. Used everywhere. |
| `prompt` | string | yes | Full subagent instruction. Must include target files and boundaries. |
| `model_tier` | enum: `haiku`, `sonnet`, `opus` | yes | Tier classification from SKILL.md tier table. |
| `verification_command` | string | yes | Shell command to execute after work completes. No exceptions. |
| `expected_output_pattern` | string (regex) | yes | Regex that must match `verify/{task_id}.stdout`. |
| `depends_on` | array of task_id | yes | May be empty `[]`; must not be omitted. Cycles are rejected. |
| `touches_paths` | array of strings | yes | Files the task may modify. Used by convergence checker for conflict detection. |
| `run_in_background` | boolean | no (default false) | `true` for long builds/test suites. |
| `timeout_seconds` | integer | no (default 600) | Per-task timeout for the Task tool. |

### Example: three independent tasks

```json
[
  {
    "task_id": "t_001",
    "prompt": "Add `export type Config` to src/types.ts using the shape from docs/config-shape.md. Do not modify any other file.",
    "model_tier": "haiku",
    "verification_command": "npx tsc --noEmit",
    "expected_output_pattern": "^$",
    "depends_on": [],
    "touches_paths": ["src/types.ts"],
    "run_in_background": false,
    "timeout_seconds": 120
  },
  {
    "task_id": "t_002",
    "prompt": "Implement POST /api/users per specs/users-api.md. Target: src/api/users.ts. Add tests at src/api/users.test.ts covering the 4 scenarios in the spec.",
    "model_tier": "sonnet",
    "verification_command": "npm test -- src/api/users.test.ts",
    "expected_output_pattern": "Tests:\\s+4 passed",
    "depends_on": [],
    "touches_paths": ["src/api/users.ts", "src/api/users.test.ts"],
    "run_in_background": false,
    "timeout_seconds": 600
  },
  {
    "task_id": "t_003",
    "prompt": "Add integration tests for the auth middleware covering the 4 scenarios in docs/auth.spec.md. Target: tests/integration/auth.integration.test.ts. Do NOT modify middleware source.",
    "model_tier": "sonnet",
    "verification_command": "npm run test:integration -- auth",
    "expected_output_pattern": "Tests:\\s+4 passed",
    "depends_on": [],
    "touches_paths": ["tests/integration/auth.integration.test.ts"],
    "run_in_background": true,
    "timeout_seconds": 900
  }
]
```

---

## Per-Task Result File

Each subagent writes to `parallel-exec-{run_id}/results/{task_id}.md`. Files without `STRUCTURED_OUTPUT_START` / `STRUCTURED_OUTPUT_END` markers are treated as failed (not partially consumed).

```markdown
# Task {task_id} Result
**Spec:** parallel-exec-{run_id}/specs/{task_id}.json
**Subagent tier:** {tier}
**Completed at:** {iso timestamp}

## Summary
[2-4 sentences describing what was done. This is NOT the label — the convergence checker assigns the label.]

## Files modified
- path/to/file_a — [one-line change description]
- path/to/file_b — [one-line change description]

## Verification run
```
$ {verification_command}
[captured output, trimmed to last 200 lines if long]
exit: {exit_code}
```

Raw output paths:
- `verify/{task_id}.stdout`
- `verify/{task_id}.stderr`
- `verify/{task_id}.exit`

## Notes
[Optional — anything the reviewer should know, e.g. "skipped unrelated pre-existing lint errors", "had to stub method foo because bar() is unimplemented"]

STRUCTURED_OUTPUT_START
TASK_ID|{task_id}
SUBAGENT_CLAIM|completed|failed|partial
VERIFICATION_EXIT_CODE|{integer}
VERIFICATION_STDOUT_PATH|verify/{task_id}.stdout
FILES_MODIFIED|path_a,path_b,path_c
NOTES|{one-line free-text note, optional}
STRUCTURED_OUTPUT_END
```

### Structured block rules

- Exactly one of `completed`, `failed`, `partial` for `SUBAGENT_CLAIM`.
- `VERIFICATION_EXIT_CODE` must be a parseable integer. Non-integer → coordinator treats as `unverified`.
- `FILES_MODIFIED` is a comma-separated list of file paths. Empty is allowed (coordinator will flag: "claims completed but modified nothing").
- `NOTES` is optional; single line; no pipes.
- Pipe characters inside a field are not escaped; parser splits on first N-1 pipes, last field absorbs the rest.

---

## Four Per-Task Labels (assigned by convergence checker)

The convergence checker is the sole authority for these labels. The coordinator does not assign them.

| Label | When the checker assigns it | Required evidence |
|---|---|---|
| `passed_with_evidence` | First-run verification exit 0 AND rerun exit 0 AND stdout matches `expected_output_pattern` AND no sibling path overlap. | `verify/{id}.exit` (both runs) + `verify/{id}.stdout` + path-overlap analysis. |
| `failed_with_error` | Exit code nonzero OR pattern not matched OR subagent self-reported `failed` OR modified files outside `touches_paths`. | Exit code from disk; stdout/stderr; `FILES_MODIFIED` vs `touches_paths` diff. |
| `conflicted_with_sibling` | Task and another task without a `depends_on` edge both modified the same path, AND actual file contents do not match at least one task's claimed diff. | Path overlap + git-diff (or file content) comparison. |
| `unverified` | `results/{id}.md` missing, malformed, structured markers absent, verification rerun disagrees with first run, or required fields empty. | Fail-safe. Coordinator does NOT fall back to "probably passed." |

---

## Convergence-Check Output Format

The convergence-checker agent writes to `parallel-exec-{run_id}/convergence/convergence-check.md`. This file is the authoritative per-task classification.

```markdown
# Convergence Check — parallel-exec {run_id}
**Completed at:** {iso timestamp}
**Tasks inspected:** {N}
**Independent reruns performed:** {N}

## Per-task verdicts

### t_001 — {label}
- Subagent self-claim: `completed | failed | partial`
- First-run exit: {code}; stdout match: `yes | no`
- Rerun exit: {code}; stdout match: `yes | no`
- Files modified vs touches_paths: `within bounds | out-of-bounds: path_x`
- Sibling overlap: `none | t_003 overlaps on src/auth/session.ts`
- Verdict reason: [one-line rationale]
- Evidence paths: verify/t_001.stdout, verify/t_001.exit, results/t_001.md

### t_002 — {label}
[...same structure per task]

## Detected conflicts

### Conflict 1
- Tasks: t_002, t_003
- Overlapping path: src/auth/session.ts
- Dependency edge in graph: `none`
- Diff consistency: `inconsistent` — t_002 renames `getUserId` → `getViewerId`; t_003 keeps the old name in call sites
- Both tasks labeled: `conflicted_with_sibling`

## Detected flakiness

### Flaky verification
- Task t_004: first-run exit=0 (Tests: 7 passed); rerun exit=1 (Tests: 6 passed, 1 failed due to setup race)
- Labeled: `unverified` with reason `flaky_verification`

## Aggregate

STRUCTURED_OUTPUT_START
RUN_ID|{run_id}
TASKS_TOTAL|{N}
PASSED_WITH_EVIDENCE|{count}|{task_id_csv}
FAILED_WITH_ERROR|{count}|{task_id_csv}|{reason_csv}
CONFLICTED_WITH_SIBLING|{count}|{task_id_csv}|{path_csv}
UNVERIFIED|{count}|{task_id_csv}|{reason_csv}
AGGREGATE_STATUS|all_passed|partial_with_failures|blocked_on_conflicts|unverified_batch|convergence_check_failed
CONVERGENCE_CHECKER_NOTES|{one-line summary}
STRUCTURED_OUTPUT_END
```

### Structured block field rules

- `PASSED_WITH_EVIDENCE|{count}|{task_id_csv}` — count and comma-separated task IDs. Count must equal number of IDs; mismatch → coordinator treats as `convergence_check_failed`.
- `FAILED_WITH_ERROR|{count}|{task_id_csv}|{reason_csv}` — per-ID reasons as a parallel CSV. Reasons are short tokens: `nonzero_exit`, `pattern_mismatch`, `self_reported_failed`, `out_of_bounds_modification`, etc.
- `CONFLICTED_WITH_SIBLING|{count}|{task_id_csv}|{path_csv}` — paths CSV parallel to the ID CSV. Use `+` to join multiple paths for one task (e.g., `path_a+path_b`).
- `UNVERIFIED|{count}|{task_id_csv}|{reason_csv}` — reasons: `missing_result_file`, `missing_structured_markers`, `flaky_verification`, `required_field_empty`, etc.
- `AGGREGATE_STATUS` — exactly one of the five enumerated values. No freeform status strings.

### Unparseable convergence output

If `convergence-check.md` is missing or lacks `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END`:

- Coordinator sets `aggregate_status: convergence_check_failed`.
- Coordinator prints all per-task evidence paths for manual review.
- No task is labeled `passed_with_evidence` by the coordinator — labels remain null.
- The coordinator does NOT fall back to reading the subagent self-claims as authoritative.

---

## Coordinator Aggregate Report (printed to user)

After parsing the convergence block, the coordinator prints:

```
parallel-exec {run_id} complete
- passed_with_evidence:   {count} ({task_id_csv})
- failed_with_error:      {count} ({task_id_csv}) — reasons: {short}
- conflicted_with_sibling:{count} ({task_id_pairs}) — paths: {short}
- unverified:             {count} ({task_id_csv}) — reasons: {short}
- aggregate_status:       {one of five labels}

Evidence files:
- parallel-exec-{run_id}/convergence/convergence-check.md
- parallel-exec-{run_id}/state.json
- Per-task results: parallel-exec-{run_id}/results/
- Per-task verify: parallel-exec-{run_id}/verify/

Next step recommendation:
- all_passed → commit / merge / proceed
- partial_with_failures → inspect failed tasks; re-run or accept
- blocked_on_conflicts → reconcile conflicting paths manually; re-run affected tasks
- unverified_batch → investigate missing/flaky evidence before proceeding
- convergence_check_failed → run convergence checker manually; do NOT claim success
```

Never print "all tasks complete" or "work done" as a headline — only the labeled counts and the enumerated aggregate status.
