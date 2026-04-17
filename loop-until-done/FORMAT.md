# Output Formats

## PRD: `loop-{run_id}/prd.json`

Structured JSON. Every criterion has executable verification and a concrete match pattern. No prose-only criteria.

```json
{
  "task": "Original task description from Step 0",
  "generated_at": "2026-04-16T15:30:22Z",
  "locked": true,
  "prd_sha256": "sha256-hex-of-canonicalized-stories-array",
  "stories": [
    {
      "story_id": "US-001",
      "subject": "Add flag detection helpers",
      "priority": 1,
      "status": "pending",
      "rationale": "Foundational — other stories depend on these helpers",
      "acceptance_criteria": [
        {
          "id": "AC-001-1",
          "criterion": "detectNoPrdFlag('ralph --no-prd fix') returns true; detectNoPrdFlag('ralph fix this') returns false",
          "verification_command": "npm test -- --testPathPattern=flag-detection.test.ts",
          "expected_output_pattern": "Tests:       4 passed",
          "passes": false,
          "last_verified_at": null
        },
        {
          "id": "AC-001-2",
          "criterion": "TypeScript compiles with no errors",
          "verification_command": "npm run build 2>&1",
          "expected_output_pattern": "/build succeeded|Compiled successfully|tsc --noEmit.*exit 0/",
          "passes": false,
          "last_verified_at": null
        }
      ],
      "created_iteration": 1,
      "last_modified_iteration": null,
      "iterations_spent": 0,
      "files_modified": []
    }
  ]
}
```

### Story status enum

| Value | Meaning |
|---|---|
| `pending` | Not yet selected for an iteration |
| `in_progress` | Currently being worked on |
| `passed` | Every criterion `passes: true` with fresh `last_verified_at` |
| `blocked` | Explicit `STORY_INFEASIBLE` note filed OR 3+ consecutive failing iterations |

### Acceptance criterion fields (required, all of them)

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Format `AC-{story_num}-{criterion_num}`; stable for the run |
| `criterion` | string | yes | Human-readable statement; MUST be objectively verifiable |
| `verification_command` | string | yes | Executable shell command; no prompts, no human input |
| `expected_output_pattern` | string | yes | Substring match by default; regex if wrapped in `/.../` |
| `passes` | boolean | yes | Set by Step 5 only after a successful match |
| `last_verified_at` | ISO string or null | yes | Timestamp of the most recent verification run; required > iteration_started_at for `passes: true` to count |

**Forbidden patterns** (rejected by the falsifiability judge in Step 2b):
- `expected_output_pattern: "success"` or `"no errors"` or `"it works"` — a broken implementation could emit these
- `verification_command` that prints a literal "PASS" regardless of outcome (test gaming)
- Criterion phrased subjectively ("code is clean", "reads nicely")
- Criterion requiring human observation ("the UI looks right")

### Append-only semantics after lock

Once `locked: true` and `prd_sha256` are set (Step 2d), existing criteria MUST NOT be modified. The coordinator may:
- Append new stories (subject to falsifiability gate on first iteration)
- Update `status`, `passes`, `last_verified_at`, `iterations_spent`, `files_modified` on existing entries

It MAY NOT:
- Modify `criterion`, `verification_command`, or `expected_output_pattern` of a locked criterion
- Delete stories or criteria (stories move to `blocked`, they do not disappear)

## Progress Log: `loop-{run_id}/progress.jsonl`

One JSON object per line. Structured fields only. No freeform prose (freeform notes go in `progress.jsonl` as `event: "note"` entries with a structured `message` field).

