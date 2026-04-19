---
name: ship-it
description: Takes a validated product idea and builds it into a complete, shippable project through a multi-phase pipeline with parallel subagents. Use when the user says "build this idea", "ship it", "go to product", "implement this", "make this real", or wants to turn a product spec into working code with tests, docs, and packaging. Handles TypeScript, Python, or Node.js projects end-to-end.
---

# Ship It

Transforms a product idea into a shippable project through a 6-phase pipeline with iron-law phase gates, delegation to the orchestration suite, two-stage review on every code modification, and three-judge final validation. The coordinator orchestrates but never evaluates. Honest termination labels per phase; no self-approval anywhere.

## Execution Model

Non-negotiable contracts:

- **Iron-law phase gate between every phase.** A phase may only advance when its evidence files (listed in `STATE.md`) exist on disk, contain required `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` markers where applicable, and carry machine-parseable judge/critic verdicts. Missing or unparseable evidence → phase stays `blocked`; coordinator may not claim the phase complete.
- **Delegation to the orchestration suite.** Phase 2 Design delegates to `/deep-plan` for plan consensus. Phase 3 Build delegates to `/team` for the staged executor pipeline with TDD preamble and two-stage review. Phase 4 Test delegates to `deep-qa --diff` for defect audit. The coordinator does not re-implement planner, executor, or QA logic inline.
- **Two-stage review on every source modification.** All code emitted during Phase 3 Build passes through spec-compliance review then independent code-quality review, via `/team`'s mandatory two-stage gate. Ship-It does not patch code directly.
- **State written before any delegation.** `spawn_time_iso` written to `state.json` before invoking each delegate skill. Delegation failure is recorded as `delegation_failed`, not silently retried.
- **No coordinator self-approval at any phase boundary.** The coordinator reads structured fields from evidence files. Approval judgments come from independent agents; the coordinator's role is file aggregation and state transitions only.
- **Honest termination labels.** Per-phase exhaustive vocabulary in the table below. `complete` requires evidence files for all 6 phases. Any missing evidence forces `partial_with_accepted_tradeoffs`, `blocked_at_phase_N`, or `budget_exhausted`.
- **Data passed via files.** All phase inputs and outputs live under `ship-it-{run_id}/` in CWD. No inline data transfer between phases.
- **Three-judge final validation.** Phase 6 Package concludes with three fully independent judges (correctness, security, quality) reading from files. All three must return `approved` or `conditional` with no new blocking scenarios. Coordinator aggregates only.

## Philosophy

Ship-It is a full-lifecycle composition operator. It preserves the familiar Spec → Design → Build → Test → Integrate → Package phase structure, but every load-bearing judgment is delegated: plan consensus to `/deep-plan`, execution to `/team`, defect audit to `deep-qa`, defect-fix to `/loop-until-done`, final validation to three independent judges. The coordinator's value is (1) ambiguity-sensitive spec creation, (2) iron-law gates between phases, (3) clean-install reproducibility verification, (4) three-judge shipping validation, (5) honest completion reporting.

## Workflow

### Phase 1 — Spec

1. Generate `run_id = $(date +%Y%m%d-%H%M%S)`. Create `ship-it-{run_id}/` with subdirectories listed in `STATE.md`.
2. Write initial `state.json` with `current_phase: "spec"`, raw user input in `initial_idea`, empty `phases` status.
3. Write `SPEC.md` in the project root per the structure in [SPEC-PHASE.md](SPEC-PHASE.md). Present to the user and request explicit approval before advancing.
4. Phase 1 evidence files (required before transition):
   - `ship-it-{run_id}/spec/SPEC.md` (canonical copy; the project-root SPEC.md is a live working copy)
   - `ship-it-{run_id}/spec/user-approval.md` — dated record of user approval
   - `ship-it-{run_id}/spec/phase-gate.md` — iron-law gate verdict
