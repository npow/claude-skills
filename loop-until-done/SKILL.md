---
name: loop-until-done
description: Use when a task must be driven to guaranteed completion through a PRD-driven persistence loop — breaking work into user stories with structured acceptance criteria, iterating story-by-story with independent verification, and terminating only when every criterion has fresh passing evidence and an independent reviewer approves. Trigger phrases include "keep going until done", "loop until complete", "don't stop until", "finish this completely", "iterate until done", "persistence loop", "PRD-driven execution", "work through all stories", "drive this to completion", "until all tests pass", "keep iterating", "loop this", "self-loop until finished". Honest termination labels; no self-approval.
user_invocable: true
argument: |
  Task description, with optional flags:
    --no-prd                          skip PRD generation (legacy single-task mode)
    --no-deslop                       skip post-review deslop pass
    --critic=architect|critic|deep-qa|codex
                                      reviewer selection (default: architect)
    --budget=N                        iteration budget cap (default: 25)
    --resume=<run_id>                 resume a prior run from state.json
---

# Loop Until Done

PRD-driven persistence loop. Given a task, decompose it into user stories with structured, falsifiable acceptance criteria, iterate story-by-story until every criterion has fresh passing evidence, then gate completion behind two-stage independent review. Output is working, verified code plus an honest termination label.

## Execution Model

Contracts are non-negotiable:

- **All data passed via files.** PRD content, story criteria, reviewer inputs, verification evidence — all written to disk before any agent spawn. Inline content is silently truncated.
- **State written before agent spawn.** `spawn_time_iso` written to `state.json` before the Agent tool call. Spawn failure records `spawn_failed`, not "spawned but silent." Resume retries spawn; does not wait.
- **Structured output is the contract.** Judges, reviewers, verifiers produce machine-parseable lines between `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` markers. Free-text is ignored. Unparseable output → fail-safe rejected.
- **No coordinator self-approval.** The coordinator orchestrates. Every approval (PRD falsifiability, criterion pass, story completion, final sign-off) is produced by an independent agent reading from files.
- **Iron-law verification gate.** A story cannot be marked `passes: true` until every criterion has a fresh `last_verified_at` from this iteration AND the `expected_output_pattern` was matched in the verification run's captured output.
- **Termination labels are honest.** Four defined labels cover all reachable exits — never "complete" without evidence. See the Termination Labels table.

**Shared contracts:** this skill inherits the four execution-model contracts (files-not-inline, state-before-agent-spawn, structured-output, independence-invariant) from [`_shared/execution-model-contracts.md`](../_shared/execution-model-contracts.md). The items listed above are the skill-specific elaborations; the shared file is authoritative for the base contracts.

**Subagent watchdog:** every `run_in_background=true` spawn (story worker, independent verifier, reviewer) MUST be armed with a staleness monitor per [`_shared/subagent-watchdog.md`](../_shared/subagent-watchdog.md). Use Flavor A with thresholds `STALE=10 min`, `HUNG=30 min` for story workers (may run tests/builds); `STALE=5 min`, `HUNG=20 min` for verifier/reviewer agents. A hung worker silently blocks the whole persistence loop — `TaskOutput` status is not evidence of progress. Contract inheritance: `timed_out_heartbeat` joins this skill's per-iteration story-level termination vocabulary; `stalled_watchdog` / `hung_killed` join per-worker state. A watchdog-killed worker's criteria stay `passes: false` regardless of partial output — iron-law verification gate blocks story completion until the story is retried or the run terminates as `blocked_unresolved`.

## Philosophy

Complex tasks fail silently. Partial implementations get declared "done"; tests get skipped; edge cases get forgotten. This loop prevents silent failure by forcing the work to pass through four independent gates before terminating: falsifiability judge (PRD is testable), verifier (criteria pass now), spec-compliance reviewer (implementation matches the plan), and code-quality reviewer (implementation is built well). The coordinator never evaluates.

## Workflow

### Step 0: Input Validation Gate

Before any work begins, validate the task:

**Task rubric** — reject if any apply:
- Too vague to decompose ("make it better") — request specificity
- Single atomic fix (< 5 lines) — suggest delegating directly to an executor agent instead
- Requests harmful output — decline

**Flag parsing:**
- Parse `--no-prd`, `--no-deslop`, `--critic=`, `--budget=`, `--resume=` from the task string
- Store parsed flags in `state.json.config`
- Default `--critic` is `architect`; `--budget` defaults to 25 iterations

