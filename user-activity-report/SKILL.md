---
name: user-activity-report
description: "Use when researching what someone has been working on, getting up to speed on a colleague's recent activity, or preparing for a 1:1. Trigger phrases: what has X been working on, catch me up on X, person report, activity report for X, what's X been up to."
---

# Person Activity Report

Research all available sources to produce a comprehensive picture of what a specific person has been working on recently. Use when you need to quickly get up to speed on a colleague's work — before a 1:1, when onboarding to a new team, or when context on someone's work area is needed.

## Arguments

- **person**: name, email, GitHub username, or Slack group alias like `@metaflow-dev-group` (required). When a group alias is given, resolve to individual members and produce a consolidated report with a section per person.
- **lookback_days**: how far back to look (default: 30)
- **--no-html**: skip S3 HTML upload (default: upload HTML and share commuter link)

## Workflow

1. **Resolve identity.** If input is a group alias (starts with `@`), resolve via Pandora to individual members, then run steps 2-4 for each person and produce a consolidated report with a section per person. For a single person, follow the cascade in [`_shared/identity-resolution.md`](../_shared/identity-resolution.md) to map to: full name, email, GitHub username, team, and role. Include `resolution_confidence` in the report header. Never stop to ask for names — degrade gracefully with confidence notes.

2. **Search all sources in parallel.** Fire these searches concurrently:

   **a) GitHub activity** (`gh` CLI — use `gh api`, NOT `gh search` which fails on GHE):
   - First discover their repos via Sourcegraph: `get_contributor_repos(authors=["{name}", "{email}"])`
   - For each active repo: `gh api repos/{org}/{repo}/pulls?state=all&sort=created&direction=desc --hostname github.netflix.net` and filter by author
   - For reviews: `gh api repos/{org}/{repo}/pulls?state=all --hostname github.netflix.net` and check reviewers
   - For commits: `gh api repos/{org}/{repo}/commits?author={username}&since={lookback_date} --hostname github.netflix.net`

   **b) Code changes** (Sourcegraph):
   - `commit_search` with `authors=["{name}", "{email}"]` across relevant repos
   - `diff_search` with `author="{username}"` for significant code patterns added

   **c) Slack threads** (`rag-slack-prod`):
   - Search for their name/username in recent threads
   - Look for threads they started or had significant participation in
   - Focus on public channels only — NEVER search DMs or private channels

   **d) Documents & Confluence** (`netflix_search_api`):
   - Search DOCUMENTS source for docs authored/edited by this person
   - Search CONFLUENCE source for pages they've created or updated
   - Search MANUAL source for any internal docs they've contributed to

   **e) Jira/Projects** (`netflix_search_api`):
   - Search PROJECTS source for tickets assigned to or created by this person

3. **Synthesize by work area.** Group findings into work areas (not by source). A "work area" is a project, feature, or initiative — not "their GitHub activity" vs "their Slack activity." Cross-reference: a PR + Slack discussion + Jira ticket about the same feature = one work area.

4. **Generate report.** Output markdown:

```
## Activity Report: {name} ({username})
Role: {role} | Team: {team} | Period: last {lookback_days} days

### Current Focus Areas
(Top 2-3 work areas, synthesized across all sources)

#### 1. {Work Area Name}
- What: {1-2 sentence summary of what they're building/doing}
- Evidence: {PRs, Slack threads, docs, tickets that show this}
- Status: {in progress / shipped / blocked — from most recent signals}

#### 2. {Work Area Name}
...

### Code Activity
- PRs opened: {count} | PRs merged: {count} | Reviews done: {count}
- Most active repos: {repo1}, {repo2}
- Notable PRs: {top 3 by significance, with titles and links}

### Communication & Collaboration
- Active Slack threads: {count} in {N} channels
- Key discussion topics: {2-3 topics they've been discussing}
- Docs authored/updated: {list with links}

### Open Work
- Open PRs: {list with titles and links}
- Assigned tickets: {list if found}
```

