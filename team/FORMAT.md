# Output Formats

All structured outputs MUST be enclosed in `STRUCTURED_OUTPUT_START` / `STRUCTURED_OUTPUT_END` markers. Files without these markers are treated as failed (not partially consumed). Coordinator reads only structured lines.

## Handoff Doc Schema

Used in `team-{run_id}/handoffs/{stage}.md`. Required at every stage transition.

```markdown
# Handoff: {from-stage} → {to-stage}
**Run ID:** {run_id}
**Written by:** {agent_id}
**Date:** {ISO timestamp}

## Decided
- {decision with one-line rationale}
- {decision with one-line rationale}

## Rejected
- {alternative} | {reason for rejection}
- {alternative} | {reason for rejection}

## Risks
- {risk} | {mitigation — or "accepted" with rationale}
- {risk} | {mitigation}

## Files
- `path/to/file.ts` — {what changed}
- `path/to/test.ts` — {what was added}

## Remaining
- {concrete item the next stage must handle}
- {concrete item}

## Evidence
- `team-{run_id}/handoffs/plan-verdict.md` — {what was verified, verdict}
- `team-{run_id}/prd/falsifiability-verdict.md` — {verdict}

STRUCTURED_OUTPUT_START
HANDOFF_STAGE|{from_stage}|{to_stage}
HANDOFF_COMPLETE|yes
EVIDENCE_FILE|{relative_path}
EVIDENCE_FILE|{relative_path}
STRUCTURED_OUTPUT_END
```

**Required fields (no freeform prose allowed in lieu of these):** `Decided`, `Rejected`, `Risks`, `Files`, `Remaining`, `Evidence`. Empty section permitted ONLY with explicit `- None — {reason}` entry. Bare empty section fails schema check.

**Stage-specific required entries:**

| Stage | Extra required items in `Decided` | Extra required items in `Evidence` |
|---|---|---|
| plan | task decomposition rationale; dependency ordering | `handoffs/plan-verdict.md`; `handoffs/plan-adversarial-review.md` (if deep-design ran) |
| prd | scope boundary; acceptance criteria count + IDs | `prd/prd-final.md`; `prd/falsifiability-verdict.md`; `prd/critique.md` |
| exec | worker assignments; per-AC test coverage | `exec/{worker}-AC-{id}-red.txt`, `-green.txt`, `-verify.txt` for every AC; `verify/per-worker/` per-worker two-stage review outputs |
| verify | spec-compliance verdict summary; code-quality verdict summary | `verify/spec-compliance/defect-registry.md`; `verify/code-quality/review.md`; `verify/verdict.md` |
| fix | per-defect fix strategy; per-defect verifier verdicts | `fix/iter-{N}/defect-{id}-verdict.md` for every defect |

## Acceptance Criterion Schema

Used inside `prd/prd-final.md`. Every AC MUST have every field populated.

```markdown
### AC-{id}: {one-line criterion statement}
**Statement:** {precise criterion — no "should", no "probably"}
**Verification command:** `{executable shell command}`
**Expected output pattern:** {regex or exact-string fragment that must appear in verification output for pass}
**Owner (set in team-exec):** worker-{N}
**Status:** pending | in_progress | passed | blocked

STRUCTURED_OUTPUT_START
AC|{id}|{statement}|{verification_command}|{expected_output_pattern}
STRUCTURED_OUTPUT_END
```

The falsifiability judge rejects any AC where:
- `verification_command` is missing or not executable (no binary, no pipe target).
- `expected_output_pattern` is "no error" or empty (non-discriminating — passes on no-output too).
- Statement contains weasel words: "should", "probably", "typically", "ideally", "try to".

## Plan-Validator Verdict

Written by plan-validator agent to `handoffs/plan-verdict.md`.

```markdown
# Plan Verdict
**Validator:** {agent_id}
**Reviewed:** `handoffs/plan.md`

## Findings
{narrative findings; each issue described + severity}

STRUCTURED_OUTPUT_START
VERDICT|approved|rejected|rejected_with_rework
ISSUE|critical|{description}|{handoff_field_that_is_broken}
ISSUE|major|{description}|{handoff_field_that_is_broken}
ISSUE|minor|{description}|{handoff_field_that_is_broken}
MISSING_FIELD|{field_name}
REQUIRES_REWORK_OF|{stage_name}
STRUCTURED_OUTPUT_END
```

Valid `VERDICT` values: `approved` (proceed), `rejected_with_rework` (loop back to planner with issue file), `rejected` (terminate stage → `blocked_unresolved`).

## Critic Output (team-prd)

Written by independent critic to `prd/critique.md`.

```markdown
# PRD Critique
**Critic:** {agent_id}
**Reviewed:** `prd/prd-v{N}.md`

## Attack Report
{one section per finding}

### Finding: {title}
**Severity:** critical | major | minor
**Scenario:** {concrete scenario showing PRD is broken/ambiguous/underspecified}
**Root cause:** {the PRD section or missing section responsible}
**Suggested fix:** {what the PRD should say instead}

STRUCTURED_OUTPUT_START
FINDING|critical|{title}|{prd_section}
FINDING|major|{title}|{prd_section}
FINDING|minor|{title}|{prd_section}
STRUCTURED_OUTPUT_END
```

## Falsifiability Verdict

Written by falsifiability judge to `prd/falsifiability-verdict.md`.

