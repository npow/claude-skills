# Golden Rules

The eight cross-cutting rules apply to every orchestration skill in this suite. This file tailors them with concrete `/autopilot` examples and adds a skill-specific anti-rationalization counter-table.

## The Eight Rules (autopilot-specific)

### 1. Independence invariant

**The coordinator orchestrates; it never evaluates.** In autopilot, "evaluate" means: classify ambiguity, approve a plan, judge code correctness, assess security, review quality, decide whether a phase is complete, or write any portion of the completion report.

Every load-bearing judgment in autopilot is produced by a fresh independent subagent reading from disk:
- **Phase 0 ambiguity class** — ambiguity-classifier subagent. Coordinator reads `AMBIGUITY_CLASS` field only.
- **Phase 0/1/2/3/4 gate decisions** — phase-gate subagent. Coordinator reads `ADVANCE` field only.
- **Phase 4 per-dimension verdicts** — correctness, security, quality judges. Coordinator reads `VERDICT` field only.
- **Phase 4 aggregation** — allowed as coordinator since it is purely mechanical (count verdicts, apply table). Coordinator may NOT add rationale or override.
- **Completion report content** — completion-report subagent. Coordinator prints the path only.

If at any point the coordinator thinks "I can tell this is fine" — that's the rule firing. Spawn a subagent.

### 2. Iron-law verification gate

**No phase transition without evidence.** Every phase (0 through 4) has a fixed evidence file list in `STATE.md`. Before transition:
- Every required file exists on disk
- Every file with structured output contains the required markers
- Every file's mtime is after `state.json.created_at` (fresh this session)
- The phase-gate subagent emits `ADVANCE: true`

If any condition fails → phase status becomes `blocked` and termination label becomes `blocked_at_phase_N`. Coordinator cannot override.

Example: Phase 2 `/team` returns `partial_with_accepted_unfixed`. The gate passes (label is acceptable), but the unfixed items flow into the completion report under "Accepted Tradeoffs" — they do NOT get quietly dropped.

### 3. Two-stage review on source modifications

Autopilot does not directly modify source. Source modifications happen inside Phase 2 `/team`, which enforces the two-stage rule (spec-compliance then code-quality, separate independent agents) per its own golden rules.

Autopilot's obligation: when Phase 3 fix-loop runs (`/loop-until-done`), it passes `--critic=deep-qa` so each fixed story receives the two-stage treatment via the reviewer. Autopilot never invokes a bare executor without review.

If autopilot appears to "patch something directly" — e.g., writing a temporary fix file — that's a rule violation. Route through `/team` or `/loop-until-done`.

### 4. Honest termination labels

Exhaustive table in SKILL.md. Forbidden: "success", "done", "all complete", "ready to ship", "no issues remain", "pipeline green".

Hard rule: **`complete` requires evidence files for all 5 phases AND zero `UNVERIFIED_COUNT` AND zero `ACCEPTED_TRADEOFFS_COUNT` in the completion report's structured output.** The completion-report subagent enforces this; if the coordinator tries to paste `complete` without qualification, parser rules force the label down to `partial_with_accepted_tradeoffs`.

When reporting to the user, print the structured label verbatim. Do not translate `partial_with_accepted_tradeoffs` to "mostly done" — the user deserves the exact vocabulary.

### 5. State written before delegation

Every phase delegation writes `phases.{phase}.spawn_time_iso` and increments `generation` BEFORE invoking the delegate skill. If the delegate errors or never produces evidence: status becomes `delegation_failed`, not "spawned but silent".

This matters for resume. Session restart reads `state.json`; any phase with `spawn_time_iso` set but no evidence gets re-delegated (within budget). Without the pre-write, a killed session looks like a pending phase and would double-delegate on resume.

Resume retries spawn. Resume does NOT wait for a dead subagent.

### 6. Structured output is the contract

Every judge, critic, gate, and termination file has a `STRUCTURED_OUTPUT_START` / `STRUCTURED_OUTPUT_END` block. Coordinator reads only the fields in that block. Prose above the block is for humans.

Files without the markers are treated as failed (coordinator re-spawns the agent once, then fail-safe classifies as rejected/critical). Free-text in a judge verdict like "this looks good overall, approved" without the structured block produces no approval — the parser sees nothing.

Autopilot-specific: the completion report has its own structured block. `TERMINATION|complete` is only valid if `PHASES_WITH_EVIDENCE == 5` AND `UNVERIFIED_COUNT == 0` AND `ACCEPTED_TRADEOFFS_COUNT == 0`. Violating combination → parser forces label down.

### 7. All data passed via files

Phase delegates receive paths, not content. Examples:
- `/deep-plan --spec {path}` — spec content read from disk by deep-plan
- `deep-qa --diff {modified-files-path}` — file list read from disk
- Judges receive `judge-input.md` containing paths; each judge reads the contents itself
- `/loop-until-done --prd {path}` — PRD JSON read from disk

If the coordinator catches itself constructing an inline prompt with pasted code — that's the rule firing. Write to a file; pass the path.

### 8. No coordinator self-approval at any phase boundary

