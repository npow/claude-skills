# Golden Rules

The eight cross-cutting rules tailored to `/deep-plan`, plus the anti-rationalization counter-table. These rules are load-bearing. If you catch yourself writing "this case is an exception," re-read this file before acting.

## The Eight Rules

### 1. Independence invariant
The coordinator orchestrates agent spawns; it never evaluates.

**In `/deep-plan` specifically:**
- The coordinator does NOT decide whether the plan is good.
- The coordinator does NOT rewrite a Critic rejection ("they probably meant…").
- The coordinator does NOT paraphrase an Architect tradeoff ("the real concern here is…").
- All evaluation is delegated to Planner, Architect, Critic, ADR Scribe — separate Agent spawns reading/writing files only.
- Example violation: the coordinator reads a Critic REJECT, thinks "this concern is already addressed in Step 3", and marks verdict as APPROVE. **Forbidden.** Write the Critic's verbatim rejection to the feedback bundle and re-run the Planner.

### 2. Iron-law verification gate
No completion claims without fresh evidence.

**In `/deep-plan`:**
- "Iteration complete" requires: `plan.md` exists AND parseable structured block, `architect-verdict.md` exists AND parseable, `critic-verdict.md` exists AND parseable.
- "Consensus reached" requires: a Critic verdict of `APPROVE` (or promoted `APPROVE_AFTER_RUBBER_STAMP_FILTER`) physically on disk in the current iteration.
- "Plan validated" requires: every acceptance criterion has a `verification_command` AND `expected_output_pattern` — verified post-Planner by the Critic.
- Example violation: the coordinator observes 4 iterations of ITERATE verdicts, decides the remaining concerns are minor, and writes `consensus_reached`. **Forbidden.** Either Critic says APPROVE or label is `max_iter_no_consensus`.

### 3. Two-stage review — Architect then Critic
Two independent passes, strictly sequential.

**In `/deep-plan`:**
- Architect: architectural soundness — does the plan's structure work?
- Critic: quality gate — are principles, drivers, criteria, risks, and verification commands concrete?
- These are SEPARATE Agent spawns with disjoint prompts. Architect is spawned first, must complete and write a parseable verdict, THEN Critic is spawned.
- Example violation: spawning Architect and Critic in the same parallel batch to save a turn. **Forbidden.** Critic must read Architect's verdict from disk.

### 4. Honest termination labels
Explicit vocabulary; no "approved" without evidence.

**In `/deep-plan` the authoritative label set is in STATE.md. Three labels a user will actually see:**
- `consensus_reached_at_iter_N` — Critic said APPROVE in iter-N.
- `max_iter_no_consensus` — hit N==max_iterations with the last verdict still ITERATE or REJECT.
- `user_stopped` — user said stop at an interactive gate.

**Never:**
- "Approved after 5 iterations" when the last Critic verdict was ITERATE. Use `max_iter_no_consensus`.
- "Consensus reached" when all rejections were rubber-stamp filtered. Use `consensus_reached_at_iter_N` with the `APPROVE_AFTER_RUBBER_STAMP_FILTER` promoted-verdict flag set — and surface the drop count in the final summary.

### 5. State written before agent spawn
`spawn_time_iso` recorded pre-call; spawn failure recorded as `spawn_failed`; resume retries.

**In `/deep-plan`:**
- Before calling `Task(subagent_type="general-purpose", ...)` for Planner: write `iterations[N].planner.spawn_time_iso` and bump `generation`.
- Before external CLI call for `--architect codex` or `--critic codex/gemini`: same rule. State is the single source of truth.
- On Agent error: mark `spawn_failed`, clear `spawn_time_iso`, record `failure_reason`. Resume retries. Do NOT wait for a ghost output file.
- Example violation: calling the Agent tool first "because it's simpler" and writing state only on return. If the tool is killed mid-call, resume cannot distinguish "waiting" from "never ran." **Forbidden.**

### 6. Structured output is the contract
Judges, critics, reviewers produce `STRUCTURED_OUTPUT_START/END` blocks. Free-text is ignored.

**In `/deep-plan`:**
- Planner output must end with a `STRUCTURED_OUTPUT` block containing `ACCEPTANCE_CRITERION`, `PRINCIPLE`, `DRIVER`, `OPTION`, `PREMORTEM` lines.
- Architect output must end with `VERDICT`, `CONCERN`, `TRADEOFF`, optionally `SYNTHESIS` and `PRINCIPLE_VIOLATION`.
- Critic output must end with `VERDICT`, `REJECTION`, `APPROVAL_EVIDENCE`.
- Files without markers are treated as **failed** (not partially consumed). Re-spawn once; second failure terminates the iteration.
- The coordinator reads ONLY the structured block for state mutation. The prose preceding it is not evaluated.

### 7. All data passed via files
Task descriptions, plans, verdicts — all via file paths in agent prompts. Never inline.