5. **Iron-law gate (Phase 1 → Phase 2):** fresh `phase-gate` subagent reads evidence files, verifies presence + parseability + freshness, emits `ADVANCE: true|false` per the structured block in [FORMAT.md](FORMAT.md).

### Phase 2 — Design (deep-plan delegation)

1. Update state: `current_phase: "design"`. Write `spawn_time_iso`.
2. Invoke `/deep-plan` with the spec at `ship-it-{run_id}/spec/SPEC.md`. `/deep-plan` internally runs Planner → Architect → Critic independent agents with falsifiability-gated rejection. Ship-It does not re-implement any of that logic.
3. Write `DESIGN.md` in the project root from the consensus plan output, adapting to the Ship-It design schema in [DESIGN-PHASE.md](DESIGN-PHASE.md). The design file structure is Ship-It's responsibility; the architectural content is the consensus plan's output.
4. Write `types.ts` (or equivalent) containing all shared types from DESIGN.md. This file is immutable for Phase 3 coder subagents.
5. Phase 2 evidence files:
   - `ship-it-{run_id}/design/DESIGN.md` — canonical copy
   - `ship-it-{run_id}/design/consensus-termination.md` — `/deep-plan`'s termination label
   - `ship-it-{run_id}/design/adr.md` — ADR from `/deep-plan`
   - `ship-it-{run_id}/design/phase-gate.md`
6. If `/deep-plan` returns `max_iter_no_consensus` or `user_stopped`: phase gate reports `ADVANCE: false`. Ship-It terminates as `blocked_at_phase_2`.
7. **Degraded-mode fallback** (when `/deep-plan` unavailable): inline critic subagent per [INTEGRATION.md](INTEGRATION.md). Evidence files tagged `VERIFICATION_MODE: degraded`.
8. Iron-law gate (Phase 2 → Phase 3).

### Phase 3 — Build (team delegation)

1. Update state: `current_phase: "build"`. Write `spawn_time_iso`.
2. Scaffold project skeleton (directories, package.json/pyproject.toml, tsconfig, install deps, write immutable types.ts). Verify skeleton compiles.
3. Invoke `/team` with `--plan ship-it-{run_id}/design/DESIGN.md --output ship-it-{run_id}/build/`. `/team` internally runs staged pipeline `team-plan → team-prd → team-exec → team-verify → team-fix` with TDD preamble, mandatory critic falsifiability gate, two-stage review on every source modification, and `deep-qa --diff` verification. Ship-It does not duplicate any stage.
4. `/team`'s component-level parallelization honors the dependency graph from DESIGN.md. Waves execute sequentially; modules within a wave build in parallel.
5. Phase 3 evidence files:
   - `ship-it-{run_id}/build/team-termination.md` — `/team` termination label
   - `ship-it-{run_id}/build/handoffs/` — structured handoff docs per `/team` schema
   - `ship-it-{run_id}/build/modified-files.txt` — list of files changed (used by Phase 4 `--diff`)
   - `ship-it-{run_id}/build/build-output.txt` — fresh build output captured at end of `/team`
   - `ship-it-{run_id}/build/phase-gate.md`
6. If `/team` returns `blocked_unresolved` or `budget_exhausted`: gate reports `ADVANCE: false`. Ship-It terminates as `blocked_at_phase_3` or `budget_exhausted`. `partial_with_accepted_unfixed` is a gate-pass condition but is surfaced in the Phase 6 completion report.
7. **Degraded-mode fallback** (when `/team` unavailable): inline coder+reviewer loop per module, max 3 iterations, explicit degraded-mode tag. See [INTEGRATION.md](INTEGRATION.md).
8. Iron-law gate (Phase 3 → Phase 4).

### Phase 4 — Test (deep-qa audit + fix loop)

