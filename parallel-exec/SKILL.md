---
name: parallel-exec
description: Use when running multiple independent tasks in parallel with per-task verification — batch edits, multi-file refactors, independent subtasks across a codebase, multi-module updates, parallel research, or any fanout work. Trigger phrases include "run these in parallel", "parallel tasks", "fanout", "do these tasks concurrently", "parallel execution", "run all of these at once", "batch these tasks", "execute in parallel", "dispatch in parallel", "multiple subagents", "parallel subagents", "parallelize this work", "run N agents", "concurrent task execution". Fires N subagents in parallel with model-tier routing, mandatory per-task verification, and an independent convergence-checker agent to detect conflicts, flaky tasks, and unverified claims before any aggregate completion is claimed.
argument-hint: A batch of task specs (JSON array) or a natural-language description of parallel work with per-task verification targets
---

# Parallel Exec Skill

Fire N independent subagents in parallel, route each to the appropriate model tier, enforce per-task verification, and run an independent convergence checker before any aggregate completion is claimed. Output is a per-task result registry labeled `passed_with_evidence / failed_with_error / conflicted_with_sibling / unverified`, plus a convergence-check verdict — never a flat "all tasks complete" claim.

## Execution Model

All operations use Claude Code primitives (Task, Read, Write, Bash). The following contracts are non-negotiable:

- **Every task spec carries a mandatory `verification_command`.** Fire-and-forget is prohibited. A task without a command cannot be dispatched.
- **Task specs and results passed to agents via files, never inline.** Each task's prompt, inputs, and verification command are written to disk before the subagent is spawned. Inline data is silently truncated.
- **State written before subagent spawn, not after.** `spawn_time_iso` is written to `state.json` before the Task tool call. Spawn failure records `status: spawn_failed`, not "spawned but silent." Resume retries the spawn.
- **Convergence check is an independent agent.** The coordinator never evaluates whether the batch succeeded. A fresh agent reads all task outputs from disk and produces a structured verdict.
- **Structured output is the contract.** Per-task results and convergence verdicts are machine-parseable blocks enclosed in `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` markers. Free-text is ignored. Unparseable → fail-safe `unverified`.
- **Iron-law gate.** No aggregate "all tasks complete" claim until convergence-check structured output is received and parsed. Missing output → fail-safe; the coordinator reports `aggregate_status: convergence_check_failed` with evidence paths.
- **Coordinator never grades tasks.** Per-task labels (`passed_with_evidence`, `failed_with_error`, `conflicted_with_sibling`, `unverified`) come from the convergence checker — not the coordinator's inspection of task stdout.

## Philosophy

Parallelism is cheap; undetected conflicts are expensive. Two subagents modifying the same file in parallel is not a completion — it is a race. This skill treats parallel execution as **fanout-then-reconcile**: fan N tasks to N tiered workers, each produces evidence via its verification command, then an independent reconciler reads all evidence files and surfaces the true state of the world. No task is "done" until the reconciler says so, and every claim is backed by a file on disk.

## Workflow

### Step 0: Input Validation Gate

Before any work begins, validate the task batch.

**Task-batch rubric** — reject if any of these apply:

- No tasks, or fewer than 2 parallelizable tasks — parallel-exec is the wrong tool (delegate directly to one executor).
- Any task lacks a `verification_command` — prompt user to add one; do not substitute a default.
- Any task has a `depends_on` cycle — reject with the cycle printed.
- A task prompt is "fix the whole repo" or otherwise unscoped — reject with rationale; demand concrete file/module targets.
- Two tasks modify the same path and are not in a `depends_on` chain — flag as conflict risk; require user confirmation.

**Print:** `Starting parallel-exec on {N} tasks [run: {run_id}]`

### Step 1: Initialize

