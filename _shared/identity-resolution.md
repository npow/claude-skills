# Cross-Platform Identity Resolution

Resolve a person's identity across systems given any starting identifier (chat handle, GitHub username, email, or name). Used by `user-activity-report`, `sprint-retro`, and any skill that needs to map a person across platforms.

## The Problem

People have different identifiers on different systems. A single person might be `jdoe` on GitHub, `Jane Doe` in git commits, `jane@example.com` in email, and `@jane` on chat. Reports that hardcode one identifier miss activity under the others.

## Input formats

| Input | Type | Action |
|---|---|---|
| `jdoe` | Username | Look up on GitHub, then cross-reference git log |
| `Jane Doe` | Full name | Search GitHub users, then git log |
| `jane@example.com` | Email | Search git log by email, then GitHub |
| `@team-name` | Group handle | Resolve via GitHub team API or org membership |

## Resolution cascade

### Step 1: Determine input type

| Pattern | Type |
|---|---|
| Contains `@` and `.` (email-like) | Email — skip to Step 2b |
| Starts with `@` | Group handle — skip to Group Resolution |
| Contains a space | Full name — search by name |
| Otherwise | Username — search by username |

### Step 2a: Username or name lookup

1. GitHub API: `gh api users/{username}` or `gh api search/users?q={name}`
2. Git log: `git log --all --format='%an <%ae>' | sort -u | grep -i "{query}"`
3. If a people directory or search API is available (configured via MCP tools), use it to enrich with role/team info

### Step 2b: Email lookup

1. Git log: `git log --all --format='%an <%ae>' | sort -u | grep -i "{email}"`
2. GitHub API: `gh api search/users?q={email}+in:email`
3. Extract username from email prefix as a fallback guess

### Step 3: Build identity map

Cross-reference results to build:
- **username**: primary GitHub handle
- **full_name**: display name
- **email**: primary email
- **team**: if discoverable
- **role**: if discoverable

Use this map consistently across all queries in the report.

## Confidence levels

| Level | Criteria |
|---|---|
| `high` | Exact username match confirmed via GitHub profile, or email matches git + GitHub |
| `medium` | Name match with plausible email, or single search result |
| `low` | Partial match or best guess — flag in report header |

Include `resolution_confidence` in the report output.

## Group resolution

For group handles (e.g., `@team-name`):

1. Try GitHub team membership: `gh api orgs/{org}/teams/{team}/members`
2. If that fails, identify frequent committers to repos associated with the team
3. If a search API is available, query it for team/group membership

Once individual names are found, resolve ALL members through the cascade above **in parallel** — fire all lookups concurrently, not one at a time.

**Show every resolved member.** When reporting on a group, every resolved member gets a section — even if sparse. Never silently drop members.

## Cross-platform identity

A subject may have different handles on different systems: GitHub login, email username, ticket assignee field, chat handle. Build the identity map once and use it in every query. A report that hardcodes one handle in all queries will silently miss attributions on other platforms.

## Failure diagnosis

| Symptom | Fix |
|---|---|
| GitHub returns 404 for username | Try search API, try email lookup, check for alt handles |
| Git log returns nothing | Try broader name search, check other repos |
| Multiple matches for a name | Ask user to disambiguate, or pick highest-confidence match and note it |
| Group resolution returns 0 members | Try alternative: repo committer analysis, ask user for member list |

**Never stop to ask for names — degrade gracefully with confidence notes.** A report with `resolution_confidence: low` is better than a blocked report.
