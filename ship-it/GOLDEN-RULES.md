# Golden Rules

The eight cross-cutting rules apply to every orchestration skill in this suite. This file tailors them with concrete ship-it examples and adds a skill-specific anti-rationalization counter-table.

## The Eight Rules (ship-it-specific)

### 1. Independence invariant

**The coordinator orchestrates; it never evaluates.** In ship-it, "evaluate" means: approve a spec, approve a plan, review code correctness, judge security, assess quality, decide a phase is complete, write the completion report, or decide a defect is "minor enough to skip".

Every load-bearing judgment in ship-it is produced by a fresh independent subagent reading from disk:
- **Phase 1 user approval** — the user, not the coordinator. Coordinator records the response verbatim.
- **Phase 2 plan consensus** — `/deep-plan` independent Planner/Architect/Critic. Coordinator reads `CONSENSUS_LABEL` only.
- **Phase 3 code review** — `/team`'s two-stage reviewer pipeline (spec-compliance → code-quality). Coordinator never reviews code.
- **Phase 4 defect audit** — `deep-qa`. Coordinator reads defect registry only.
- **Phase 5 integration fix decisions** — `/loop-until-done` per failing smoke test. Coordinator never hand-patches integration bugs.
- **Phase 6 three-judge verdicts** — correctness, security, quality judges. Coordinator reads `VERDICT` fields only.
- **Phase gate decisions at every transition** — phase-gate subagent. Coordinator reads `ADVANCE` field only.
- **Completion report content** — completion-report subagent. Coordinator prints the path only.

If at any point the coordinator thinks "I can tell this is fine" — that's the rule firing. Spawn a subagent.

### 2. Iron-law verification gate

**No phase transition without fresh evidence.** Every phase (1 through 6) has a fixed evidence file list in [STATE.md](STATE.md). Before transition:
- Every required file exists on disk
- Every file with a structured block contains the required markers
- Every file's mtime is after `state.json.created_at` (fresh this session)
- The phase-gate subagent emits `ADVANCE: true`

If any condition fails → phase status becomes `blocked`; termination label becomes `blocked_at_phase_N`. Coordinator cannot override.

Example: Phase 3 `/team` returns `partial_with_accepted_unfixed`. The gate passes (label is acceptable for advance), but the unfixed items flow into the completion report under "Accepted Tradeoffs" — not quietly dropped.

Example: Phase 6 `clean-install-output.txt` shows `npm install` exit code 0 but `npm run build` exit code 1 — gate fails. Coordinator does not decide "the build mostly works". Fix via `/loop-until-done` and re-run the clean-install cycle, or terminate as `blocked_at_phase_6`.

### 3. Two-stage review on source modifications

Ship-It does not directly modify source. Source modifications happen inside Phase 3 `/team`, which enforces the two-stage rule (spec-compliance then code-quality, separate independent agents) per its own golden rules.

Ship-It's obligation: Phase 4 fix-loop invokes `/loop-until-done --critic=deep-qa` so each fixed story receives the deep-qa treatment. Phase 5 integration fixes route through `/loop-until-done` rather than coordinator-authored patches.

If ship-it appears to "patch something directly" — e.g., adding a missing import in integrate/, hand-editing a test — that's a rule violation. Route through `/loop-until-done` or `/team`.

### 4. Honest termination labels

Exhaustive table in SKILL.md. Forbidden: "success", "done", "all complete", "ready to ship", "shipped", "no issues remain", "pipeline green".

Per-phase labels are tracked in `state.json` and surfaced in the completion report. The top-level run label is derived mechanically:

- `complete` requires evidence files for all 6 phases AND zero `UNVERIFIED_COUNT` AND zero `ACCEPTED_TRADEOFFS_COUNT` AND `CLEAN_INSTALL_PASSED == true` in the completion report's structured output.
- Any violation → parser rules force the label down to `partial_with_accepted_tradeoffs`.
- `blocked_at_phase_N` is not negotiable — if the gate failed at phase N, the label is `blocked_at_phase_N` regardless of what later phases might have done.

