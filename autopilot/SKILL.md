---
name: autopilot
description: |
  Use when the user says "autopilot", "build this", "make it", "ship it", "just do it",
  "do it", "implement this", or gives a vague idea, spec, task list, or bug fix and expects
  autonomous execution. Handles decomposition, agent coordination, and verification automatically.
  "build me end to end", "go from idea to code", "do everything", "run this autonomously".
user_invocable: true
argument: The task, idea, spec, or goal (may be vague — Phase 0 handles ambiguity)

category: execution
capabilities:
  - auto-topology
  - parallel-agents
  - loop-based
  - defect-detection
best_for:
  - "Any build task from one-line fix to greenfield project"
  - "When you don't want to pick between build/team/parallel-exec/loop-until-done"
not_for:
  - "Pure research with no artifact output (use deep-research)"
  - "Diagnosing a bug without fixing it (use deep-debug)"
  - "Reviewing someone else's work (use deep-qa)"
input_types:
  - idea
  - spec
  - task
  - bug-report
output_types:
  - code
  - report
  - artifact
output_signals:
  - termination_label
  - phase_reached
  - topology_selected
  - subtask_count
complexity: auto
cost_profile: auto
execution:
  sagaflow: preferred
  temporal_skill: autopilot-temporal
  estimated_duration: "5-180min (auto-scaled)"
---

# Autopilot

The unified orchestrator. One skill that auto-scales from a single-agent one-file fix to a multi-agent staged pipeline with parallel fanout. The user never picks a topology — autopilot reads the task and selects one.

## Phases

### Phase 0: Task Analysis (always runs, <30s)

Read the input. Classify along three axes:

1. **Clarity**: vague idea → partial spec → full spec → single task
2. **Scope**: one-file fix → multi-file feature → multi-module project → greenfield repo
3. **Decomposability**: atomic (can't split) → sequential (must be ordered) → parallel (independent parts) → mixed

Output: a `TaskProfile` logged to the user. Example: "Task: multi-file feature, partial spec, 4 subtasks (2 parallel + 2 sequential). Topology: staged fanout."

### Phase 1: Plan (conditional — skip if atomic)

- If clarity is "vague idea": invoke deep-design inline to stress-test the concept, then deep-plan to break into steps.
- If clarity is "partial spec" or higher: invoke deep-plan inline to produce ordered subtasks with acceptance criteria.
- If atomic (single task, clear spec): skip directly to Phase 2.

Output: ordered list of subtasks with dependencies and acceptance criteria.

### Phase 2: Topology Selection (automatic, never user-facing)

Based on TaskProfile + plan output, select one:

| Condition | Topology | How it runs |
|-----------|----------|-------------|
| 1 subtask or atomic | **Solo** | Main agent executes directly |
| N independent subtasks, no shared state | **Fanout** | Spawn N agents in parallel, convergence check |
| N dependent subtasks, sequential | **Pipeline** | Execute in order, each verified before next |
| Mix of independent + dependent | **Staged fanout** | Pipeline of phases, fanout within each phase |
| Any topology + source code changes | **+Review gate** | 4-reviewer panel on modifications |

Log the selection: "Selected fanout (5 independent subtasks)" or "Selected pipeline (3 phases, 2 parallel in phase 2)." The user never chooses.

**Agent cap:** max 8 concurrent agents for fanout. If more subtasks exist, batch into waves.

#### Routing Decision Manifest (required at Phase 0 and Phase 2)

Every routing decision writes a manifest to `autopilot-{run_id}/routing-manifest.json` BEFORE the routed phase begins:

```
routing_decisions[]:
  phase: "expand" | "topology"
  chosen: the skill/topology selected
  rejected: list of alternatives considered and why each was ruled out
  trigger: the signal that drove the choice (ambiguity score, subtask count, dependency graph shape)
  predicted_outcome: what the coordinator expects this choice to produce (e.g., "3 independent artifacts, no merge conflicts")
  confidence: low | medium | high
```

At Phase 5 (termination), verify each routing prediction against actual outcome. Write `autopilot-{run_id}/routing-verification.md` with:
- For each routing decision: predicted vs actual outcome, verdict (confirmed / partially_confirmed / refuted)
- If refuted: what would have been a better choice in hindsight

This is a falsifiable contract — the prediction is recorded before execution and verified after. No post-hoc rationalization.

### Phase 3: Execute

Run the selected topology. Each subtask:

1. **Execute** — agent writes code / creates artifact
2. **Verify** — run tests, check acceptance criteria, lint
3. **If fails** — retry with error context (up to 3 attempts per subtask)
4. **If passes** — mark complete, unlock dependents

For fanout: a convergence checker runs after all agents complete — detects conflicts, duplicate work, or incompatible changes before merging.
For pipeline: each phase gate requires all subtasks in that phase to pass verification before the next phase starts.

### Phase 4: QA (always runs unless `--no-qa`)

After all subtasks complete:
- Invoke deep-qa in fix mode on the combined output
- If defects found: fix and re-verify (loop, max 2 QA rounds)
- If clean: proceed to ship

### Phase 5: Ship (conditional)

- If code project detected: package with tests, docs, CI config, README
- If report/presentation: generate styled HTML output
- If neither: produce honest completion report

Output: what was built, what was verified, what's untested, termination label.

**Termination labels** (honest, exhaustive):
- `completed_verified` — all subtasks passed verification + QA clean
- `completed_partial` — some subtasks passed, others failed after retries
- `completed_unverified` — execution finished but verification was skipped or inconclusive
- `blocked` — cannot proceed (missing credentials, access, unclear requirements)
- `budget_exhausted` — hit max retries, max agents, or time limit

## Flags

- `--solo` — force single-agent execution (skip topology selection)
- `--dry-run` — plan only, don't execute (stops after Phase 1)
- `--no-qa` — skip Phase 4 QA pass
- `--depth=quick` — lightweight mode: skip deep-design, use simple plan, solo topology
- `--depth=deep` — full ceremony: always run deep-design, deep-plan, QA, ship

## Composable Engines (called by autopilot, also standalone)

| Engine | Called in | Standalone use |
|--------|----------|---------------|
| deep-design | Phase 1 (vague ideas) | "design this system" |
| deep-plan | Phase 1 (all non-atomic) | "plan this work" |
| deep-qa | Phase 4 (QA + fix) | "review this artifact" |
| deep-idea | Pre-Phase 0 (if needed) | "generate ideas" |
| monitor | Phase 3 (health checks) | "check service health" |

## What This Absorbed

| Former Skill | Now handled by |
|-------------|---------------|
| build | Autopilot Phase 0-5 (the whole pipeline) |
| ship-it | Phase 5 (code project packaging) |
| team | Phase 2 staged topology + review gate |
| parallel-exec | Phase 2 fanout topology |
| loop-until-done | Phase 3 per-subtask verify loop |

## Golden Rules

1. **Auto-scale, don't ask.** Never ask the user to pick a topology. Read the task and decide.
2. **Verify every subtask.** No subtask is "done" without passing its acceptance criteria.
3. **Honest termination.** Use the five labels above. Never say "looks good" or "mostly done."
4. **Convergence check after fanout.** Parallel agents may conflict. Always check before merging.
5. **Phase gates are non-negotiable.** Phase 1 output gates Phase 2. Phase 3 output gates Phase 4. No skipping.
