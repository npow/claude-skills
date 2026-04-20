---
name: deep-plan
description: Use before touching code for any multi-step task — features, refactors, migrations, architectural decisions, bug fixes, or any work that needs to be broken into verifiable steps. Trigger phrases include "write a plan", "implementation plan", "plan this", "plan the work", "break this down", "how should I approach this", "make a plan", "design the approach", "before I code this", "I need a plan", "write up the plan", "spec to plan", "requirements to plan". Produces an ADR-backed plan with verification-backed acceptance criteria via a Planner → Architect → Critic consensus loop.
user_invocable: true
argument: The task description or problem statement to produce a deep plan for.
---

# Deep Plan Skill

Produce an ADR-backed plan that three fully independent agents — Planner, Architect, Critic — agree on, or stop honestly at max iterations. The coordinator never evaluates. All three roles read and write via files only; they do not inherit coordinator context.

## Execution Model

All operations use Claude Code primitives. Contracts are non-negotiable:

- **Fully independent agents, file I/O only.** Planner, Architect, Critic are separate Agent-tool spawns. Each receives file paths, not inline content. None of them inherit the coordinator's message history. Coordinator reads structured outputs, never paraphrases.
- **Strictly sequential Architect → Critic.** Architect verdict file must exist on disk before Critic is spawned. Never parallelize Steps 3 and 4.
- **Falsifiable rejection gate.** Critic rejection is invalid without a concrete failure scenario AND an executable verification command that would prove the flaw. Vague "needs more detail" rejections are dropped.
- **Verification commands per acceptance criterion.** Every acceptance criterion in the final plan has a `verification_command` and `expected_output_pattern`. Prose-only criteria are rejected by the Critic.
- **Honest termination labels.** One of: `consensus_reached_at_iter_N` / `max_iter_no_consensus` / `user_stopped`. Never "approved" without a Critic APPROVE verdict on disk.
- **State written before each agent spawn.** `spawn_time_iso` recorded pre-call; spawn failure records `spawn_failed` and is retried on resume, not waited on.
- **Structured output is the contract.** All role outputs include `STRUCTURED_OUTPUT_START` / `STRUCTURED_OUTPUT_END` markers. Unparseable output fails the iteration for that role (fail-safe: Critic unparseable → treat as `REJECT`, Architect unparseable → re-spawn once then fail).
- **No coordinator self-approval.** The coordinator cannot author a plan revision or approve one. Every revision is by the Planner; every approval is by the Critic.

**Shared contracts:** this skill inherits the four execution-model contracts (files-not-inline, state-before-agent-spawn, structured-output, independence-invariant) from [`_shared/execution-model-contracts.md`](../_shared/execution-model-contracts.md). The items listed above are the skill-specific elaborations; the shared file is authoritative for the base contracts.

**Subagent watchdog:** every `run_in_background=true` spawn (Planner, Architect, Critic) MUST be armed with a staleness monitor per [`_shared/subagent-watchdog.md`](../_shared/subagent-watchdog.md). Use Flavor A with thresholds `STALE=10 min`, `HUNG=30 min` — planning agents can legitimately sit quiet while they think, but a 30-min silence is pathological. `TaskOutput` status is not evidence of progress. Contract inheritance: `timed_out_heartbeat_<role>` joins this skill's iteration-level termination vocabulary (e.g. `planner_timed_out_heartbeat_at_iter_N`); `stalled_watchdog` / `hung_killed` join per-role state. A watchdog-killed Planner/Architect/Critic pass terminates the iteration honestly — never silently rolls forward into consensus.

## Flags

