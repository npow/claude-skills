# Phase 4: Test

Audit via `deep-qa --diff`; fix any critical/major defects AND any failing tests via `/loop-until-done`. This phase differs from a plain test-run in that passing tests alone are not sufficient — defects the tests don't cover still block advancement.

## Prerequisites

- Phase 3 complete: `/team` produced `complete` or `partial_with_accepted_unfixed` termination
- `build/modified-files.txt` and `build/build-output.txt` on disk
- `types.ts` still immutable

## Process

### Sub-phase 4a — Audit

1. Update `state.json`: `phases.test.audit.spawn_time_iso = <iso>`, `phases.test.status = "in_progress"`.
2. Invoke `deep-qa` per [INTEGRATION.md](INTEGRATION.md):
   ```
   deep-qa --type code --diff ship-it-{run_id}/build/modified-files.txt \
           --output ship-it-{run_id}/test/audit/
   ```
3. `deep-qa` runs parallel critics across artifact-type-aware dimensions (correctness, error_handling, security, testability) and produces a prioritized defect registry. Ship-It does NOT author defect entries.
4. After completion, parse `test/audit/structured-verdict.md` per [FORMAT.md](FORMAT.md):
   - `AUDIT_LABEL|clean` with `CRITICAL_COUNT=0 AND MAJOR_COUNT=0` → record
   - `AUDIT_LABEL|defects_found` with counts → record
   - `AUDIT_LABEL|delegate_failed` → mark `delegation_failed`, retry within budget, else block

### Sub-phase 4a.1 — Run full test suite

Separate from the defect audit:

1. In the project root, run the full test suite:
   - Node: `npm test`
   - Python: `pytest`
   - Other: the `test` script from `package.json` / `pyproject.toml`
2. Capture full output to `ship-it-{run_id}/test/test-output.txt`.
3. Record `phases.test.test_run.exit_code`, `tests_passed`, `tests_failed`.

### Decision: skip or run fix loop

Fix loop runs iff `FIX_LOOP_REQUIRED == true`, defined as:
- `CRITICAL_COUNT > 0` OR
- `MAJOR_COUNT > 0` OR
- `test-output.txt` shows any failing test

If NONE of these are true:
- Write `test/skipped-fix-loop.md` per the schema in [FORMAT.md](FORMAT.md).
- Minor defects (if any) are deferred to Phase 6 Accepted Tradeoffs.
- Proceed to phase gate.

If ANY are true → Sub-phase 4b runs.

### Sub-phase 4b — Fix loop

1. Synthesize acceptance criteria for `/loop-until-done`:
   - Each critical/major defect → one user story with:
     - `criterion` — derived from the defect's description
     - `verification_command` — defect's `suggested_verification` or a default based on the defect's file
     - `expected_output_pattern` — from the defect entry
   - Each failing test → one user story with the test command as verification and pass-pattern as expected output
2. Write the PRD to `ship-it-{run_id}/test/fix/prd.json` in the `/loop-until-done` acceptance-criterion schema.
3. Update `state.json`: `phases.test.fix.spawn_time_iso = <iso>`.
4. Invoke `/loop-until-done`:
   ```
   /loop-until-done --prd ship-it-{run_id}/test/fix/prd.json \
                    --critic=deep-qa \
                    --output ship-it-{run_id}/test/fix/
   ```
5. `/loop-until-done` iterates story-by-story, invokes `deep-qa` as reviewer per story, and terminates only when every criterion has fresh passing evidence.
6. Parse `test/fix/loop-termination.md`:
   - `all_stories_passed` → record; proceed to gate
   - `blocked_on_story_{id}` → gate fails; terminate as `blocked_at_phase_4`
   - `reviewer_rejected_N_times` → gate fails; terminate as `blocked_at_phase_4`
   - `budget_exhausted` → gate fails; terminate as `budget_exhausted`

## Test quality requirements (enforced via `/team` internal TDD preamble + `deep-qa` testability dimension)

| Category | Minimum |
|----------|---------|
| Happy path (main feature works) | 1 test per public function |
| Error path (bad input, missing data) | 1 test per documented error case in DESIGN.md |
| Edge cases (empty input, null, boundary values) | 1 test per module |
| Integration (modules work together) | Added in Phase 5 (smoke tests) |

If `deep-qa` reports testability defects (missing test coverage on a branch, vacuous tests), they appear in the defect registry and are handled by sub-phase 4b.

## Anti-patterns `deep-qa` flags (not the coordinator)

- Tests that always pass (`expect(true).toBe(true)`)
- Tests that mock everything (test implementation details)
- Tests that duplicate the implementation (`expect(add(1,2)).toBe(1+2)`)
- Snapshot-only tests without semantic assertions

Ship-It does NOT evaluate tests directly. All test quality judgments come from `deep-qa`.

## Degraded-mode fallbacks

- No `deep-qa`: single code-reviewer subagent; `VERIFICATION_MODE: degraded (deep-qa not installed)` tag
- No `/loop-until-done`: fall back to `/team` team-fix stage; if that's also unavailable, mark `failed_unfixable` and terminate

## Iron-law gate (Phase 4 → Phase 5)

Fresh phase-gate subagent reads evidence. Required:
- `test/audit/defects.md`
- `test/audit/structured-verdict.md` with parseable `AUDIT_LABEL`
- `test/test-output.txt` with exit code 0 (or the fix loop must have run and produced `all_stories_passed` that fixed failing tests)
- Exactly ONE of `test/fix/loop-termination.md` (with `LOOP_LABEL|all_stories_passed`) or `test/skipped-fix-loop.md`
- `test/phase-gate.md` with `ADVANCE: true`

Both `loop-termination.md` and `skipped-fix-loop.md` present → invalid state; gate fails.
