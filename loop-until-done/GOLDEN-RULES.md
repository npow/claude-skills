# Golden Rules

Eight cross-cutting rules apply to every `/loop-until-done` run. These absorb the npow/deep-design independence invariant, superpowers/verification-before-completion, and superpowers/subagent-driven-development — tailored with concrete examples for this skill.

A run that violates any of these rules is broken even if it appears to succeed. The rules are enforced by the self-review checklist in SKILL.md and by the state invariants in STATE.md.

## The Eight Rules

### 1. Independence invariant

The coordinator orchestrates; it never evaluates. Every load-bearing evaluation — falsifiability, verification match, reviewer approval, rubber-stamp detection — is delegated to an independent agent reading from files.

- **Concrete:** The coordinator does NOT decide whether `expected_output_pattern: "success"` is falsifiable. The falsifiability judge does. The coordinator does NOT decide whether the spec-compliance reviewer's rejection is valid; it acts on the structured verdict.
- **Corollary:** When the coordinator reads verification output and checks the pattern match, it is executing a mechanical `grep` equivalent — not evaluating. If the "evaluation" requires judgment, it must be an agent.

### 2. Iron-law verification gate

No story is marked `passes: true` until every criterion has fresh `last_verified_at` from THIS iteration AND the captured output matches `expected_output_pattern`.

- **Concrete:** Story US-003 had AC-003-1 and AC-003-2 pass in iteration 5. In iteration 8, we touched the code for US-003 again. BOTH criteria must re-run in iteration 8 — stale passing evidence from iteration 5 does NOT count.
- **Corollary:** If the executor claims "I ran the tests, they pass," the coordinator MUST still run `verification_command` and read the captured output. Executor claims are not evidence.

### 3. Two-stage review on source modifications

Every completion gate runs BOTH spec-compliance review (7a) and code-quality review (7b) as SEPARATE INDEPENDENT agent spawns. Same critic tier is fine; same spawn is not.

- **Concrete:** `--critic=architect` runs two architect spawns with two different prompts reading from two different files. Not one architect spawn that "also checks quality."
- **Corollary:** If the task modifies only a single file with < 100 lines, the two reviews still both run. The rule has no "small change" exception.

### 4. Honest termination labels

Four defined labels cover all reachable exits. Never "complete", "done", or "finished" without matching evidence in files.

| Label | What it means | What it does NOT mean |
|---|---|---|
| `all_stories_passed` | Every criterion verified fresh this session + both reviewers approved + post-deslop regression green | "the task is finished" — it means the PRD's criteria pass, which may or may not match user intent |
| `blocked_on_story_{id}` | A specific story cannot be made to pass | "the task is impossible" — only that the coordinator found no path |
| `budget_exhausted` | Iteration budget hit before all stories passed | "the code doesn't work" — it may partially work |
| `reviewer_rejected_{count}_times` | Reviewer said no five times | "the code is bad" — reviewer rejections are hypotheses, not facts |

- **Concrete:** Task finishes with 4/5 stories passed. Label is `blocked_on_story_US-005`, NOT `partial_complete` or `mostly_done`.

### 5. State written before agent spawn

`spawn_time_iso` is written to `state.json` BEFORE the Agent tool call, not after. Spawn failure records `spawn_failed`, not "spawned but silent." Resume retries spawn; does not wait.

- **Concrete:** Before spawning the falsifiability judge: write `spawns.falsifiability_judge_iter1_attempt1` with `spawn_time_iso: <now>`, `status: "in_progress"`. Only THEN call the Agent tool. If the tool returns an error, update `status: "spawn_failed"` and set `spawn_time_iso: null`.
- **Corollary:** Resume treats `in_progress` with missing output file as `timed_out` (not re-spawned silently); resume treats `spawn_failed` as "retry."

### 6. Structured output is the contract

Judges, reviewers, verification outputs all produce machine-parseable lines between `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` markers. Free-text is ignored. Unparseable output → fail-safe rejected.

- **Concrete:** If the reviewer produces a beautifully written multi-page analysis with no markers, the coordinator treats it as `VERDICT|rejected|unparseable_verdict`. The reviewer is not trusted to have approved.
- **Corollary:** This is not punitive — it is mechanical. The coordinator cannot read free-text without evaluating, and the coordinator never evaluates (Rule 1).

### 7. All data passed via files

PRD content, verify outputs, reviewer inputs, deslop outputs, judge inputs — everything goes on disk BEFORE the agent is spawned. Inline content in agent prompts is silently truncated and loses fidelity.