- Generate run ID: `parallel-exec-$(date +%Y%m%d-%H%M%S)` — e.g., `parallel-exec-20260416-153022`.
- Create directory structure in the CWD:
  - `parallel-exec-{run_id}/state.json` — authoritative run state (see STATE.md).
  - `parallel-exec-{run_id}/specs/` — one file per task: `{task_id}.json`.
  - `parallel-exec-{run_id}/results/` — one file per task: `{task_id}.md` (subagent output + verification-command output).
  - `parallel-exec-{run_id}/verify/` — raw verification command stdout/stderr per task: `{task_id}.stdout`, `{task_id}.stderr`, `{task_id}.exit`.
  - `parallel-exec-{run_id}/convergence/` — convergence-checker output file with structured markers.
  - `parallel-exec-{run_id}/logs/` — `dispatch_log.jsonl` (one line per spawn) and `dependency_graph.json`.
- Parse user input into task specs using the schema below. Each spec is written to its own file **before** dispatch.

### Step 2: Task Spec Schema

Each task is a JSON object conforming to this schema:

```json
{
  "task_id": "t_001",
  "prompt": "Full instructions for the subagent. Include target files, acceptance criteria, and 'do not modify' boundaries.",
  "model_tier": "haiku | sonnet | opus",
  "verification_command": "npm test -- path/to/affected.test.ts",
  "expected_output_pattern": "tests: \\d+ passed",
  "depends_on": [],
  "touches_paths": ["src/auth/login.ts"],
  "run_in_background": false,
  "timeout_seconds": 600
}
```

Required fields: `task_id`, `prompt`, `model_tier`, `verification_command`, `expected_output_pattern`, `depends_on`, `touches_paths`. Missing any required field → spec rejected at Step 0.

`depends_on` is an explicit array of `task_id`s that must reach `passed_with_evidence` before this task may be dispatched. Prose dependency rules ("run X first") are not accepted.

See FORMAT.md for the full schema and examples.

### Step 3: Tier Routing (INLINE GUIDANCE — no external doc)

Each task's `model_tier` is an honest classification of the work, not a cost-minimization dial. Over-tiering wastes tokens; under-tiering produces bad code. Classify before dispatching.

| Tier | Use for | Do NOT use for | Concrete task examples |
|---|---|---|---|
| **haiku** | Mechanical edits with a single well-specified change. Regex-shaped work. Single-file renames. Lint fixups. Format cleanup. Doc-comment additions. Type-export additions. Adding a missing import. | Anything that requires understanding business logic, choosing between two designs, or reading more than one non-trivial file. | Add `export type Config` to `src/types.ts`. Rename `getUserId` → `getViewerId` in `src/auth/session.ts`. Add JSDoc header to every exported function in `src/utils/dates.ts`. Fix all `no-unused-vars` lint errors in `src/api/`. Replace `var` with `const` in `scripts/build.js`. |
| **sonnet** | Standard feature implementation against a clear spec. Writing tests for an existing module. Refactoring one module with a defined boundary. Fixing a specific bug with a known reproduction. Integration between two well-understood systems. | Cross-cutting architectural changes. Designing a new subsystem. Any task where the acceptance criterion is "it should be good." Performance tuning without a target metric. | Implement `POST /api/users` with validation per `specs/users-api.md`. Add integration tests for the auth middleware covering the 4 scenarios in `auth.spec.md`. Refactor `src/payments/` to extract the Stripe webhook handler into its own module. Fix bug #4521 — incorrect date parsing in `src/utils/dates.ts::parseISO`. |
| **opus** | Multi-file refactors with load-bearing reasoning. Debugging failures whose cause is not obvious from stack traces. Designing an API or schema. Security-critical changes. Work that requires weighing competing correctness concerns. Any task where a wrong choice costs more than an extra model call. | Work that fits in one file and has a single correct answer. Lookups. Format conversions. | Refactor the plugin system to support async lifecycle hooks without breaking the 14 existing plugins. Diagnose and fix the intermittent test failure in `integration/order-flow.test.ts` (likely a race). Design the schema and migration for adding multi-tenant support to the users table. Audit `src/auth/` for CSRF and session-fixation defects and fix them. |