| Flag | Effect |
|---|---|
| `--interactive` | Gates at draft review (after first Planner pass) and at final approval. Without it, runs fully autonomous and stops after the terminal label is written. |
| `--deliberate` | Forces Deliberate mode: Planner must emit a pre-mortem (3 failure scenarios) and an expanded test plan (unit / integration / e2e / observability). Critic rejects on missing/weak pre-mortem. Auto-enables for explicit high-risk signals (auth, security, data migration, destructive ops, production incident, compliance/PII, public API breakage). |
| `--architect codex` | Spawn Architect via `codex` CLI instead of Claude Agent. See INTEGRATION.md for invocation and degraded-mode fallback. |
| `--critic codex` / `--critic gemini` | Same for Critic. |
| `--max-iter N` | Override default max iterations (5). Never exceeds 5 without explicit user extension. |

## Workflow

### Step 0: Input Validation & Initialization

1. Validate task description. Reject if:
   - Empty or <10 words of actionable content
   - Pure execution request with concrete file/symbol anchors — route back to direct execution
   - Harmful scope (weapon, exploit) — decline
2. Detect high-risk signals (see `--deliberate`) and set `mode: "short" | "deliberate"`.
3. Generate `run_id = $(date +%Y%m%d-%H%M%S)`.
4. Create directory: `deep-plan-{run_id}/`
   - `state.json` (see STATE.md)
   - `task.md` — task description locked verbatim
   - `iterations/iter-{N}/` — one directory per iteration
     - `plan.md` — Planner output
     - `architect-verdict.md` — Architect output with `STRUCTURED_OUTPUT_START/END`
     - `critic-verdict.md` — Critic output with `STRUCTURED_OUTPUT_START/END`
     - `feedback-bundle.md` — coordinator-assembled file handed to next Planner
   - `adr.md` — final ADR (written only on consensus or max-iter stop)
   - `plan.md` — final plan (written only on consensus or max-iter stop)
   - `logs/decisions.jsonl` — audit trail, one line per decision
5. Write initial `state.json` with `iteration: 0`, `status: "planner_pending"`, `mode`, `max_iterations` (default 5, capped by `--max-iter`).
6. Print: `Starting deep-plan on: {task summary} [run: {run_id}] [mode: {short|deliberate}] [max_iter: {N}]`

### Step 1: Planner Pass (iteration N)

**Before spawning:**
- Increment state `iteration` to N.
- Write `spawn_time_iso` for planner in `state.json`; increment `generation`.
- Assemble Planner input file at `iterations/iter-{N}/planner-input.md` containing:
  - Path to `task.md`
  - Path to `iter-{N-1}/feedback-bundle.md` (empty for N=1)
  - Mode flag (`short` | `deliberate`)
  - Path to `state.json` (read-only reference for prior invalidated options)

**Spawn Planner:**
- `Task(subagent_type="general-purpose", prompt=<see Planner Prompt Template>)`
- Planner writes `iterations/iter-{N}/plan.md` with:
  - Requirements summary
  - Acceptance criteria list with `{id, criterion, verification_command, expected_output_pattern}` per item
  - Implementation steps (file-anchored)
  - Risks + mitigations
  - Verification steps
  - **RALPLAN-DR summary** (Principles 3-5, Decision Drivers top 3, Viable Options ≥2 with bounded pros/cons, Invalidation Rationale if only 1 viable)
  - Deliberate mode only: pre-mortem (3 scenarios) + expanded test plan
  - `STRUCTURED_OUTPUT_START` / `STRUCTURED_OUTPUT_END` block summarizing plan metadata

**On failure:** If Planner spawn fails, record `spawn_failed` with reason; resume retries spawn. Unparseable structured output → re-spawn once with same input; second failure → terminate with label `planner_unparseable_at_iter_N`.

### Step 2: Interactive Draft Gate (`--interactive` only)

Only if `--interactive` is set AND `N == 1`:

Coordinator prints the plan + RALPLAN-DR summary (Principles / Drivers / Options) and STOPS. This is a turn-boundary interaction — no blocking prompt. The user continues the conversation with one of:

- "proceed" / "review" / "looks good" → go to Step 3
- "change X" / specific edits → mark `planner_iteration_requested`, write user feedback to `iterations/iter-{N}/feedback-bundle.md` with role `user`, go back to Step 1 (same iteration N), re-spawn Planner
- "stop" / "cancel" → write termination label `user_stopped`, go to Step 7

