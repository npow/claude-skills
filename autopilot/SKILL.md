---
name: autopilot
description: |
  Use when the user says "autopilot", "build this", "make it", "ship it", "just do it",
  "do it", "implement this", or gives a vague idea, spec, task list, or bug fix and expects
  autonomous execution. Handles decomposition, agent coordination, and verification automatically.
  "build me end to end", "go from idea to code", "do everything", "run this autonomously".
  Follows the Spec-Driven Development workflow: specify → clarify → plan → tasks → analyze → implement.
user_invocable: true
argument: The task, idea, spec, or goal (may be vague — Phase 0 handles ambiguity)

category: execution
capabilities:
  - auto-topology
  - parallel-agents
  - loop-based
  - defect-detection
  - spec-driven-development
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

Follows the Spec-Driven Development (SDD) workflow: specifications are the primary artifact, code serves the spec. All non-atomic tasks produce structured artifacts in `specs/{feature}/` before any code is written.

## SDD Artifact Directory

For non-atomic tasks, autopilot creates and maintains:

```
specs/{NNN-feature-name}/
├── spec.md              # Feature specification (Phase 1a)
├── checklists/          # Quality checklists (Phase 1a)
│   └── requirements.md  # Spec quality validation
├── research.md          # Technical research (Phase 1c)
├── plan.md              # Implementation plan (Phase 1c)
├── data-model.md        # Entity definitions (Phase 1c)
├── contracts/           # API/interface contracts (Phase 1c)
├── quickstart.md        # Validation scenarios (Phase 1c)
└── tasks.md             # Ordered task list (Phase 1d)
```

Feature numbering is sequential: scan existing `specs/` directories, take the next available 3-digit prefix. Feature name is derived from the task description (2-4 word kebab-case slug).

## Phases

### Phase 0: Task Analysis (always runs, <30s)

Read the input. Classify along three axes:

