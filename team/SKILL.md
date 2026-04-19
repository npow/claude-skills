---
name: team
description: Use when coordinating multiple agents on a staged pipeline — plan → PRD → exec → verify → fix — with independent critic/verifier gates and two-stage review on every source modification. Trigger phrases include "spawn a team", "team of agents", "coordinate agents", "staged pipeline", "multi-agent pipeline", "agent team", "run a team on this", "PRD-driven team", "team workflow", "agents working together", "assemble a team", "delegate to a team", "orchestrate agents", "pipeline of agents". File-based state, no external MCP dependencies, honest termination labels, Claude Code native team tools.
argument-hint: "[N:agent-type] <task description>"
---

# Team Skill

Spawn N coordinated agents on a staged pipeline using Claude Code's native team tools. The coordinator orchestrates; it never evaluates. Every stage gate is approved by an independent agent reading from files. Every source modification gets a two-stage review (spec-compliance then code-quality). Every worker writes a failing test first. Termination labels are exhaustive and honest.

## Execution Model

Non-negotiable contracts:

- **All data passed to agents via files, never inline.** Handoff docs, PRDs, task graphs, diffs, judge inputs — all written to `team-{run_id}/` before the agent call. Inline data is silently truncated.
- **State written before agent spawn.** `spawn_time_iso` is written to `state.json` before the `TeamCreate` / `Task` / `Agent` call. Spawn failure records `spawn_failed`. Resume retries spawn; it does not wait.
- **Structured output is the contract.** Every critic, judge, reviewer, and verifier produces machine-parseable lines inside `STRUCTURED_OUTPUT_START` / `STRUCTURED_OUTPUT_END` markers. Coordinator reads only structured fields. Unparseable → fail-safe (treated as the worst legal verdict for that check).
- **No coordinator self-approval of anything load-bearing.** Stage completion, PRD criterion validity, exec correctness, verify verdicts, fix acceptance — all written to disk by independent agents. The coordinator only reads verdicts; it never authors them.
- **Iron-law pre-transition gate.** A stage cannot advance until `state.stages[<stage>].evidence_files` is non-empty and each listed file exists on disk. This is checked by reading `state.json` plus `ls` of listed paths — no in-memory claim is accepted.
- **Honest termination labels.** Exactly one of: `complete` | `partial_with_accepted_unfixed` | `blocked_unresolved` | `budget_exhausted` | `cancelled`. Never "no issues remain", "all done", "LGTM".

**Shared contracts:** this skill inherits the four execution-model contracts (files-not-inline, state-before-agent-spawn, structured-output, independence-invariant) from [`_shared/execution-model-contracts.md`](../_shared/execution-model-contracts.md). The items listed above are the skill-specific elaborations; the shared file is authoritative for the base contracts.

**Subagent watchdog:** every `run_in_background=true` spawn (plan, PRD, exec, verify, fix agents, critic/verifier gates) MUST be armed with a staleness monitor per [`_shared/subagent-watchdog.md`](../_shared/subagent-watchdog.md). Use Flavor A with thresholds `STALE=10 min`, `HUNG=30 min` for exec/fix agents that may run tests or builds; `STALE=5 min`, `HUNG=20 min` for plan/PRD/verify agents; `STALE=3 min`, `HUNG=10 min` for Haiku critics. `TaskOutput` status is not evidence of progress. Contract inheritance: `timed_out_heartbeat` joins this skill's per-worker termination vocabulary at the exec stage; `stalled_watchdog` / `hung_killed` join `state.stages[<stage>].workers[<id>]` state. A watchdog-killed worker's evidence file is NOT added to `evidence_files` — iron-law gate blocks stage advance until the work is reassigned or the stage terminates as `blocked_unresolved`.

## Philosophy

A team is only as trustworthy as its weakest review step. OMC's `/team` skill lets the coordinator mark stages complete, allows single-pass verification, and does not enforce test-first execution. This skill fixes each of those: the coordinator is a librarian, not a judge. Verification is two-stage by mandate. Workers write a failing test before implementation and attach the test-run output as evidence.

## Workflow

### Step 0: Input Validation Gate

Before any team is created, validate the invocation:

