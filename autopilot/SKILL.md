---
name: autopilot
description: Use when running full-lifecycle autonomous execution from a vague idea to working verified code — idea to battle-tested design to consensus plan to executed code to audited defects to three independent judge verdicts to honest completion report. Trigger phrases include "autopilot", "build me end to end", "full lifecycle", "idea to working code", "auto-run this project", "run this autonomously", "just build it", "go from idea to code", "do everything", "autonomous execution", "end-to-end build", "build this for me", "make it real end to end", "full autonomous build". Iron-law phase gates between every stage; no coordinator self-approval; honest termination labels.
user_invocable: true
argument: The product idea, feature request, or task description (may be vague — Phase 0 handles ambiguity detection)
---

# Autopilot Skill

Full-lifecycle autonomous pipeline: vague idea → battle-tested design → consensus plan → executed code → audited defects → three independent judge verdicts → honest completion report. Every phase delegates to the right specialized skill; the coordinator orchestrates but never evaluates. Iron-law phase gates require fresh evidence files before transition. Honest termination labels with no self-approval.

## Execution Model

Non-negotiable contracts:

- **All phase work delegated.** Phase 0 → `deep-interview` or `/spec` or `deep-design`. Phase 1 → `/deep-plan`. Phase 2 → `/team`. Phase 3 → `deep-qa --diff` + `/loop-until-done`. Phase 4 → 3 independent judges. Phase 5 → completion-report writer agent. The autopilot coordinator composes outputs — it does not author or evaluate any load-bearing artifact.
- **Iron-law phase gate before every transition.** A phase may only advance when the evidence files listed in `STATE.md` for that phase exist on disk, contain `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` markers where applicable, and the judge/critic verdicts they carry are machine-parseable. Missing or unparseable evidence → phase stays `blocked`; coordinator may not claim the phase complete.
- **State written before delegation.** `spawn_time_iso` for each phase delegation is written to `state.json` before invoking the delegate skill. Delegation failure is recorded as `delegation_failed`, not silently retried.
- **No coordinator self-approval at any phase boundary.** The coordinator reads structured fields from evidence files. Approval judgments come from independent agents; the coordinator's role is file aggregation and state transitions only.
- **Honest termination labels.** `complete` requires evidence files for all 5 phases (Phase 0 through Phase 4 — Phase 5 is the reporting phase itself). Any missing evidence forces `partial_with_accepted_tradeoffs`, `blocked_at_phase_N`, or `budget_exhausted`.
- **Data passed via files.** All phase inputs and outputs live under `autopilot-{run_id}/`. No inline data transfer between phases.

**Shared contracts:** this skill inherits the four execution-model contracts (files-not-inline, state-before-agent-spawn, structured-output, independence-invariant) from [`_shared/execution-model-contracts.md`](../_shared/execution-model-contracts.md). The items listed above are the skill-specific elaborations; the shared file is authoritative for the base contracts.

**Subagent watchdog:** every `run_in_background=true` spawn across every phase (plan consensus agents, staged pipeline agents, deep-qa audit, three-judge validation) MUST be armed with a staleness monitor per [`_shared/subagent-watchdog.md`](../_shared/subagent-watchdog.md). Use Flavor A with thresholds `STALE=10 min`, `HUNG=30 min` for Sonnet exec/validation agents that may run tests or builds; `STALE=5 min`, `HUNG=20 min` for planning/consensus agents; `STALE=3 min`, `HUNG=10 min` for Haiku judges. Multi-hour autopilot runs are the exact case where an unwatched stall is most costly — every phase spawn needs a watchdog. `TaskOutput` status is not evidence of progress. Contract inheritance: `timed_out_heartbeat_at_phase_N` joins this skill's phase-level termination vocabulary (peer of `blocked_at_phase_N`); `stalled_watchdog` / `hung_killed` join per-phase spawn state. A watchdog-killed delegation fails the phase gate — coordinator never advances with missing evidence.

## Philosophy

Autopilot is a composition operator. It does not re-implement planning, execution, QA, or validation — those jobs belong to `/deep-plan`, `/team`, `deep-qa`, `/loop-until-done`, and the independent judges. Autopilot's value is (1) Phase 0 ambiguity routing, (2) iron-law gates between phases, (3) independent Phase 4 validation, (4) honest completion reporting. Anything else is scope creep — if it smells like coordinator-authored content, it belongs in a subagent.

## Workflow

### Phase 0 — Expand (ambiguity-routed)

