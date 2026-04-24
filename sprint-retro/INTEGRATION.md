# Integration

How sprint-retro composes with other skills and handles degraded modes.

## Required MCP tools

The skill uses these Netflix MCP tools. If any are unavailable, the skill degrades gracefully.

| Tool | Purpose | Degraded fallback |
|------|---------|-------------------|
| `rag-slack-prod` | Slack semantic search | Use `netflix_search_api` with `sources: ["SLACK"]` |
| `netflix_search_api` | Jira, Confluence, Google Docs, Pandora search | Note source as unavailable in coverage table |
| `netflix_search_data` | Fetch full content of found docs | Reference title/summary only, skip full content |
| `fetch-slack-thread` | Get full thread context | Use snippet from search result only |
| `netflix-ci-official` (search_builds) | CI/CD build data | Skip CI/CD section, note in coverage |
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
