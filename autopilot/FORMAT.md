# Output Formats

All evidence files under `autopilot-{run_id}/` use the schemas in this file. Coordinator reads only structured fields; free-text is ignored. Files without the required `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` markers are treated as failed (not partially consumed).

## Phase 0 — Expand

### `expand/ambiguity-verdict.md`

Emitted by the ambiguity classifier subagent.

```markdown
# Ambiguity Verdict

**Run:** {run_id}
**Date:** {iso_date}

## Input
{raw_user_idea_verbatim}

## Classification Rationale
[2-4 sentences explaining what anchors were present/absent, why the score lands where it does.]

STRUCTURED_OUTPUT_START
AMBIGUITY_SCORE|<float_0_to_1>
AMBIGUITY_CLASS|high|medium|low
CONCRETE_ANCHORS|<integer_count>
DEEP_INTERVIEW_AVAILABLE|true|false
ROUTED_TO|deep-interview|spec|deep-design
RATIONALE|<one_line>
STRUCTURED_OUTPUT_END
```

Parser rules:
- `AMBIGUITY_CLASS` ∈ {high, medium, low} — any other value → fail-safe `high`
- `AMBIGUITY_SCORE` outside [0, 1] → fail-safe `high`
- `ROUTED_TO` must match the table in SKILL.md Phase 0; mismatch → coordinator halts with `routing_invalid`

### `expand/spec.md` OR `expand/design.md`

Whichever branch ran. Schema is inherited from `/spec` or `deep-design` skills respectively. Autopilot does not redefine these schemas — it consumes the delegate skill's output verbatim.

Autopilot requires the following fields exist in whichever file was produced:
- A `Core Concept` or equivalent section
- Explicit `Non-Goals` (autopilot refuses to proceed to Phase 1 if non-goals are absent — too much ambiguity downstream)
- At least one falsifiable acceptance hint (e.g., "Success means X is possible", "The system must prevent Y") — used to seed Phase 1 consensus

### `expand/phase-gate.md`

Emitted by the fresh phase-gate subagent. Same schema used for all five phases.

```markdown
# Phase Gate Verdict: {phase_name}

**Run:** {run_id}
**Phase:** expand | plan | exec | qa | validate
**Date:** {iso_date}

## Evidence Checked
- {file_path_1} — {present|missing|unparseable}
- {file_path_2} — {present|missing|unparseable}
...

## Staleness Check
[Confirms that every evidence file was written this session (mtime after `autopilot-{run_id}/state.json` creation). Any stale file → ADVANCE=false.]

## Blocking Reasons (if any)
[One bullet per reason. Concrete — cite which file and what was missing.]

STRUCTURED_OUTPUT_START
PHASE|expand|plan|exec|qa|validate
EVIDENCE_PRESENT|true|false
EVIDENCE_PARSEABLE|true|false
EVIDENCE_FRESH_THIS_SESSION|true|false
ADVANCE|true|false
BLOCKING_REASON|<string_or_null>
STRUCTURED_OUTPUT_END
```

Parser rules:
- All of `EVIDENCE_PRESENT`, `EVIDENCE_PARSEABLE`, `EVIDENCE_FRESH_THIS_SESSION` must be `true` for `ADVANCE` to be `true`
- `ADVANCE|true` with any false precondition → coordinator rejects the gate verdict as invalid, marks phase `blocked`, and re-spawns the gate subagent once. Second invalid verdict → `blocked_at_phase_N` termination.

---

## Phase 1 — Plan

### `plan/plan.md`, `plan/adr.md`

Produced by `/deep-plan`. Schemas owned by that skill. Autopilot consumes verbatim.

### `plan/consensus-termination.md`

```markdown
# Consensus Termination

**Delegate:** /deep-plan
**Iterations:** {n}

STRUCTURED_OUTPUT_START
CONSENSUS_LABEL|consensus_reached_at_iter_N|max_iter_no_consensus|user_stopped
ITER_COUNT|<integer>
APPROVED_AT_ITER|<integer_or_null>
STRUCTURED_OUTPUT_END
```