**Input rubric** — reject if any apply:
- Task description < 10 words and not a named artifact (request specificity)
- Scope is zero-source (pure research, no code change) — suggest `research-brief` or `deep-research` instead
- Scope is a single-file edit — suggest direct execution, not `/team`
- Requested agent count > 8 — requires explicit justification; default cap is 6 workers in `team-exec`

**Parse the invocation:**
1. Extract `N` (worker count for `team-exec`). If omitted: set after `team-plan` based on task decomposition. Hard cap 8.
2. Extract `agent-type` (applies to `team-exec` workers only — all other stages use stage-appropriate specialists picked by the lead).
3. Extract task text verbatim. This text is locked as `task_text` in `state.json` and never paraphrased into agent prompts.

**Print:** `Starting team run on: {task_text} [run: {run_id}]`

### Step 1: Initialize

- Generate run ID: `$(date +%Y%m%d-%H%M%S)` — e.g., `20260416-153022`
- Create directory structure:
  - `team-{run_id}/state.json` — run state (see STATE.md)
  - `team-{run_id}/handoffs/` — one file per stage transition
  - `team-{run_id}/prd/` — PRD draft, PRD critique, final PRD, falsifiability verdict
  - `team-{run_id}/exec/` — per-worker assignment files, TDD test evidence, diff snapshots
  - `team-{run_id}/verify/` — deep-qa outputs, code-quality reviewer output, verdict files
  - `team-{run_id}/fix/` — per-defect fix proposals, per-fix independent verification files
  - `team-{run_id}/logs/` — `stage_transitions.jsonl`, `gate_decisions.jsonl`
- Write initial `state.json` with `run_id`, `task_text`, `skill: "team"`, `generation: 0`, empty `stages[]`, `termination: null`
- Check for `deep-design` and `deep-qa` skills; record availability in `state.json.integrations`. See INTEGRATION.md for degraded-mode behavior.

### Step 2: Stage 1 — team-plan

**Agents:** `explore` (haiku, codebase scan) → `planner` (opus, task-graph author) → optional `deep-design` pass when `integrations.deep_design_available` is true AND task has >3 unknowns or >5 files likely touched.

**Entry gate:** Step 1 complete, `state.stages[0]` initialized with `status: "in_progress"`.

**Work:**
1. Write `team-{run_id}/exec/codebase-context.md` — what `explore` found (files, modules, prior art).
2. Spawn `planner` with file paths to `codebase-context.md` and `task_text`. Planner writes `team-{run_id}/handoffs/plan.md` conforming to the handoff schema in FORMAT.md.
3. If `deep_design_available` and task complexity threshold met: spawn `deep-design` on `plan.md`. Output goes to `team-{run_id}/handoffs/plan-adversarial-review.md`. See INTEGRATION.md for invocation contract. Planner revises `plan.md` to address critical flaws, logs rejections with rationale in the handoff's Rejected section.
4. Spawn an **independent plan-validator agent** (separate context from planner, opus). Plan-validator verifies the handoff has all required fields populated and at least one concrete verification plan for each major component. Writes verdict to `team-{run_id}/handoffs/plan-verdict.md`. See FORMAT.md for verdict format.

**Exit gate (all must pass):**
- `handoffs/plan.md` exists and parses against the FORMAT.md handoff schema (all 6 required fields non-empty).
- `handoffs/plan-verdict.md` has `VERDICT: approved` inside structured markers.
- If `deep_design_available`: `handoffs/plan-adversarial-review.md` exists; unresolved critical flaws from it are either fixed or marked `accepted_with_rationale` in `plan.md` under Rejected.
- `state.stages[0].evidence_files = ["handoffs/plan.md", "handoffs/plan-verdict.md", ...]`.

If exit fails: do not transition. Re-spawn `planner` with the validator's rejection reasons as a new input file.

### Step 3: Stage 2 — team-prd

**Agents:** `analyst` (opus, PRD author) + **mandatory independent critic** (opus, separate context) + **falsifiability gate** (independent, opus).

**Entry gate:** Stage 1 exit-gate passed, `handoffs/plan.md` readable.