1. Generate `run_id = $(date +%Y%m%d-%H%M%S)`. Create `autopilot-{run_id}/` with subdirectories listed in `STATE.md`.
2. Write initial `state.json` with `current_phase: "expand"`, the raw user input in `initial_idea`, empty `stages[]`.
3. Run the **ambiguity classifier** — an independent subagent that reads `initial_idea` and emits structured output:

   ```
   STRUCTURED_OUTPUT_START
   AMBIGUITY_SCORE|<0.0-1.0>
   AMBIGUITY_CLASS|high|medium|low
   CONCRETE_ANCHORS|<count_of_file_paths_function_names_apis_named>
   RATIONALE|<one_line>
   STRUCTURED_OUTPUT_END
   ```

   Unparseable → fail-safe: treat as `high` ambiguity. Coordinator does not classify.
4. Route based on classifier output and availability of optional skills (see `INTEGRATION.md` availability detection):

   | Ambiguity | `deep-interview` available | Route |
   |---|---|---|
   | high | yes | `deep-interview` → spec at `autopilot-{run_id}/expand/spec.md` |
   | high | no | `/spec` template mode → same path |
   | medium | — | `/spec` template mode → same path |
   | low | — | `deep-design` for adversarial stress → design at `autopilot-{run_id}/expand/design.md` + coverage report |

5. Phase 0 evidence files (required before transition):
   - `autopilot-{run_id}/expand/ambiguity-verdict.md` — structured output from the classifier
   - Either `autopilot-{run_id}/expand/spec.md` or `autopilot-{run_id}/expand/design.md`
   - `autopilot-{run_id}/expand/phase-gate.md` — iron-law gate result (see below)
6. **Iron-law gate (Phase 0 → Phase 1):** a fresh `phase-gate` subagent reads evidence files and emits:

   ```
   STRUCTURED_OUTPUT_START
   PHASE|expand
   EVIDENCE_PRESENT|true|false
   EVIDENCE_PARSEABLE|true|false
   ADVANCE|true|false
   BLOCKING_REASON|<string_or_null>
   STRUCTURED_OUTPUT_END
   ```

   `ADVANCE: true` required to proceed. Coordinator may not override.

### Phase 1 — Plan (consensus)

1. Update state: `current_phase: "plan"`. Write `spawn_time_iso`.
2. Invoke `/deep-plan` with `--spec autopilot-{run_id}/expand/<spec-or-design>.md --output autopilot-{run_id}/plan/`. The deep-plan skill internally runs Planner → Architect → Critic independent agents with falsifiability-gated rejection; autopilot does not re-implement any of that logic inline.
3. Phase 1 evidence files (required before transition):
   - `autopilot-{run_id}/plan/plan.md` — the approved plan
   - `autopilot-{run_id}/plan/adr.md` — the ADR backing the plan
   - `autopilot-{run_id}/plan/consensus-termination.md` — deep-plan's own termination label (`consensus_reached_at_iter_N` | `max_iter_no_consensus` | `user_stopped`)
   - `autopilot-{run_id}/plan/phase-gate.md`
4. If deep-plan returns `max_iter_no_consensus` or `user_stopped`: Phase 1 gate reports `ADVANCE: false, BLOCKING_REASON: no-consensus`. Autopilot terminates as `blocked_at_phase_1`.
5. Iron-law gate (Phase 1 → Phase 2): same structure as Phase 0.

### Phase 2 — Exec (staged team)

1. Update state: `current_phase: "exec"`. Write `spawn_time_iso`.
2. Invoke `/team` with `--plan autopilot-{run_id}/plan/plan.md --output autopilot-{run_id}/exec/`. `/team` internally runs the staged pipeline `team-plan → team-prd → team-exec → team-verify → team-fix` with TDD-preamble workers, mandatory critic falsifiability gate, two-stage review on every source modification, and `deep-qa --diff` verification. Autopilot does not duplicate any stage.
3. Phase 2 evidence files (required before transition):
   - `autopilot-{run_id}/exec/team-termination.md` — `/team` termination label (`complete` | `partial_with_accepted_unfixed` | `blocked_unresolved` | `budget_exhausted` | `cancelled`)
   - `autopilot-{run_id}/exec/handoffs/` — structured handoff docs per `/team`'s schema
   - `autopilot-{run_id}/exec/modified-files.txt` — list of files changed (used by Phase 3 `--diff`)
   - `autopilot-{run_id}/exec/build-output.txt` — fresh build/test output captured at end of `/team`
   - `autopilot-{run_id}/exec/phase-gate.md`