- **Concrete:** To spawn the spec-compliance reviewer, write `{run_id}/reviews/input-{iter}.md` listing: `prd_path`, `verify_dir`, `diff_path`. Pass the reviewer those paths, not the PRD contents inline.
- **Corollary:** If the agent returns a verdict without having read the input files (detectable by e.g. a reviewer approving a story whose verify directory is empty), treat the verdict as unparseable and re-spawn.

### 8. No coordinator self-approval

Same context cannot author and approve. Every approval — PRD falsifiability, story completion, final sign-off, deslop regression — comes from an independent agent.

- **Concrete:** The coordinator cannot say "this PRD looks well-structured, proceeding to Step 3." It must spawn the falsifiability judge. Similarly, the coordinator cannot say "both reviewers seemed satisfied" — it must read the structured `VERDICT` lines.
- **Corollary:** If the coordinator is ever tempted to write prose approving a stage, it is violating this rule. The fix is always to spawn another agent.

## Anti-Rationalization Counter-Table

Under time pressure, the coordinator will invent rationalizations for skipping gates. Each of these has been observed in prior loop runs. When you notice yourself thinking the "Excuse" column, read the "Reality" column and re-run the gate.

| Excuse | Reality |
|---|---|
| "The criterion was verified last iteration — it's still passing." | Stale. Re-run `verification_command` this iteration. `last_verified_at > iteration_started_at` or it doesn't count. |
| "The criteria are close enough to falsifiable; the judge would pass them." | The judge is the judge, not you. Run it. A 100% pass rate on first draft is evidence the judge is broken, not evidence the PRD is good. |
| "This story only touches one file; one reviewer is fine." | Rule 3 has no exception. Two independent spawns, always. |
| "The reviewer gave a thumbs-up in prose." | Unparseable = `rejected` with reason `unparseable_verdict`. Spawn again with a stricter prompt. |
| "The executor said it ran the tests and they pass." | Executor claims are not evidence. Read the captured output. If the output file doesn't exist, the tests weren't run. |
| "The criterion is subjective but the intent is clear." | If the intent is clear, write a concrete `verification_command` that captures it. If you can't, the criterion is not falsifiable — file it as blocked. |
| "I'll mark it passed and verify later." | Never. Iron-law gate is blocking, not advisory. |
| "The deslop pass introduced a regression but the original code works — skip the re-verify." | No. Post-deslop regression MUST re-run every criterion. Roll back the cleaner or fix the regression; do not ship a silently-broken post-deslop state. |
| "Reviewer is approving everything — must be doing great work." | `approved / total_reviews > 0.95` with `total_reviews >= 10` triggers `REVIEWER_POSSIBLY_BROKEN`. A rubber-stamping reviewer is evidence of failure, not success. |
| "The test was flaky and failed once — I'll mark it passed since it passed the second time." | No. The criterion's `verification_command` must produce matching output on THIS verification run. If the test is flaky, the criterion needs to change (e.g., add a retry wrapper to the command, or use a deterministic fixture) — don't silently paper over it. |
| "Story US-004 depends on a service that's down; I'll skip it and mark the run complete." | Label is `blocked_on_story_US-004`. Not `all_stories_passed`. Document the blocker in a `STORY_INFEASIBLE` note. |
| "The final reviewer rejected for a minor issue — I'll override and call it done." | Never. Coordinator cannot override reviewer verdicts. Fix the issue, re-queue the story, re-run the gate. |

## Detection Signals

Self-review during a run should flag these signals. Any of them means the coordinator is drifting off the rails:

- A `passes: true` criterion with `last_verified_at < budget.iteration_started_at` of its passing iteration
- A story `status: passed` with any criterion `passes: false`
- A reviewer verdict file without `STRUCTURED_OUTPUT_START`/`END` markers treated as approved
- `state.json.termination: "complete"` or any non-enum value
- `budget.current_iteration > budget.max_iterations` without `termination: "budget_exhausted"`
- `reviewer_approval_rate.approved / total_reviews > 0.95` without `warning_threshold_approaching_rubber_stamp: true`
- Criteria modified after `prd_locked: true` (non-append-only mutations)
- A spawn with `status: "in_progress"` when `current_phase: "complete"` or `"blocked"`
- A story marked `passed` where the executor's claimed output `files_modified` is empty AND the story's criteria include any test-file criterion (zero-file change passing a test-file criterion means the tests were pre-existing, not written this run)

If any signal fires mid-run, the coordinator writes a `note` event to `progress.jsonl` with `message: "INVARIANT_VIOLATION: <description>"`, halts the current phase, and re-enters the gate that was skipped.
