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
3. Synthesize findings into a cohesive narrative
4. Review for gaps, contradictions, unsupported claims (critic agent, cross-provider preferred)
5. If gaps found → research the specific gaps (back to step 2, max 5 iterations)
6. If no gaps → ship the report

Exit: reviewer found no evidence gaps or contradictions.

## Output structure (all reports MUST include)

- **Sources**: every claim backed by a URL, paper, or tool output
- **Limitations**: explicit section on caveats, unknowns, and confidence levels
- **Quantitative data**: specific numbers, percentages, metrics — not just qualitative claims
- **Comparative analysis**: contrast alternatives, approaches, or positions against each other

> **Note:** Placeholders like `{user_question}` in Agent prompts are filled by you (Claude)
> from the current task context. They are not template variables — read the user input,
> gather the relevant context, and substitute before spawning the agent.

## Evidence Standards (mandatory for all agents)

Every explorer agent must follow these rules:
- **Every claim needs a source** — URL, doc reference, or tool output. No unsourced assertions.
- **Name specifics** — repos, teams, people, PRs, incidents, versions. Never vague references like "some teams" or "a recent change."
- **Verify currency** — when referencing people or roles, check they are still current when possible.
- **Full clickable URLs** — no shorthand, no relative paths, no "see above."
- **Cross-reference** — claims corroborated by multiple independent sources are stronger. Flag single-source claims.

## Source Coverage (mandatory for all agents)

Explorers must use ALL available tools, not just the obvious ones:
- **Code search** — grep, sourcegraph, file reads
- **Documentation** — internal docs, wikis, manuals, READMEs
- **Document repositories** — shared drives, internal doc platforms, slides, spreadsheets. Strategy docs, architecture specs, and roadmaps often live in document stores separate from code or chat. Search these explicitly.
- **Chat/messaging archives** — Slack threads, team channels, recent discussions
- **Web search** — industry context, peer companies, benchmarks, public engineering blogs
- **Project tracking** — Jira, linear, issue trackers for recent decisions and timelines

Do not rely on a single source type. A direction researched only via web search misses internal context; a direction researched only via code search misses strategic framing.

## Agents

### RESEARCH phase — parallel exploration

Spawn one explorer per dimension. All run concurrently:

```
Agent(subagent_type="Explore", model="opus", prompt="""
Research dimension: {dimension}
Question: {user_question}

Use ALL available tools exhaustively: search code, docs, document repositories,
chat archives, web, and project trackers. Make at least 5-10 tool calls.
Cross-reference across independent sources. Flag confidence levels.

Evidence rules:
- Every claim must have a source (URL or tool output)
- Name specific repos, teams, people, PRs, incidents
- Verify people/roles are current when possible
- Include industry comparisons where relevant
- Full clickable URLs only

Output: structured findings with evidence citations.
""")
```

### SYNTHESIZE — merge findings

After all explorers return, synthesize in the main context (no agent needed).

Rules for synthesis:
- Write as a cohesive narrative, not a patchwork of explorer outputs
- Every sentence earns its place — cut filler, hedging, and redundant transitions
- Deduplicate facts that appear across multiple dimensions
- Surface contradictions explicitly rather than hiding them
- Use tables where 3+ parallel items share the same structure
- Preserve all source citations through the merge

Editorial standards (apply during synthesis and verify before shipping):
- **People**: Full name on first mention with role/context. No orphaned surnames.
- **Proper nouns**: Disambiguate product names that could be confused with people or common words.
- **Counts**: If you write "three documents" or "five teams," the enumeration must match exactly.
- **Transitions**: Every sentence follows logically from the previous. No topic shifts without paragraph breaks.
- **Links**: Every URL is a well-formed clickable markdown link. No bare citation tags.
- **Evidence**: Every factual claim has a source (URL, doc reference, or tool output). Flag single-source claims.

### REVIEW phase — different model catches different blind spots

```
Agent(subagent_type="oh-my-claudecode:code-reviewer", model="opus", prompt="""
Review these research findings for:
- Evidence gaps (claims without sources)
- Contradictions between sources
- Missing perspectives or dimensions
- Unsupported conclusions
- Source diversity (are findings over-reliant on one source type?)
- Editorial quality: orphaned names (surname without first-name intro), ambiguous
  proper nouns, count mismatches (e.g. "three X" but four enumerated), jarring
  transitions, broken or non-clickable links, bare citation tags without URLs

Findings:
{synthesized_findings}

Output: list of specific gaps to fill, or "APPROVED" if complete.
""")
```

### SHIP phase

Write report as styled HTML to `/tmp/investigate-report.html`. Include:
- Clickable table of contents
- All source URLs as clickable links
- Dark theme consistent with other reports

## Flags

- `--depth=quick|standard|deep` — research breadth (default: standard). Quick: 2-3 dimensions, 3 tool calls each. Standard: 3-5 dimensions, 5-10 calls. Deep: 5-7 dimensions, 10+ calls, 2 review iterations.
- `--no-ship` — stop after findings, don't write HTML
- `--max-iterations=N` — cap research-review loop (default: 5)

## Examples

```
/investigate "LoRA vs full fine-tuning for encoder-decoder models"
/investigate --depth=deep "autonomous engineering readiness across all AI domains"
/investigate --depth=quick "what is pytorch helion?"
```
