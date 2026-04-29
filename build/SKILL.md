---
name: build
description: |
  Create any artifact: code, experiments, reports, presentations, pipelines.
  Auto-plans if needed, auto-researches context, self-verifies, loops through
  review until quality passes. The universal "make it" command.
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, WebSearch, WebFetch, Agent, Write, Edit, Monitor
---

# Build

## Strategy

1. Assess input: is it vague, a spec, or a plan?
   - Vague → CLARIFY (Socratic Q&A in main context)
   - Spec/description → PLAN
   - Plan with file paths → EXECUTE
2. During PLAN, if context is missing → scoped RESEARCH (quick lookup, not full investigation)
3. PLAN: decompose into ordered tasks, identify parallel groups, set acceptance criteria
   - `--plan-only` stops here and outputs the plan
4. EXECUTE: spawn builder agents for each task (parallel where independent)
5. SELF-VERIFY: run test suite, lint, type check
6. REVIEW: spawn critic agent (different model) to check quality
7. If review finds issues → fix and re-review (loop)
8. SHIP: PR, deploy, publish based on mode

Exit: review passes with no critical/major issues. Tests pass.


> **Note:** Placeholders like `{user_question}` in Agent prompts are filled by you (Claude)
> from the current task context. They are not template variables — read the user input,
> gather the relevant context, and substitute before spawning the agent.

## Agents

### PLAN phase — single architect agent

```
Agent(subagent_type="oh-my-claudecode:architect", model="opus", prompt="""
Create an implementation plan for:
{spec_or_description}

Codebase context:
{relevant_files_and_patterns}

Output an ordered task list:
- Task name, file paths, what to change, acceptance criteria
- Mark independent tasks that can run in parallel
- Include test requirements per task
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
