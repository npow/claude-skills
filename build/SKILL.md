---
name: build
description: |
  Create any artifact: code, experiments, reports, presentations, pipelines.
  Auto-plans if needed, auto-researches context, self-verifies, loops through
  review until quality passes. The universal "make it" command.
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, WebSearch, WebFetch, Agent, Write, Edit, Monitor
---

## Strategy

### Phase 0: Intent Detection (always first)
Read the request and assign exactly one label:
- `CLARIFY`: missing key constraints, ambiguous scope, no actionable signal
- `PLAN_ONLY`: explicit request for spec, design doc, file list, or plan — no implementation asked
- `BUILD`: has description/spec + implicit or explicit build intent
- `EXECUTE`: has concrete plan with file paths already

Never skip this step. The label determines all subsequent behavior.

### Phase 1: Research (conditional)
Only if `BUILD` or `EXECUTE` and context is insufficient. Time-box to quick lookups:
- Exact import paths, library versions, schema column names, API endpoints
- Do NOT do exploratory research; gather only what the plan requires

### Phase 2: Plan
*Required for `BUILD`. Optional enrichment for `EXECUTE`.*

The plan must contain:
1. **Task breakdown**: ordered steps, each with a single clear output
2. **Dependency graph**: which tasks can run in parallel
3. **Input handling**: exact parsing strategy — library name, function, format (never generic "read the file")
4. **Failure modes**: ≥3 specific edge cases with expected handling (not "handle errors gracefully")
5. **Output specification**: schema, file structure, or report format with concrete examples
6. **Smoke test commands**: runnable validation commands, not descriptions of tests

If `--plan-only` or `PLAN_ONLY` intent: emit plan and stop. No agents.

### Phase 3: Execute
Spawn builder agents. Rules:
- One agent per independent task group
- Parallel spawning for non-dependent groups
- Pass each agent only the context it needs (task spec + relevant plan section)
- Agents must not re-plan; they implement

### Phase 4: Self-Verify
Run automatically after builders finish:
```
<test runner> && <linter> && <type checker>
```
Fix trivial failures (import errors, formatting) without escalating.

### Phase 5: Review
Critic agent (distinct model) evaluates against:
- [ ] Spec compliance
- [ ] Edge case coverage from plan
- [ ] Output format matches specification
- [ ] No security regressions
- [ ] Performance acceptability

### Phase 6: Iterate or Ship
- Issues found → fix → re-review (cap at 3 cycles)
- Clean review → SHIP (PR / deploy / publish per mode)

**Done when**: tests green + no critical/major review findings.

## Agents

### PLAN phase — single architect agent

```
Agent(subagent_type="oh-my-claudecode:architect", model="opus", prompt="""
Create an implementation plan for:
{spec_or_description}

Codebase context:
{relevant_files_and_patterns}

Output an ordered task list with:
- Task name, file paths, what to change, acceptance criteria
- Mark independent tasks that can run in parallel
- Include test requirements per task

REQUIRED sections (do not skip):
- **Parsing/input approach**: name the specific library, API, or technique for reading input data
- **Edge cases**: list at least 3 concrete failure modes with handling strategy
- **Output format**: describe exact structure with a sample snippet
- **Verification commands**: runnable commands to prove the artifact works
""")
```
### EXECUTE phase — parallel builder agents

Spawn one builder per independent task group. Run concurrently:

```
Agent(subagent_type="oh-my-claudecode:executor", model="opus", prompt="""
Implement this task:
{task_description}

Files to modify: {file_paths}
Acceptance criteria: {criteria}

Steps:
1. Read the target files and understand existing patterns
2. Write/run tests FIRST (TDD)
3. Implement the change
4. Run tests, fix until passing
5. Commit atomically
""")
```
### REVIEW phase — critic on different model

```
Agent(subagent_type="oh-my-claudecode:code-reviewer", model="opus", prompt="""
Review these changes for:
- Correctness and logic errors
- Security vulnerabilities
- Performance issues
- Missing edge cases
- Test coverage gaps

Changes:
{git_diff}

Output: list of issues with severity (critical/major/minor), or "APPROVED".
""")
```
### SHIP phase

```
Agent(subagent_type="oh-my-claudecode:executor", model="haiku", prompt="""
Ship this work:
- Create PR with descriptive title and summary
- Or upload presentation if --present flag
""")
```

# Build


## Plan quality checklist

Before leaving the PLAN phase, verify the plan includes ALL:

- [ ] Named the specific parsing/introspection approach (library, API, or technique)
- [ ] Listed at least 3 edge cases or failure modes with handling strategy
- [ ] Specified output format with concrete example (schema, sample output, or template)
- [ ] Included verification commands that run against fixture/sample input
- [ ] Ordered tasks by dependency (core types → implementation → tests → integration)
- [ ] Each task has clear acceptance criteria (not just "implement X")


> **Note:** Placeholders like `{user_question}` in Agent prompts are filled by you (Claude)
> from the current task context. They are not template variables — read the user input,
> gather the relevant context, and substitute before spawning the agent.

## Agents









## Modes

- `--code` — write/edit code + tests (default)
- `--experiment` — run ML experiment, collect metrics
- `--report` — produce formatted document
- `--presentation` — create slides
- `--pipeline` — build data/ML pipeline
- `--plan-only` — stop after planning, output plan for review

## Cross-provider review

When mcp__pal__codereview is available, run critics on a non-Claude model in parallel
with the Claude critic for maximum blind-spot diversity:

```
# Parallel: Claude + GPT-5
Agent(subagent_type="oh-my-claudecode:code-reviewer", model="opus", prompt=<review>)
mcp__pal__codereview(model="gpt5", code=<artifact>)
```

Merge findings from both before passing to judge.

## Flags

- `--plan-only` — output plan without executing
- `--no-ship` — stop after review passes
- `--no-review` — skip review loop (for low-stakes changes)
- `--max-iterations=N` — cap review-fix loop (default: 5)

## Examples

```
/build "add Redis caching to the API layer"
/build plan.md --code
/build --experiment "compare LoRA vs QLoRA on our model"
/build --report sprint-data.md
/build --plan-only "migrate from PostgreSQL to DynamoDB"
```

## Execution routing (sagaflow-first)

**Sagaflow is the default execution path.** The in-session workflow above is the FALLBACK, used only when the sagaflow worker is confirmed unavailable.

**Routing sequence (mandatory before any in-session work):**
0. If planning-only request (asks for spec/plan/file-list, no "build" or "implement" intent) → produce output directly in-session. Do NOT route to sagaflow.
1. Run `sagaflow doctor`
2. If healthy → launch via sagaflow below. Stop. Do not run in-session.
3. If unhealthy → log `SAGAFLOW_UNAVAILABLE`, proceed with in-session fallback.

**Launch command:**
```
Bash(
  run_in_background=true,
  command="sagaflow launch build --arg spec='<SPEC>' --arg max_iterations=3 --await"
)
```