```jsonl
{"event":"prd_drafted","iteration":1,"timestamp":"2026-04-16T15:30:45Z","story_count":5,"criteria_count":18}
{"event":"prd_falsifiability_judged","iteration":1,"timestamp":"2026-04-16T15:31:10Z","passed":15,"failed":3,"verdict_file":"judge/falsifiability-2026-04-16T15-31-10Z.md"}
{"event":"prd_revised","iteration":1,"timestamp":"2026-04-16T15:31:55Z","attempt":2,"failed_criteria":["AC-002-3","AC-004-1","AC-005-2"]}
{"event":"prd_locked","iteration":1,"timestamp":"2026-04-16T15:32:20Z","prd_sha256":"abc123..."}
{"event":"iteration_start","iteration":2,"timestamp":"2026-04-16T15:32:25Z","story_id":"US-001"}
{"event":"executor_dispatched","iteration":2,"timestamp":"2026-04-16T15:32:30Z","story_id":"US-001","tier":"sonnet","spawn_time_iso":"2026-04-16T15:32:30Z"}
{"event":"criterion_verified","iteration":2,"timestamp":"2026-04-16T15:35:10Z","story_id":"US-001","criterion_id":"AC-001-1","passes":true,"verify_output_path":"verify/AC-001-1-2.txt","matched_pattern":"Tests:       4 passed"}
{"event":"criterion_verified","iteration":2,"timestamp":"2026-04-16T15:35:25Z","story_id":"US-001","criterion_id":"AC-001-2","passes":false,"verify_output_path":"verify/AC-001-2-2.txt","matched_pattern":null,"reason":"pattern_not_matched"}
{"event":"story_passed","iteration":3,"timestamp":"2026-04-16T15:42:00Z","story_id":"US-001","files_modified":["src/flags.ts","tests/flag-detection.test.ts"]}
{"event":"reviewer_spawned","iteration":8,"timestamp":"2026-04-16T16:12:00Z","pass":"spec_compliance","critic":"architect","spawn_time_iso":"2026-04-16T16:12:00Z"}
{"event":"reviewer_verdict","iteration":8,"timestamp":"2026-04-16T16:14:30Z","pass":"spec_compliance","verdict":"rejected","reason":"AC-003-1 output file is empty","feedback_file":"reviews/spec-compliance-8.md"}
{"event":"reviewer_verdict","iteration":8,"timestamp":"2026-04-16T16:14:45Z","pass":"code_quality","verdict":"approved","feedback_file":"reviews/code-quality-8.md"}
{"event":"deslop_ran","iteration":9,"timestamp":"2026-04-16T16:30:00Z","files_modified":["src/flags.ts"],"cleaner_output":"deslop/cleaner-output-9.md"}
{"event":"post_deslop_regression","iteration":9,"timestamp":"2026-04-16T16:31:00Z","status":"passed","criteria_re_verified":18}
{"event":"note","iteration":5,"timestamp":"2026-04-16T15:55:00Z","message":"STORY_INFEASIBLE: US-004 requires network access to staging; blocked pending credentials","story_id":"US-004"}
{"event":"run_complete","iteration":9,"timestamp":"2026-04-16T16:32:10Z","termination":"all_stories_passed","total_iterations":9,"reviewer_rejection_count":1}
```

### Event types (exhaustive)

| Event | Required fields |
|---|---|
| `prd_drafted` | `iteration`, `timestamp`, `story_count`, `criteria_count` |
| `prd_falsifiability_judged` | `iteration`, `timestamp`, `passed`, `failed`, `verdict_file` |
| `prd_revised` | `iteration`, `timestamp`, `attempt`, `failed_criteria` |
| `prd_locked` | `iteration`, `timestamp`, `prd_sha256` |
| `iteration_start` | `iteration`, `timestamp`, `story_id` |
| `executor_dispatched` | `iteration`, `timestamp`, `story_id`, `tier`, `spawn_time_iso` |
| `executor_completed` | `iteration`, `timestamp`, `story_id`, `files_modified` |
| `criterion_verified` | `iteration`, `timestamp`, `story_id`, `criterion_id`, `passes`, `verify_output_path`, `matched_pattern` or `reason` |
| `story_passed` | `iteration`, `timestamp`, `story_id`, `files_modified` |
| `story_blocked` | `iteration`, `timestamp`, `story_id`, `reason` |
| `reviewer_spawned` | `iteration`, `timestamp`, `pass`, `critic`, `spawn_time_iso` |
| `reviewer_verdict` | `iteration`, `timestamp`, `pass`, `verdict`, `reason` or null, `feedback_file` |
| `deslop_ran` | `iteration`, `timestamp`, `files_modified`, `cleaner_output` |
| `post_deslop_regression` | `iteration`, `timestamp`, `status`, `criteria_re_verified` |
| `note` | `iteration`, `timestamp`, `message`, optional `story_id` |
| `run_complete` | `iteration`, `timestamp`, `termination`, `total_iterations`, `reviewer_rejection_count` |

Unrecognized event types are permitted for extensibility but MUST include `iteration` and `timestamp`.

## Reviewer Verdict File: `loop-{run_id}/reviews/{pass}-{iter}.md`

Each reviewer (spec-compliance and code-quality) writes a file with structured markers at the tail. Free-text notes above the markers are advisory only; the coordinator reads ONLY between the markers.