**Rule of thumb:** If the task prompt cannot be handed to a Haiku agent without additional context-gathering turns, it is not Haiku work. If the task has a single objectively-correct answer once you understand the problem, it is not Opus work. Default to Sonnet when uncertain; escalate a task rather than batch-escalating.

### Step 4: Dispatch Protocol

Build the dependency graph from `depends_on` edges and write it to `logs/dependency_graph.json`. Topologically sort; identify the frontier (tasks with no pending dependencies).

**For each dispatch wave:**

1. Pop all frontier tasks (tasks whose `depends_on` list is entirely `passed_with_evidence`).
2. For each task in the wave, **before** calling the Task tool:
   - Write the task spec to `specs/{task_id}.json`.
   - Append a line to `logs/dispatch_log.jsonl`: `{"task_id": "...", "tier": "...", "spawn_time_iso": "...", "wave": N}`.
   - Update `state.json`: set `tasks[task_id].status = "in_progress"`, `spawn_time_iso = <now>`, increment `generation`.
3. Fire the entire wave **in a single tool-call block** using the Task tool. Never serialize a wave. Tasks within a wave are independent by construction.
4. Each subagent is instructed (via its prompt) to:
   - Do the work described in `specs/{task_id}.json::prompt`.
   - Run the `verification_command` after the work completes.
   - Write its output to `results/{task_id}.md` with a required `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` block.
   - Write raw verification stdout/stderr/exit-code to `verify/{task_id}.{stdout,stderr,exit}`.
   - **Tier-matched work pace** (inject the appropriate phrase into each subagent prompt — Opus 4.7 needs explicit pacing signals):
     - **haiku** tasks: `"Prioritize speed over depth; respond directly when uncertain. This is mechanical work — ship fast, don't over-engineer."`
     - **sonnet** tasks: no extra pacing directive (default behavior is correct).
     - **opus** tasks: `"Think carefully and step-by-step; this problem is harder than it looks. Reason about edge cases and downstream effects before writing."`
5. Long-running tasks (`run_in_background: true`) use `Task(..., run_in_background=true)`; their completion is detected by the presence of the result files, not by in-memory state.
6. If the Task tool returns a spawn error: record `status: "spawn_failed"`, `spawn_time_iso: null`, `failure_reason: <error>` in state.json. Do NOT record as "spawned." Resume retries; it does not wait.

**Wave completion criterion:** Wave is complete when every dispatched task has either produced `results/{task_id}.md` with parseable structured output OR has status `spawn_failed`.

**Timeout:** Default per-task timeout is 600 seconds; scaled by `timeout_seconds` in the spec. A task that exceeds its timeout is marked `status: "timed_out"` and is not retried. Its downstream dependencies are marked `blocked_on_dependency` (never dispatched).

**Quorum is not applicable.** Unlike deep-design's critic quorum, parallel-exec has no "ignore failures if most pass" mode — every task is load-bearing and every result is processed.

### Step 5: Per-Task Result Collection

For each task that produced a `results/{task_id}.md` file, the coordinator extracts the structured block and writes a normalized record to `state.json::tasks[task_id].subagent_self_report` — this is the subagent's claim, NOT the coordinator's evaluation of it.

Required structured fields per task (see FORMAT.md):

```
STRUCTURED_OUTPUT_START
TASK_ID|{task_id}
SUBAGENT_CLAIM|{completed|failed|partial}
VERIFICATION_EXIT_CODE|{integer}
VERIFICATION_STDOUT_PATH|verify/{task_id}.stdout
FILES_MODIFIED|path1,path2,path3
NOTES|{one-line free-text note, optional}
STRUCTURED_OUTPUT_END
```

The subagent's claim is written verbatim to state; it is NOT the final label. The final label is assigned by the convergence checker in Step 6.

### Step 6: Post-Execution Convergence Check (Independent Agent)

**After the final wave completes**, spawn a single convergence-checker subagent. This agent is the sole authority for per-task labels and aggregate status. The coordinator does not pre-classify.