**Work:**
1. Spawn `analyst` with `handoffs/plan.md`. Analyst writes `team-{run_id}/prd/prd-v0.md` containing:
   - Scope in/out of scope
   - Acceptance criteria — each criterion MUST include `{id, statement, verification_command, expected_output_pattern}` (see FORMAT.md AC schema).
   - Explicit non-goals.
2. Spawn **independent critic** reading `prd-v0.md`. Critic attacks PRD for ambiguity, underspecification, overscope, missing edge cases. Writes `team-{run_id}/prd/critique.md` with structured output per FORMAT.md.
3. Spawn **falsifiability judge** (independent) reading `prd-v0.md` + `critique.md`. For each acceptance criterion, judge answers: "Can I construct a concrete failing scenario? Is `verification_command` executable and deterministic? Does `expected_output_pattern` actually discriminate pass from fail?" Writes `team-{run_id}/prd/falsifiability-verdict.md`. Any criterion marked `unfalsifiable` blocks advancement.
4. Analyst revises to `prd-v1.md` addressing critique + falsifiability issues. Loop once if needed (max 2 PRD revisions); if still failing after revision 2 → label stage `blocked_unresolved`, terminate run with that label.
5. Final PRD copied to `team-{run_id}/prd/prd-final.md`. Handoff written to `team-{run_id}/handoffs/prd.md`.

**Exit gate (all must pass):**
- `prd/prd-final.md` exists.
- `prd/falsifiability-verdict.md` has zero `unfalsifiable` criteria inside structured markers.
- `prd/critique.md` has all `critical` findings marked `addressed_in_prd_v{N}` or `accepted_with_rationale`.
- `handoffs/prd.md` conforms to FORMAT.md schema.
- `state.stages[1].evidence_files = ["prd/prd-final.md", "prd/falsifiability-verdict.md", "prd/critique.md", "handoffs/prd.md"]`.

### Step 4: Stage 3 — team-exec

**Agents:** Lead + N workers (default `executor` sonnet; opus for complex autonomous work; `designer` for UI; `test-engineer` for test scaffolding). Worker type can be overridden by the `agent-type` invocation arg; specialty routing (designer for UI tasks, etc.) remains automatic.

**Entry gate:** Stage 2 exit-gate passed, `prd/prd-final.md` readable, acceptance criteria have `verification_command` populated.

**Work:**
1. Lead creates team: `TeamCreate({team_name: "team-{run_id}-exec", description: task_text})`.
2. Lead decomposes `prd-final.md` into subtasks. Each subtask becomes a `TaskCreate` call. Dependencies set via `TaskUpdate(addBlockedBy=...)`.
3. Lead **pre-assigns owners** via `TaskUpdate(taskId, owner=worker-N)` BEFORE spawning workers (avoids claim races).
4. Lead writes each worker's assignment file: `team-{run_id}/exec/worker-{N}-assignment.md` containing:
   - Subtask IDs assigned
   - PRD acceptance criteria this worker owns
   - Reference paths (handoffs, PRD)
   - TDD mandate (see Worker Preamble below)
5. Before spawn, state write: `state.stages[2].workers[N].spawn_time_iso = <ISO>`, `status: "spawned"`, `generation += 1`.
6. Lead spawns N workers in parallel: `Task(subagent_type=<worker-type>, team_name=..., name=worker-N, prompt=<preamble + assignment file path>)`.
7. Monitor loop: lead reads `TaskList`, inbound `SendMessage`. On task completion, the lead runs the **two-stage review on that worker's diff** before marking the task truly complete in state (see Step 5 team-verify for the same two-stage protocol applied per-worker).

**Worker Preamble (TDD-enforced, injected into every worker prompt):**