1. Update state: `current_phase: "test"`. Write `spawn_time_iso`.
2. **Sub-phase 4a — Audit.** Invoke `deep-qa --diff ship-it-{run_id}/build/modified-files.txt --type code --output ship-it-{run_id}/test/audit/`. `deep-qa` runs parallel critics across artifact-type-aware dimensions (correctness, error_handling, security, testability). Ship-It does not author defect entries.
3. Run the full project test suite in the project root (`npm test` / `pytest` / equivalent) and capture output at `ship-it-{run_id}/test/test-output.txt`.
4. Read `ship-it-{run_id}/test/audit/defects.md` and the test-output file.
5. If `deep-qa` returns zero critical and zero major defects AND all tests pass: skip sub-phase 4b; write `test/skipped-fix-loop.md`; proceed to gate.
6. **Sub-phase 4b — Fix loop.** For each open critical+major defect AND each failing test, synthesize a falsifiable acceptance criterion (`criterion`, `verification_command`, `expected_output_pattern`). Write `ship-it-{run_id}/test/fix/prd.json` in the `/loop-until-done` schema. Invoke `/loop-until-done --prd ship-it-{run_id}/test/fix/prd.json --critic=deep-qa --output ship-it-{run_id}/test/fix/`.
7. Phase 4 evidence files:
   - `ship-it-{run_id}/test/audit/defects.md`
   - `ship-it-{run_id}/test/audit/structured-verdict.md`
   - `ship-it-{run_id}/test/test-output.txt` — fresh full test suite output
   - If sub-phase 4b ran: `ship-it-{run_id}/test/fix/loop-termination.md`
   - Else: `ship-it-{run_id}/test/skipped-fix-loop.md`
   - `ship-it-{run_id}/test/phase-gate.md`
8. If `/loop-until-done` returns `blocked_on_story_{id}` or `reviewer_rejected_N_times` or `budget_exhausted`: gate reports `ADVANCE: false`. Ship-It terminates as `blocked_at_phase_4` or `budget_exhausted`.
9. Iron-law gate (Phase 4 → Phase 5). See [TEST-PHASE.md](TEST-PHASE.md) for additional test-quality requirements.

### Phase 5 — Integrate

1. Update state: `current_phase: "integrate"`. Write `spawn_time_iso`.
2. Run full build (`npm run build` / equivalent). Capture output at `ship-it-{run_id}/integrate/build-output.txt`.
3. Wire entry point. Verify the main entry imports all modules without crashing. Capture startup probe at `ship-it-{run_id}/integrate/startup-probe.txt` (for CLI: `--help`; for MCP server: short-timeout spawn; for library: import round-trip).
4. Write and run 2-3 smoke tests that exercise the public interface end-to-end with real code (no mocks). Capture output at `ship-it-{run_id}/integrate/smoke-output.txt`.
5. Stub/placeholder scan: grep for `TODO|FIXME|PLACEHOLDER|Not implemented|pass  # TODO` in the source tree. Write results to `ship-it-{run_id}/integrate/stub-scan.txt`.
6. Phase 5 evidence files:
   - `ship-it-{run_id}/integrate/build-output.txt`
   - `ship-it-{run_id}/integrate/startup-probe.txt`
   - `ship-it-{run_id}/integrate/smoke-output.txt`
   - `ship-it-{run_id}/integrate/stub-scan.txt` — must show zero matches, or each match must be annotated as intentional
   - `ship-it-{run_id}/integrate/phase-gate.md`
7. Any sub-step failure → delegate fix to `/loop-until-done` with the failure as an acceptance criterion. No coordinator-authored fixes. See [INTEGRATE-PHASE.md](INTEGRATE-PHASE.md).
8. Iron-law gate (Phase 5 → Phase 6).

### Phase 6 — Package (three-judge final validation)