**Convergence-checker inputs (all passed as file paths):**

- `parallel-exec-{run_id}/specs/` — all task specs
- `parallel-exec-{run_id}/results/` — all subagent output files
- `parallel-exec-{run_id}/verify/` — all raw verification stdout/stderr/exit-codes
- `parallel-exec-{run_id}/state.json` — authoritative state
- `parallel-exec-{run_id}/logs/dependency_graph.json` — topology

**Convergence-checker job:**

1. For each task, read the corresponding `verify/{task_id}.exit` and `verify/{task_id}.stdout`. Compare against `expected_output_pattern` from the spec. Do not rely on the subagent's self-report.
2. Detect conflicts: two tasks that modified the same path without a `depends_on` edge between them. Read the actual file state; diff against the subagent's claim. If two tasks' diffs overlap or contradict, both are `conflicted_with_sibling`.
3. Detect flaky verification: rerun each task's `verification_command` one additional time (in the reconciler agent's own tool calls). If first-run and rerun disagree, label the task `unverified` with reason `flaky_verification: first_exit={X}, rerun_exit={Y}`.
4. Detect claim-vs-evidence mismatch: subagent says `completed` but exit code is nonzero, or pattern does not match stdout → label `failed_with_error`, reason `claim_evidence_mismatch`.
5. Emit structured output to `convergence/convergence-check.md` using the format in FORMAT.md, enclosed in `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END`.

**Four labels, no binary completed/failed:**

| Label | Meaning | Evidence required |
|---|---|---|
| `passed_with_evidence` | Subagent completed; verification command exited 0 on first run and on rerun; pattern matched; no sibling conflict. | `verify/{id}.exit == 0` on both runs; `verify/{id}.stdout` matches `expected_output_pattern`; no path overlap with independent sibling. |
| `failed_with_error` | Verification command exited nonzero OR pattern did not match OR subagent self-reported `failed`. | Exit code, stdout, or self-report from disk. |
| `conflicted_with_sibling` | Two or more tasks modified overlapping paths without a dependency edge between them, and their diffs are inconsistent. | Path overlap + diff comparison from disk. |
| `unverified` | Output file missing, structured block unparseable, verification rerun disagrees with first run, or required field absent. | Fail-safe default when any of the above. Coordinator does not "best-guess" as passed. |

**Unparseable convergence output:** If `convergence/convergence-check.md` is missing or lacks structured markers, the coordinator reports `aggregate_status: convergence_check_failed` and surfaces all per-task evidence paths for manual review. No aggregate success claim is made.

### Step 7: Aggregate Report

The coordinator reads the convergence checker's structured block and prints:

```
parallel-exec {run_id} complete
- passed_with_evidence: {count}
- failed_with_error: {count}  (list task IDs + one-line reasons)
- conflicted_with_sibling: {count}  (list conflicting pairs + paths)
- unverified: {count}  (list task IDs + reasons)
- aggregate_status: {all_passed | partial_with_failures | blocked_on_conflicts | unverified_batch}

Evidence:
- {run_id}/convergence/convergence-check.md
- {run_id}/state.json
- per-task: {run_id}/results/{task_id}.md + {run_id}/verify/{task_id}.*
```

**Aggregate status values (honest termination labels):**

- `all_passed` — every task `passed_with_evidence`.
- `partial_with_failures` — one or more tasks `failed_with_error`, rest `passed_with_evidence`.
- `blocked_on_conflicts` — one or more `conflicted_with_sibling`; user intervention required.
- `unverified_batch` — one or more tasks `unverified` and the user did not approve proceeding without evidence.
- `convergence_check_failed` — convergence checker produced no parseable output; nothing is labeled.

Never emit "all tasks complete" or "work done" as a top-level status.

### Step 8: Resume Protocol

If the run is interrupted (user Ctrl-C, tool failure, session restart):