**Print:** `Starting loop-until-done on: {task} [run: {run_id}] [critic: {critic}] [budget: {budget}]`

### Step 1: Initialize

- Generate run ID: `$(date +%Y%m%d-%H%M%S)` — e.g., `20260416-153022`
- Create directory structure:
  - `loop-{run_id}/state.json` — run state (see STATE.md)
  - `loop-{run_id}/prd.json` — user stories with structured acceptance criteria (see FORMAT.md)
  - `loop-{run_id}/progress.jsonl` — one line per iteration (structured fields, see FORMAT.md)
  - `loop-{run_id}/verify/` — one file per criterion verification per iteration
  - `loop-{run_id}/reviews/` — spec-compliance and code-quality reviewer outputs
  - `loop-{run_id}/judge/` — independent PRD falsifiability judge outputs
  - `loop-{run_id}/deslop/` — deslop pass records
  - `loop-{run_id}/logs/` — decision audit trail
- If `--resume=<run_id>` was passed: load the existing `state.json`; skip PRD generation; resume from the current iteration. See STATE.md for resume protocol.
- Write initial `state.json` with `generation: 0`, `termination: null`, `config` from Step 0

### Step 2: PRD Generation and Falsifiability Gate (first iteration only)

Skipped if `--no-prd` is set. In legacy mode, treat the task as a single implicit story with the coordinator-supplied criterion "the task description is implemented" — but this mode is discouraged because it bypasses the falsifiability gate.

**Step 2a — Draft:** Spawn a planner agent (Sonnet) to read the task and draft `prd.json`:
- Decompose the task into right-sized user stories (each completable in one iteration)
- For each story, write 3-7 structured acceptance criteria with fields `{id, criterion, verification_command, expected_output_pattern, passes: false, last_verified_at: null}`
- Order stories by priority (foundational first, dependent last)
- Write output to `loop-{run_id}/prd.json`

**Step 2b — Independent Falsifiability Judge:** Spawn a judge agent (Sonnet, `subagent_type: general-purpose`). The coordinator does NOT evaluate criterion quality. The judge receives:
- Path to `prd.json`
- Judge prompt template (see Falsifiability Judge Prompt below)

Judge writes one structured verdict per criterion to `loop-{run_id}/judge/falsifiability-{iso_timestamp}.md` with markers:

```
STRUCTURED_OUTPUT_START
CRITERION|{story_id}|{criterion_id}|pass|{rationale}
CRITERION|{story_id}|{criterion_id}|fail|{rationale_with_concrete_failure_mode}
STRUCTURED_OUTPUT_END
```

A criterion passes the falsifiability gate only if the judge returns `pass`. A criterion fails if any of the following hold and the judge must state which:
- `verification_command` is missing or non-executable
- `expected_output_pattern` would match both a passing and a failing implementation
- Criterion is subjective ("code is clean", "reads nicely")
- Criterion is untestable from a terminal (requires human observation)

**Step 2c — Revise on failure:** If ≥ 1 criterion fails the gate, the coordinator writes the failed list to `loop-{run_id}/judge/revise-request-{iter}.md` and re-spawns the planner with the specific failure rationale. Loop 2a-2c up to 3 times; if still failing, abort with label `prd_not_falsifiable_after_3_attempts` (a diagnostic subcase of `blocked_on_story_{id}`).

**Step 2d — Lock:** Once all criteria pass, write `state.json.prd_locked: true` and `state.json.prd_sha256: <hash>`. The coordinator cannot rewrite criteria after this point; new stories may be added but existing criteria are append-only.

### Step 3: Pick Next Story

- Read `prd.json`; select the highest-priority story with `status: pending` or `status: in_progress`
- If all stories have `status: passed`, proceed to Step 7 (final reviewer verification)
- Mark the selected story `status: in_progress` in `prd.json` and increment `state.json.budget.current_iteration`
- Check iteration budget: if `current_iteration > max_iterations`, abort with label `budget_exhausted`
- Append a `progress.jsonl` entry: `iteration_start` event with `story_id`, `iteration`, `timestamp`

### Step 4: Implement the Current Story

Delegate implementation to an executor subagent at the appropriate tier:
- Simple lookups / trivial edits: Haiku
- Standard work: Sonnet
- Complex analysis / architectural changes: Opus

