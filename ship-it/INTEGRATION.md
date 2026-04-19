# Integration

Ship-It is a composition operator. It delegates load-bearing work to the orchestration suite and never re-implements it inline. This file documents the mapping, the detection of available integrations, and the degraded-mode fallbacks when integrations are missing.

## Detection

At Phase 1 initialization (before any delegation), probe for each integration. Write results to `state.integrations`.

```
consensus_plan_available = exists(~/.claude/skills/deep-plan/SKILL.md)
                            OR exists(~/.claude/plugins/.../skills/deep-plan/SKILL.md)
team_available           = exists(~/.claude/skills/team/SKILL.md)
deep_qa_available        = exists(~/.claude/skills/deep-qa/SKILL.md)
loop_until_done_available= exists(~/.claude/skills/loop-until-done/SKILL.md)
```

Record each flag. If any required integration is missing, set `degraded_mode_active: true` and populate `degraded_mode_reasons[]`. Surface in the Phase 6 completion report with explicit tags.

## Phase 2 — Design (delegated to `/deep-plan`)

### Invocation contract

```
Spawn Skill("deep-plan") via Skill tool with:
  Arguments: "--spec ship-it-{run_id}/spec/SPEC.md --output ship-it-{run_id}/design/"
After completion:
  Copy the consensus plan output to ship-it-{run_id}/design/deep-plan.md
  Adapt it into ship-it-{run_id}/design/DESIGN.md using the Ship-It design schema
    (file tree, shared types, modules, data flow, deps, security)
  Copy adr.md verbatim
  Parse consensus-termination.md for label:
    consensus_reached_at_iter_N | max_iter_no_consensus | user_stopped
  Accept Phase 2 only if label == consensus_reached_at_iter_N
```

The Ship-It design schema is a refinement — the file tree and types.ts pattern are Ship-It concerns. The architectural content (module boundaries, API contracts, risk analysis) comes from `/deep-plan`. The coordinator does NOT author architectural content; it reshapes the consensus output into the Ship-It DESIGN.md template.

### Degraded-mode fallback (no `/deep-plan`)

Run an inline critic subagent with prompt:
```
"Read SPEC.md. Produce DESIGN.md covering: file tree, shared types (types.ts), per-module responsibility + public API + dependencies + error handling, data flow, external dependencies table, security considerations. Then review your own DESIGN.md and list missing error handling, API inconsistencies, circular dependencies, unclear module boundaries, missing data validation. Revise once. Tag output with VERIFICATION_MODE: degraded (no /deep-plan installed). Max 2 revisions; if still flagged, surface issues in DESIGN.md and halt."
```

Output quality is lower (single-agent, no independent critic, no falsifiability gate). Phase 6 surfaces the degradation tag.

## Phase 3 — Build (delegated to `/team`)

### Invocation contract

```
Spawn Skill("team") via Skill tool with:
  Arguments: "--plan ship-it-{run_id}/design/DESIGN.md --output ship-it-{run_id}/build/"
After completion:
  Parse team-termination.md for label:
    complete | partial_with_accepted_unfixed | blocked_unresolved |
    budget_exhausted | cancelled
  Accept Phase 3 only if label ∈ {complete, partial_with_accepted_unfixed}
  Extract modified-files.txt and build-output.txt from team's output dir
```

`/team` honors dependency ordering from DESIGN.md internally. Modules at dependency-graph leaves build in parallel; dependent modules build after their deps. Ship-It does not pre-wave the build — `/team` does it.

### Degraded-mode fallback (no `/team`)

Refuse to run by default — `/team`'s staged pipeline (plan → prd → exec → verify → fix) with two-stage review on every source modification is too complex to substitute inline without losing the discipline guarantees.

If the user passes `--skip-team` explicitly: spawn one coder subagent per module from DESIGN.md's dependency graph (respecting wave order), followed by one reviewer subagent per module. Max 2 revisions per module. Record `VERIFICATION_MODE: degraded (no /team installed)` in `build/team-termination.md`. Hard-ceiling at 5 parallel subagents per wave. No TDD preamble enforcement in degraded mode (document the loss).

## Phase 4 — Test (delegated to `deep-qa --diff` + `/loop-until-done`)

### Phase 4a — Audit (`deep-qa --diff`)

```
Spawn Skill("deep-qa") via Skill tool with:
  Arguments: "--type code --diff ship-it-{run_id}/build/modified-files.txt --output ship-it-{run_id}/test/audit/"
After completion:
  Copy qa-report.md → ship-it-{run_id}/test/audit/defects.md
  Copy structured-verdict → ship-it-{run_id}/test/audit/structured-verdict.md
  Parse structured-verdict for critical_count, major_count, fix_loop_required
```

Gate: if `critical_count == 0 AND major_count == 0 AND test-output.txt shows all passing`: skip sub-phase 4b. Otherwise sub-phase 4b fires.

### Degraded-mode fallback (no `deep-qa`)

Spawn a single code-reviewer subagent to review the diff against the plan's acceptance criteria (from `design/DESIGN.md` and `design/adr.md`). Output to the same `defects.md` path with `VERIFICATION_MODE: degraded (deep-qa not installed)` tag. Coverage is measurably lower — no parallel critics, no dimension guarantees (correctness, error_handling, security, testability).

### Phase 4b — Fix (`/loop-until-done`, only if defects found or tests failing)