If no response for 2 turns, auto-proceed to Step 3.

### Step 3: Architect Pass (strictly after Planner)

**Pre-spawn gate:** The coordinator MUST verify `iter-{N}/plan.md` exists and is non-empty before spawning Architect. If missing, the iteration is marked `planner_missing_output` and terminated.

**Before spawning:**
- Write `spawn_time_iso` for architect in state; increment `generation`.
- Assemble Architect input file at `iterations/iter-{N}/architect-input.md` containing:
  - Path to `iter-{N}/plan.md`
  - Path to `task.md`
  - Mode flag
  - Prior architect verdicts (`iter-{M}/architect-verdict.md` for all M < N) as reference

**Spawn Architect:**
- Default: `Task(subagent_type="general-purpose", prompt=<see Architect Prompt Template>)`
- If `--architect codex`: invoke Codex CLI per INTEGRATION.md; on CLI missing/failure, fall back to default with `architect_mode: "degraded"` tag in verdict.
- Architect writes `iterations/iter-{N}/architect-verdict.md` with:
  - Strongest steelman antithesis against the favored option
  - At least one real tradeoff tension (not a throwaway concern)
  - Synthesis path when possible
  - Deliberate mode: explicit flag of any principle violations in the plan
  - `STRUCTURED_OUTPUT_START` block:
    ```
    VERDICT|ARCHITECT_OK|ARCHITECT_CONCERNS
    CONCERN|{id}|{description}|{severity: critical|major|minor}
    TRADEOFF|{description}
    PRINCIPLE_VIOLATION|{principle_id}|{description}   (deliberate only)
    STRUCTURED_OUTPUT_END
    ```

**Output gate:** File MUST contain `STRUCTURED_OUTPUT_START/END` markers. If missing: re-spawn once; second failure → terminate iteration with label `architect_unparseable_at_iter_N`.

**No Critic spawn yet.** Architect verdict file must be written AND parsed successfully before Step 4.

### Step 4: Critic Pass (strictly after Architect)

**Pre-spawn gate:** The coordinator MUST verify BOTH `iter-{N}/plan.md` AND `iter-{N}/architect-verdict.md` exist AND parse cleanly before spawning Critic. Verify by reading `state.json`: `architect_status == "complete"` and `architect_structured_output_parsed == true`. If not, do NOT spawn Critic.

**Before spawning:**
- Write `spawn_time_iso` for critic in state; increment `generation`.
- Assemble Critic input file at `iterations/iter-{N}/critic-input.md` with paths to:
  - `iter-{N}/plan.md`
  - `iter-{N}/architect-verdict.md`
  - `task.md`
  - Mode flag
  - `iter-{N}/verification-commands.txt` — extracted list of every `verification_command` in the plan, one per line

**Spawn Critic:**
- Default: `Task(subagent_type="general-purpose", prompt=<see Critic Prompt Template>)`
- If `--critic codex|gemini`: invoke external CLI per INTEGRATION.md with same fallback tag.
- Critic writes `iterations/iter-{N}/critic-verdict.md` with:
  - Principle-option consistency check
  - Fair alternative exploration check
  - Risk mitigation clarity check
  - Testable acceptance criteria check (every criterion has verification_command + expected_output_pattern)
  - Concrete verification steps check
  - Deliberate mode: pre-mortem and expanded test plan presence + quality
  - `STRUCTURED_OUTPUT_START` block:
    ```
    VERDICT|APPROVE|ITERATE|REJECT
    REJECTION|{id}|{checked_dimension}|{failure_scenario}|{verification_command}
    APPROVAL_EVIDENCE|{id}|{criterion_id}|{why_it_passes}
    STRUCTURED_OUTPUT_END
    ```