1. Update state: `current_phase: "package"`. Write `spawn_time_iso`.
2. Generate README.md, LICENSE, .gitignore per [PACKAGE-PHASE.md](PACKAGE-PHASE.md). Verify `package.json` / `pyproject.toml` metadata.
3. **Clean install test** (the reproducibility gate): `rm -rf node_modules dist && npm install && npm run build && npm test` (or Python equivalent). Capture output at `ship-it-{run_id}/package/clean-install-output.txt`.
4. Initialize git repo with an initial commit (do NOT push without explicit user request).
5. Write judge input at `ship-it-{run_id}/package/judge-input.md` — paths only, not contents. Judges read files from disk themselves.
6. **Spawn three fully independent judges in parallel**, one per dimension. Each judge is a separate Agent invocation with no shared context, no coordinator orchestration. Judge prompts are in the "Judge Prompt Templates" section below.
   - `correctness_judge` → reads SPEC.md, DESIGN.md, modified files, test output, deep-qa defects → writes `package/correctness-verdict.md`
   - `security_judge` → reads modified files with adversarial-security lens → writes `package/security-verdict.md`
   - `quality_judge` → reads modified files with code-quality lens → writes `package/quality-verdict.md`
7. Each verdict MUST include the structured block documented in [FORMAT.md](FORMAT.md) with `VERDICT|approved|rejected|conditional`. Unparseable verdict → fail-safe `rejected`.
8. **Coordinator aggregates only.** Read three verdicts; apply aggregation rule from FORMAT.md verbatim. Write `ship-it-{run_id}/package/aggregation.md`. Coordinator does NOT render its own judgment.
9. If any judge returns `rejected`: synthesize the blocking scenario into a new acceptance criterion and invoke `/loop-until-done` with `max_iter=2`. After fix, **re-spawn fresh judge agents** (never reuse the rejecting judge). Maximum 2 re-validation rounds. After 2 rounds still-rejected: gate reports `ADVANCE: false`; Ship-It terminates as `blocked_at_phase_6`.
10. Phase 6 evidence files:
    - `ship-it-{run_id}/package/clean-install-output.txt`
    - `ship-it-{run_id}/package/correctness-verdict.md`
    - `ship-it-{run_id}/package/security-verdict.md`
    - `ship-it-{run_id}/package/quality-verdict.md`
    - `ship-it-{run_id}/package/aggregation.md`
    - `ship-it-{run_id}/package/phase-gate.md`
11. Iron-law gate (Phase 6 → completion report).
12. Spawn completion-report subagent that reads all Phase 1–6 evidence files and writes `ship-it-{run_id}/completion-report.md` per the schema in FORMAT.md. Report is written BEFORE any state deletion. Coordinator prints the path and termination label verbatim.

## Termination Labels

Exhaustive — no other labels permitted:

| Label | When |
|---|---|
| `complete` | All 6 phases produced evidence this session; every iron-law gate passed; clean-install test passed; all three Phase 6 judges returned `approved` (or `conditional` with no new blocking scenarios); completion report written with aggregated `VERDICT|approved` |
| `partial_with_accepted_tradeoffs` | All 6 phases produced evidence; gates passed; but `/team` carried forward accepted unfixed items OR `deep-qa` disputed defects present OR Phase 6 judges returned `conditional` with conditions the user accepted. Report lists them explicitly. |
| `blocked_at_phase_N` | Phase N iron-law gate returned `ADVANCE: false`. Evidence file for the blocked phase is written; earlier phases retained. |
| `budget_exhausted` | Cumulative delegation/token budget exceeded mid-run. Distinct from `blocked_at_phase_N` because blocker is budget, not content. |

Per-phase labels used internally (recorded in `state.json`, surfaced in completion report):

| Phase | Labels |
|---|---|
| Phase 1 Spec | `complete` / `blocked_on_user_approval` |
| Phase 2 Design | `complete` / `partial_with_accepted_tradeoffs` (consensus conditional) / `blocked_at_phase_2` / `budget_exhausted` |
| Phase 3 Build | `complete` / `partial_with_accepted_tradeoffs` (team `partial_with_accepted_unfixed`) / `blocked_at_phase_3` / `budget_exhausted` |
| Phase 4 Test | `complete` / `partial_with_accepted_tradeoffs` (disputed defects) / `blocked_at_phase_4` / `budget_exhausted` |
| Phase 5 Integrate | `complete` / `blocked_at_phase_5` |
| Phase 6 Package | `complete` / `partial_with_accepted_tradeoffs` (judge conditional) / `blocked_at_phase_6` / `budget_exhausted` |