```
You are TEAM WORKER "{worker_name}" in team "{team_name}".
Report to team-lead. You are an executor, not an orchestrator.

== TDD PROTOCOL (NON-NEGOTIABLE) ==

For each acceptance criterion assigned to you, follow this exact order:

1. READ the assignment file: {assignment_file_path}
2. READ the PRD: {prd_final_path}
3. For each acceptance criterion in your scope:
   a. WRITE a failing test that targets the criterion. Test name must reference
      the criterion ID (e.g., test_AC_001_returns_true_for_valid_flag).
   b. RUN the test; confirm it fails for the RIGHT reason (not import/syntax).
      Capture stdout+stderr to: team-{run_id}/exec/{worker_name}-AC-{id}-red.txt
   c. IMPLEMENT the minimal code to make the test pass. Do not write
      unrelated code.
   d. RUN the test; confirm it passes. Capture output to:
      team-{run_id}/exec/{worker_name}-AC-{id}-green.txt
   e. RUN the PRD-specified verification_command for the criterion.
      Capture output to: team-{run_id}/exec/{worker_name}-AC-{id}-verify.txt
4. Call TaskUpdate status=completed ONLY when every AC has red+green+verify
   evidence files. If any file is missing, the task is NOT complete.

== WORK PROTOCOL ==

1. CLAIM: TaskList → pick your assigned pending task → TaskUpdate in_progress.
2. WORK: Follow the TDD protocol above. Never skip the red step.
3. REPORT: SendMessage to team-lead with evidence file paths:
   { "type": "message", "recipient": "team-lead",
     "content": "Task #{id} complete. Evidence: <list paths>",
     "summary": "Task #{id} complete" }
4. SHUTDOWN: On shutdown_request, respond shutdown_response approve=true.

== RULES ==
- NEVER spawn sub-agents; NEVER invoke team/ralph/autopilot skills.
- NEVER mark a task completed without red+green+verify evidence files.
- NEVER skip the red test step ("it's obvious"). The red step is the contract.
- ALWAYS use absolute paths.
- ALWAYS write evidence files before claiming completion.
```

**Per-worker completion gate (enforced by the lead, NOT by the worker):**

When a worker reports completion, the lead runs the two-stage review protocol on that worker's diff before accepting completion into `state.json`:

- Stage A: spec-compliance — spawn `deep-qa --diff` (if available) or a single code-reviewer (degraded mode; see INTEGRATION.md) on the worker's diff vs PRD.
- Stage B: code-quality — spawn a separate `code-reviewer` agent on the diff for code-quality defects.

Both reviewers write structured output. Lead reads only `STRUCTURED_OUTPUT` lines. Any `critical` defect → task status reverts to `in_progress`, worker receives a `SendMessage` with the defect file path, loops to fix and re-verify.

**Exit gate (all must pass):**
- All non-internal tasks have `status: completed` in `TaskList`.
- For every AC in `prd-final.md`: an `exec/{worker}-AC-{id}-red.txt`, `-green.txt`, and `-verify.txt` file exists; each has non-empty content; `-verify.txt` matches `expected_output_pattern`.
- Two-stage per-worker review passed for each completed task (evidence files in `verify/per-worker/`).
- `handoffs/exec.md` written summarizing what changed + pointers to evidence.
- `state.stages[2].evidence_files` populated with all the above paths.

### Step 5: Stage 4 — team-verify

**Agents:** `deep-qa --diff` (parallel critics across QA dimensions: correctness, error_handling, security, testability) OR single code-reviewer in degraded mode + **independent code-quality reviewer** (opus) as a separate second stage. Two-stage review by mandate.

**Entry gate:** Stage 3 exit-gate passed, all worker evidence files present.

**Work — mandatory two-stage protocol:**

**Stage A — spec-compliance (deep-qa --diff):**
1. Write `team-{run_id}/verify/diff.patch` capturing the full change set from exec.
2. Invoke `deep-qa --diff` on `diff.patch` with `prd-final.md` as the reference spec. Output directory: `team-{run_id}/verify/spec-compliance/`. See INTEGRATION.md for the exact invocation contract and degraded-mode fallback.
3. Read `team-{run_id}/verify/spec-compliance/defect-registry.md`. Categorize by severity: critical / major / minor.

**Stage B — code-quality reviewer (runs AFTER Stage A completes; separate independent agent):**
1. Spawn `code-reviewer` (opus) with: `diff.patch`, `prd-final.md`, `verify/spec-compliance/defect-registry.md` (so the reviewer can see but cannot dilute spec-compliance findings).
2. Reviewer prompt: "Focus on code quality — readability, maintainability, idiomatic use, duplication, error handling, test coverage structural issues. Do NOT re-litigate spec compliance (that was Stage A's job). File only code-quality defects."
3. Reviewer writes `team-{run_id}/verify/code-quality/review.md` with structured output.