Autopilot rule: only `consensus_reached_at_iter_N` permits Phase 1 → Phase 2 transition. Other labels → `blocked_at_phase_1`.

### `plan/phase-gate.md`

Same schema as Phase 0 gate.

---

## Phase 2 — Exec

### `exec/team-termination.md`

```markdown
# Team Termination

**Delegate:** /team
**Stages completed:** {list}

STRUCTURED_OUTPUT_START
TEAM_LABEL|complete|partial_with_accepted_unfixed|blocked_unresolved|budget_exhausted|cancelled
STAGES_COMPLETED|<comma_separated_list>
MODIFIED_FILES_COUNT|<integer>
ACCEPTED_UNFIXED_COUNT|<integer>
STRUCTURED_OUTPUT_END
```

Gate rule:
- `complete` → `ADVANCE=true`
- `partial_with_accepted_unfixed` → `ADVANCE=true` but flagged; surfaced in Phase 5 completion report
- `blocked_unresolved` → `ADVANCE=false`, terminate as `blocked_at_phase_2`
- `budget_exhausted` → `ADVANCE=false`, terminate as `budget_exhausted`
- `cancelled` → `ADVANCE=false`, terminate as `blocked_at_phase_2` with blocking reason `user_cancelled`

### `exec/handoffs/*.md`

Inherited from `/team` schema. Autopilot does not parse beyond existence check.

### `exec/modified-files.txt`

Newline-separated absolute paths. Used directly as input to `deep-qa --diff`.

### `exec/build-output.txt`

Fresh captured output from `/team`'s final verification run. Phase 4 judges read this.

### `exec/phase-gate.md`

Same schema.

---

## Phase 3 — QA

### `qa/audit/defects.md`

Inherited from `deep-qa` defect registry schema. Autopilot reads the structured section.

### `qa/audit/structured-verdict.md`

```markdown
# deep-qa Audit Summary

**Delegate:** deep-qa --diff
**Input:** {modified_files_count} files

STRUCTURED_OUTPUT_START
AUDIT_LABEL|clean|defects_found|delegate_failed
CRITICAL_COUNT|<integer>
MAJOR_COUNT|<integer>
MINOR_COUNT|<integer>
DISPUTED_COUNT|<integer>
FIX_LOOP_REQUIRED|true|false
STRUCTURED_OUTPUT_END
```

Rule: `FIX_LOOP_REQUIRED=true` iff `CRITICAL_COUNT > 0` OR `MAJOR_COUNT > 0`.

### `qa/fix/prd.json` (if sub-phase 3b ran)

Conforms to `/loop-until-done` acceptance-criterion schema. One story per unresolved critical/major defect. Each criterion has executable `verification_command` and `expected_output_pattern`.

### `qa/fix/loop-termination.md` (if sub-phase 3b ran)

```markdown
# Loop Termination

**Delegate:** /loop-until-done
**Critic:** deep-qa

STRUCTURED_OUTPUT_START
LOOP_LABEL|all_stories_passed|blocked_on_story_{id}|budget_exhausted|reviewer_rejected_N_times
STORIES_TOTAL|<integer>
STORIES_PASSED|<integer>
STRUCTURED_OUTPUT_END
```

Gate rule:
- `all_stories_passed` → `ADVANCE=true`
- anything else → `ADVANCE=false`, terminate accordingly

### `qa/skipped-fix-loop.md` (if sub-phase 3b was skipped)

```markdown
# Fix Loop Skipped

**Rationale:** deep-qa returned CRITICAL_COUNT=0 and MAJOR_COUNT=0; no fix-required defects.
**Minor defects deferred:** {count} (listed in audit/defects.md; will be reported in completion report as accepted-tradeoffs)

STRUCTURED_OUTPUT_START
FIX_LOOP_SKIPPED|true
SKIP_REASON|no_critical_or_major_defects
MINOR_DEFERRED_COUNT|<integer>
STRUCTURED_OUTPUT_END
```