When reporting to the user, print the structured label verbatim. Do NOT translate `partial_with_accepted_tradeoffs` to "mostly done". The user deserves the exact vocabulary.

### 5. State written before delegation

Every phase delegation writes `phases.{phase}.spawn_time_iso` and increments `generation` BEFORE invoking the delegate skill. If the delegate errors or never produces evidence: status becomes `delegation_failed`, not "spawned but silent".

This matters for resume. Session restart reads `state.json`; any phase with `spawn_time_iso` set but no evidence gets re-delegated within budget. Without the pre-write, a killed session looks like a pending phase and would double-delegate on resume.

Resume retries spawn. Resume does NOT wait for a dead subagent.

### 6. Structured output is the contract

Every judge, critic, gate, and termination file has a `STRUCTURED_OUTPUT_START` / `STRUCTURED_OUTPUT_END` block. Coordinator reads only the fields in that block. Prose above is for humans.

Files without the markers are treated as failed (coordinator re-spawns once, then fail-safe classifies as rejected/critical). Free-text in a judge verdict like "this looks good overall, approved" without the structured block produces no approval — the parser sees nothing.

Ship-It-specific: the completion report has its own structured block. `TERMINATION|complete` is only valid if `PHASES_WITH_EVIDENCE == 6` AND `UNVERIFIED_COUNT == 0` AND `ACCEPTED_TRADEOFFS_COUNT == 0` AND `CLEAN_INSTALL_PASSED == true`. Violating combination → parser forces label down.

### 7. All data passed via files

Phase delegates receive paths, not content. Examples:
- `/deep-plan --spec ship-it-{run_id}/spec/SPEC.md` — spec content read from disk
- `/team --plan ship-it-{run_id}/design/DESIGN.md --output ship-it-{run_id}/build/` — plan read from disk
- `deep-qa --diff ship-it-{run_id}/build/modified-files.txt` — file list read from disk
- Judges receive `judge-input.md` containing paths; each judge reads contents itself
- `/loop-until-done --prd ship-it-{run_id}/test/fix/prd.json` — PRD JSON read from disk

If the coordinator catches itself constructing an inline prompt with pasted code, spec, or defect — that's the rule firing. Write to a file; pass the path.

### 8. No coordinator self-approval at any phase boundary

The coordinator may NEVER decide "this phase looks done" without the phase-gate subagent emitting `ADVANCE: true`. The coordinator may NEVER substitute its own judgment for a rejecting judge (e.g., "the security judge is being paranoid about secrets in test fixtures"). The coordinator may NEVER write the completion report itself.

Enforcement: `invariants.coordinator_never_evaluated` in `state.json` is a kill-switch. If ever flipped to `false`, the run is invalid and the completion report MUST surface that fact in the `unverified` section.

Re-validation corollary: if Phase 6 produces a rejection and a fix loop runs, the re-validation judge MUST be a fresh spawn — not the rejecting judge re-asked. Reusing the rejecting judge smuggles coordinator judgment in through "context continuity".

---

## Anti-Rationalization Counter-Table

When the coordinator notices it is starting to think any of these thoughts, stop. The excuse is recognizable; the rule wins.

