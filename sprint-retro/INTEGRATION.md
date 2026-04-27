# Integration

How sprint-retro composes with other skills and handles degraded modes.

## Required MCP tools

The skill uses these MCP tools. If any are unavailable, the skill degrades gracefully.

| Tool | Purpose | Degraded fallback |
|------|---------|-------------------|
| Slack semantic search | Slack thread discovery | Use a Slack search API with keyword queries |
| Project/docs search API | Jira, Confluence, Google Docs, people directory search | Note source as unavailable in coverage table |
| Document content fetch | Fetch full content of found docs | Reference title/summary only, skip full content |
| `fetch-slack-thread` | Get full thread context | Use snippet from search result only |
| CI search API (e.g. `search_builds`) | CI/CD build data | Skip CI/CD section, note in coverage |
| `gh` CLI | GitHub PR/commit data | Use Sourcegraph as fallback |
| Sourcegraph (commit_search, diff_search) | Cross-repo code search | Use `gh` CLI per-repo |

## Degraded mode protocol

When a tool is unavailable:

1. Mark that source as `unavailable` in the coverage table
2. Continue with remaining sources
3. If fewer than 3 sources return data: set termination label to `retro_partial`
4. Add a line to the retro footer: `[Source X unavailable — retro coverage is reduced]`

Never halt the retro because one source is unavailable. Deliver what you can, tag coverage honestly.

## Composition with other skills

### slack-briefing

If the `slack-briefing` skill is available, it can be used as an input accelerator:
- Run `slack-briefing` for relevant team channels first
- Use its output as a starting point for the Slack data layer
- Still apply all privacy gates from PRIVACY.md to the briefing output

### user-activity-report (per-member pre-gather)

If the `user-activity-report` skill is available, it can serve as a per-member data layer:

1. For each resolved team member, run `user-activity-report` with the same sprint window as `lookback_days`
2. Each report returns work areas synthesized across all 5 sources — richer per-person context than sprint-retro's source-parallel strategy provides
3. The coordinator merges per-member work areas into the retro's team-level themes (What went well / What didn't / Action items)

**Why this helps:** Sprint-retro gathers data by source (one pass per source across all members). User-activity-report gathers by person (all sources per member) and cross-references into work areas. The per-person view catches individual focus areas that get lost in source-level aggregation.

**Privacy:** All privacy gates from PRIVACY.md still apply to the merged output. User-activity-report has its own privacy rules (no DMs, no sentiment, no productivity scoring) that are compatible but not identical — the stricter rule wins at merge time.

**When to use:** Default to this approach for any team size. The per-person view catches individual focus areas and cross-source work areas that source-parallel aggregation misses. The source-parallel strategy in the "Parallel agent strategy" section below is a fallback when user-activity-report is unavailable, not the preferred path.

### deep-qa (optional review)

After generating the retro, the user can run `deep-qa` on the output to audit for:
- Privacy leaks (content without source citations)
- Generic filler (items without data backing)
- Attribution safety (individual blame language)

This is not automatic — the user invokes it if desired.

## Parallel agent strategy

For teams with 5+ members, data gathering can be parallelized:

1. **Agent per data source** — spawn parallel agents for GitHub, Slack, Jira, Docs, CI/CD
2. Each agent writes its findings to a temp file: `retro-data-{source}.md`
3. Coordinator merges findings, applies privacy gates, and produces the final retro

Privacy gates are applied by the coordinator AFTER merge, not by individual agents. This prevents inconsistent filtering.

## Sprint window configuration

Default: 14 days ending today. Override options:

| Input format | Interpretation |
|---|---|
| No dates provided | Last 14 days |
| "last sprint" | Last 14 days |
| "last 3 weeks" | Last 21 days |
| "April 1-14" | Specific date range |
| "Q1" | January 1 to March 31 |

The sprint window is passed to every data source query. All sources use the same window.