**Aggregate verdict:**
- Spawn an **independent verify-judge** (opus, separate context) reading both `verify/spec-compliance/defect-registry.md` and `verify/code-quality/review.md`. Judge writes `team-{run_id}/verify/verdict.md` with structured output: `VERDICT: passed | failed_fixable | failed_unfixable`. See FORMAT.md verdict schema.

**Exit gate:**
- Both stage outputs exist with structured markers.
- `verify/verdict.md` written by independent judge.
- If `VERDICT: passed` and no critical/major defects: proceed to termination at Step 7 (skip team-fix).
- If `VERDICT: failed_fixable`: proceed to Step 6 (team-fix).
- If `VERDICT: failed_unfixable`: terminate with label `blocked_unresolved`.
- `handoffs/verify.md` written.
- `state.stages[3].evidence_files` populated.

### Step 6: Stage 5 — team-fix (loop, budget-bounded)

**Agents:** `executor` (sonnet; opus for complex) or `debugger` (sonnet) selected per defect type; **plus independent per-fix verifier**.

**Entry gate:** Stage 4 produced `VERDICT: failed_fixable` with a non-empty defect registry.

**Budget:** `fix_budget` (default 3 iterations). Each iteration handles the full remaining defect set; retries per individual defect are tracked in `state.stages[4].defects[].fix_attempts`.

**Work (per iteration):**
1. For each critical/major defect from `verify/spec-compliance/defect-registry.md` + `verify/code-quality/review.md`:
   - Write per-defect work file: `team-{run_id}/fix/defect-{id}-work.md` with defect description, reference files, and TDD mandate.
   - Spawn fix-worker on the work file. Worker follows the same TDD preamble as team-exec: write failing reproducing test → fix → green → verify.
2. After all fix-workers return: **spawn an independent per-fix verifier** for each defect. Verifier reads: defect description + fix diff + test evidence. Verdict per defect: `fixed` | `not_fixed` | `partial`. Output to `team-{run_id}/fix/iter-{N}/defect-{id}-verdict.md`.
3. Iterate remaining `not_fixed` / `partial` defects up to `fix_budget`. Each iteration writes a fresh `iter-{N}` subdirectory.

**Exit gate:**
- All critical defects have `fixed` verdicts from an independent per-fix verifier, OR
- Remaining defects are explicitly labeled `accepted_with_rationale` in `handoffs/fix.md` (reserved for minors only; critical + major cannot be accepted), OR
- `fix_budget` exhausted → label `budget_exhausted` with honest defect report, OR
- New critical defect introduced by fixes AND no fresh budget → label `blocked_unresolved`.

After a successful fix iteration: **return to Step 5 (team-verify) for a fresh two-stage review of the updated diff**. Previous verify results do NOT carry forward. This enforces the "fresh evidence every stage" rule.

### Step 7: Termination

Exactly one of:

| Label | Condition |
|---|---|
| `complete` | All PRD AC have green `-verify.txt` matching `expected_output_pattern`; team-verify `VERDICT: passed`; no unresolved critical/major defects. |
| `partial_with_accepted_unfixed` | All critical defects fixed; some major/minor defects explicitly accepted with rationale in `handoffs/fix.md`; team-verify verdict references acceptance list. |
| `blocked_unresolved` | Critical defect unfixed with no path forward (e.g., external blocker, invariant contradiction) AND `fix_budget` not exhausted. |
| `budget_exhausted` | `fix_budget` reached with unresolved critical/major defects. Honest report lists which. |
| `cancelled` | User interrupted mid-run. State preserved for resume. |

"Complete" requires ALL of:
- `state.stages[0..4].evidence_files` all non-empty and all listed files exist on disk.
- `verify/verdict.md` final iteration `VERDICT: passed`.
- Zero open defects with severity `critical` or `major` in any verify/fix output.

**Write final output:**
- `team-{run_id}/SUMMARY.md` — executive summary with termination label, AC coverage table, defect registry, accepted-tradeoffs list, evidence index.
- Update `state.termination = <label>`.

### Step 8: Shutdown Protocol

**Order is BLOCKING — never call `TeamDelete` before shutdown confirmed.**

