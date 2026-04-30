# Unified Build Skill — Design Spec

**Status:** Proposed
**Date:** 2026-04-30
**Absorbs:** autopilot, ship-it, team, parallel-exec, loop-until-done

## Core Idea

One skill to rule them all. The user says "build X" and the skill figures out
the right decomposition, the right number of agents, the right coordination
topology, and the right verification strategy. The user never picks between
build/autopilot/ship-it/team/parallel-exec/loop-until-done.

## Phases

### Phase 0: Task Analysis (always runs, <30s)

Read the input. Classify along three axes:

1. **Clarity**: vague idea → partial spec → full spec → single task
2. **Scope**: one-file fix → multi-file feature → multi-module project → greenfield repo
3. **Decomposability**: atomic (can't split) → sequential (must be ordered) → parallel (independent parts) → mixed

Output: a `TaskProfile` with clarity, scope, decomposability, estimated subtask count.

### Phase 1: Plan (conditional — skip if atomic)

- If clarity is "vague idea": run deep-design inline (adversarial stress-test the concept)
- If clarity is "partial spec" or higher: run deep-plan inline (break into steps with acceptance criteria)
- If atomic: skip to Phase 2

Output: ordered list of subtasks with dependencies and acceptance criteria.

### Phase 2: Topology Selection (automatic)

Based on TaskProfile + plan output:

| Condition | Topology | Implementation |
|-----------|----------|---------------|
| 1 subtask or atomic | **Solo** | Main agent executes directly |
| N independent subtasks, no shared state | **Fanout** | Spawn N agents in parallel, convergence check |
| N dependent subtasks, sequential | **Pipeline** | Execute in order, each verified before next |
| Mix of independent + dependent | **Staged fanout** | Pipeline of phases, fanout within each phase |
| Any topology + code changes | **+Review gate** | 4-reviewer panel on source modifications (from team skill) |

The user never sees this decision. The skill logs it: "Selected fanout (5 independent subtasks)" or "Selected pipeline (3 sequential phases, 2 parallel within phase 2)."

### Phase 3: Execute

Run the selected topology. Each subtask:
1. Execute (agent writes code / creates artifact)
2. Verify (run tests, check acceptance criteria — from loop-until-done)
3. If fails: retry with error context (up to 3 attempts per subtask)
4. If passes: mark complete, unlock dependents

For fanout: convergence checker detects conflicts between parallel agents before merging.
For pipeline: each phase gate requires all subtasks in that phase to pass verification.

### Phase 4: QA (always runs)

After all subtasks complete:
- Run deep-qa in fix mode on the combined output
- If defects found: fix and re-verify (loop)
- If clean: proceed to ship

### Phase 5: Ship (conditional)

- If code project detected: package with tests, docs, CI config (from ship-it)
- If report/presentation: generate HTML output (from build's current ship phase)
- If neither: just report completion

Output: honest completion report with what was built, what was verified, what's untested.

## Flags

- `--solo` — force single-agent (skip topology selection)
- `--dry-run` — plan only, don't execute
- `--no-qa` — skip Phase 4 QA pass
- `--audit-only` — execute but don't modify (review mode)

## What Gets Deprecated

| Old Skill | Absorbed By |
|-----------|------------|
| `autopilot` | Phase 0-1 (vague idea → design → plan) + Phase 3-5 |
| `ship-it` | Phase 5 (code project packaging) |
| `team` | Phase 2 staged topology + review gate |
| `parallel-exec` | Phase 2 fanout topology |
| `loop-until-done` | Phase 3 per-subtask verify loop |

## What Stays Separate

- `deep-research` — not building, researching. Different output type.
- `deep-debug` — not building, diagnosing. Different entry point (symptom, not goal).
- `deep-qa` — called BY build in Phase 4, but also standalone for reviewing others' work.
- `deep-design` — called BY build in Phase 1, but also standalone for design exploration.
- `deep-plan` — called BY build in Phase 1, but also standalone for planning without executing.

## Migration

1. Update `build/SKILL.md` with unified phases
2. Add topology selection logic
3. Wire deep-design, deep-plan, deep-qa as composable phases
4. Deprecate autopilot, ship-it, team, parallel-exec, loop-until-done from runtime
5. Keep temporal variants: `build-temporal` becomes the single durable orchestrator
6. Update skill routing in CLAUDE.md / superpowers

## Open Questions

1. Should Phase 2 topology selection be a separate agent (for objectivity) or inline?
2. Max agents for fanout — cap at 5? 10? Dynamic based on task?
3. How does build compose with the temporal backend — does every build run durably, or only `build-temporal`?