**In `/deep-plan`:**
- Planner receives a path to `task.md` and a path to `feedback-bundle.md`. Not the text of those files.
- Architect receives a path to `plan.md`. Not a summary the coordinator wrote.
- Critic receives paths to `plan.md`, `architect-verdict.md`, `verification-commands.txt`.
- ADR Scribe receives an array of file paths for architect/critic verdicts across all iterations.
- Rationale: inline data is silently truncated; file paths are stable and auditable. Also lets agents re-read sections they need.

### 8. No coordinator self-approval
The author cannot approve their own work.

**In `/deep-plan`:**
- The Planner cannot serve as Critic. Separate Agent spawns with disjoint prompts.
- The coordinator cannot mark a plan APPROVE even if "it's obviously correct." Spawn a Critic.
- If the Critic errors repeatedly, the run terminates — the coordinator does not substitute its own verdict.

## Anti-Rationalization Counter-Table

These are the specific rationalizations that creep in during `/deep-plan` runs. When you catch yourself about to say one, STOP and re-read the "Reality" column.

| Excuse | Reality |
|---|---|
| "The Architect and Critic can share the same context this time — it'll save a turn." | No. They must be independent Agent spawns with disjoint prompts. Shared context is shared bias. The whole point is orthogonal review. |
| "Critic already REJECTED twice with the same concern; we've addressed it — just mark APPROVE." | No. Either the Critic says APPROVE on disk or it doesn't. If you've addressed the concern, run another iteration; the Critic will agree. If it won't agree, it's not addressed. |
| "It's iteration 5 and the last Critic was ITERATE — close enough, label it approved." | No. The label is `max_iter_no_consensus`. "Close enough" is a rationalization vector. The user sees the honest label and decides whether to extend or accept the current plan. |
| "The Critic's rejection is vague, I know what they mean — let me rewrite it for the Planner." | No. Apply the falsifiability gate: does it have a concrete failure scenario AND a verification command? If yes, pass it to the Planner verbatim. If no, drop it with reason logged. Coordinator never rewrites Critic output. |
| "This plan is short, a full RALPLAN-DR is overkill — skip the Options section." | No. The Principles/Drivers/Options structure is what prevents solution-space narrowing. A 3-line plan with 1 option = untested decision. Critic MUST reject. |
| "Running in `--deliberate` mode for this small refactor is overkill — run in short mode." | Check the high-risk signals first: auth, security, data migration, destructive ops, production incident, compliance/PII, public API breakage. If any match, deliberate is MANDATORY. "Small refactor of the auth flow" is not small; it hits `auth`. |
| "Codex is down — the `--critic codex` fallback can just skip the Critic this iteration." | No. Fall back to the default Claude Critic with a `degraded` tag in the verdict and a surfaced warning in the final summary. Skipping Critic violates Rule 3 (two-stage review). |
| "The Critic filed 4 rejections but 3 were rubber-stamp phrases — the Critic is broken, just APPROVE." | No. Dropped rejections are logged to `dropped-rejections.md`. If ALL rejections drop, the verdict is promoted to `APPROVE_AFTER_RUBBER_STAMP_FILTER` — honest label, consensus treated as real but the drop count is visible. If ONE real rejection survives, iterate. |
| "The Architect is obsessing over a minor tradeoff — override the concern and proceed to Critic." | No. Architect CONCERNS of `minor` severity do not block Critic. Architect CONCERNS of `critical` severity DO block advance — the Planner must address before Critic sees the plan. Read the severity field; don't judge with your own taste. |
| "Resume from state is tricky — just re-run from iteration 1." | No. Resume protocol in STATE.md preserves all prior iterations' verdicts and the agent_verdict_registry. Re-running from scratch loses the audit trail AND the sunk cost of prior Critic rejections. Read `state.json` and replay per the status enum. |

## Pre-Spawn Checklist (every agent)

Before every Planner / Architect / Critic / ADR Scribe spawn, verify:

- [ ] Input files exist on disk at the paths about to be passed.
- [ ] `state.json` `generation` pre-read captured.
- [ ] `spawn_time_iso` written with fresh ISO timestamp.
- [ ] `agent_verdict_registry.{role}.total_spawns` incremented.
- [ ] Prompt uses FILE PATHS only — no inline plan/task/verdict content.
- [ ] For Critic: Architect verdict file exists AND its `structured_output_parsed == true` in state.
- [ ] For ADR Scribe: termination label already assigned.

## Post-Spawn Checklist (every agent)

After every spawn returns:

- [ ] Output file exists at expected path.
- [ ] File contains `STRUCTURED_OUTPUT_START` and `STRUCTURED_OUTPUT_END` markers — otherwise mark `unparseable`.
- [ ] Structured fields parsed successfully; recorded in `state.json`.
- [ ] `completion_time_iso` set.
- [ ] `status` transitioned to `complete` only if parse succeeded.
- [ ] `agent_verdict_registry` verdict counts updated (if applicable).
- [ ] For Critic: falsifiability gate applied to every REJECTION line; dropped rejections written to `dropped-rejections.md` with reasons.
