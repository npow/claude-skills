# Integration

How `/parallel-exec` composes with other npow skills, and how it behaves when paired skills are not installed.

---

## Composition Patterns

### Called by `/team` (team-exec phase)

The `/team` pipeline stages are `team-plan → team-prd → team-exec → team-verify → team-fix`. The `team-exec` stage is where N parallel workers actually modify the codebase. In npow's `/team`, `team-exec` delegates to `/parallel-exec` internally rather than spawning executors directly.

**Hand-off contract:**

- `/team` produces `team-{run_id}/handoffs/prd-to-exec.md` listing per-worker task specs with all required fields (`prompt`, `model_tier`, `verification_command`, `expected_output_pattern`, `depends_on`, `touches_paths`).
- `/team`'s coordinator writes the specs as a JSON array to `team-{run_id}/handoffs/exec-task-batch.json` and invokes `/parallel-exec` with the path.
- `/parallel-exec` runs the full workflow (dispatch → convergence check) and writes its own `parallel-exec-{run_id}/` tree under `team-{run_id}/` (nested runs are allowed).
- `/parallel-exec`'s structured aggregate output is read by `/team`'s coordinator and becomes the evidence file for the `team-exec` stage.
- `aggregate_status` controls the `team-exec` stage gate:
  - `all_passed` → advance to `team-verify`.
  - `partial_with_failures` or `blocked_on_conflicts` or `unverified_batch` → advance to `team-fix` with the failed/conflicted/unverified task IDs as input.
  - `convergence_check_failed` → halt; `/team` reports to user and does not advance.

**Why this is strictly better than OMC:**
OMC's `ultrawork` is a component of `ralph`/`autopilot` but has no honest handoff back to the wrapping pipeline — failures are aggregated as "completed/failed" with no conflict or flakiness detection. npow's `/parallel-exec` returns structured convergence evidence that `/team` uses to drive its own stage gate.

---

### Called by `/autopilot` (Phase 2, transitively)

`/autopilot` Phase 2 (Exec) delegates to `/team`, which delegates to `/parallel-exec` during its `team-exec` stage. There is no direct `/autopilot → /parallel-exec` call; the chain is `/autopilot → /team → /parallel-exec`. This is intentional: it reuses `/team`'s staged discipline rather than duplicating dispatch logic.

---

### Called directly by the user

`/parallel-exec` is invocable standalone for batches of independent tasks that do not need the full `/team` plan-PRD-verify-fix pipeline. Typical standalone uses:

- Multi-file mechanical refactors with known targets (e.g., rename an exported function across 8 files with per-file verification).
- Parallel test generation: N modules each need unit tests with known acceptance criteria.
- Parallel doc generation: N components each need a JSDoc header where the source structure is fixed.
- Parallel lint-cleanup: N files each need a specific lint rule satisfied, verified by rerun of the linter.

In standalone mode, the convergence-checker pass is the complete quality gate. Callers who want a second-stage code-quality review must follow up with `deep-qa --diff` themselves — see "Degraded Mode" below.

---

## Integration with Other npow Skills

### With `deep-qa`

`/parallel-exec` can invoke `deep-qa --diff` as an optional post-convergence pass for callers that want code-quality review on top of spec compliance. This is controlled by a caller flag (typically set by `/team` during `team-verify`), not by `/parallel-exec` itself.

**Flow:**

1. `/parallel-exec` completes convergence check.
2. If the caller passed `run_deep_qa_on_diff: true`, `/parallel-exec` invokes `deep-qa --diff` pointed at the union of all `touches_paths`.
3. `deep-qa` produces its defect registry.
4. `/parallel-exec` includes the path to the `deep-qa` registry in its aggregate report. The aggregate status is NOT affected by `deep-qa` findings — those are passed back to the caller.

**Why:** `deep-qa` surfaces defects but does not fix them. Mixing it into the `aggregate_status` would conflate "this batch executed correctly" (what convergence check measures) with "this batch produced high-quality code" (what `deep-qa` measures). Separating the two lets callers like `/team` route `deep-qa` findings to `team-fix`, not conflate them with execution failures.