Pass the executor:
- Story path: `loop-{run_id}/prd.json` and the story ID
- Context file: the list of files touched in prior iterations (from `progress.jsonl`)
- Explicit instruction: "Do not modify tests to make them pass. Do not reduce scope. If a criterion is genuinely infeasible, file a `STORY_INFEASIBLE` note in the progress log instead of silently skipping it."
- **Tier-matched work pace** (inject into the executor prompt — Opus 4.7 needs explicit pacing signals):
  - **Haiku stories** (mechanical edits, single-file fixups): `"Prioritize speed over depth; respond directly when uncertain. Ship fast — don't over-engineer."`
  - **Sonnet stories** (standard work against a clear spec): no extra pacing directive.
  - **Opus stories** (architectural / multi-file reasoning / load-bearing decisions): `"Think carefully and step-by-step; this problem is harder than it looks. Reason about edge cases and downstream effects before writing."`

If during implementation the executor discovers sub-tasks, the coordinator appends new stories to `prd.json` (never overwrites existing criteria). New stories must pass the falsifiability gate before their first iteration — re-run Step 2b on the newly added story only.

Run long operations (builds, installs, test suites) in background (`run_in_background: true`).

### Step 5: Verify Each Acceptance Criterion (Iron-Law Gate)

For EACH acceptance criterion in the current story:

1. Run the criterion's `verification_command` and capture stdout + stderr to `loop-{run_id}/verify/{criterion_id}-{iter}.txt`
2. Check whether the captured output matches the `expected_output_pattern` (substring match, or regex if the pattern begins/ends with `/`)
3. Update the criterion in `prd.json`:
   - `passes: true` and `last_verified_at: <iso>` if matched
   - `passes: false` and `last_verified_at: <iso>` if not matched
4. Append a `progress.jsonl` entry: `criterion_verified` event with `criterion_id`, `passes`, `verify_output_path`

**Iron-law:** A story may be marked `status: passed` ONLY when EVERY criterion has `passes: true` AND `last_verified_at` is from this iteration (strictly: a timestamp greater than `state.json.iteration_started_at`). Stale `passes: true` from a prior iteration does NOT count — evidence must be fresh this iteration.

If any criterion fails: do NOT mark the story passed. Return to Step 4 with the failed criteria as the focus. Do not mutate criteria to make them pass — this is forbidden (see GOLDEN-RULES.md).

**Degraded verification mode:** If `deep-qa` is not available and `--critic=deep-qa` was NOT requested, Step 5 proceeds with command execution only (no deep-qa audit during per-criterion verification). Record `state.json.verification_mode: "basic"` so the final report can flag it.

### Step 6: Mark Story Passed and Advance