1. **Clarity**: vague idea → partial spec → full spec → single task
2. **Scope**: one-file fix → multi-file feature → multi-module project → greenfield repo
3. **Decomposability**: atomic (can't split) → sequential (must be ordered) → parallel (independent parts) → mixed

Output: a `TaskProfile` logged to the user.

**Fast-path:** If scope is "one-file fix" AND clarity is "single task" AND decomposability is "atomic" → skip directly to Phase 3 (Execute solo). No SDD ceremony for trivial fixes.

**Pressure awareness:** this skill applies the pressure circuit breakers from [`_shared/pressure-awareness.md`](../_shared/pressure-awareness.md). After 2 retries of the same phase producing no new evidence, escalate rather than retrying.

### Phase 1: Spec-Driven Development Workflow (skip if atomic)

The SDD workflow replaces ad-hoc planning with structured, traceable artifacts. Each sub-phase produces files in `specs/{feature}/` that gate the next sub-phase.

#### Phase 1a: Specify — produce `spec.md`

Create `specs/{NNN-feature-name}/` directory. Generate `spec.md` following the SDD specification format.

**Routing by clarity:**
- **Vague idea**: invoke deep-design inline to stress-test the concept, then distill into spec.md.
- **Partial spec**: extract what exists, fill gaps with informed defaults, mark critical unknowns with `[NEEDS CLARIFICATION]` (max 3 markers — only for decisions that significantly impact scope, security, or UX).
- **Full spec**: transcribe into the structured spec.md format. Validate completeness.
- **Existing spec.md**: if the user provides a file already in SDD format, adopt it directly.

**spec.md required sections:**
- *User Scenarios & Testing* — prioritized user stories (P1, P2, P3) with Given/When/Then acceptance scenarios. Each story must be independently testable.
- *Functional Requirements* — FR-001, FR-002, etc. Each must be testable and unambiguous.
- *Success Criteria* — SC-001, SC-002, etc. Technology-agnostic, measurable outcomes.
- *Key Entities* — if data is involved.
- *Assumptions* — reasonable defaults documented here, not asked about.
- *Edge Cases* — boundary conditions and error scenarios.

**Quality validation:** after writing spec.md, generate `checklists/requirements.md` and validate:
- No implementation details (languages, frameworks, APIs) in the spec
- All requirements are testable
- Success criteria are measurable and technology-agnostic
- Max 3 `[NEEDS CLARIFICATION]` markers (scope > security > UX priority)

If validation fails, self-correct (max 3 iterations). Proceed when clean.

**Focus on WHAT and WHY, never HOW.** The spec is for stakeholders, not developers. Implementation details belong in plan.md.

#### Phase 1b: Clarify — resolve ambiguities (conditional)

If spec.md contains `[NEEDS CLARIFICATION]` markers:

- **Interactive mode** (`--interactive`): present each as a multiple-choice question with a recommended answer. Max 5 questions, one at a time. Record answers in a `## Clarifications` section and update the relevant spec sections.
- **Non-interactive mode** (default for autopilot): make informed defaults based on context, industry standards, and common patterns. Document choices in the Assumptions section. Log: "Auto-resolved N clarifications (non-interactive mode)."

Skip entirely if spec has no clarification markers.

#### Phase 1c: Plan — produce `plan.md` + supporting artifacts

Invoke deep-plan (Planner → Architect → Critic consensus loop). deep-plan now outputs SDD-compatible artifacts:

- `plan.md` — Technical Context (language, deps, storage, testing, platform, constraints), Constitution Check (if `/memory/constitution.md` exists), Project Structure, Complexity Tracking.
- `research.md` — resolved unknowns with Decision / Rationale / Alternatives Considered per item.
- `data-model.md` — entities, fields, relationships, validation rules, state transitions.
- `contracts/` — interface contracts appropriate for project type (API endpoints, CLI schemas, library interfaces). Skip for purely internal tools.
- `quickstart.md` — key validation scenarios for integration testing.

The Planner/Architect/Critic consensus loop ensures plan quality. See deep-plan skill for the full protocol.

**Gate:** plan.md must exist and pass Critic approval (or reach max iterations honestly) before proceeding.

#### Phase 1d: Tasks — produce `tasks.md`

Generate an ordered task list from the plan and spec:

- Tasks grouped by user story (from spec.md) to enable independent implementation.
- Phase structure: Setup → Foundational → User Story 1 (P1) → User Story 2 (P2) → ... → Polish.
- Format: `[ID] [P?] [Story] Description` where `[P]` marks parallelizable tasks.
- Each task includes exact file paths from plan.md's Project Structure.
- Checkpoints between phases for independent story validation.
- Dependencies explicitly stated: foundational tasks block all story work.

**Task quality rules:**
- Every task maps to ≥1 requirement (FR-###) or user story.
- No vague tasks ("implement feature") — each must reference specific files/components.
- Parallel markers `[P]` only when tasks touch different files with no shared state.

#### Phase 1e: Analyze — cross-artifact consistency (conditional)

Runs automatically for `--depth=deep`. Skipped for `--depth=quick`.

Read-only cross-artifact validation across spec.md, plan.md, and tasks.md:

- **Coverage gaps**: requirements with zero tasks, tasks with no mapped requirement.
- **Duplication**: near-duplicate requirements across artifacts.
- **Ambiguity**: vague adjectives without measurable criteria, unresolved placeholders.
- **Terminology drift**: same concept named differently across files.
- **Inconsistency**: conflicting requirements, task ordering contradictions.
- **Constitution alignment**: violations of `/memory/constitution.md` principles (if exists).

Severity: CRITICAL (blocks implementation) > HIGH > MEDIUM > LOW.

If CRITICAL issues found: auto-fix spec/plan/tasks and re-validate (max 1 reiteration). If still critical after fix attempt, report honestly and proceed with warnings.

### Phase 2: Topology Selection (automatic, never user-facing)

Read `tasks.md` phase structure and `[P]` markers. Select topology:

| Condition | Topology | How it runs |
|-----------|----------|-------------|
| 1 task or atomic fast-path | **Solo** | Main agent executes directly |
| N independent tasks marked [P], no shared state | **Fanout** | Spawn N agents in parallel, convergence check |
| N dependent tasks, sequential phases | **Pipeline** | Execute in order, each verified before next |
| Mixed phases with [P] tasks within phases | **Staged fanout** | Pipeline of phases, fanout within each phase |
| Any topology + source code changes | **+Review gate** | 4-reviewer panel on modifications |

**Agent cap:** max 8 concurrent agents for fanout. Batch into waves if more.

#### Routing Decision Manifest

Every routing decision writes to `autopilot-{run_id}/routing-manifest.json` BEFORE execution:

```
routing_decisions[]:
  phase: "expand" | "topology"
  chosen: the skill/topology selected
  rejected: alternatives and why ruled out
  trigger: signal that drove the choice
  predicted_outcome: expected result
  confidence: low | medium | high
```

### Phase 3: Execute

Run the selected topology, driven by `tasks.md`:

1. **Execute** — agent implements the task, referencing spec.md and plan.md for context
2. **Verify** — run tests, check acceptance criteria from spec.md, lint
3. **If fails** — retry with error context (up to 3 attempts per task)
4. **If passes** — mark task `[X]` in tasks.md, unlock dependents

For fanout: convergence checker after all agents complete — detects conflicts, duplicate work, incompatible changes.
For pipeline: phase gate requires all tasks in that phase to pass before next phase starts.

**Checkpoint validation:** at each phase boundary, verify the completed user story works independently (as defined in spec.md's "Independent Test" field).

### Phase 4: QA (always runs unless `--no-qa`)

After all tasks complete:
- Invoke deep-qa in fix mode on the combined output
- deep-qa's TESTABILITY dimension includes an empirical mutation-test lane (3-min budget). Surviving mutants with `scope: changed` surface as testability defects and enter the fix loop.
- If defects found: fix and re-verify (loop, max 2 QA rounds)
- If clean: proceed to ship

### Phase 5: Ship (conditional)

- If code project detected: package with tests, docs, CI config, README
- If report/presentation: generate styled HTML output
- If neither: produce honest completion report

Output: what was built, what was verified, what's untested, termination label.

**Routing verification:** compare each Phase 2 routing prediction against actual outcome. Write `autopilot-{run_id}/routing-verification.md` with predicted vs actual verdicts.

### Phase 6: Retrospect (always runs)

After ship, run a lightweight retrospect scan:
1. Scan for P1-P3 signals (user corrections, self-corrections, structural failures)
2. Scan for P6 signals (QA-driven patterns): defect clusters suggesting behavioral gaps
3. If qualifying signals found: invoke `/retrospect` for full enforcement-first analysis
4. If none found: skip

**Termination labels** (honest, exhaustive):
- `completed_verified` — all tasks passed verification + QA clean
- `completed_partial` — some tasks passed, others failed after retries
- `completed_unverified` — execution finished but verification was skipped or inconclusive
- `blocked` — cannot proceed (missing credentials, access, unclear requirements)
- `budget_exhausted` — hit max retries, max agents, or time limit

## Flags

- `--solo` — force single-agent execution (skip topology selection)
- `--dry-run` — SDD workflow only, don't execute (stops after Phase 1)
- `--no-qa` — skip Phase 4 QA pass
- `--interactive` — gate at spec review (Phase 1a) and clarification (Phase 1b)
- `--depth=quick` — skip specify/clarify, minimal plan, solo topology
- `--depth=deep` — full SDD ceremony: specify, clarify, plan, tasks, analyze, QA, ship

## Composable Engines (called by autopilot, also standalone)

| Engine | Called in | Standalone use |
|--------|----------|---------------|
| deep-design | Phase 1a (vague ideas) | "design this system" |
| deep-plan | Phase 1c (plan + consensus) | "plan this work" |
| deep-qa | Phase 4 (QA + fix) | "review this artifact" |
| mutation-test | Phase 4 via deep-qa | "find test gaps" |
| deep-idea | Pre-Phase 0 (if needed) | "generate ideas" |
| monitor | Phase 3 (health checks) | "check service health" |

## What This Absorbed

| Former Skill | Now handled by |
|-------------|---------------|
| build | Autopilot Phase 0-5 (the whole pipeline) |
| ship-it | Phase 5 (code project packaging) |
| team | Phase 2 staged topology + review gate |
| parallel-exec | Phase 2 fanout topology |
| loop-until-done | Phase 3 per-task verify loop |
| speckit.specify | Phase 1a (specify) |
| speckit.clarify | Phase 1b (clarify) |
| speckit.plan | Phase 1c (plan) |
| speckit.tasks | Phase 1d (tasks) |
| speckit.analyze | Phase 1e (analyze) |
| speckit.implement | Phase 3 (execute) |

## Golden Rules

1. **Spec before code.** Non-atomic tasks always produce spec.md before any implementation. The spec is the source of truth; code serves the spec.
2. **Auto-scale, don't ask.** Never ask the user to pick a topology. Read the task and decide.
3. **Verify every task.** No task is "done" without passing its acceptance criteria from spec.md.
4. **Honest termination.** Use the five labels above. Never say "looks good" or "mostly done."
5. **Convergence check after fanout.** Parallel agents may conflict. Always check before merging.
6. **Phase gates are non-negotiable.** spec.md gates plan.md. plan.md gates tasks.md. tasks.md gates execution. No skipping.
7. **Artifacts are traceable.** Every task traces to a requirement (FR-###). Every requirement traces to a user story. Untraceable work is rejected.