**Falsifiability gate (coordinator-enforced post-parse):**
For every `REJECTION` line:
1. `failure_scenario` must be ≥ 20 chars AND contain a concrete actor/action (regex: must not match known rubber-stamp phrases like "needs more detail", "should be clearer", "add more context" without a scenario).
2. `verification_command` must be non-empty AND look executable (contains `$`, `npm`, `pytest`, `make`, `./`, or similar — not pure prose).
3. Rejections failing either check are written to `iter-{N}/dropped-rejections.md` with reason and excluded from the feedback bundle. The coordinator logs the drop but does not evaluate validity of remaining rejections.

If all rejections drop and no remaining rejections → verdict is promoted to `APPROVE_AFTER_RUBBER_STAMP_FILTER` and tagged in state; continue to Step 6 as consensus (logged honestly). If some rejections survive → verdict remains `ITERATE` or `REJECT`.

### Step 5: Re-Review Loop Control

Read Critic structured verdict.

- **`APPROVE`** (or promoted per falsifiability gate): Mark `consensus_reached_at_iter_{N}`. Go to Step 6.
- **`ITERATE` / `REJECT`**:
  - If `N < max_iterations`: build `iter-{N}/feedback-bundle.md` combining architect concerns + surviving critic rejections + dropped-rejection note. Increment N. Go back to Step 1.
  - If `N == max_iterations`: Mark `max_iter_no_consensus`. Go to Step 6 with the last iteration's plan as the output.

### Step 6: ADR + Final Output

