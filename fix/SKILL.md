---
name: fix
description: |
  Something is broken. Hypothesis-driven root cause analysis, fix, verify,
  loop until resolved. Covers: bugs, incidents, test failures, data issues, model drift.
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, WebSearch, WebFetch, Agent, Write, Edit, Monitor
---

# Fix

## Strategy

1. Gather symptom evidence (error messages, logs, stack traces, metrics)
2. Form 3-5 hypotheses ranked by likelihood
3. For each hypothesis: design minimal probe, execute, evaluate
4. Narrow to root cause
5. Implement fix
6. Verify fix resolves symptom (different model checks)
7. Add regression test
8. If verification fails or new issues → back to step 2 with updated evidence
9. Ship fix

Exit: original symptom no longer reproduces. Regression test passes. No new issues.


> **Note:** Placeholders like `{user_question}` in Agent prompts are filled by you (Claude)
> from the current task context. They are not template variables — read the user input,
> gather the relevant context, and substitute before spawning the agent.

## Agents

### DEBUG phase — hypothesis generation + probing

```
Agent(model="opus", prompt="""
Symptom: {symptom_description}

Evidence gathered so far:
{logs_errors_metrics}

1. Form 3-5 hypotheses for the root cause, ranked by likelihood
2. For each hypothesis, design a minimal probe (a command, query, or code read) that would confirm or eliminate it
3. Execute the probes
4. Based on results, narrow to the most likely root cause
5. Implement the fix
6. Run the failing test/scenario to confirm the fix works

If the fix doesn't work, form new hypotheses from the updated evidence and repeat.
""")
```

### VERIFY phase — independent verification on different model

```
Agent(subagent_type="oh-my-claudecode:code-reviewer", model="opus", prompt="""
A fix was applied for this symptom: {symptom}
Root cause identified: {root_cause}
Fix applied: {fix_description}

Verify:
1. Run the original failing test/scenario — does it pass?
2. Run the full test suite — any regressions?
3. Is the fix correct, or does it mask the symptom?
4. Is there a regression test? If not, write one.

Output: VERIFIED (with evidence) or FAILED (with what's still broken).
""")
```

### SHIP phase

```
Agent(subagent_type="oh-my-claudecode:executor", model="haiku", prompt="""
Ship this fix:
- Commit fix + regression test
- Create PR with: symptom, root cause, fix description, test evidence
- If --incident: skip PR, deploy hotfix directly
""")
```

## Cross-provider review

When mcp__pal__codereview is available, run verification on a non-Claude model
in parallel for maximum blind-spot diversity.

## Flags

- `--no-ship` — stop after verified fix
- `--incident` — priority mode: hotfix deploy, skip PR
- `--max-iterations=N` — cap debug-verify loop (default: 5)

## Examples

```
/fix "500 errors on /api/checkout since the last deploy"
/fix "pytest test_auth.py::test_login failing with KeyError"
/fix --incident "prod is down, 5xx rate at 30%"
/fix "model accuracy dropped 3% after Tuesday's data refresh"
/fix "pipeline dropping 10% of records between ingestion and warehouse"
```
