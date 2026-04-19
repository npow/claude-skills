# Phase 3: Build

Implement all modules via delegation to `/team`. Ship-It handles scaffolding and skeleton verification; `/team` handles the staged executor pipeline with two-stage review on every source modification.

## Prerequisites

- SPEC.md approved by user (Phase 1 gate passed)
- DESIGN.md written and `/deep-plan` returned `consensus_reached_at_iter_N` (Phase 2 gate passed)
- `types.ts` frozen (immutable for Phase 3)

## Process

### Step 1: Scaffold the project

Coordinator runs these steps (mechanical, no evaluation):

1. Create directory structure from DESIGN.md file tree.
2. Write `package.json` with all dependencies from DESIGN.md External Dependencies table.
3. Write `tsconfig.json` (or equivalent config).
4. Run `npm install` (or `pip install -e ".[dev]"`) in the background. Wait for success.
5. Confirm `types.ts` is present at the canonical path from Phase 2. DO NOT regenerate it — it is frozen.
6. Verify the skeleton compiles: `npx tsc --noEmit` should pass. If it doesn't, the types.ts is broken; re-open Phase 2 via `/deep-plan` — do NOT patch types.ts in Phase 3.

### Step 2: Delegate to `/team`

1. Update `state.json`: `phases.build.spawn_time_iso = <iso>`, `phases.build.status = "in_progress"`.
2. Invoke `/team` with arguments per [INTEGRATION.md](INTEGRATION.md):
   ```
   /team --plan ship-it-{run_id}/design/DESIGN.md \
         --output ship-it-{run_id}/build/
   ```
3. `/team` runs the staged pipeline:
   - **team-plan** — explore + planner + optional deep-design pass
   - **team-prd** — analyst + mandatory independent critic with falsifiability gate
   - **team-exec** — executor with TDD preamble; honors DESIGN.md wave order for parallelization
   - **team-verify** — `deep-qa --diff` (parallel critics) + independent code-quality reviewer (two-stage)
   - **team-fix** — bounded fix loop; each fix independently verified before merge
4. Ship-It does NOT intervene in any of these stages. The coordinator orchestrates state but does not author, review, or approve code.

### Step 3: Consume `/team` outputs

After `/team` completes:

1. Parse `build/team-termination.md` for `TEAM_LABEL` per [FORMAT.md](FORMAT.md):
   - `complete` → proceed to gate
   - `partial_with_accepted_unfixed` → proceed to gate; count is recorded for Phase 6 completion report
   - `blocked_unresolved` → gate fails; terminate as `blocked_at_phase_3`
   - `budget_exhausted` → gate fails; terminate as `budget_exhausted`
   - `cancelled` → gate fails; terminate as `blocked_at_phase_3`
2. Copy `build/modified-files.txt` and `build/build-output.txt` for use by Phase 4 (`deep-qa --diff`) and Phase 6 (judges).
3. Verify `build/handoffs/` directory is non-empty (per `/team` schema).

## Parallelization rules (honored inside `/team`)

- **DO parallelize**: Independent modules in the same wave (e.g., utils + db in Wave 1)
- **DO NOT parallelize**: Dependent modules (e.g., tools depends on analysis)
- **DO NOT parallelize** more than 5 subagents simultaneously — diminishing returns
- **ALWAYS** include types.ts (read-only) and DESIGN.md in every worker's context
- TDD preamble is mandatory in every `/team` worker prompt (failing test first, then implementation)

## Degraded-mode fallback

If `/team` is unavailable:

- By default, **refuse to proceed** — `/team`'s staged pipeline with two-stage review is too rich to substitute losslessly. Prompt user to install `/team`.
- If user passes `--skip-team` explicitly: follow the inline fallback in [INTEGRATION.md](INTEGRATION.md) (coder+reviewer per module, max 2 revisions, tagged `VERIFICATION_MODE: degraded`). Document TDD and two-stage-review losses in the evidence files.

## Handling delegation failures

| Failure | Response |
|---------|----------|
| `/team` errors on spawn | Mark `phases.build.status = "delegation_failed"`; increment `budget.current_delegation_count.build`; re-delegate if under max, else block |
| `/team` modifies `types.ts` | Invariant `types_ts_immutable_after_design` flips false; run is invalid; halt and report |
| `/team` misses a module from DESIGN.md | Parse `build/modified-files.txt` vs DESIGN.md module list; if gap, re-delegate `/team` with the missing modules explicitly listed |
| `/team` returns `partial_with_accepted_unfixed` | Permitted — gate passes. Items flow into Phase 6 Accepted Tradeoffs. Coordinator does NOT evaluate whether items are "really minor" |
| `/team` returns `budget_exhausted` | Ship-It terminates as `budget_exhausted` (distinct from `blocked_at_phase_3`) |

## Iron-law gate (Phase 3 → Phase 4)

Fresh phase-gate subagent reads evidence. Required:
- `build/team-termination.md` with `TEAM_LABEL ∈ {complete, partial_with_accepted_unfixed}`
- `build/handoffs/` directory non-empty
- `build/modified-files.txt` non-empty (or explicitly empty with rationale if DESIGN.md was a no-op plan)
- `build/build-output.txt` showing exit code 0
- `build/phase-gate.md` with `ADVANCE: true`

Any missing/unparseable → `ADVANCE: false`.
