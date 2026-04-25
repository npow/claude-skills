# Data Sources

How to gather sprint activity data from each available source, with privacy constraints.

## Sprint window

Default: last 14 days from today. Override with user-provided dates. All queries use this window.

**All 5 sources below are independent and should be queried in parallel.** Don't wait for GitHub results before starting Slack or Jira queries — fire them all concurrently and collect results.

## Source 1: GitHub (gh CLI + Sourcegraph)

**What to gather:**
- PRs merged by each team member (`gh pr list --state merged --author <user> --search "merged:>YYYY-MM-DD"`)
- PRs reviewed by each team member (`gh pr list --state merged --search "reviewed-by:<user> merged:>YYYY-MM-DD"`)
- Commits to main/default branch per member
- Open PRs (in-progress work)

**Search strategy:**
1. Use `gh` CLI for the team's primary repos (ask user or infer from recent activity)
2. Use Sourcegraph `commit_search` for cross-repo contribution discovery
3. Use Sourcegraph `diff_search` for code change patterns

**Privacy notes:** GitHub data is inherently team-visible. No special filtering needed beyond respecting repo access.

**Output per member:** PR count (merged/reviewed/open), notable PRs (title only, no diff content), review load distribution.

## Source 2: Slack (rag-slack-prod, netflix_search_api)

**What to gather:**
- Public channel discussions involving team members
- Threads about incidents, releases, blockers
- Positive signals: kudos, thanks, celebrations

**Search strategy:**
1. Use `rag-slack-prod` with semantic queries: team member names + sprint-relevant topics ("deploy", "release", "incident", "blocked", "shipped", "launched")
2. Use `netflix_search_api` with `sources: ["SLACK"]` for broader coverage
3. For each result, check `channel_id` metadata

**PRIVACY RULES (HARD):**
- Never query or include DM/private channel content
- If a search result comes from a DM or private channel: discard it entirely, do not reference its existence
- If a public message references a DM ("as I mentioned in our DM..."), include only the public message, never follow the DM trail
- Never include messages that assign personal blame or contain interpersonal conflict
- Strip any quoted text from private sources

**Output per member:** Key discussion topics, blockers raised, incidents handled, kudos received.

## Source 3: Jira / Confluence (netflix_search_api)

**What to gather:**
- Tickets completed (status changed to Done/Closed in sprint window)
- Tickets in progress
- Tickets blocked or overdue
- Sprint velocity if available

**Search strategy:**
1. Use `netflix_search_api` with `sources: ["JIRA"]` and team member names
2. Use `netflix_search_api` with `sources: ["CONFLUENCE"]` for sprint docs, decision records
3. Search by project key if known, otherwise by assignee names

**Privacy notes:** Jira tickets are generally team-visible. However:
- Skip tickets with labels like "confidential", "hr", "performance"
- Skip Confluence pages with restricted sharing (check viewer count / sharing metadata)

**Output:** Ticket counts by status, notable completions, blockers, velocity trends.

## Source 4: Google Docs (netflix_search_api)

**What to gather:**
- Sprint planning docs
- Design docs, RFCs, tech specs authored during sprint
- Meeting notes (retro-relevant only)

**Search strategy:**
1. Use `netflix_search_api` with `sources: ["GOOGLE_DOCS"]` and sprint-related terms
2. Search for docs authored by team members in the sprint window

**PRIVACY RULES (HARD):**
- Never include docs shared with fewer than 3 people
- Never include docs with titles containing: "1:1", "performance", "review", "feedback", "comp", "promotion", "PIP", "termination"
- If uncertain about sharing scope: exclude the doc
- For included docs: reference title and author only, never quote content verbatim
- If doc content contains personal performance assessments, salary, or HR information: exclude entirely even if sharing is broad

**Output:** List of team-visible docs produced during sprint (title, author, type).

## Source 5: CI/CD (Jenkins via netflix-ci-official, Spinnaker)

**What to gather:**
- Build success/failure rates for team repos
- Deployment frequency
- Failed builds and their resolution time

**Search strategy:**
1. Use `mcp__netflix-ci-official__search_builds` filtered by team repos and sprint window
2. Check completion status distribution

**Privacy notes:** CI data is team-visible. No special filtering needed.

**Output:** Build health metrics, deployment count, notable failures.

## Data completeness tracking

After querying all sources, produce a coverage report:

| Source | Status | Items Found | Notes |
|--------|--------|-------------|-------|
| GitHub | queried / skipped / failed | N | |
| Slack | queried / skipped / failed | N | |
| Jira | queried / skipped / failed | N | |
| Google Docs | queried / skipped / failed | N | |
| CI/CD | queried / skipped / failed | N | |

If any source returns zero results or fails:
1. Try an alternative query strategy (different search terms, broader date range)
2. If still empty: note the gap explicitly in the retro output
3. Never fill gaps with generic filler text ("communication could be improved")

## Alias resolution

When input is a Slack alias (starts with `@`):

**Steps 1 & 2: Try Pandora AND Slack in parallel**

Fire both searches concurrently — don't wait for Pandora to fail before trying Slack:

- `netflix_search_api(sources: ["PANDORA"], queryString: "{alias_without_@}")` — may match a team or org unit
- `netflix_search_api(sources: ["SLACK"], queryString: "{alias_without_@}")` — find Slack mentions that list usergroup members
- `rag-slack-prod(query_str: "{alias} members team")` — semantic search for membership context

Slack usergroups (e.g. `@metaflow-dev-group`) are NOT indexed in Pandora — they're Slack-specific constructs. If Pandora returns nothing, use the Slack results to discover individual names from channel bot responses, thread authors, or group mentions.

**Step 3: Resolve each member via Pandora**

Once you have individual names (from Pandora team results or Slack channel discovery), resolve each one through the identity cascade in [`_shared/identity-resolution.md`](../_shared/identity-resolution.md) to get full name, email, GitHub username, team, and role.

**Step 4: List resolved members for verification**
- Show all resolved members in the report header
- Note any members that could not be resolved (with confidence level)
- Never silently drop members — sparse data is not grounds for exclusion

**If resolution still fails:** degrade gracefully with `resolution_confidence: low`. Never stop to ask the user for names — search harder using alternative terms, partial names, or channel membership.

## Failure diagnosis

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Pandora returns 0 for alias | Alias is a Slack usergroup, not a Pandora team | Try Slack channel search — find the corresponding channel and discover members from recent threads |
| Slack search returns 0 results | Wrong team member handles or search terms too specific | Broaden search: use just the person's first name, try without date filters |
| Jira returns 0 results | Team uses different project key or board | Ask user for Jira project key, or search by assignee email |
| Google Docs search empty | Docs may be in shared drives not indexed | Note the gap; suggest user manually share relevant docs |
| GitHub returns 0 PRs | Wrong org/repo or member uses different GH handle | Check `gh api /users/<handle>` or ask user for GitHub usernames |
| Alias resolution fails after all fallbacks | Usergroup has no corresponding channel, or channel is private | Degrade gracefully — note the gap, don't block |
