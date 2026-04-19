# Output Formats

All evidence files under `ship-it-{run_id}/` use the schemas in this file. The coordinator reads only structured fields; free-text is ignored. Files without the required `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` markers are treated as failed — the coordinator does NOT try to partially-consume a half-formed file.

## Phase 1 — Spec

### `spec/SPEC.md`

Structure defined in [SPEC-PHASE.md](SPEC-PHASE.md). Ship-It requires the following fields exist:

- `Problem` — 1-2 sentences
- `Target User` — specific persona
- `Core Features (MVP)` — enumerated list
- `Non-Goals` — explicit out-of-scope items (absence fails the gate; downstream ambiguity is too costly)
- `Tech Stack` — language, framework, key deps
- `Success Criteria` — at least one falsifiable checklist item
- `API / Tool Interface` — public contracts

### `spec/user-approval.md`

```markdown
# User Approval Record

**Run:** {run_id}
**Date:** {iso_date}
**Spec path:** {absolute_path_to_spec}

## User response verbatim
{user_input_confirming_approval}

STRUCTURED_OUTPUT_START
USER_APPROVED|true|false
APPROVAL_SCOPE|full|partial|conditional
CONDITIONS|<pipe_joined_conditions_or_none>
STRUCTURED_OUTPUT_END
```

Parser rule: `USER_APPROVED|true` is required to advance. `partial` or `conditional` approval → coordinator MUST surface the conditions in the Phase 6 completion report under Accepted Tradeoffs.

### `spec/phase-gate.md`

Shared phase-gate schema — identical structure for every phase.

```markdown
# Phase Gate Verdict: {phase_name}

**Run:** {run_id}
**Phase:** spec | design | build | test | integrate | package
**Date:** {iso_date}

## Evidence Checked
- {file_path_1} — {present|missing|unparseable}
- {file_path_2} — {present|missing|unparseable}
...

## Staleness Check
[Confirms every evidence file's mtime is after `ship-it-{run_id}/state.json` creation. Any stale file → ADVANCE=false.]

## Blocking Reasons (if any)
[One bullet per reason. Concrete — cite which file and what was missing.]

STRUCTURED_OUTPUT_START
PHASE|spec|design|build|test|integrate|package
EVIDENCE_PRESENT|true|false
EVIDENCE_PARSEABLE|true|false
EVIDENCE_FRESH_THIS_SESSION|true|false
ADVANCE|true|false
BLOCKING_REASON|<string_or_null>
STRUCTURED_OUTPUT_END
```

Parser rules:
- All of `EVIDENCE_PRESENT`, `EVIDENCE_PARSEABLE`, `EVIDENCE_FRESH_THIS_SESSION` must be `true` for `ADVANCE=true`.
- `ADVANCE|true` with any false precondition → coordinator rejects the verdict, marks phase `blocked`, re-spawns the gate subagent once. Second invalid verdict → `blocked_at_phase_N` termination.
- Unparseable gate verdict → fail-safe `ADVANCE=false`.

---

## Phase 2 — Design

### `design/DESIGN.md`

Structure defined in [DESIGN-PHASE.md](DESIGN-PHASE.md). Produced from `/deep-plan` output; Ship-It writes it in the canonical shape (File Tree, Shared Types, Module sections, Data Flow, External Dependencies, Security Considerations).

### `design/adr.md`

Inherited from `/deep-plan`. Ship-It copies verbatim; requires the ADR structure (context, decision, consequences).

### `design/consensus-termination.md`

```markdown
# Consensus Termination

**Delegate:** /deep-plan
**Iterations:** {n}

STRUCTURED_OUTPUT_START
CONSENSUS_LABEL|consensus_reached_at_iter_N|max_iter_no_consensus|user_stopped
ITER_COUNT|<integer>
APPROVED_AT_ITER|<integer_or_null>
DEGRADED_MODE|true|false
STRUCTURED_OUTPUT_END
```