Forbidden labels: "success", "done", "all complete", "no issues remain", "shipped", "ready to go". The coordinator cannot substitute optimistic phrasing.

## Judge Prompt Templates (Phase 6)

All three judges use this structure. Judge-specific dimension and checklist filled per judge type.

```
You are an independent {dimension} judge evaluating a Ship-It run that is about to be declared shippable. Your job is to REJECT or flag defects. A 100% approval rate is evidence of failure.

You have no stake in this run succeeding. Prior phases already claimed success; you are the last line of defense before shipping.

Your dimension: {correctness | security | quality}

Input file (paths only — read contents yourself from disk):
{judge_input_path}

Available evidence:
- Spec: ship-it-{run_id}/spec/SPEC.md
- Design: ship-it-{run_id}/design/DESIGN.md
- ADR: ship-it-{run_id}/design/adr.md
- Modified files: ship-it-{run_id}/build/modified-files.txt
- Build output: ship-it-{run_id}/integrate/build-output.txt
- Smoke output: ship-it-{run_id}/integrate/smoke-output.txt
- Clean-install output: ship-it-{run_id}/package/clean-install-output.txt
- Test output: ship-it-{run_id}/test/test-output.txt
- Defect registry: ship-it-{run_id}/test/audit/defects.md
- Stub scan: ship-it-{run_id}/integrate/stub-scan.txt

Instructions:
1. Read the spec and design. Read the modified files. Read test+build+clean-install output. Read the defect registry.
2. Run your dimension's checklist (below). For each check, gather concrete evidence from the files.
3. If you find a blocking defect, construct a falsifiable scenario: who does what, what goes wrong, what the correct behavior should be.
4. Write your verdict to: {verdict_path}
5. Use the verdict schema in FORMAT.md with STRUCTURED_OUTPUT_START/END markers.

Dimension checklist:
{checklist_per_dimension}

Adversarial mandate:
- Approving without a checklist walkthrough is rubber-stamping. Do not.
- "Looks fine" is not a verdict. Cite specific file:line evidence for every claim.
- If evidence is missing to judge an item, say so in the verdict — do not infer approval.
- Conditional approvals must list the exact condition + a verification command the user can run.

Calibration:
- Approved = no blocking defect found after systematic checklist walkthrough.
- Rejected = concrete blocking scenario with evidence.
- Conditional = minor issue with a stated fix requirement.
```

### Correctness judge checklist

- Does each acceptance criterion from SPEC.md have a verification command that actually ran and passed this session?
- For each changed file: does the diff match what DESIGN.md called for?
- Are there design items in modified-files.txt that were never referenced, or vice versa?
- Do the tests actually exercise the new code path, or are they vacuous?
- Did the clean-install test pass from a truly clean state?
- Are any stubs/TODOs still present in the source?

### Security judge checklist

- Does any change introduce an auth bypass, injection vector, unbounded recursion, unsafe deserialization, secret exposure, or privilege escalation path?
- Are inputs validated at trust boundaries?
- Are error paths leaking sensitive information?
- Are new dependencies from untrusted sources?
- Are secrets/API keys hardcoded in source or config?

### Quality judge checklist

- Is the code maintainable — clear names, focused functions, no dead code?
- Test coverage of new logic: any branches with zero tests?
- Obvious code smells: duplication, god objects, magic numbers without rationale?
- Documentation present for non-obvious decisions (README, inline docs)?
- Does the README match reality — can a new user actually follow it?

## Self-review checklist