The coordinator may NEVER decide "this phase looks done" without the phase-gate subagent emitting `ADVANCE: true`. The coordinator may NEVER substitute its own judgment for a rejecting judge (e.g., "the security judge is being paranoid about this one"). The coordinator may NEVER write the completion report itself.

Enforcement: `invariants.coordinator_never_evaluated` in `state.json` is a kill-switch. If ever flipped to `false`, the run is invalid and the completion report MUST surface that fact in the `unverified` section.

Re-validation corollary: if Phase 4 produces a rejection and a fix loop runs, the re-validation judge MUST be a fresh spawn — not the rejecting judge re-asked. Reusing the rejecting judge smuggles coordinator judgment in through "context continuity".

---

## Anti-Rationalization Counter-Table

When the coordinator notices it is starting to think any of these thoughts, stop. The excuse is recognizable; the rule wins.

| Excuse | Reality |
|---|---|
| "Skip QA if the build passes — Phase 2 tests already ran." | Passing tests do not equal a defect audit. `deep-qa --diff` probes dimensions tests do not cover (edge cases, security, maintainability). Phase 3 runs. |
| "Skip Phase 4 — deep-qa was clean and tests pass." | deep-qa audits defects; judges evaluate the whole artifact against plan, security posture, and quality. Different jobs. Phase 4 runs. |
| "I can tell this is low-ambiguity, skip the classifier." | Ambiguity classification is load-bearing (determines routing). Coordinator cannot classify. Spawn the classifier. |
| "The user said 'just build it' — I'll skip Phase 0." | User framing doesn't alter the phase pipeline. Phase 0's output can be a trivial spec if the idea is truly concrete, but the phase still runs and produces evidence. |
| "Phase 4 judge said 'rejected' but I think they missed context — I'll override." | Overriding a judge is coordinator self-approval. Fix the context (e.g., add a conditional requirement), re-spawn a fresh judge, let the new verdict decide. |
| "The security judge always finds something — one low-severity finding is fine to dismiss." | The aggregation rule is mechanical. A low-severity finding that translates to `conditional` does not block; one that translates to `rejected` does. Let the structured output decide, not the coordinator's tolerance for the judge. |
| "The coordinator can aggregate the three verdicts — that's just counting." | True — mechanical aggregation is allowed. But the coordinator may NOT add rationale ("all three approved because the code is clean"). The rule for aggregation: apply the table in FORMAT.md verbatim; no commentary. |
| "The phase-gate subagent said blocked, but I can see the evidence file exists, so I'll mark it complete." | Evidence existing is necessary but not sufficient. The gate checks parseability and freshness. Trust the gate; re-spawn it if you think it was wrong. |
| "Consensus plan hit `max_iter_no_consensus` — I'll patch the plan and continue." | Coordinator patching a plan is authoring Phase 1 output — forbidden. Re-invoke `/deep-plan` with tighter scope, or terminate as `blocked_at_phase_1`. |
| "The fix loop is blocked on story 3; I'll just implement that story directly." | Phase 3 fix loop runs inside `/loop-until-done`. Coordinator directly implementing a story violates both Rule 3 (two-stage review) and Rule 8 (self-approval). Terminate as `blocked_at_phase_3` or reduce scope in `/loop-until-done`. |
| "I already read the spec earlier in this session — no need to re-read for Phase 4." | Rule 7 / Rule 5 combined: every agent reads from disk fresh. Prior reads are stale. Judges read the judge-input paths themselves. |
| "We're past budget — let me skip Phase 4 to deliver something." | Skipping Phase 4 is not an option. Budget-exhausted mid-run produces `budget_exhausted` label with honest reporting. Half-validated code shipped as `complete` is worse than nothing — it misrepresents the work. |
| "The completion report says `unverified_count > 0` but the items are minor — I'll drop them." | Minor or not, `UNVERIFIED_COUNT > 0` forces label `partial_with_accepted_tradeoffs`. The user must see the unverified list. Dropping items is coordinator evaluation. |
| "Re-validation round 2 rejected; let me just try a third round." | Max 2 re-validation rounds. Round 3 is forbidden by the rules. After 2 rounds, `blocked_at_phase_4` is the honest label. |
| "Phase 0 routed to `deep-design` but the user really wanted a quick spec — I'll swap it." | Routing is classifier-decided. Coordinator overriding routing = classifying ambiguity, which is evaluation. If the classifier was wrong, re-invoke the classifier with more context; do not swap the route. |
| "I can use the OMC autopilot's Phase 0 shortcut — `.omc/plans/ralplan-*.md` exists." | We are not OMC. Autopilot runs the full pipeline. If the user wants to re-use a prior plan, they can invoke `/deep-plan` directly and pass its output as the spec — but autopilot's Phase 0 still produces an ambiguity verdict + phase gate for audit trail. |

---

## When a Rule Seems Wrong

If a rule seems to be producing a bad outcome in a specific case:
1. Document the case in `autopilot-{run_id}/rule-friction.md` — specific, evidence-cited.
2. Proceed per the rule. Do not skip.
3. After run completion, raise the friction doc for skill maintenance (update `SKILL.md`, not mid-run override).

The rules exist because coordinator judgment has failed before. A rule that "seems wrong" is usually the coordinator rationalizing an evaluation it is not entitled to make.