| Excuse | Reality |
|---|---|
| "Tests pass locally so we're good" | Local pass ≠ clean-install pass. Phase 6 clean-install is the reproducibility gate. Run `rm -rf node_modules dist && npm install && npm run build && npm test` and capture output. |
| "We'll add the integration tests in a follow-up" | Phase 5 requires smoke tests in THIS session. Deferred integration = shipped-without-integration. Write them now, run them now, capture output. |
| "This is the MVP we can iterate" | MVP framing doesn't exempt the phase gates. `complete` label requires the same evidence for MVP as for v2. If the scope was truly MVP, Phase 1 spec should have said so; that doesn't shrink the validation requirement. |
| "The docs are obvious from the code" | README.md is evidence for the quality judge. "Obvious" is coordinator evaluation. Let the quality judge audit the README against SPEC.md. |
| "Skip deep-qa if the tests pass — Phase 3 tests already ran" | `/team`'s internal tests verify `/team` stages. Phase 4 `deep-qa --diff` audits defects the tests don't cover (edge cases, security, maintainability, disputed behavior). Different jobs. Run deep-qa. |
| "Skip Phase 6 judges — deep-qa was clean and tests pass" | deep-qa audits defects at the code level; judges evaluate the whole artifact against spec, security posture, and quality at shipping time. Different jobs. The 3 judges run. |
| "The user said 'just ship it' — I can skip the spec approval" | User urgency doesn't waive Phase 1 user-approval. A one-line spec is fine; a missing spec blocks the gate. User must explicitly OK the spec artifact. |
| "Phase 6 judge said rejected but I think they missed context — I'll override" | Overriding a judge is coordinator self-approval. Fix the context (e.g., add a conditional requirement), re-spawn a fresh judge, let the new verdict decide. 2-round cap. |
| "The security judge always finds something — one low-severity finding is fine to dismiss" | Aggregation is mechanical. A low-severity finding that maps to `conditional` does not block; one that maps to `rejected` does. Let the structured output decide, not the coordinator's tolerance. |
| "The coordinator can aggregate the three judge verdicts — that's just counting" | True — mechanical aggregation is allowed. But the coordinator may NOT add rationale ("all three approved because the code is clean"). Apply the table in FORMAT.md verbatim; no commentary. |
| "types.ts needs a quick tweak during build — it's still early" | `types.ts` is immutable after Phase 2 ends. Type changes mid-build cause integration failures that appear later as mysterious build errors. If the type is wrong, re-open Phase 2 via `/deep-plan`; do not patch during Phase 3. |
| "The clean-install test failed with a transient network error — let me mark it passed" | Transient ≠ absent. Re-run the clean-install until it passes deterministically OR investigate the flakiness. Never paper over a failed clean-install; reproducibility is the shipping gate. |
| "Phase 5 smoke test failed but the unit tests all pass — this is fine" | Smoke tests exist because unit-passing integration-failing is the classic ship-it bug. Smoke failure → fix via `/loop-until-done`. Not optional. |
| "I already read the spec earlier in this session — no need to re-read for Phase 6" | Rule 7 / Rule 5 combined: every agent reads from disk fresh. Prior reads are stale. Judges read the judge-input paths themselves. |
| "We're past budget — let me skip Phase 6 to deliver something" | Skipping Phase 6 is not an option. Budget-exhausted mid-run produces `budget_exhausted` label with honest reporting. Half-validated code shipped as `complete` is worse than nothing — misrepresents the work. |
| "The completion report says `unverified_count > 0` but the items are minor — I'll drop them" | Minor or not, `UNVERIFIED_COUNT > 0` forces label `partial_with_accepted_tradeoffs`. User must see the unverified list. Dropping items is coordinator evaluation. |
| "Re-validation round 2 rejected; let me try a third round" | Max 2 re-validation rounds. Round 3 is forbidden. After 2 rounds, `blocked_at_phase_6` is the honest label. |
| "Consensus plan hit `max_iter_no_consensus` — I'll patch the plan and continue" | Coordinator patching a plan is authoring Phase 2 output — forbidden. Re-invoke `/deep-plan` with tighter scope, or terminate as `blocked_at_phase_2`. |
| "The TODO is a known limitation, not a blocker" | If the TODO is intentional, annotate it in-line so the grep-scan finds it AND the comment explains why. Then `stub-scan.txt` reports it as `ANNOTATED_INTENTIONAL`, not `UNANNOTATED`. Annotation is evidence; "known to me" is not. |
| "Git init is optional for this project" | Phase 6 evidence requires an initial commit. No commit → no audit trail → cannot establish what shipped. Commit always; push only on explicit user request. |

---

## When a Rule Seems Wrong

If a rule seems to be producing a bad outcome in a specific case:
1. Document the case in `ship-it-{run_id}/rule-friction.md` — specific, evidence-cited.
2. Proceed per the rule. Do not skip.
3. After run completion, raise the friction doc for skill maintenance — update SKILL.md, not mid-run override.

The rules exist because coordinator judgment has failed before. A rule that "seems wrong" is usually the coordinator rationalizing an evaluation it is not entitled to make.
