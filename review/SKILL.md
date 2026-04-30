---
name: review
description: |
  Adversarial multi-perspective critique of any artifact.
  Parallel critics with different focus dimensions, severity-rated findings.
  Covers: code review, security audit, proposal critique, claim validation.
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, WebSearch, WebFetch, Agent
---

# Review

## Strategy

1. Determine review mode from input (code, security, proposal, claims)
2. Select focus dimensions for that mode
3. Spawn parallel critic agents, one per dimension (different model from author)
4. Collect findings, deduplicate, rate severity
5. If `--fix` flag: spawn builder to fix issues, then re-review (loop)
6. Output: findings with severity ratings

Exit: all critics pass or fix loop exhausted.

## Finding format (every finding MUST include)

- **Line reference**: exact file:line or line range, not just "in the function"
- **Severity**: critical / major / minor with justification
- **Concrete fix**: specific code change or approach, not just "consider fixing"
- **Category**: correctness / security / performance / style


> **Note:** Placeholders like `{user_question}` in Agent prompts are filled by you (Claude)
> from the current task context. They are not template variables — read the user input,
> gather the relevant context, and substitute before spawning the agent.

## Agents

### CRITIQUE phase — parallel critics (all spawn concurrently)

For `--code` mode:

```
Agent(subagent_type="oh-my-claudecode:code-reviewer", model="opus", prompt="""
Focus: CORRECTNESS
Review this artifact for logic errors, incorrect assumptions, wrong behavior.
{artifact}
Output: list of defects found (or "no issues").
""")

Agent(subagent_type="oh-my-claudecode:security-reviewer", model="opus", prompt="""
Focus: SECURITY
Review for OWASP top 10, secrets exposure, injection, unsafe patterns.
{artifact}
Output: list of vulnerabilities found (or "no issues").
""")

Agent(subagent_type="oh-my-claudecode:code-reviewer", model="opus", prompt="""
Focus: PERFORMANCE
Review for unnecessary allocations, N+1 queries, missing caching, scalability.
{artifact}
Output: list of performance issues (or "no issues").
""")

Agent(subagent_type="oh-my-claudecode:code-reviewer", model="opus", prompt="""
Focus: EDGE CASES
Review for missing error handling, null checks, boundary conditions, race conditions.
{artifact}
Output: list of edge cases not handled (or "no issues").
""")
```

### JUDGE phase — severity rating

```
Agent(model="sonnet", prompt="""
These defects were found by 4 independent reviewers:
{all_findings}

1. Deduplicate (same issue found by multiple reviewers)
2. Rate each: critical (must fix) / major (should fix) / minor (nice to fix)
3. Verdict: APPROVED (no critical/major) or REJECTED (has critical/major)
""")
```

### FIX phase (only if --fix flag)

```
Agent(subagent_type="oh-my-claudecode:executor", model="opus", prompt="""
Fix these issues found during review:
{critical_and_major_findings}
Run tests after each fix. Commit atomically.
""")
```

## Modes

- `--code` — correctness, security, performance, edge cases (default)
- `--security` — deep security focus: OWASP, secrets, deps, supply chain
- `--proposal` — viability, market fit, technical feasibility, risks
- `--claims` — statistical validity, methodology, reproduction, evidence quality
- `--design` — architecture soundness, scalability, failure modes, operability

## Flags

- `--fix` — auto-fix critical/major issues and re-review
- `--cross-provider` — add GPT/Gemini critics for maximum blind-spot diversity
- `--max-rounds=N` — cap critique-fix loop (default: 3)

## Examples

```
/review PR#1234
/review --security src/auth/
/review --proposal business-case.md
/review --claims experiment-results.md
/review --fix src/api/cache.py
```