When every criterion in the current story has fresh matching evidence:
- Set the story `status: passed` in `prd.json`
- Append a `progress.jsonl` entry: `story_passed` event with `story_id`, `iteration`, `files_modified` (captured from the executor's output)
- Loop back to Step 3 (pick next story)

### Step 7: Two-Stage Reviewer Verification

Fired once all stories are `passed`. The coordinator does NOT approve the run itself — two independent reviewers read from files and render verdicts.

**Step 7a — Spec-Compliance Review (matches the plan?):**

Spawn a reviewer agent selected by `--critic`:
- `--critic=architect` (default): `subagent_type: oh-my-claudecode:architect` if available, else Sonnet `general-purpose`
- `--critic=critic`: `subagent_type: oh-my-claudecode:critic`
- `--critic=codex`: `omc ask codex --agent-prompt critic`
- `--critic=deep-qa`: invoke deep-qa in `--diff` mode against the session's file delta (see INTEGRATION.md)

Reviewer receives:
- `loop-{run_id}/prd.json` path
- `loop-{run_id}/verify/` directory path (all verification evidence)
- Git diff of the session's modifications
- Spec-compliance reviewer prompt (see Reviewer Prompt Template below)

Reviewer writes verdict to `loop-{run_id}/reviews/spec-compliance-{iter}.md` with structured markers:

```
STRUCTURED_OUTPUT_START
VERDICT|approved|
VERDICT|rejected|{one_line_reason}
REASON|{defect_id}|{story_id}|{criterion_id_or_NONE}|{severity}|{description}
STRUCTURED_OUTPUT_END
```

**Step 7b — Code-Quality Review (built well?):**

Spawned in parallel with 7a (independent agent, different prompt). Same reviewer tier but a distinct prompt focusing on structural quality:
- Unused code, dead branches, duplication
- Error handling completeness
- Obvious security issues (input validation, injection surfaces)
- Test adequacy against the criterion set

Reviewer writes verdict to `loop-{run_id}/reviews/code-quality-{iter}.md` with the same structured marker format.

**Step 7c — Gate:**

Both verdicts must parse AND return `VERDICT|approved|` for the loop to proceed. If either returns `VERDICT|rejected|` or is unparseable:
- Increment `state.json.reviewer_rejection_count`
- Append the rejection reasons to the current iteration's `progress.jsonl` entry
- If `reviewer_rejection_count > 5`: abort with label `reviewer_rejected_5_times`
- Otherwise: the coordinator writes the rejection reasons to `loop-{run_id}/reviews/feedback-for-iter-{n}.md`, re-queues the failed stories (setting their `status` back to `in_progress` and flipping `passes: false` on whichever criteria the reviewer flagged), and returns to Step 3

### Step 8: Deslop Pass (preserved from OMC)

Skipped if `--no-deslop` is set.

After reviewer approval but BEFORE final completion, invoke `oh-my-claudecode:ai-slop-cleaner` on the file delta from the session (scope MUST be bounded to session-modified files only; do not broaden to unrelated files). Record:
- Path to cleaner output: `loop-{run_id}/deslop/cleaner-output-{iter}.md`
- Files modified by the cleaner

**Post-deslop regression gate:** After the deslop pass, RE-RUN every acceptance criterion's `verification_command` in every story. If any criterion that previously passed now fails:
- Roll back the cleaner's edits that introduced the regression (or fix the regression directly)
- Re-run the verification
- Loop this mini-gate until post-deslop verification matches pre-deslop verification

Degraded mode: if `ai-slop-cleaner` is not installed, skip with explicit `state.json.deslop_mode: "skipped_unavailable"` and tag the final report accordingly.

### Step 9: Final Completion

Only reachable when Steps 2d, 6, 7c, and 8 all succeeded:

- Set `state.json.termination: "all_stories_passed"`
- Write the final summary to `loop-{run_id}/summary.md` (template below)
- Append final `progress.jsonl` entry: `run_complete` event
- Print the termination label and summary path

## Termination Labels

Four labels cover all reachable exits. Never "complete" without matching evidence in files.

| Label | Meaning | Required evidence |
|---|---|---|
| `all_stories_passed` | Every story `passes: true`, both reviewers approved, post-deslop regression green | All of: all criteria `passes: true` with fresh `last_verified_at`; both reviewer files contain `VERDICT\|approved\|`; post-deslop re-verification matches pre-deslop |
| `blocked_on_story_{id}` | One or more stories cannot be made to pass; includes PRD gate failures (`prd_not_falsifiable_after_3_attempts`) and executor-reported infeasibility (`STORY_INFEASIBLE` note) | The blocked story's progress entries show ≥ 3 failed iterations or an explicit `STORY_INFEASIBLE` note |
| `budget_exhausted` | `current_iteration > max_iterations` before all stories passed | `state.json.budget.current_iteration > max_iterations` |
| `reviewer_rejected_{count}_times` | Reviewer produced `VERDICT\|rejected\|` more than 5 times on the same iteration's full story set | `state.json.reviewer_rejection_count > 5` |

The coordinator MUST write one of these labels — not "complete", "done", or "finished" — to `state.json.termination` on exit.

## Reviewer Selection

The `--critic` flag chooses the reviewer tier for Step 7:

| Flag | Spec-compliance reviewer | Code-quality reviewer | When to use |
|---|---|---|---|
| `--critic=architect` (default) | oh-my-claudecode:architect or Sonnet general-purpose | same tier, separate spawn | Balanced default for most runs |
| `--critic=critic` | oh-my-claudecode:critic | oh-my-claudecode:critic | Heavier critique; security/arch-sensitive |
| `--critic=codex` | omc ask codex --agent-prompt critic | omc ask codex --agent-prompt critic | Cross-model second opinion |
| `--critic=deep-qa` | deep-qa --diff (parallel critics across QA dimensions) | deep-qa --diff second pass on code-quality dimensions | Highest-rigor audit; many files; production code |

The two reviewer passes (7a and 7b) ALWAYS run as separate independent agent spawns, even when the same critic tier is selected. A single spawn cannot author both verdicts. If `--critic=deep-qa`, the two passes are two distinct `deep-qa` invocations with different angle pools.

## Falsifiability Judge Prompt

```
You are an independent falsifiability judge. Your job is to REJECT acceptance criteria that cannot be objectively verified from a terminal. You are NOT a rubber-stamp.

A 100% pass rate is evidence of failure. Well-decomposed PRDs with 5-10 stories expect 20-40% of criteria to fail this gate on first draft.

Input: {prd_path}

For each criterion in every story, check:
1. Is `verification_command` executable from a terminal with no human input?
2. Would `expected_output_pattern` distinguish a passing implementation from a failing one? (A pattern that matches both is a failure.)
3. Is the criterion objective (not "code is clean", "reads nicely", "feels good")?
4. Can the criterion be falsified — is there a specific scenario where it would NOT match?

Output one line per criterion (no preamble, no summary):

STRUCTURED_OUTPUT_START
CRITERION|{story_id}|{criterion_id}|pass|{one_line_rationale}
CRITERION|{story_id}|{criterion_id}|fail|{one_line_rationale_with_concrete_failure_mode}
STRUCTURED_OUTPUT_END

Failure modes you MUST reject (not warn, reject):
- verification_command is empty, prose, or non-executable
- expected_output_pattern is "success", "no errors", "it works", or any generic token that a broken implementation could also emit
- Criterion depends on human judgment ("code quality is good", "the UI looks right")
- Criterion requires network access to a service the command cannot reach
```

## Reviewer Prompt Template (Step 7a — Spec Compliance)

```
You are an independent spec-compliance reviewer. Your job is to REJECT if the implementation does not match the PRD.

You succeed by finding genuine mismatches. You fail by rubber-stamping.

Inputs (read from files, do not ask the user):
- PRD: {prd_path}
- Verification evidence directory: {verify_dir}
- Git diff of session changes: {diff_path}

For each story in the PRD:
1. Read the story's acceptance criteria and their `expected_output_pattern`
2. Read the corresponding verification output in {verify_dir}/{criterion_id}-{iter}.txt
3. Check: does the output genuinely match the pattern, or is there fake evidence (empty file, "PASS" echoed by the executor, tests skipped)?
4. Check: does the git diff implement what the story describes, or only the test-surface?

Output:

STRUCTURED_OUTPUT_START
VERDICT|approved|
VERDICT|rejected|{one_line_reason}
REASON|{defect_id}|{story_id}|{criterion_id_or_NONE}|{critical|major|minor}|{description}
STRUCTURED_OUTPUT_END

You MUST reject (not warn) if:
- A criterion's verification output was fabricated (empty, or obviously not produced by running the command)
- The implementation satisfies the test but not the story description (test-gaming)
- A criterion is marked `passes: true` but its `last_verified_at` is earlier than the current iteration start
- Tests were deleted or skipped to make criteria pass
```

## Reviewer Prompt Template (Step 7b — Code Quality)

```
You are an independent code-quality reviewer. Your job is to REJECT if the implementation has structural defects, even when it passes the spec.

You succeed by finding structural defects. You fail by rubber-stamping.

Inputs:
- Git diff of session changes: {diff_path}
- File contents: read directly from working tree

Review dimensions (weight each equally; any critical finding rejects):
1. Dead/unused code introduced by this session
2. Error handling: are failure paths handled, or swallowed?
3. Input validation and injection surfaces (SQL, shell, path, regex)
4. Test adequacy: do the tests cover the criterion, or only the happy path?
5. Duplication: does this session add code that duplicates existing utilities?

Output:

STRUCTURED_OUTPUT_START
VERDICT|approved|
VERDICT|rejected|{one_line_reason}
REASON|{defect_id}|quality|{file_path}|{critical|major|minor}|{description}
STRUCTURED_OUTPUT_END

Out of scope (do NOT reject for):
- Spec compliance (that is the 7a reviewer's job)
- Style preferences that do not affect correctness
- Refactoring opportunities that the PRD did not request
```

## Final Summary Template

Written by a Sonnet subagent reading from `state.json`, `prd.json`, and `progress.jsonl` — NOT by the coordinator.

```markdown
# Loop Run Summary — {run_id}

**Task:** {task}
**Termination:** {termination_label}
**Iterations:** {current_iteration} / {max_iterations}
**Reviewer:** {critic}
**Verification mode:** {verification_mode}

## Stories
| ID | Subject | Status | Criteria (passed / total) | Iterations used |
|---|---|---|---|---|

## Evidence
- PRD: `{run_id}/prd.json`
- Progress log: `{run_id}/progress.jsonl`
- Verification outputs: `{run_id}/verify/`
- Reviewer verdicts: `{run_id}/reviews/`

## Reviewer rejections
{count} total; rationale excerpts from `{run_id}/reviews/feedback-*.md`

## Deslop pass
{ran | skipped_unavailable | skipped_no_deslop}

## Known tradeoffs accepted
{any `STORY_INFEASIBLE` or `accepted_tradeoff` entries from progress.jsonl}
```

## Self-Review Checklist

- [ ] `state.json` is valid JSON after every write
- [ ] `generation` counter incremented on every write
- [ ] `prd.json` locked after Step 2d; existing criteria are append-only
- [ ] Every criterion has `{id, criterion, verification_command, expected_output_pattern, passes, last_verified_at}` — no prose-only criteria
- [ ] Falsifiability judge ran on every new criterion (including those added mid-run) before the story's first iteration
- [ ] Every `passes: true` criterion has `last_verified_at > state.json.iteration_started_at` for the iteration that marked it passed
- [ ] No story marked `status: passed` without every criterion having fresh passing evidence this iteration
- [ ] Spec-compliance reviewer (7a) and code-quality reviewer (7b) ran as separate independent spawns
- [ ] Both reviewer files contain `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` markers and a parseable `VERDICT` line
- [ ] Deslop pass ran (or `--no-deslop` set) AND post-deslop regression re-verification produced fresh passing evidence
- [ ] `state.json.termination` is one of the four defined labels — never "complete" or "done"
- [ ] `progress.jsonl` has one line per iteration event, all with structured fields (no freeform prose)
- [ ] Resume protocol (STATE.md) works: relaunch with `--resume=<run_id>` replays from `current_iteration` without re-running finished work
- [ ] Coordinator never authored a reviewer verdict, a falsifiability verdict, or a verification verdict

## Golden Rules

See GOLDEN-RULES.md for the full set and the anti-rationalization counter-table. Short form:

1. **Independence invariant.** Coordinator orchestrates; never evaluates. Falsifiability, verification match, reviewer approval — all delegated to independent agents reading from files.
2. **Iron-law verification gate.** No `passes: true` without fresh evidence from THIS iteration matching `expected_output_pattern` in captured output.
3. **Two-stage review on source modifications.** Spec-compliance (7a) and code-quality (7b) ALWAYS run as separate independent spawns.
4. **Honest termination labels.** Four defined labels. Never "complete" without matching evidence in files.
5. **State written before agent spawn.** `spawn_time_iso` recorded before Agent call. Spawn failure = `spawn_failed`, not "spawned."
6. **Structured output is the contract.** `STRUCTURED_OUTPUT_START/END` markers are mandatory. Unparseable = fail-safe rejected.
7. **All data passed via files.** PRD, verify outputs, reviewer inputs — all on disk before agent spawn.
8. **No coordinator self-approval.** Same context cannot author and approve. Ever.

## Cancellation and Stop Conditions

- User says "stop", "cancel", or "abort": write `state.json.termination: "user_cancelled"` (a diagnostic subcase outside the four labels — reported but not counted as completion) and exit; leave state files intact for later resume
- Same criterion fails 3+ iterations in a row: file a `STORY_INFEASIBLE` note in `progress.jsonl` with rationale; block on that story rather than thrashing
- Reviewer approval rate > 95% over 10+ reviews: file a `REVIEWER_POSSIBLY_BROKEN` log entry and require a second reviewer for the next completion attempt (adversarial check — a rubber-stamping reviewer is as broken as a rubber-stamping critic)

## Related Files

- `FORMAT.md` — prd.json schema, progress.jsonl schema, verdict format
- `STATE.md` — state.json schema, resume protocol, iteration budget tracking
- `GOLDEN-RULES.md` — 8 cross-cutting rules + anti-rationalization counter-table
- `INTEGRATION.md` — deep-qa composition, deslop pass, degraded-mode fallbacks