Gate rule: only `consensus_reached_at_iter_N` permits Phase 2 → Phase 3 transition. Other labels → `blocked_at_phase_2`.

### `design/phase-gate.md`

Shared schema.

---

## Phase 3 — Build

### `build/team-termination.md`

```markdown
# Team Termination

**Delegate:** /team
**Stages completed:** {list}

STRUCTURED_OUTPUT_START
TEAM_LABEL|complete|partial_with_accepted_unfixed|blocked_unresolved|budget_exhausted|cancelled
STAGES_COMPLETED|<comma_separated_list>
MODIFIED_FILES_COUNT|<integer>
ACCEPTED_UNFIXED_COUNT|<integer>
DEGRADED_MODE|true|false
STRUCTURED_OUTPUT_END
```

Gate rule:
- `complete` → `ADVANCE=true`
- `partial_with_accepted_unfixed` → `ADVANCE=true` but flagged; surfaced in Phase 6 completion report
- `blocked_unresolved` → `ADVANCE=false`, terminate as `blocked_at_phase_3`
- `budget_exhausted` → `ADVANCE=false`, terminate as `budget_exhausted`
- `cancelled` → `ADVANCE=false`, terminate as `blocked_at_phase_3` with blocking reason `user_cancelled`

### `build/handoffs/*.md`

Inherited from `/team`'s structured handoff schema. Required fields: Decided, Rejected, Risks, Files, Remaining, Evidence. Ship-It does not parse beyond existence check.

### `build/modified-files.txt`

Newline-separated absolute paths. Used directly as input to `deep-qa --diff` in Phase 4.

### `build/build-output.txt`

Fresh captured output from `/team`'s final verification run. Phase 6 judges read this.

### `build/phase-gate.md`

Shared schema.

---

## Phase 4 — Test

### `test/audit/defects.md`

Inherited from `deep-qa` defect registry schema. Each defect has `severity|dimension|file:line|description|suggested_verification`. Ship-It reads the structured section.

### `test/audit/structured-verdict.md`

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
DEGRADED_MODE|true|false
STRUCTURED_OUTPUT_END
```

Rule: `FIX_LOOP_REQUIRED=true` iff `CRITICAL_COUNT > 0` OR `MAJOR_COUNT > 0` OR `test-output.txt` shows failing tests.

### `test/test-output.txt`

Fresh full test suite output captured in this session. Plain text; no structured block. The phase-gate subagent parses for pass/fail counts.

### `test/fix/prd.json` (if sub-phase 4b ran)

Conforms to `/loop-until-done` acceptance-criterion schema:

```json
{
  "stories": [
    {
      "story_id": "defect-001",
      "subject": "Fix critical defect #1: null pointer in parser",
      "acceptance_criteria": [
        {
          "id": "AC-defect-001-1",
          "criterion": "parse() returns Result.Err on null input, never throws",
          "verification_command": "npm test -- --testPathPattern=parser.test.ts",
          "expected_output_pattern": "parser.test.ts:.*passed",
          "passes": false,
          "last_verified_at": null
        }
      ],
      "status": "pending"
    }
  ]
}
```

One story per critical/major defect AND one per failing test. Every criterion has an executable verification command.

### `test/fix/loop-termination.md` (if sub-phase 4b ran)

```markdown
# Loop Termination

**Delegate:** /loop-until-done
**Critic:** deep-qa

STRUCTURED_OUTPUT_START
LOOP_LABEL|all_stories_passed|blocked_on_story_{id}|budget_exhausted|reviewer_rejected_N_times
STORIES_TOTAL|<integer>
STORIES_PASSED|<integer>
DEGRADED_MODE|true|false
STRUCTURED_OUTPUT_END
```

Gate rule:
- `all_stories_passed` → `ADVANCE=true`
- anything else → `ADVANCE=false`, terminate accordingly

### `test/skipped-fix-loop.md` (if sub-phase 4b was skipped)

```markdown
# Fix Loop Skipped

