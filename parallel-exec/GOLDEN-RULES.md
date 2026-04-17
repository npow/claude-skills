# Golden Rules

Eight cross-cutting rules from the orchestration-suite design, specialized for `/parallel-exec`. These are non-negotiable. Violating any one of them puts the run into an honest-failure posture that is strictly better than an optimistic completion claim, but the invariants are designed so the coordinator simply cannot violate them without producing evidence of the violation.

---

## 1. Independence Invariant — Coordinator never grades

The coordinator orchestrates: it validates specs, writes state, spawns tasks, spawns the convergence checker, and prints the aggregate report from structured output. The coordinator does NOT decide whether a task passed or failed.

**Concrete for `/parallel-exec`:**
- Per-task labels (`passed_with_evidence`, `failed_with_error`, `conflicted_with_sibling`, `unverified`) are written ONLY by the convergence checker.
- Any coordinator code path that reads `verify/{task_id}.exit` and assigns a label is a violation.
- Even when the subagent self-reports `completed` and exit code is 0, the coordinator waits for the convergence checker's verdict. The subagent's self-report is captured verbatim but is not authoritative.

---

## 2. Iron-Law Verification Gate — No aggregate claim without convergence output

No aggregate "all tasks complete" claim is made until `convergence/convergence-check.md` exists AND contains a parseable `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` block AND that block's `AGGREGATE_STATUS` field is one of the five enumerated values.

**Concrete for `/parallel-exec`:**
- Missing file → `aggregate_status: convergence_check_failed`. No success claim.
- File exists but markers missing → same. No success claim.
- Markers present but count/list mismatch (e.g., `PASSED_WITH_EVIDENCE|3|t_001,t_002` — count says 3, list has 2) → `convergence_check_failed`.
- Coordinator NEVER "best-guesses" from per-task exit codes when convergence output is missing.

---

## 3. Two-Stage Review on Source Modifications — applies to `/parallel-exec` via convergence check + optional quality pass

The design spec's two-stage review (spec-compliance → code-quality) is enforced at the wave level via the convergence check. The convergence checker validates spec compliance (exit code, pattern match, path bounds). When `/parallel-exec` is invoked by `/team` or `/autopilot`, those outer skills add the second-stage code-quality review via `deep-qa`.

**Concrete for `/parallel-exec` standalone:**
- Convergence checker IS the spec-compliance review.
- If source files were modified, the caller is responsible for the code-quality review (typically via `deep-qa --diff`).
- Skipping the code-quality review in a standalone `/parallel-exec` run is acceptable only when the caller explicitly opts out. The aggregate report should recommend the follow-up pass in that case.

---

## 4. Honest Termination Labels — four per-task labels and five aggregate labels

Explicit vocabulary. "Done" and "complete" are forbidden as standalone labels.

**Per-task (assigned by convergence checker):**
- `passed_with_evidence` / `failed_with_error` / `conflicted_with_sibling` / `unverified`