1. Locate the most recent `parallel-exec-*/state.json` in CWD.
2. For each task in `state.json::tasks`:
   - `status: in_progress` and `results/{task_id}.md` exists → mark `status: pending_convergence_check` (will be re-evaluated by convergence checker).
   - `status: in_progress` and `results/{task_id}.md` missing → mark `status: timed_out` (not re-queued).
   - `status: spawn_failed` → re-add to dispatch frontier.
   - `status: passed_with_evidence`, `failed_with_error`, `conflicted_with_sibling`, `unverified` → leave as-is.
3. If any task still needs dispatch, resume Step 4 from the remaining frontier.
4. If all tasks are terminal but no convergence-check output exists, resume at Step 6.

## Golden Rules

1. **Every task carries a `verification_command`.** No exceptions. Fire-and-forget is the #1 failure mode of parallel execution and it is banned here.
2. **Coordinator never grades.** Per-task labels come from the convergence checker reading evidence files. If a coordinator is tempted to write "looks good" it has violated this rule.
3. **State is written before spawn.** `spawn_time_iso` exists in `state.json` before the Task tool is called. Spawn failure is recorded as `spawn_failed`, not "spawned but silent."
4. **Convergence check is an independent agent.** It reads from disk, not from the coordinator's memory. It has authority over per-task labels. Its verdict is final for that run.
5. **Structured output is the contract.** Each task and the convergence checker must emit `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` blocks. Unparseable → fail-safe `unverified`, never optimistic interpretation.
6. **Dependencies are explicit fields, not prose.** `depends_on: ["t_003"]` is enforceable; "run task 3 before task 4" in a comment is not.
7. **Tier routing is honest classification.** Haiku for mechanical edits, Sonnet for standard work, Opus for load-bearing reasoning. Over-tiering and under-tiering are both failures.
8. **No aggregate completion claim until convergence output is parsed.** The iron-law gate: if `convergence/convergence-check.md` is missing or malformed, the coordinator refuses to claim success.

## Self-Review Checklist

Before printing the aggregate report, verify:

- [ ] Every task spec had a `verification_command` (no spec accepted without one).
- [ ] Every task spec had a `depends_on` array (empty is fine; omitted is not).
- [ ] `state.json` is valid JSON; `generation` counter incremented on every write.
- [ ] No task has `status: "in_progress"` — all are terminal or `pending_convergence_check`.
- [ ] No `spawn_failed` task is labeled `passed_with_evidence` anywhere in state.
- [ ] `dispatch_log.jsonl` has one line per dispatched task with `spawn_time_iso` set.
- [ ] `verify/{task_id}.exit` exists for every task the subagent claimed to complete.
- [ ] Convergence-checker output file exists and contains `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` markers.
- [ ] Convergence checker, not the coordinator, assigned every per-task label.
- [ ] Each task labeled `passed_with_evidence` has a concrete evidence path in the aggregate report.
- [ ] Each task labeled `failed_with_error` has a one-line reason drawn from the convergence output.
- [ ] Each `conflicted_with_sibling` pair lists the overlapping paths.
- [ ] Aggregate status is one of the six honest labels — NOT "all tasks complete" or "work done."
- [ ] Tier routing was per-task (inline classification), not batch-assigned.
- [ ] No task was dispatched before its `depends_on` list was fully `passed_with_evidence`.

## Integration with Other Skills

See INTEGRATION.md for composition patterns. Key examples:

- `/team`'s `team-exec` phase can call `/parallel-exec` internally to fan work across N executor agents with verified convergence.
- `/autopilot`'s Phase 2 (Exec) delegates via `/team` which in turn uses `/parallel-exec` for wave-level fanout.
- `/parallel-exec` runs standalone without `deep-qa` or `deep-design` installed — degraded mode is documented in INTEGRATION.md.

## Cancellation

To cancel mid-run: Ctrl-C, then inspect `parallel-exec-{run_id}/state.json` to see in-flight tasks. Completed tasks remain `passed_with_evidence`; in-flight tasks will be marked `timed_out` on next resume. There is no separate cancel skill.