**Rationale:** deep-qa returned CRITICAL_COUNT=0 and MAJOR_COUNT=0; all tests in test-output.txt passed.
**Minor defects deferred:** {count} (listed in audit/defects.md; will be reported in completion report as accepted-tradeoffs)

STRUCTURED_OUTPUT_START
FIX_LOOP_SKIPPED|true
SKIP_REASON|no_critical_or_major_defects_and_tests_pass
MINOR_DEFERRED_COUNT|<integer>
STRUCTURED_OUTPUT_END
```

### `test/phase-gate.md`

Shared schema.

---

## Phase 5 — Integrate

### `integrate/build-output.txt`

Fresh `npm run build` (or equivalent) output. Exit code must be 0.

### `integrate/startup-probe.txt`

Fresh entry-point probe output:
- CLI: `<entry> --help` output (must include usage info, not a stack trace)
- MCP server: short-timeout spawn output (must show "connecting" or "error: connection failed", not a crash)
- Library: import round-trip script output

### `integrate/smoke-output.txt`

Fresh run of the 2-3 smoke tests added this phase. All smoke tests must pass. Plain text.

### `integrate/stub-scan.txt`

```text
# Stub Scan
# Command run: grep -rn "TODO\|FIXME\|PLACEHOLDER\|throw new Error('Not implemented')\|pass  # TODO" src/ test/
# Date: {iso}

{matches_verbatim_or_empty}

STRUCTURED_OUTPUT_START
STUB_MATCH_COUNT|<integer>
ANNOTATED_INTENTIONAL_COUNT|<integer>
UNANNOTATED_COUNT|<integer>
STRUCTURED_OUTPUT_END
```

Gate rule: `UNANNOTATED_COUNT == 0` required for advance. Each match must either be removed or annotated with a trailing comment explaining why it's intentional (and the annotation must be grep-visible so the judge can find it).

### `integrate/phase-gate.md`

Shared schema. Additionally requires:
- `build-output.txt` exit code 0
- `smoke-output.txt` all pass
- `stub-scan.txt` `UNANNOTATED_COUNT == 0`

---

## Phase 6 — Package

### `package/clean-install-output.txt`

Fresh output from a truly clean install + build + test cycle. Required sequence:

```bash
# Node
rm -rf node_modules dist
npm install
npm run build
npm test

# Python
rm -rf .venv
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Must be run in this session. Exit code 0 on every step. Any non-zero exit → phase gate fails.

### `package/judge-input.md`

Written by coordinator BEFORE spawning judges. Contains ONLY file paths — judges read file contents themselves.

```markdown
# Judge Input

**Run:** {run_id}
**Date:** {iso_date}

## Phase 1 outputs
- Spec: {absolute_path_to_spec}

## Phase 2 outputs
- Design: {absolute_path_to_design}
- ADR: {absolute_path_to_adr}

## Phase 3 outputs
- Modified files list: {absolute_path}
- Build output: {absolute_path}
- Handoffs dir: {absolute_path}

## Phase 4 outputs
- Audit defects: {absolute_path}
- Test output: {absolute_path}
- Fix loop termination (if ran): {absolute_path}

## Phase 5 outputs
- Build output: {absolute_path}
- Smoke output: {absolute_path}
- Stub scan: {absolute_path}

## Phase 6 outputs
- Clean install output: {absolute_path}

## Instructions
Read each file from disk fresh. Do not infer contents. Do not summarize without citing file:line.
```

### `package/{correctness|security|quality}-verdict.md`

Each judge writes this structure. All three use the same schema — the dimension differs only in the applied checklist (listed in SKILL.md).

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
- Missing `STRUCTURED_OUTPUT_*` markers → judge run treated as failed; coordinator re-spawns fresh judge once; second failure → fail-safe `rejected`

### `package/aggregation.md`

Written by coordinator. Mechanical aggregation only — no additional judgment.