4. If `/team` returns `blocked_unresolved` or `budget_exhausted`: Phase 2 gate reports `ADVANCE: false`. Autopilot terminates as `blocked_at_phase_2` or `budget_exhausted`. `partial_with_accepted_unfixed` is a gate-pass condition but gets surfaced in the final completion report.
5. Iron-law gate (Phase 2 → Phase 3).

### Phase 3 — QA (defect audit, then fix loop)

This phase differs in purpose from OMC `ultraqa`. OMC's ultraqa is a test-build-fix loop driving CI to green. Our Phase 3 is a **two-sub-phase audit-then-fix** flow because code that passes its own tests can still have defects the tests do not cover.

1. Update state: `current_phase: "qa_audit"`. Write `spawn_time_iso`.
2. **Sub-phase 3a — Audit.** Invoke `deep-qa --diff autopilot-{run_id}/exec/modified-files.txt --type code --output autopilot-{run_id}/qa/audit/`. `deep-qa` runs parallel critics across artifact-type-aware dimensions (correctness, error_handling, security, testability) and produces a prioritized defect registry. Autopilot does not author defect entries.
3. Read `autopilot-{run_id}/qa/audit/defects.md`. If `deep-qa` returns zero critical and zero major defects: skip sub-phase 3b; write `qa/skipped-fix-loop.md` with rationale; proceed to gate.
4. **Sub-phase 3b — Fix loop.** For each open critical + major defect, synthesize a falsifiable acceptance criterion (`criterion`, `verification_command`, `expected_output_pattern`). Write `autopilot-{run_id}/qa/fix/prd.json` in the `/loop-until-done` acceptance-criterion schema. Invoke `/loop-until-done --prd autopilot-{run_id}/qa/fix/prd.json --critic=deep-qa --output autopilot-{run_id}/qa/fix/`. Autopilot does not execute fixes directly.
5. Phase 3 evidence files (required before transition):
   - `autopilot-{run_id}/qa/audit/defects.md` — deep-qa defect registry
   - `autopilot-{run_id}/qa/audit/structured-verdict.md` — deep-qa summary with STRUCTURED_OUTPUT markers
   - If sub-phase 3b ran: `autopilot-{run_id}/qa/fix/loop-termination.md` — loop-until-done termination label
   - `autopilot-{run_id}/qa/phase-gate.md`
6. If `/loop-until-done` returns `blocked_on_story_{id}` or `reviewer_rejected_{count}_times` or `budget_exhausted`: gate reports `ADVANCE: false`. Autopilot terminates as `blocked_at_phase_3` or `budget_exhausted`.
7. Iron-law gate (Phase 3 → Phase 4).

### Phase 4 — Validate (three independent judges)

1. Update state: `current_phase: "validate"`. Write `spawn_time_iso` for each judge separately.
2. Write the judge input file: `autopilot-{run_id}/validate/judge-input.md` containing paths (not contents) to `expand/`, `plan/plan.md`, `exec/modified-files.txt`, `qa/audit/defects.md`. Each judge reads the files from disk themselves.
3. **Spawn three fully independent judges in parallel**, one per dimension. Each judge is a separate Agent invocation with no shared context, no coordinator orchestration. Judge prompts are documented in this file's "Judge Prompt Templates" section.
   - `correctness_judge` → reads plan, reads modified files, reads test output, reads `deep-qa` defects → writes `validate/correctness-verdict.md`
   - `security_judge` → reads modified files with adversarial-security lens → writes `validate/security-verdict.md`
   - `quality_judge` → reads modified files with code-quality lens (maintainability, clarity, test coverage) → writes `validate/quality-verdict.md`
4. Each verdict file MUST include the structured block documented in `FORMAT.md` with `VERDICT|approved|rejected|conditional`, a rationale, and (for rejected/conditional) a concrete blocking scenario. Unparseable verdict → fail-safe: treat as `rejected`.
5. **Coordinator aggregates only.** Read the three verdicts. Aggregation rule: all three must be `approved` OR (`conditional` with no new blocking scenarios introduced by fix) for Phase 4 to pass. Coordinator does NOT render its own judgment.
6. If any judge returns `rejected`: synthesize the blocking scenario into a new acceptance criterion and invoke `/loop-until-done` with `max_iter=2` to fix. After fix, **re-spawn fresh judge agents** (never reuse the rejecting judge — stale context). Maximum 2 re-validation rounds. After 2 rounds still-rejected: Phase 4 gate reports `ADVANCE: false`; autopilot terminates as `blocked_at_phase_4`.
7. Phase 4 evidence files (required before transition to Phase 5):
   - `autopilot-{run_id}/validate/correctness-verdict.md`
   - `autopilot-{run_id}/validate/security-verdict.md`
   - `autopilot-{run_id}/validate/quality-verdict.md`
   - `autopilot-{run_id}/validate/aggregation.md` — structured aggregation of the three verdicts
   - `autopilot-{run_id}/validate/phase-gate.md`