5. **Deliver as HTML.** Follow the shared HTML delivery pattern in [`_shared/html-delivery.md`](../_shared/html-delivery.md). Report name: `activity-report`. TLDR includes person name (or group name) and top 2 focus areas.

6. **Terminate.** Report is complete when all sources have been searched, findings synthesized by work area, and HTML uploaded (or fallback noted).

## Design Principles

1. **Synthesize by work area, not by source.** The reader wants to understand what the person is working on, not get a list of GitHub activity + Slack activity + Jira activity separately. Cross-reference sources to build a coherent picture.
2. **Deterministic math first, LLM narrates only.** PR counts, commit counts, and channel participation are computed from data. The LLM synthesizes the work-area narrative but doesn't invent activity.
3. **Recency-weighted.** Most recent activity gets the most space. A PR from yesterday matters more than one from 25 days ago.

## Privacy Rules

1. **Public channels only.** Never search Slack DMs, private channels, or 1:1 conversations.
2. **Shared docs only.** Never include docs shared only between the person and their manager (performance reviews, 1:1 notes).
3. **No sentiment analysis.** Report what they worked on, not how they felt about it or how others perceived their work.
4. **No productivity scoring.** Never compute or imply a productivity score. This is a context-gathering tool, not an evaluation tool.

## Golden Rules

1. **Cross-reference sources.** A PR title mentioning "HPO" + a Slack thread about "HPO integration" + a Jira ticket for "HPO rework" = one work area, not three separate items.
2. **Search ALL configured sources.** Don't skip Slack because GitHub had enough data. Each source reveals different facets of work.
3. **Include links for everything.** Every PR, every Slack thread, every doc — include a link so the reader can dive deeper.
4. **Work areas first, raw data second.** The synthesized "Current Focus Areas" section is the primary output. Code/Slack/Jira breakdowns are supporting detail.
5. **Handle sparse results gracefully.** If someone has no Slack activity or no Jira tickets, note it — don't pad with filler.
6. **Show every resolved member.** When reporting on a group alias, every resolved member gets a section — even if their only data is "1 PR review, no other signals." Silently dropping members with sparse data is a defect, not graceful degradation.

## Anti-Rationalization Counter-Table

| Excuse | Reality |
|---|---|
| "Their GitHub activity tells the full story." | Code is one signal. Slack threads reveal context, design discussions, and collaboration that code doesn't show. Search all sources. |
| "I'll list their PRs and Slack threads separately." | That's a data dump, not a report. Synthesize by work area — the reader wants to understand what they're working on, not browse raw activity. |
| "I found a DM thread that's really relevant." | No DMs. Ever. Public channels only. The privacy boundary is non-negotiable. |
| "They haven't been very active, so the report will be short." | Short is fine. "No PRs, 3 Slack threads about X, 1 doc update" is a valid report. Don't pad. |
| "I can infer what they're working on from their team." | Inferences aren't evidence. Report what the data shows, not what you assume from their role. |

## Termination Labels

| Label | Meaning |
|---|---|
| `report_complete` | All sources searched, findings synthesized by work area |
| `report_partial` | Some sources unavailable or returned errors — noted which |
| `person_not_found` | Could not resolve the person's identity across systems |
| `insufficient_data` | Person found but very little activity in the lookback period |

## Self-Review Checklist

- [ ] Person's identity resolved (GitHub username + email + full name)
- [ ] All 5 source categories searched (GitHub, Sourcegraph, Slack, Docs, Jira)
- [ ] Findings synthesized into work areas, not listed per-source
- [ ] No DM or private channel content included
- [ ] No productivity scoring or sentiment analysis
- [ ] Links included for all PRs, threads, docs, and tickets
- [ ] Current Focus Areas section has 2-3 synthesized work areas
- [ ] Report covers the full lookback period, not just the last few days
- [ ] HTML version uploaded to S3 with commuter link (unless `--no-html` or upload failed with noted fallback)
- [ ] Slack/chat delivery uses TLDR + link, not the full report
- [ ] Group alias resolved to individuals with per-person sections (if applicable)