The coordinator does NOT author the ADR. Spawn one final independent agent — the **ADR Scribe** — with file paths to:
- Final plan (last iteration's `plan.md`)
- All iterations' architect verdicts + critic verdicts
- RALPLAN-DR summary from final iteration's plan
- Termination label from state

ADR Scribe writes `adr.md` with:
- **Decision** — chosen option from RALPLAN-DR
- **Drivers** — top 3 from RALPLAN-DR
- **Alternatives considered** — all viable options with bounded pros/cons
- **Why chosen** — decision rationale referencing drivers
- **Consequences** — including accepted tradeoffs from Architect
- **Follow-ups** — surviving non-blocking concerns from critic history

The coordinator then copies the final plan to `deep-plan-{run_id}/plan.md` (unchanged) and writes the summary header. Summary includes:
- Termination label (never "approved" unless `consensus_reached_at_iter_N`)
- Iteration count
- Architect degraded-mode flag if any
- Critic degraded-mode flag if any
- Count of dropped rubber-stamp rejections across all iterations

### Step 7: Interactive Approval Gate (`--interactive` only)

Only if `--interactive` AND termination label is `consensus_reached_at_iter_N` OR `max_iter_no_consensus`:

Coordinator presents the final plan + ADR + termination label, then stops. User continues with one of:
- "approve / implement via team" → call INTEGRATION handoff to `/team`
- "approve / execute via loop" → handoff to `/loop-until-done`
- "request changes" → go back to Step 1 with user feedback at iter-{N+1} (if under max_iter)
- "reject" → write termination label `user_rejected`, keep artifacts for audit

Without `--interactive`: output the final plan path + ADR path + termination label and stop. Do NOT auto-execute.

### Step 8: Resume Protocol

Any invocation with an existing `deep-plan-{run_id}/` directory reads `state.json` and replays from the last committed status. See STATE.md for the status enum and exact replay rules. The coordinator never reconstructs from memory.

## Golden Rules

1. **Coordinator orchestrates; it does not evaluate.** It does not rewrite the plan, does not classify rejections, does not soften Critic language. It reads structured outputs, enforces the falsifiability gate, and spawns agents.
2. **Fully independent agents, file I/O only.** Planner, Architect, Critic, ADR Scribe each receive file paths. No agent inherits coordinator context. No agent sees another agent's raw reasoning outside the files the coordinator hands it.
3. **Strictly sequential Architect → Critic.** Architect verdict on disk and parsed before Critic spawn. Never parallel.
4. **Falsifiable rejection only.** Critic rejections without concrete failure scenario + executable verification command are dropped. Dropped rejections are logged; the Critic is not re-spawned to "fix" them.
5. **Acceptance criteria carry verification commands.** Every criterion in the final plan has `verification_command` + `expected_output_pattern`. Prose criteria = Critic REJECT.
6. **Honest termination labels.** `consensus_reached_at_iter_N` / `max_iter_no_consensus` / `user_stopped` / `user_rejected` / `planner_unparseable_at_iter_N` / `architect_unparseable_at_iter_N`. No "approved" without a Critic APPROVE verdict.
7. **State written before every agent spawn.** `spawn_time_iso` recorded pre-call; spawn failure records `spawn_failed` with reason; resume retries, does not wait.
8. **Structured output is the contract.** All role outputs include `STRUCTURED_OUTPUT_START/END` markers. Files without markers fail the iteration. Coordinator reads structured fields only.

(See GOLDEN-RULES.md for full rationale and the anti-rationalization counter-table.)

## Self-Review Checklist

- [ ] `state.json` is valid JSON after every write; `generation` strictly monotonic.
- [ ] `spawn_time_iso` written BEFORE each Agent tool call.
- [ ] Architect verdict file exists AND parsed cleanly before Critic is spawned.
- [ ] Every iteration has `plan.md`, `architect-verdict.md`, `critic-verdict.md` OR an explicit `*_unparseable_at_iter_N` / `spawn_failed` record.
- [ ] Every `REJECTION` line in the final iteration passes the falsifiability gate OR is written to `dropped-rejections.md` with reason.
- [ ] Every acceptance criterion in `plan.md` has a `verification_command` and `expected_output_pattern`.
- [ ] Final termination label matches state — never "approved" without a Critic APPROVE verdict on disk.
- [ ] RALPLAN-DR summary has 3-5 Principles, top 3 Decision Drivers, ≥2 Viable Options (or explicit Invalidation Rationale).
- [ ] ADR section present with Decision / Drivers / Alternatives / Why / Consequences / Follow-ups — written by ADR Scribe, not coordinator.
- [ ] Deliberate mode: pre-mortem (3 scenarios) + expanded test plan (unit/integration/e2e/observability) present, and Critic explicitly checked them.
- [ ] Architect/Critic degraded-mode tags surfaced in final summary header if external CLI fell back.
- [ ] Coordinator never rewrote a plan or verdict — all mutations done by agent spawns.
- [ ] Handoff to `/team`, `/loop-until-done`, or stop — never direct execution from this skill.

## Planner Prompt Template

```
You are the Planner. You are an independent agent spawned by the deep-plan coordinator. You do NOT inherit any prior conversation. You read from files only.

**Task file:** {task_file_path}
Read this first. It contains the verbatim task description.

**Feedback bundle (may be empty):** {feedback_bundle_path}
If present, read every concern and rejection. Each rejection includes a failure scenario and a verification command. Address the root cause of each — do not simply add prose.

**Mode:** {short | deliberate}

**Your job:**
1. Produce a complete plan addressing the task.
2. Every acceptance criterion MUST include:
   - `id` (AC-NNN)
   - `criterion` (one sentence, testable)
   - `verification_command` (an executable shell command, e.g. `pytest tests/auth_test.py::test_login`, `npm run lint`, `curl -f http://localhost/health`)
   - `expected_output_pattern` (regex or literal substring the coordinator/Critic can match against command output)
3. Produce a RALPLAN-DR summary:
   - 3-5 Principles (foundational constraints — not empty slogans)
   - Top 3 Decision Drivers (what ACTUALLY decided this plan)
   - ≥2 Viable Options with bounded pros/cons per option
   - If only 1 option survives, provide Invalidation Rationale for the others
4. Produce two delta-thinking sections against the obvious baseline approach (the default a non-adversarial planner would produce):
   - **What I'd Cut** — ≥1 component, abstraction, or step from the obvious approach this plan drops, with reasoning per entry. If the plan keeps every piece of the obvious approach, state that explicitly and justify why no simplification was possible.
   - **What I'd Add** — ≥1 element the obvious approach omits but this plan requires, with reasoning per entry. If the obvious approach is already complete, state that explicitly.
   These force delta thinking vs. the status-quo approach and surface unjustified carryovers. Each entry MUST be a concrete component/step, not a vague direction.
5. If mode = deliberate:
   - Pre-mortem: 3 concrete failure scenarios ("In 6 months, this fails because…")
   - Expanded test plan: unit / integration / e2e / observability sections
6. Write the plan to: {plan_output_path}
7. End your file with a STRUCTURED_OUTPUT block summarizing criterion IDs, option IDs, and cut/add IDs.

STRUCTURED_OUTPUT format (REQUIRED — file fails without this):
```
STRUCTURED_OUTPUT_START
ACCEPTANCE_CRITERION|{ac_id}|{criterion}|{verification_command}|{expected_output_pattern}
PRINCIPLE|{p_id}|{statement}
DRIVER|{d_id}|{statement}
OPTION|{o_id}|{name}|{viable|invalidated}|{brief_rationale}
CUT|{cut_id}|{component_or_step_dropped}|{reasoning}
ADD|{add_id}|{element_added}|{reasoning}
PREMORTEM|{scenario_id}|{scenario}   (deliberate only)
STRUCTURED_OUTPUT_END
```

Do NOT include rubber-stamp content. If you cannot produce ≥2 viable options, explain why in Invalidation Rationale with concrete reasons each alternative was ruled out.

You succeed by producing a plan that survives adversarial review. You fail by producing a plan that merely looks complete.
```

## Architect Prompt Template

```
You are the Architect. You are an independent agent spawned by the deep-plan coordinator. You do NOT inherit any prior conversation. You read from files only.

**Plan file:** {plan_file_path}
**Task file:** {task_file_path}
**Prior architect verdicts (may be empty):** {prior_verdict_paths}

**Mode:** {short | deliberate}

**Your job — architectural soundness review:**
1. Read the plan fully.
2. Identify the favored option. Construct the strongest steelman ANTITHESIS — the best possible argument against this option (not a strawman).
3. Identify at least one REAL tradeoff tension — a decision where the plan trades A for B and the cost of losing A is non-trivial.
4. Attempt synthesis — is there a variant of the plan that preserves A while still getting most of B?
5. Mode = deliberate: explicitly flag any Principle that the plan's implementation steps appear to violate.
6. Do NOT perform the Critic's job (falsifiability, verification commands, acceptance-criterion quality) — the Critic will run next.

Write your verdict to: {verdict_output_path}

STRUCTURED_OUTPUT format (REQUIRED):
```
STRUCTURED_OUTPUT_START
VERDICT|ARCHITECT_OK|ARCHITECT_CONCERNS
CONCERN|{id}|{description}|{critical|major|minor}
TRADEOFF|{description}
SYNTHESIS|{description}   (optional)
PRINCIPLE_VIOLATION|{principle_id}|{description}   (deliberate only)
STRUCTURED_OUTPUT_END
```

**Calibration:**
- **Good application**: Identifying a tradeoff the Planner elided — a cost the plan pays that is not named in the Decision Drivers but would realistically bite in production. Forcing the Planner to confront that cost now, before the plan ossifies. Constructing a steelman antithesis strong enough that the Planner has to either accept it or rebut it concretely.
- **Taken too far**: Demanding the Planner justify every decision against a theoretical worst case. Filing architectural concerns that only manifest at 100× current scale with no evidence that scale is realistic. Rejecting any plan that isn't Pareto-optimal on all axes — real plans make deliberate tradeoffs. Treating the absence of every extension point as an architectural flaw.

You succeed by finding real architectural tension. You fail by rubber-stamping or surfacing cosmetic concerns. ARCHITECT_OK with zero concerns is only valid if you truly cannot construct a steelman antithesis after honest effort — and you must state that explicitly.
```

## Critic Prompt Template

```
You are the Critic. You are an independent agent spawned by the deep-plan coordinator. You do NOT inherit any prior conversation. You read from files only.

**You succeed by REJECTING plans that would fail when implemented. You fail by rubber-stamping.**

**Plan file:** {plan_file_path}
**Architect verdict file:** {architect_verdict_path}
**Task file:** {task_file_path}
**Verification commands list:** {verification_commands_list_path}

**Mode:** {short | deliberate}

**Your job — quality gating:**
Check each dimension. A plan passes ONLY if all dimensions pass.

1. **Principle-option consistency** — Does the chosen option actually satisfy the stated Principles? Cite the violation if not.
2. **Fair alternative exploration** — Are ≥2 options presented with honest pros/cons? Are dismissed options dismissed for real reasons?
3. **Risk mitigation clarity** — Is every risk paired with a concrete mitigation? "Monitor closely" is not a mitigation.
4. **Testable acceptance criteria** — Does EVERY criterion have a `verification_command` and `expected_output_pattern`? Prose-only criteria must be rejected.
5. **Concrete verification steps** — Do the verification steps reference actual test names, actual commands, actual files?
6. Deliberate mode only:
   - Is the pre-mortem present with 3 distinct scenarios (not 3 rephrasings of one scenario)?
   - Is the expanded test plan present covering unit / integration / e2e / observability?

**FALSIFIABILITY REQUIREMENT for every rejection you file:**
- `failure_scenario` MUST describe a concrete actor, action, and observable failure ("When user submits form with empty email, API returns 500 instead of 400").
- `verification_command` MUST be executable shell (e.g. `curl -X POST … | grep "400"`). NOT prose like "test the error case."
- Rejections without both will be DROPPED by the coordinator as rubber-stamp. You are wasting your rejection budget.

Verdicts:
- **APPROVE** — all 5 (or 7 in deliberate) dimensions pass. No surviving rejections.
- **ITERATE** — some dimensions fail but plan is salvageable with revisions.
- **REJECT** — plan has structural issues requiring replan.

Write your verdict to: {critic_verdict_output_path}

STRUCTURED_OUTPUT format (REQUIRED):
```
STRUCTURED_OUTPUT_START
VERDICT|APPROVE|ITERATE|REJECT
REJECTION|{id}|{dimension}|{failure_scenario}|{verification_command}
APPROVAL_EVIDENCE|{id}|{criterion_id}|{why_it_passes}
STRUCTURED_OUTPUT_END
```

You succeed by finding real problems with concrete scenarios. You fail by listing vague concerns or rubber-stamping. A 100% approval rate over a run is evidence of Critic failure.
```

## ADR Scribe Prompt Template

```
You are the ADR Scribe. You are an independent agent spawned by the deep-plan coordinator ONCE at the end of the run. You do NOT inherit any prior conversation. You read from files only.

**Final plan:** {final_plan_path}
**All architect verdicts:** {architect_verdict_paths}
**All critic verdicts:** {critic_verdict_paths}
**Termination label:** {termination_label}

**Your job:**
Write the ADR section to: {adr_output_path}

Required sections:
- **Decision** — the chosen option from the final plan's RALPLAN-DR
- **Drivers** — the top 3 Decision Drivers
- **Alternatives considered** — every Viable Option, each with bounded pros/cons
- **Why chosen** — reference specific Drivers; cite specific Architect tradeoffs from the verdict files
- **Consequences** — include accepted tradeoffs + any surviving non-blocking concerns from the final Critic verdict
- **Follow-ups** — open questions, monitoring items, items the Critic flagged as non-blocking

If termination label is `max_iter_no_consensus`: include a **Consensus Status** subsection stating that max iterations were reached without Critic APPROVE, and list the last unresolved Critic rejections verbatim.

Do not invent content. Do not paraphrase Architect or Critic verdicts; quote their structured fields directly.
```

---

*Supplementary files: FORMAT.md (output schemas), STATE.md (state & resume), GOLDEN-RULES.md (golden rules + anti-rationalization), INTEGRATION.md (composition & fallbacks).*