- [ ] `ship-it-{run_id}/state.json` is valid JSON after every phase transition; `generation` monotonically increasing
- [ ] Every phase produced its evidence files this session (mtime after `state.json.created_at`)
- [ ] Every phase has a `phase-gate.md` with `ADVANCE: true` before advancing
- [ ] Phase 2 did NOT re-implement planner/architect/critic logic inline — delegated to `/deep-plan` (or explicitly tagged degraded)
- [ ] Phase 3 did NOT re-implement executor/verifier logic inline — delegated to `/team` (or explicitly tagged degraded)
- [ ] Phase 4 ran `deep-qa --diff` for audit, NOT a generic test-loop
- [ ] Phase 4 sub-phase 4b invoked `/loop-until-done` only if critical/major defects OR failing tests
- [ ] Phase 6 spawned THREE independent judges in parallel, not sequentially by the coordinator
- [ ] Phase 6 aggregation is purely mechanical — coordinator did not add judgment
- [ ] Phase 6 re-validation used FRESH judge agents, not rejecting judges re-asked
- [ ] Clean-install test ran from a truly clean state (rm -rf node_modules dist first)
- [ ] Completion report written BEFORE any state deletion
- [ ] Termination label is from the exhaustive table; no substitutions
- [ ] `complete` label only used when all 6 phases produced evidence this session AND every judge returned approved/conditional
- [ ] No evidence was copied forward in memory — all agents read from disk
- [ ] `delegation_failed` recorded on spawn error, not silently retried
- [ ] Degraded-mode tags present in evidence files when `/deep-plan`, `/team`, `deep-qa`, or `/loop-until-done` unavailable
- [ ] Completion report lists unverified items explicitly (not silently omitted)
- [ ] No hardcoded secrets/keys in source files (verified by security judge; not coordinator-claimed)

## Golden rules (summary)

Full list and anti-rationalization table in [GOLDEN-RULES.md](GOLDEN-RULES.md). Short form:

1. Independence invariant — coordinator orchestrates; never evaluates.
2. Iron-law phase gate — no transition without fresh evidence.
3. Two-stage review on source modifications — inherited via `/team` (Phase 3).
4. Honest termination labels — exhaustive vocabulary per phase, no substitutions.
5. State written before delegation — spawn failure recorded, not retried silently.
6. Structured output is the contract — `STRUCTURED_OUTPUT_START`/`END` markers.
7. All data passed via files — no inline content between phases.
8. No coordinator self-approval at any phase boundary.

## Cancellation

Ctrl-C at any phase is safe. State is written before every delegation; resume protocol replays from `state.json.current_phase` (see [STATE.md](STATE.md)). To explicitly abandon: delete `ship-it-{run_id}/` manually.

## Reference files

| File | Contents |
|------|----------|
| [SPEC-PHASE.md](SPEC-PHASE.md) | How to write the product spec from an idea |
| [DESIGN-PHASE.md](DESIGN-PHASE.md) | Design structure and types.ts pattern (deep-plan delegation details) |
| [BUILD-PHASE.md](BUILD-PHASE.md) | Build phase scaffolding and delegation to `/team` |
| [TEST-PHASE.md](TEST-PHASE.md) | Test requirements and delegation to `deep-qa` + `/loop-until-done` |
| [INTEGRATE-PHASE.md](INTEGRATE-PHASE.md) | Integration gate and fix-delegation pattern |
| [PACKAGE-PHASE.md](PACKAGE-PHASE.md) | Packaging, clean-install gate, and three-judge validation |
| [FORMAT.md](FORMAT.md) | Per-phase evidence schemas + verdict format + completion report schema |
| [STATE.md](STATE.md) | state.json schema + phase evidence registry + resume protocol |
| [GOLDEN-RULES.md](GOLDEN-RULES.md) | 8 rules tailored + anti-rationalization counter-table |
| [INTEGRATION.md](INTEGRATION.md) | Which phase calls which skill + degraded-mode fallbacks |