---

### With `deep-design`

Not directly integrated. `/parallel-exec` is an execution engine; `deep-design` is a design-critique engine. If a caller (e.g., `/autopilot` Phase 1 via `/deep-plan`) used `deep-design` to stress-test the plan before dispatch, that happens upstream of `/parallel-exec`.

---

### With `/deep-plan`

Not directly integrated. `/deep-plan` produces an ADR that can then be decomposed into `/parallel-exec` task specs (typically by `/team`'s `team-prd` stage). The decomposition preserves acceptance criteria and verification commands from the ADR so `/parallel-exec` receives specs with falsifiable verification intact.

---

### With `/loop-until-done`

Not directly integrated. Different failure modes: `/parallel-exec` fans N independent tasks once and reports evidence; `/loop-until-done` loops until all stories pass. A `/loop-until-done` iteration might internally invoke `/parallel-exec` if one story has parallelizable sub-tasks, but this is an implementation choice of the caller, not a standard pattern.

---

## Degraded Mode (no paired skills installed)

`/parallel-exec` is fully functional as a standalone skill. No other npow skills are required.

| Scenario | Behavior | Aggregate tag |
|---|---|---|
| Called by `/team`, which is not installed | User invokes `/parallel-exec` directly with a JSON task batch. Same workflow, same guarantees. | None — this is normal standalone mode, not degraded. |
| `deep-qa` not installed, caller requested `run_deep_qa_on_diff: true` | Skip the `deep-qa` pass. Aggregate report appends: `VERIFICATION_MODE: degraded_no_deep_qa — code-quality review skipped. Run deep-qa --diff manually on {path_union} for full audit.` | `VERIFICATION_MODE: degraded_no_deep_qa` (advisory tag; does NOT change aggregate_status). |
| `deep-design` not installed, upstream planner wanted adversarial plan review | No effect on `/parallel-exec`. This is an upstream concern. | None. |
| Environment lacks the Task tool (plain Claude Code vs. Claude Code with subagent support) | Skill cannot run. Print: `parallel-exec requires the Task subagent tool. Falling back to sequential in-context execution is not supported — sequential in-context is not parallel-exec.` Do NOT silently run sequentially. | Not applicable — skill refuses to run. |
| Environment has a single-agent concurrency limit of 1 | `/parallel-exec` will dispatch waves sequentially in practice (one task at a time). Convergence check still runs. Aggregate report appends: `CONCURRENCY_LIMITED: 1 — waves dispatched sequentially; parallelism benefit lost but correctness guarantees preserved.` | `CONCURRENCY_LIMITED: 1` (advisory tag). |

**Iron rule for degraded mode:** Every guarantee from the main workflow — mandatory `verification_command`, convergence checker, structured output, four per-task labels, five aggregate labels — remains in force. Degraded mode only skips OPTIONAL second-stage reviews. It never relaxes the iron-law gate.

---

## What `/parallel-exec` Does NOT Do

Explicit non-goals so callers know where to route work:

- **Does not plan.** Task specs must be provided. If the user has an idea and needs decomposition into tasks, route to `/deep-plan` first.
- **Does not design.** If the batch is experimental and needs adversarial pressure before execution, route to `deep-design` first.
- **Does not loop.** If tasks fail and must be retried until success, route to `/loop-until-done`. `/parallel-exec` runs one pass and reports evidence.
- **Does not fix.** If the convergence checker surfaces failures, `/parallel-exec` reports them; it does not spawn fix tasks. Looping back is the caller's responsibility.
- **Does not grade code quality.** The convergence checker verifies spec compliance (exit code, pattern match, path bounds). Quality review is `deep-qa --diff`, which is separate and optional.
- **Does not persist across sessions.** State is file-based in CWD. Resume within the same CWD works; cross-session cross-CWD resume is out of scope.

Callers that need any of the above should either route to the appropriate skill or compose `/parallel-exec` with it explicitly.