```
Generate a PRD at ship-it-{run_id}/test/fix/prd.json from:
  - each critical/major defect → one story with falsifiable criterion
  - each failing test → one story with the test as verification command
  Each story's acceptance_criteria has (criterion, verification_command, expected_output_pattern).

Spawn Skill("loop-until-done") via Skill tool with:
  Arguments: "--prd ship-it-{run_id}/test/fix/prd.json --critic=deep-qa --output ship-it-{run_id}/test/fix/"
After completion:
  Parse loop-termination.md for label:
    all_stories_passed | blocked_on_story_{id} | budget_exhausted | reviewer_rejected_N_times
  Accept Phase 4 only if label == all_stories_passed
```

### Degraded-mode fallback (no `/loop-until-done`)

Fall back to `/team` team-fix stage (inline fix loop bounded by max_fix_loops=3). If `/team` also not available: surface critical defects and failing tests as open issues, mark Phase 4 as `failed_unfixable`, terminate run as `blocked_at_phase_4`.

## Phase 5 — Integrate (inline, with delegation on failure)

Phase 5 runs four coordinator-driven steps (full build, startup probe, smoke tests, stub scan). These are NOT evaluations — they are capturing mechanical outputs (exit codes, greps). Evaluation is in the phase-gate subagent that reads the outputs.

When a step fails:
- Do NOT hand-patch. Synthesize a one-story PRD for `/loop-until-done` with the failure as acceptance criterion.
- Invoke `/loop-until-done --prd <prd-path> --max-iter=3`.
- After the fix loop, re-run the failing step. If it still fails → terminate as `blocked_at_phase_5`.

### Degraded-mode fallback

If `/loop-until-done` is unavailable: fall back to a single fixer subagent per failure, max 3 iterations, with explicit `VERIFICATION_MODE: degraded` tag.

## Phase 6 — Package (inline, with three-judge validation)

Phase 6 is NOT delegated. The three judges are fresh Agent invocations, not calls into the orchestration suite. This preserves judge independence — no shared context, no delegated evaluation authority.

Phase 6 fix loops (when a judge rejects) use `/loop-until-done` per the same pattern as Phase 5.

### Degraded-mode fallback

None for the three judges themselves — they are always spawned fresh. If `/loop-until-done` is unavailable for Phase 6 re-validation fixes: fall back to a single fixer with a max-3 iteration loop, tagged degraded.

## Summary: Required vs Optional Integrations

| Phase | Integration | Required | Degrades To |
|---|---|---|---|
| 2 | `/deep-plan` | Recommended by default | Inline critic subagent (single-pass + self-review) |
| 3 | `/team` | **Hard required** by default | Refuse unless `--skip-team`; if skipped, inline coder+reviewer per module (lossy) |
| 4a | `deep-qa` | Recommended by default | Single code-reviewer subagent |
| 4b | `/loop-until-done` | Required when defects/failing tests | `/team` team-fix OR skip-with-blocked-label |
| 5 | `/loop-until-done` (on failure) | Required for fix path | Single fixer subagent, max 3 iter |
| 6 | 3 judges (inline) | Always required | None — never degrades |
| 6 | `/loop-until-done` (re-val fix) | Required when judge rejects | Single fixer subagent, max 3 iter |
| report | completion-report subagent | Always required | None — never degrades |

## Non-Silent Degradation

Every degraded fallback writes a line to `ship-it-{run_id}/degraded-mode.log` at the moment of fallback. At the completion report, the `completion-report.md` includes a "Verification Mode" section listing every degradation with reason:

```markdown
## Verification Mode: DEGRADED

The following integrations were unavailable; fallbacks were used:
- /deep-plan: not installed — Phase 2 ran inline critic (single-pass + self-review).
- deep-qa: not installed — Phase 4a ran single-pass code-reviewer fallback.

Output quality is measurably lower than the fully-integrated path. Consider installing the missing skills and re-running critical work.
```

Never silently substitute. The tag is the contract.

## Interaction with Other Orchestration Skills

Ship-It composes the orchestration suite:

- `/deep-plan` — Phase 2 exclusively
- `/team` — Phase 3 exclusively (indirectly uses `/parallel-exec`, `deep-qa`, `/loop-until-done` internally)
- `deep-qa` — Phase 4a
- `/loop-until-done` — Phase 4b, Phase 5 fixes, Phase 6 re-validation fixes
- Three inline judges — Phase 6 validation

Bugs in any lower-level skill surface in Ship-It output via the completion report (sub-skill termination labels propagate up).

## When NOT to Use Ship-It

- User has an existing codebase and wants a single-feature change → use `/team` directly with a tight plan
- User wants interactive control between phases → use `/deep-plan` + `/team` manually
- User's idea is still vague and needs ambiguity disambiguation → use `/autopilot` (Ship-It assumes Phase 1 spec is authorable; `/autopilot` has Phase 0 ambiguity routing)
- Task is a one-file fix → delegate to a coder subagent directly
- Project is non-code (docs, designs, analysis) → use artifact-appropriate skills

See the SKILL.md description field for authoritative triggers.

## Relationship to `/autopilot`

`/autopilot` and Ship-It overlap in scope. Key differences:

| Dimension | `/autopilot` | ship-it |
|---|---|---|
| Input | Vague idea — Phase 0 ambiguity classifier routes | Validated product idea — assumes Phase 1 spec is authorable |
| Phase 0 | Ambiguity routing → `deep-interview` / `/spec` / `deep-design` | No Phase 0 — starts at Spec with explicit user approval |
| Packaging | Not a separate phase | Phase 6 with clean-install gate and README generation |
| Clean install | Not explicitly gated | Hard gate before three-judge validation |
| Target | Working verified code (audit trail) | Shippable project (publishable package + repo) |

If the user's intent is "make this deployable/publishable", use Ship-It. If intent is "build something that works", use `/autopilot`. Both converge on three-judge validation.