**Aggregate (from convergence checker's structured block):**
- `all_passed` / `partial_with_failures` / `blocked_on_conflicts` / `unverified_batch` / `convergence_check_failed`

Never print "all tasks complete," "work done," or similar — use the exact labels.

---

## 5. State Written Before Agent Spawn — `spawn_time_iso` is a precondition, not a post-condition

Every dispatch writes `tasks[id].spawn_time_iso` and increments `generation` BEFORE the Task tool is called. Spawn refusal is recorded as `status: spawn_failed`. Resume retries spawn; it does not wait.

**Concrete for `/parallel-exec`:**
- The dispatch block writes state, then calls Task, in that order. Never inverted.
- If the Task tool returns an error, the coordinator writes `status: spawn_failed` and moves on. On resume, that task is picked up from the frontier again.
- An "in_progress" task without a `spawn_time_iso` is state corruption — coordinator treats it as `unverified` on resume and reports the inconsistency.

---

## 6. Structured Output Is the Contract — free text is ignored

Every per-task result file and the convergence-check output file must contain `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` blocks. Unparseable → fail-safe `unverified` (per-task) or `convergence_check_failed` (aggregate). The coordinator reads ONLY the structured block.

**Concrete for `/parallel-exec`:**
- A subagent that writes a beautifully-worded prose summary but no structured block → task labeled `unverified`.
- A convergence checker that emits an analysis paragraph but no structured block → `aggregate_status: convergence_check_failed`.
- Pipe characters in field values are not escaped; parser splits on first N-1 pipes, last field absorbs the rest.

---

## 7. All Data Passed Via Files — no inline payloads

Task specs, task prompts, verification commands, dependency graphs, convergence-checker inputs — all written to disk before the Task tool is called. Inline data is silently truncated and is impossible to audit.

**Concrete for `/parallel-exec`:**
- `specs/{task_id}.json` is written before dispatch.
- The subagent's prompt references `specs/{task_id}.json` by path rather than inlining the spec content.
- The convergence checker receives a set of directory paths (`specs/`, `results/`, `verify/`, `state.json`, `logs/dependency_graph.json`) — not inlined JSON.

---

## 8. No Coordinator Self-Approval — same context cannot author and approve

The coordinator dispatched the tasks and produced the spec. It cannot also judge the outcome. The convergence checker is a fresh subagent reading from files. Its context is clean — it has not seen the dispatch reasoning.

**Concrete for `/parallel-exec`:**
- Convergence checker prompt passes only the file paths listed in Rule 7 — no coordinator summary, no "I think these tasks went well" framing, no hints.
- If the coordinator had to inspect verify files to decide what to dispatch next wave, that inspection is for flow control only; the labels still come from the convergence checker.
- A run where the coordinator and convergence checker are the same context (e.g., the coordinator "simulates" the checker) is a violation.

---

## Anti-Rationalization Counter-Table

Common excuses that will be tempting during a `/parallel-exec` run, and the concrete reality. When in doubt, re-read this table.

| Excuse | Reality |
|---|---|
| "Fire-and-forget is fine here — this task is too trivial to verify." | No. Every task carries a `verification_command`, including a one-line type export. If verification is truly meaningless, the work is meaningless and doesn't need to be dispatched. |
| "Coordinator can skip the convergence check for a small batch." | No. Three tasks can produce three conflicting diffs as easily as thirty. The checker runs every batch. |
| "All three subagents reported completed — I can claim success." | No. Self-reports are captured verbatim but are not authoritative. The convergence checker verifies exit codes and path bounds against the evidence files. |
| "This task's `verification_command` is the same as the last one — reuse the previous run's output." | No. Each wave produces fresh evidence. The convergence checker reruns verifications for flaky-detection purposes; reusing stale output defeats the point. |
| "Two tasks modified the same file but both passed — it's probably fine." | No. That's a `conflicted_with_sibling` unless they had an explicit `depends_on` edge. Parallel edits to the same path without dependency ordering are a bug regardless of whether they currently pass. |
| "Convergence checker didn't output structured markers but I can tell the batch passed from context." | No. Unparseable output → `aggregate_status: convergence_check_failed`. The coordinator does not fall back to vibes-based assessment. |
| "One task is `unverified` because its result file is missing, but the others are all `passed_with_evidence`, so the batch is done." | No. Aggregate is `unverified_batch`, not `all_passed`. The user must decide whether to proceed with partial verification; the coordinator does not make that choice. |
| "This is a simple find-and-replace across 20 files — I can dispatch at Haiku tier without per-task verification." | No. Twenty Haiku tasks each need a `verification_command` — typically a lint/typecheck/test-affected-files command. Batch verification at the end is NOT a substitute; it cannot attribute failures. |
| "The dependency graph has a cycle but I can run the tasks in a safe order manually." | No. Cycles are rejected at Step 0. Tell the user to break the cycle or promote to a sequential non-parallel path. |
| "I'll skip the convergence checker this time because the user is waiting." | No. Especially because the user is waiting — otherwise what they get is a fabricated success claim, which is worse than a slower honest one. |