```markdown
# Phase 6 Aggregation

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

### `package/phase-gate.md`

Shared schema. Additionally requires:
- `clean-install-output.txt` shows all steps exit 0
- All three verdict files present with parseable structured blocks
- `aggregation.md` present with `AGGREGATE ∈ {approved, conditional}`

---

## Completion Report

### `ship-it-{run_id}/completion-report.md`

Written by the completion-report subagent (not the coordinator). This is the user-facing deliverable.

```markdown
# Ship-It Completion Report

**Run:** {run_id}
**Started:** {iso}
**Completed:** {iso}
**Original idea:** {verbatim_user_input}
**Project root:** {absolute_path}

## Termination Label
**Label:** complete | partial_with_accepted_tradeoffs | blocked_at_phase_N | budget_exhausted
**Rationale:** [One paragraph tying the label to concrete evidence files.]

## Shipped (verified fresh this session)
[One bullet per shipped item. Each bullet MUST cite:
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
This section is never empty if any `CANNOT_EVALUATE_COUNT > 0` from Phase 6.]

## Accepted Tradeoffs
[Pulled from:
- /team's partial_with_accepted_unfixed items (Phase 3)
- deep-qa disputed defects (Phase 4)
- Phase 6 conditional requirements the user acknowledged
- Phase 1 partial/conditional user approval of SPEC
Each entry: what the tradeoff is, why it's accepted, who accepted it, where it's documented.]

## Files Modified
[Read from build/modified-files.txt. Group by component.]

## Evidence Manifest
| Phase | File | mtime | Fresh this session? |
|---|---|---|---|
| spec | {path} | {iso} | yes/no |
| design | {path} | {iso} | yes/no |
| build | {path} | {iso} | yes/no |
| test | {path} | {iso} | yes/no |
| integrate | {path} | {iso} | yes/no |
| package | {path} | {iso} | yes/no |

## Degraded Mode Notes (if any)
[Inherited from INTEGRATION.md degraded-mode tags. One bullet per integration that ran in degraded mode this run.]

## Shipping Commands
[Concrete next steps. For Node: `npm publish` if publishable; for CLI: usage example; for git: push-to-remote command only if user requested.]

## Next Steps (if not `complete`)
[For `blocked_at_phase_N`: concrete list of what must happen to unblock.
For `partial_with_accepted_tradeoffs`: items user should re-visit.
For `budget_exhausted`: where the run stopped and how to resume.]

STRUCTURED_OUTPUT_START
TERMINATION|complete|partial_with_accepted_tradeoffs|blocked_at_phase_N|budget_exhausted
PHASES_WITH_EVIDENCE|<integer_0_to_6>
SHIPPED_COUNT|<integer>
UNVERIFIED_COUNT|<integer>
ACCEPTED_TRADEOFFS_COUNT|<integer>
DEGRADED_MODE_COUNT|<integer>
CLEAN_INSTALL_PASSED|true|false
STRUCTURED_OUTPUT_END
```

Parser rule: `TERMINATION|complete` requires `PHASES_WITH_EVIDENCE == 6` AND `UNVERIFIED_COUNT == 0` AND `ACCEPTED_TRADEOFFS_COUNT == 0` AND `CLEAN_INSTALL_PASSED == true`. Any violation → coordinator forces the label down to `partial_with_accepted_tradeoffs` (cannot silently publish `complete`).

---

## Common Structured Output Rules

- Pipe `|` is the field separator. Parser splits on first pipe per field. No escaping needed.
- Values must be single-line. Multi-line values go in the prose sections above the structured block.
- Integer fields accept only non-negative integers. Negative → fail-safe.
- Boolean fields accept only `true` or `false` (lowercase). Other casing → fail-safe false.
- Enum fields (labels, verdicts, dimensions) are case-sensitive and must match exactly.
- Files missing the required markers are treated as failed — coordinator does NOT partially consume half-formed files.
- Every structured block is single-occurrence per file. A second `STRUCTURED_OUTPUT_START` in the same file → fail-safe.