8. Iron-law gate (Phase 4 → Phase 5).

### Phase 5 — Cleanup (honest completion report)

1. Update state: `current_phase: "cleanup"`.
2. Spawn a completion-report subagent that reads all Phase 0–4 evidence files and writes `autopilot-{run_id}/completion-report.md` per the schema in `FORMAT.md`. Report MUST include:
   - **Passed**: items that have fresh evidence (tests run this session, judge verdicts this session)
   - **Unverified**: items with stale or missing evidence
   - **Accepted tradeoffs**: items carried forward from `/team` `partial_with_accepted_unfixed` or deep-qa disputed defects, with rationale
   - **Termination label**: one of `complete` | `partial_with_accepted_tradeoffs` | `blocked_at_phase_N` | `budget_exhausted`
   - **Evidence manifest**: list of every evidence file path with a fresh-this-session timestamp
3. **Report is written BEFORE state deletion.** The report is the deliverable; state deletion is a tidy-up step.
4. Print the completion-report path and termination label. Do NOT print a claim of success without the report having been authored by the subagent.
5. **State deletion is optional and gated.** If termination is `complete`, offer to delete `autopilot-{run_id}/` state files (keep completion-report.md at one level up). Otherwise preserve the full tree for resume.

## Termination Labels

Exhaustive — no other labels permitted:

| Label | When |
|---|---|
| `complete` | All 5 phases produced evidence; all iron-law gates passed; all three Phase 4 judges approved (or conditional with no new blockers); completion report written with `VERDICT|approved` aggregation |
| `partial_with_accepted_tradeoffs` | All 5 phases produced evidence; gates passed; but `/team` carried forward accepted unfixed items OR `deep-qa` disputed defects present. Report lists them explicitly. |
| `blocked_at_phase_N` | Phase N iron-law gate returned `ADVANCE: false`. Evidence file for the blocked phase is written; earlier phases retained. |
| `budget_exhausted` | Cumulative token/time budget exceeded; some phase(s) did not complete. Distinct from `blocked_at_phase_N` because the blocker is budget, not content. |

Forbidden labels: "success", "done", "all complete", "no issues remain", "ready to ship". The coordinator cannot substitute optimistic phrasing for the structured label.

## Budget Control

- Hard cap: 5 phases × max 3 re-invocations per delegate skill = 15 top-level delegation calls.
- Per-phase token soft cap tracked in `state.json` under `budget.phase_tokens_spent_estimate_usd`.
- Exceeding global cap mid-phase: current delegation finishes, then coordinator writes `budget_exhausted` termination label and proceeds to Phase 5 for honest reporting of partial state.

## Resume Protocol

1. On invocation, check CWD for `autopilot-{run_id}/state.json`. If present and `current_phase != "cleanup"`: prompt to resume or start fresh.
2. Resume replays from `state.json.current_phase`. Re-read the phase's evidence files. If any evidence file is `delegation_failed` or missing: re-delegate that phase. If evidence is complete and gate not yet run: run gate.
3. Resume NEVER re-runs completed phases whose evidence is intact. Resume NEVER copies evidence forward in memory — every agent that needs a prior phase's output reads it from disk fresh.

## Judge Prompt Templates (Phase 4)

All three judges use this structure. Judge-specific dimension and checklist filled per judge type.