### `qa/phase-gate.md`

Same schema.

---

## Phase 4 — Validate

### `validate/judge-input.md`

Written by coordinator before spawning judges. Contains ONLY file paths — judges read file contents themselves.

```markdown
# Judge Input

**Run:** {run_id}
**Date:** {iso_date}

## Phase 0 outputs
- Spec or design: {absolute_path}

## Phase 1 outputs
- Plan: {absolute_path}
- ADR: {absolute_path}

## Phase 2 outputs
- Modified files list: {absolute_path}
- Build output: {absolute_path}
- Handoffs dir: {absolute_path}

## Phase 3 outputs
- Audit defects: {absolute_path}
- Fix loop termination (if ran): {absolute_path}

## Instructions
Read each file from disk fresh. Do not infer contents. Do not summarize without citing file:line.
```

### `validate/{correctness|security|quality}-verdict.md`

Each judge writes this structure. All three use the same schema — dimension differs only in the checklist applied.

```markdown
# {Dimension} Judge Verdict

**Judge:** {dimension}_judge
**Run:** {run_id}
**Date:** {iso_date}
**Judge spawn time:** {iso}

## Checklist Walkthrough
[For each checklist item in SKILL.md for this dimension:]

### Item: {checklist_item_verbatim}
**Evidence examined:** {file_path}:{line_range}
**Observation:** [What was found.]
**Verdict on this item:** pass | fail | cannot_evaluate

[If cannot_evaluate: specify what evidence would be required.]

## Blocking Scenarios Found

### Scenario: {title}
**Who:** [user/attacker/operator]
**Does:** [action]
**Goes wrong:** [concrete failure]
**Correct behavior:** [what should happen]
**Evidence:** {file_path}:{line}
**Verification command:** `{exact_command_user_can_run}`

[Repeat per scenario. If none: "No blocking scenarios found during checklist walkthrough."]

## Conditional Requirements (if verdict is conditional)

### Condition: {title}
**Required fix:** [concrete]
**Verification:** `{command}`
**Expected after fix:** {pattern}

STRUCTURED_OUTPUT_START
VERDICT|approved|rejected|conditional
BLOCKING_SCENARIO_COUNT|<integer>
CONDITIONAL_COUNT|<integer>
CANNOT_EVALUATE_COUNT|<integer>
CHECKLIST_ITEMS_PASSED|<integer_of_total>
DIMENSION|correctness|security|quality
STRUCTURED_OUTPUT_END
```

Parser rules:
- `VERDICT|approved` with `BLOCKING_SCENARIO_COUNT > 0` → fail-safe treat as `rejected`
- `VERDICT|conditional` with `CONDITIONAL_COUNT == 0` → fail-safe treat as `approved`
- `CANNOT_EVALUATE_COUNT > 0` → surfaced in completion report as `unverified`, not silently dropped
- Missing `STRUCTURED_OUTPUT_*` markers → judge run is treated as failed, coordinator re-spawns fresh judge once; second failure → fail-safe `rejected`

### `validate/aggregation.md`

Written by coordinator. Mechanical aggregation only — no additional judgment.

```markdown
# Phase 4 Aggregation

**Run:** {run_id}
**Date:** {iso_date}

## Judge Verdicts
| Dimension | Verdict | Blocking | Conditional | Cannot Evaluate |
|---|---|---|---|---|
| correctness | {v} | {n} | {n} | {n} |
| security | {v} | {n} | {n} | {n} |
| quality | {v} | {n} | {n} | {n} |

## Aggregation Rule
- If all three `VERDICT == approved` AND all `CANNOT_EVALUATE_COUNT == 0` → `AGGREGATE=approved`
- Else if all three `VERDICT ∈ {approved, conditional}` AND no blocking scenarios AND `CANNOT_EVALUATE_COUNT == 0` → `AGGREGATE=conditional`
- Else → `AGGREGATE=rejected`

STRUCTURED_OUTPUT_START
AGGREGATE|approved|conditional|rejected
APPROVED_COUNT|<integer_0_to_3>
REJECTED_COUNT|<integer_0_to_3>
CONDITIONAL_COUNT|<integer_0_to_3>
CANNOT_EVALUATE_TOTAL|<integer>
REVALIDATION_ROUND|<integer>
STRUCTURED_OUTPUT_END
```