1. Verify completion: `TaskList` shows all non-internal tasks in `completed`/`failed`/`cancelled`.
2. For each active worker: send `{"type": "shutdown_request", "recipient": "worker-{N}", "content": "Team complete, shutting down"}`.
3. Wait up to 30s per worker for `shutdown_response` with `approve: true`. If timeout: log `shutdown_timeout: worker-{N}` to `logs/stage_transitions.jsonl`; mark unresponsive. Retry shutdown once with 30s window. After second timeout: proceed (OMC's shutdown protocol — known-good).
4. Call `TeamDelete({team_name: "team-{run_id}-exec"})` only after ALL workers confirmed OR double-timed-out.
5. Preserve `team-{run_id}/` directory on disk; do NOT delete. Resume requires it. Surface its path in the final report.

### Cancel Semantics

User cancel mid-run (CTRL-C or explicit):
- Write `state.termination = "cancelled"` + `state.cancel_time_iso`.
- Run Step 8 shutdown protocol.
- Do NOT delete `team-{run_id}/`. Next invocation with same CWD can resume by reading `state.json` — see STATE.md resume protocol.

## Golden Rules

See GOLDEN-RULES.md for the full 8 cross-cutting rules + anti-rationalization counter-table. The one-line summary:

1. **Independence invariant.** Coordinator never evaluates.
2. **Iron-law verification gate.** No stage advances without evidence files on disk.
3. **Two-stage review on every source modification.** Spec-compliance THEN code-quality. Separate agents. No exceptions.
4. **Honest termination labels.** Exhaustive 5-label table only.
5. **State written before agent spawn.** `spawn_failed` ≠ "spawned but silent."
6. **Structured output is the contract.** Unparseable = fail-safe critical.
7. **All data passed via files.** Inline is truncated.
8. **No coordinator self-approval.** Every gate is a fresh independent agent's verdict file.

## Self-Review Checklist

Before declaring `complete`:

- [ ] `state.json` is valid JSON; `generation` monotonic; `termination` is one of the five labels.
- [ ] Every stage in `state.stages[]` has non-empty `evidence_files`; every listed file exists on disk.
- [ ] `handoffs/plan.md`, `prd.md`, `exec.md`, `verify.md`, `fix.md` (if fix ran) all conform to FORMAT.md schema.
- [ ] `prd/prd-final.md` every AC has populated `verification_command` and `expected_output_pattern`.
- [ ] `prd/falsifiability-verdict.md` has zero `unfalsifiable` criteria.
- [ ] For every AC: `exec/{worker}-AC-{id}-red.txt`, `-green.txt`, `-verify.txt` exist + non-empty.
- [ ] `verify/spec-compliance/defect-registry.md` + `verify/code-quality/review.md` both written by independent agents with `STRUCTURED_OUTPUT` markers.
- [ ] `verify/verdict.md` authored by independent verify-judge (not coordinator).
- [ ] If `team-fix` ran: every defect has a per-fix verifier verdict file; no critical/major defect has verdict `not_fixed` or `partial` at termination.
- [ ] Termination label is NOT "no issues remain"; it is one of the exhaustive five.
- [ ] All workers received the TDD preamble; every worker completion has red-test evidence.
- [ ] `TeamDelete` called only AFTER all workers confirmed shutdown or double-timed-out.
- [ ] `team-{run_id}/` directory preserved on disk.

## Agent Preamble — Quick Reference

See Step 4 Worker Preamble for the TDD-enforced template injected into every `team-exec` worker prompt.

Per-stage specialist agents (planner, analyst, critic, code-reviewer, verify-judge, per-fix-verifier) receive prompts that include:
- The adversarial mandate from deep-design's Judge Prompt Template ("You succeed by rejecting or downgrading. You fail by rubber-stamping. 100% approval = evidence of failure.")
- Paths to input files (never inline content).
- Output path they MUST write to.
- Required `STRUCTURED_OUTPUT_START` / `STRUCTURED_OUTPUT_END` markers around machine-parseable lines.

---

*Supplementary files: FORMAT.md (handoff + verdict schemas), STATE.md (state.json + resume protocol), GOLDEN-RULES.md (cross-cutting rules + anti-rationalization counter-table), INTEGRATION.md (deep-design / deep-qa composition, degraded-mode fallbacks).*