```
You are an independent {dimension} judge evaluating a completed autopilot run. Your job is to REJECT or flag defects. A 100% approval rate is evidence of failure.

You have no stake in this run succeeding. Prior phases already claimed success; you are the last line of defense.

**Your dimension:** {correctness | security | quality}

**Input file (paths only — read contents yourself from disk):**
{judge_input_path}

**Available evidence:**
- Plan: {plan_path}
- Modified files: {modified_files_path}
- Test output: {exec/build-output.txt}
- Defects registry: {qa/audit/defects.md}

**Instructions:**
1. Read the plan. Read the modified files. Read the test output. Read the defects registry.
2. Run your dimension's checklist (below). For each check, gather concrete evidence from the files.
3. If you find a blocking defect, construct a falsifiable scenario: who does what, what goes wrong, what the correct behavior should be.
4. Write your verdict to: {verdict_path}
5. Use FORMAT.md's verdict schema with STRUCTURED_OUTPUT_START/END markers.

**Dimension checklist:**
{checklist_per_dimension}

**Adversarial mandate:**
- Approving without a checklist walkthrough is rubber-stamping. Do not.
- "Looks fine" is not a verdict. Cite specific file:line evidence for every claim.
- If evidence is missing to judge an item, say so in the verdict — do not infer approval.
- Conditional approvals must list the exact condition + a verification command the user can run.

**Calibration:** Approved = no blocking defect found after systematic checklist walkthrough. Rejected = concrete blocking scenario with evidence. Conditional = minor issue with a stated fix requirement.
```

### Correctness judge checklist

- Does each acceptance criterion from the plan have a verification command that actually ran and passed this session?
- For each changed file: does the diff match what the plan called for?
- Are there plan items in `modified-files.txt` that were never referenced, or vice versa?
- Do the tests actually exercise the new code path, or are they vacuous?

### Security judge checklist

- Does any change introduce an auth bypass, injection vector, unbounded recursion, unsafe deserialization, secret exposure, or privilege escalation path?
- Are inputs validated at trust boundaries?
- Are error paths leaking sensitive information?
- Are new dependencies from untrusted sources?

### Quality judge checklist

- Is the code maintainable — clear names, focused functions, no dead code?
- Test coverage of new logic: any branches with zero tests?
- Obvious code smells: duplication, god objects, magic numbers without rationale?
- Documentation present for non-obvious decisions?

## Golden Rules (summary)

Full list and counter-table in `GOLDEN-RULES.md`. Short form:

1. Independence invariant — coordinator orchestrates; never evaluates.
2. Iron-law phase gate — no transition without evidence.
3. Two-stage review on source modifications — inherited from `/team` (Phase 2).
4. Honest termination labels — exhaustive vocabulary, no substitutions.
5. State written before delegation — spawn failure recorded, not retried silently.
6. Structured output is the contract — `STRUCTURED_OUTPUT_START`/`END` markers.
7. All data passed via files — no inline content between phases.
8. No coordinator self-approval at any phase boundary.

## Self-Review Checklist

- [ ] `autopilot-{run_id}/state.json` is valid JSON after every phase transition
- [ ] `generation` counter incremented on every state write
- [ ] Every phase has an evidence directory and `phase-gate.md`
- [ ] Phase 0 `ambiguity-verdict.md` contains STRUCTURED_OUTPUT markers
- [ ] Phase 0 routed correctly based on classifier output + availability (not coordinator preference)
- [ ] Phase 1 did NOT re-implement planner/architect/critic logic inline — delegated to `/deep-plan`
- [ ] Phase 2 did NOT re-implement executor/verifier logic inline — delegated to `/team`
- [ ] Phase 3 ran `deep-qa --diff` for audit, NOT a generic test-loop
- [ ] Phase 3 sub-phase 3b invoked `/loop-until-done` only if critical/major defects were found
- [ ] Phase 4 spawned THREE independent judges in parallel, not sequentially by the coordinator
- [ ] Phase 4 aggregation is purely mechanical — coordinator did not add judgment
- [ ] Phase 4 re-validation used FRESH judge agents, not the rejecting judge re-asked
- [ ] Completion report written BEFORE state deletion
- [ ] Termination label is from the exhaustive table, no substitutions
- [ ] `complete` label is only used when all 5 phases produced evidence this session
- [ ] No evidence was copied forward in memory — all agents read from disk
- [ ] `delegation_failed` recorded on spawn error, not retried silently
- [ ] Degraded-mode tags present in evidence files when `deep-design` or `deep-qa` unavailable
- [ ] Completion report lists unverified items explicitly (not silently omitted)

## Cancellation

Ctrl-C at any phase is safe. State is written before every delegation; resume protocol replays from `state.json.current_phase`. To explicitly abandon a run: delete `autopilot-{run_id}/` manually. No `/cancel` subcommand; the file-based state is the source of truth.

---

*Supplementary files: FORMAT.md (per-phase evidence schemas + verdict format + completion report schema), STATE.md (state.json schema + phase evidence registry + resume protocol), GOLDEN-RULES.md (8 rules tailored + anti-rationalization counter-table), INTEGRATION.md (which phase calls which skill + degraded-mode fallbacks)*