```markdown
# Falsifiability Verdict
**Judge:** {agent_id}
**Reviewed:** `prd/prd-v{N}.md`

## Per-AC Verdicts
{narrative per AC}

STRUCTURED_OUTPUT_START
AC_VERDICT|AC-001|falsifiable|{rationale}
AC_VERDICT|AC-002|unfalsifiable|{what is missing}
AC_VERDICT|AC-003|conditionally_falsifiable|{condition that would make it falsifiable}
VERDICT_SUMMARY|{count_falsifiable}|{count_unfalsifiable}|{count_conditional}
STRUCTURED_OUTPUT_END
```

Any `unfalsifiable` blocks advancement. `conditionally_falsifiable` must be upgraded to `falsifiable` in PRD revision or blocks.

## Per-Worker Two-Stage Review (team-exec)

Written to `verify/per-worker/{worker_name}-task-{id}/`.

**Stage A — spec-compliance (deep-qa --diff output OR degraded fallback):**
See `verify/per-worker/{worker_name}-task-{id}/spec-compliance.md` with `STRUCTURED_OUTPUT` fields:
```
DEFECT|critical|{id}|{title}|{ac_reference}
DEFECT|major|{id}|{title}|{ac_reference}
DEFECT|minor|{id}|{title}|{ac_reference}
VERDICT|passed|failed_fixable|failed_unfixable
```

**Stage B — code-quality:**
See `verify/per-worker/{worker_name}-task-{id}/code-quality.md`:
```
DEFECT|critical|{id}|{title}|{file}:{line}
DEFECT|major|{id}|{title}|{file}:{line}
DEFECT|minor|{id}|{title}|{file}:{line}
VERDICT|passed|failed_fixable|failed_unfixable
```

Both files MUST be authored by separate independent agents (different spawn calls, not the same context). The lead verifies this by checking `spawn_time_iso` values differ.

## Stage-Level Verify Verdict

Written by independent verify-judge to `verify/verdict.md` (aggregates Stage A + Stage B for the full diff).

```markdown
# Verify Verdict (iteration {iter})
**Judge:** {agent_id}
**Reviewed:** `verify/spec-compliance/defect-registry.md`, `verify/code-quality/review.md`
**Diff:** `verify/diff.patch`

## Summary
{narrative summary of what passed, what failed}

STRUCTURED_OUTPUT_START
VERDICT|passed|failed_fixable|failed_unfixable
CRITICAL_COUNT|{n}
MAJOR_COUNT|{n}
MINOR_COUNT|{n}
BLOCKING_DEFECT|{defect_id}|{reason}
ACCEPTED_WITH_RATIONALE|{defect_id}|{rationale}
STRUCTURED_OUTPUT_END
```

`failed_unfixable`: judge believes no amount of `team-fix` iteration will resolve (e.g., contradictory PRD constraints, invariant violation that cannot be met without rewriting PRD). Triggers `blocked_unresolved` termination.

## Per-Fix Verifier Verdict (team-fix)

Written by independent per-fix verifier to `fix/iter-{N}/defect-{id}-verdict.md`.

```markdown
# Per-Fix Verdict: defect-{id}
**Verifier:** {agent_id}
**Reviewed:** `fix/defect-{id}-work.md`, fix diff, test evidence

## Evidence Review
{narrative on whether the fix actually addresses the defect}

STRUCTURED_OUTPUT_START
DEFECT_ID|{id}
ORIGINAL_SEVERITY|critical|major|minor
FIX_VERDICT|fixed|not_fixed|partial|introduced_new_defect
NEW_DEFECT_INTRODUCED|{description}|{severity}
TEST_EVIDENCE_VALID|yes|no
STRUCTURED_OUTPUT_END
```

If any `NEW_DEFECT_INTRODUCED` with severity critical/major → defect added to registry for next iteration (not silently folded into the "fixed" count).

## Worker TDD Evidence Files

Written by `team-exec` workers:

**`exec/{worker_name}-AC-{id}-red.txt`:**
Raw stdout+stderr from the failing test run. Must show:
- Test name containing AC ID reference.
- Assertion failure or equivalent failure signal (not import error, not syntax error).
- Nonzero exit code.

**`exec/{worker_name}-AC-{id}-green.txt`:**
Raw stdout+stderr from the passing test run. Must show:
- Same test name as in red.
- Pass signal.
- Zero exit code.

**`exec/{worker_name}-AC-{id}-verify.txt`:**
Raw stdout+stderr from running the PRD-specified `verification_command`. Must match `expected_output_pattern`.

Worker completion is INVALID if any of the three files is missing OR if red.txt does not show a legitimate failure.

## Logs

**`logs/stage_transitions.jsonl`** — one line per stage entry/exit:
```jsonl
{"ts":"<ISO>","event":"stage_enter","stage":"team-prd","generation":12}
{"ts":"<ISO>","event":"stage_exit","stage":"team-prd","generation":15,"result":"passed","evidence_files":["prd/prd-final.md","..."]}
```

**`logs/gate_decisions.jsonl`** — one line per gate evaluation:
```jsonl
{"ts":"<ISO>","gate":"team-plan-exit","verdict":"approved","evidence_ok":true,"generation":5}
{"ts":"<ISO>","gate":"team-verify-verdict","verdict":"failed_fixable","critical":2,"major":3,"generation":42}
```

## Parser Rules

- Pipe (`|`) splits fields. Parser splits on first N pipes per line, where N is the declared field count for that line type.
- Lines outside `STRUCTURED_OUTPUT_START` / `STRUCTURED_OUTPUT_END` markers are ignored by the coordinator.
- Unknown line type inside markers: logged to `logs/gate_decisions.jsonl` with `event: unknown_structured_line`, parser continues.
- Missing required fields in a structured line: whole line discarded, logged.
- Files without both markers: treated as failed (coordinator records `failure_reason: "missing_structured_markers"`).