### `validate/phase-gate.md`

Same schema.

---

## Phase 5 — Cleanup / Completion Report

### `completion-report.md`

Written by the completion-report subagent (not the coordinator). Schema is load-bearing — this is the user-facing deliverable.

```markdown
# Autopilot Completion Report

**Run:** {run_id}
**Started:** {iso}
**Completed:** {iso}
**Original idea:** {verbatim_user_input}

## Termination Label
**Label:** complete | partial_with_accepted_tradeoffs | blocked_at_phase_N | budget_exhausted
**Rationale:** [One paragraph tying the label to concrete evidence files.]

## Passed (verified fresh this session)
[One bullet per passed item. Each bullet MUST cite:
- What was verified
- Evidence file path
- Command/agent that produced the evidence
- Timestamp
Items with stale or missing evidence MUST NOT appear here.]

## Unverified (evidence stale, missing, or cannot_evaluate)
[One bullet per unverified item. Each bullet MUST cite:
- What was NOT verified
- Why (stale / missing / judge cannot_evaluate)
- What would be required to verify
This section is never empty if any `CANNOT_EVALUATE_COUNT > 0` from Phase 4.]

## Accepted Tradeoffs
[Pulled from:
- /team's partial_with_accepted_unfixed items
- deep-qa disputed defects
- Phase 4 conditional requirements that user acknowledged
Each entry: what the tradeoff is, why it's accepted, who accepted it, where it's documented.]

## Files Modified
[Read from exec/modified-files.txt. Group by component.]

## Evidence Manifest
| Phase | File | mtime | Fresh this session? |
|---|---|---|---|
| expand | {path} | {iso} | yes/no |
| plan | {path} | {iso} | yes/no |
...

## Degraded Mode Notes (if any)
[Inherited from INTEGRATION.md degraded-mode tags. One bullet per integration that ran in degraded mode this run.]

## Next Steps (if not `complete`)
[For `blocked_at_phase_N`: concrete list of what must happen to unblock.
For `partial_with_accepted_tradeoffs`: items user should re-visit.
For `budget_exhausted`: where the run stopped and how to resume.]

STRUCTURED_OUTPUT_START
TERMINATION|complete|partial_with_accepted_tradeoffs|blocked_at_phase_N|budget_exhausted
PHASES_WITH_EVIDENCE|<integer_0_to_5>
PASSED_COUNT|<integer>
UNVERIFIED_COUNT|<integer>
ACCEPTED_TRADEOFFS_COUNT|<integer>
DEGRADED_MODE_COUNT|<integer>
STRUCTURED_OUTPUT_END
```

Parser rule: `TERMINATION|complete` requires `PHASES_WITH_EVIDENCE == 5` AND `UNVERIFIED_COUNT == 0` AND `ACCEPTED_TRADEOFFS_COUNT == 0`. Any violation → coordinator forces the label down to `partial_with_accepted_tradeoffs` (cannot silently publish `complete`).

---

## Common Structured Output Rules

- Pipe `|` is the field separator. Parser splits on first pipe per field. No escaping needed.
- Values must be single-line. Multi-line values go in the prose sections above the structured block.
- Integer fields accept only non-negative integers. Negative → fail-safe.
- Boolean fields accept only `true` or `false` (lowercase). Other casing → fail-safe false.
- Enum fields (labels, verdicts, dimensions) are case-sensitive and must match exactly.
- Files missing the required markers are treated as failed — the coordinator does NOT try to partially-consume a half-formed file.