```markdown
# Spec Compliance Review — Iteration 8

**Reviewer:** architect
**Inputs read:**
- loop-20260416-153022/prd.json
- loop-20260416-153022/verify/
- git diff HEAD~7..HEAD

## Findings (advisory)

{Free-text analysis here. The coordinator ignores this section.}

## Structured verdict

STRUCTURED_OUTPUT_START
VERDICT|rejected|AC-003-1 verification output file is empty — test was not run this iteration
REASON|DEF-001|US-003|AC-003-1|critical|Verification file verify/AC-003-1-8.txt is zero bytes; no evidence the command ran
REASON|DEF-002|US-003|AC-003-2|major|Criterion claims pass but last_verified_at is from iteration 5 (stale)
STRUCTURED_OUTPUT_END
```

### Parser rules

- The coordinator MUST locate `STRUCTURED_OUTPUT_START` and `STRUCTURED_OUTPUT_END` as exact-match lines
- Parse fields between markers using `|` as separator
- First pipe delimits the record type; remaining pipes delimit fields in the order specified
- Missing markers, duplicate markers, or no `VERDICT` line inside the markers → fail-safe: treat verdict as `rejected` with reason `unparseable_verdict`
- Multiple `VERDICT` lines → last one wins (but this is a reviewer bug; log warning)
- `REASON` lines are optional when `VERDICT|approved|`; required when `VERDICT|rejected|`
- Severity enum for `REASON`: `critical | major | minor`

### Record schemas

**VERDICT** — exactly one required:
```
VERDICT|approved|
VERDICT|rejected|{one_line_reason}
```

**REASON** — zero or more per verdict (required when rejected):
```
REASON|{defect_id}|{story_id_or_"quality"}|{criterion_id_or_"NONE"_or_file_path}|{severity}|{description}
```

For 7a (spec compliance): field 3 is `story_id`, field 4 is `criterion_id` (or `NONE` for story-level defects).
For 7b (code quality): field 3 is the literal `quality`, field 4 is the affected file path.

## Falsifiability Judge Verdict File: `loop-{run_id}/judge/falsifiability-{iso_timestamp}.md`

```markdown
# Falsifiability Judge — 2026-04-16T15:31:10Z

**Input:** loop-20260416-153022/prd.json

## Analysis (advisory)

{Free-text analysis here. Coordinator ignores this.}

## Structured verdict

STRUCTURED_OUTPUT_START
CRITERION|US-001|AC-001-1|pass|verification_command is executable; expected_output_pattern is a specific test-count string
CRITERION|US-001|AC-001-2|pass|regex anchored to build tool output tokens
CRITERION|US-002|AC-002-3|fail|expected_output_pattern is "success" — a stub that prints "success" would match; needs a specific assertion
CRITERION|US-004|AC-004-1|fail|verification_command requires network access to an internal staging URL with no offline fallback; not falsifiable in isolation
STRUCTURED_OUTPUT_END
```

### Parser rules

- Same marker discipline as reviewer verdicts
- `CRITERION|{story_id}|{criterion_id}|{pass|fail}|{rationale}`
- Every criterion in `prd.json` MUST appear exactly once in the judge output; missing criteria → fail-safe `fail` with reason `judge_omitted_criterion`
- Unparseable file → all criteria treated as `fail` (coordinator re-spawns the judge with the raw output attached as context)

## Verification Output File: `loop-{run_id}/verify/{criterion_id}-{iter}.txt`

Raw captured stdout + stderr from running the criterion's `verification_command`. No structured format — this is the evidence itself. The coordinator reads the full file and matches against `expected_output_pattern`.

- File MUST exist (zero bytes is a spec-compliance failure — the reviewer will catch it)
- File MUST be written AFTER the verification run, not before
- If the command exits non-zero, stderr is captured too — that is part of the evidence
- Prefix line (optional): `# verify: {criterion_id} iter={iter} cmd={shell_quoted_command} started={iso}` — useful for debugging, ignored by the pattern matcher

## Deslop Output File: `loop-{run_id}/deslop/cleaner-output-{iter}.md`

Raw output from `oh-my-claudecode:ai-slop-cleaner` (standard mode). Preserved verbatim for audit. The coordinator uses this to compute the list of files modified by the deslop pass.

## Final Summary: `loop-{run_id}/summary.md`

Written by a Sonnet subagent reading from `state.json`, `prd.json`, `progress.jsonl`. See SKILL.md Step 9 for the template.
