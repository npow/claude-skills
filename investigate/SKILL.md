---
name: investigate
description: |
  Open-ended exploration of a question, topic, or problem space.
  Gathers evidence, validates findings, loops until gaps filled.
  Covers: research, evaluations, surveys, landscape analysis, team activity, competitive intel.
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, WebSearch, WebFetch, Agent, Write, Edit
---

# Investigate

## Strategy

1. Identify 3-5 orthogonal dimensions of the question
2. Research each dimension in parallel (explorer agents)
3. Synthesize findings into a structured report
4. Review findings for gaps, contradictions, unsupported claims (critic agent, cross-provider preferred)
5. If gaps found → research the specific gaps (back to step 2, max 5 iterations)
6. If no gaps → ship the report

Exit: reviewer found no evidence gaps or contradictions.


> **Note:** Placeholders like `{user_question}` in Agent prompts are filled by you (Claude)
> from the current task context. They are not template variables — read the user input,
> gather the relevant context, and substitute before spawning the agent.

## Agents

### RESEARCH phase — parallel exploration

Spawn one explorer per dimension. All run concurrently:

```
Agent(subagent_type="Explore", model="opus", prompt="""
Research dimension: {dimension}
Question: {user_question}

Use ALL available tools: WebSearch, WebFetch, Bash, Read, Grep.
Cross-reference across independent sources. Flag confidence levels.
Output: structured findings with evidence citations.
""")
```

### SYNTHESIZE — merge findings

After all explorers return, synthesize in the main context (no agent needed).
Merge, deduplicate, identify themes and contradictions.

### REVIEW phase — different model catches different blind spots

```
Agent(subagent_type="oh-my-claudecode:code-reviewer", model="opus", prompt="""
Review these research findings for:
- Evidence gaps (claims without sources)
- Contradictions between sources
- Missing perspectives or dimensions
- Unsupported conclusions

Findings:
{synthesized_findings}

Output: list of specific gaps to fill, or "APPROVED" if complete.
""")
```

### SHIP phase

```
Agent(subagent_type="oh-my-claudecode:executor", model="haiku", prompt="""
Format this report:
- Write to /tmp/report.html with styled formatting
""")
```

## Flags

- `--sources="web,docs,code"` — which sources to search
- `--team="name"` — scope to team activity
- `--person="name"` — scope to individual
- `--depth=quick|standard|deep` — research breadth (default: standard)
- `--no-ship` — stop after findings
- `--max-iterations=N` — cap research-review loop (default: 5)

## Examples

```
/investigate "LoRA vs full fine-tuning for encoder-decoder models"
/investigate --team="platform" "sprint retro"
/investigate --depth=quick "what is pytorch helion?"
```
