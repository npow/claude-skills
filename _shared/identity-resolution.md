# Cross-Platform Identity Resolution

Resolve a person's identity across Netflix systems given any starting identifier (Slack handle, GitHub username, email, or name). Used by `user-activity-report`, `sprint-retro`, and any skill that needs to map a person across platforms.

## The Problem

Netflix has no single lookup that maps `any_identifier → all_identifiers`. Each system stores identity differently:

| System | Identifier format | Searchable by |
|---|---|---|
| Pandora/PEOPLE | Full name, email, team | Full name or email. **Usernames alone don't match.** |
| GitHub Enterprise | Username (e.g. `npow`) | Username, email (via `gh api`) |
| Sourcegraph | Git commit metadata: `Name <email>` | Partial name, email, or username (fuzzy) |
| Slack (rag-slack-prod) | Content search only | Message text. **Cannot filter by author.** |
| Jira/Confluence | Email or display name | Name or email via `netflix_search_api` |

## Resolution Cascade

Execute steps in order. Stop expanding once you have: **full name + email + GitHub username**.

**CRITICAL: Never fabricate identity metadata.** Role, title, team, level (e.g. "Staff Engineer", "Senior SWE") must come from Pandora PEOPLE results — never inferred, guessed, or filled in from context. If Pandora doesn't return a field, use `[not resolved]` in the report. Presenting guessed metadata as fact is a defect that deep-qa must catch.

### Step 1: Normalize the input

| Input looks like | Action |
|---|---|
| `@something` | Strip `@`, treat as username/alias |
| `user@netflix.com` | Email — skip to Step 2b |
| Contains space (e.g. "Nissan Pow") | Full name — skip to Step 2a |
| Single word, no `@` | Ambiguous — could be username, first name, or alias. Try all paths. |

### Step 2: Pandora/PEOPLE lookup

**2a) If you have a full name or email:**
```
netflix_search_api(sources: ["PANDORA", "PEOPLE"], queryString: "{full_name_or_email}")
```
This reliably returns: full name, email, team, role, manager.

**2b) If you only have a username:**
- Construct email guess: `{username}@netflix.com`
- Search Pandora by email: `netflix_search_api(sources: ["PANDORA"], queryString: "{username}@netflix.com")`
- If nothing: search by username as a name: `netflix_search_api(sources: ["PEOPLE"], queryString: "{username}")`
- If still nothing: proceed to Step 3 with the username only.

**What you get:** Full name, email, team, role. If Pandora matched, you now have enough for most sources.

### Step 3: Sourcegraph commit metadata (the bridge)

This is the most reliable cross-reference for code contributors. Git commits embed both name and email.

```
get_contributor_repos(authors=["{name}", "{email}", "{username}"])
```

Pass ALL identifiers you have so far — Sourcegraph matches any of them against commit author fields. The response includes repos with commit counts, and the matched author string reveals the `Name <email>` pair from git config.

**What you get:** GitHub username (from email domain convention), full name, email, active repos.

**Limitation:** Only works for people who have committed code. Non-code contributors (PMs, managers, data analysts who only use notebooks) won't appear.

### Step 4: GitHub API confirmation

If you have a suspected GitHub username:
```
gh api users/{username} --hostname github.netflix.net
```

Returns the profile including name and email (if set). If 404, the username is wrong — fall back to email-based search or Sourcegraph commit metadata.

For email-based lookup (when you have email but not username):
```
gh api search/users?q={email}+in:email --hostname github.netflix.net
```

### Step 5: Slack (best effort)

`rag-slack-prod` is content-based search, not author-based. You cannot reliably find "messages by person X." Instead:

- Search for their **full name** (not username) in recent threads
- Search for topics they're known to work on (discovered from GitHub/Jira)
- Accept that Slack coverage for a specific person will be noisy

**Known failure mode:** Common first names or names that match other words (e.g. "nissan" matches car discussions). Use full name when possible.

## Resolution Output

After the cascade, you should have:

```
{
  "full_name": "Nissan Pow",
  "email": "npow@netflix.com",
  "github_username": "npow",
  "team": "ML Platform",
  "role": "Senior Software Engineer",
  "slack_search_terms": ["Nissan Pow", "npow"],
  "active_repos": ["org/repo1", "org/repo2"],
  "resolution_confidence": "high|medium|low",
  "resolution_path": "username → email guess → Pandora → Sourcegraph confirmed"
}
```

Include `resolution_confidence` and `resolution_path` in any report that depends on identity resolution. If confidence is `low`, note it — the reader should know the data may be incomplete or mixed with another person's activity.

## Confidence Levels

| Level | Criteria |
|---|---|
| `high` | Pandora returned a match AND Sourcegraph confirmed via commit metadata |
| `medium` | One source confirmed (Pandora OR Sourcegraph), other assumed from convention |
| `low` | Email guessed from convention, no confirmation from any system. Results may be wrong. |

## Team/Alias Resolution

When input is a team alias (e.g. `@ml-platform`):

1. Search Pandora: `netflix_search_api(sources: ["PANDORA"], queryString: "{alias}")`
2. If Pandora returns team members: run the cascade above for each member
3. If nothing: search Slack for the alias in channel descriptions or usergroup mentions
4. If nothing: search Netflix Search API with PEOPLE source for the alias as a team name
5. If still nothing: proceed with `resolution_confidence: low` and note the gap — never stop to ask the user for names
6. List resolved members in the report header so the reader can spot mismatches

## Failure Diagnosis

| Symptom | Cause | Fix |
|---|---|---|
| Pandora returns 0 for username | Pandora doesn't index usernames | Try `{username}@netflix.com` as email |
| Sourcegraph returns 0 repos | Person doesn't commit code (PM, analyst) | Rely on Pandora + email convention. Note reduced GitHub coverage. |
| `gh api users/{x}` returns 404 | Wrong GitHub username | Check Sourcegraph commit metadata for the actual username |
| Slack search returns irrelevant results | Name matches common words | Use full name in quotes, or search for their known project topics instead |
| Multiple people match | Common name, ambiguous input | Use email for precision. If still ambiguous, include all matches with a note — never stop to ask. |

## Anti-Rationalization

| Excuse | Reality |
|---|---|
| "Pandora didn't find them, they probably don't exist." | Pandora doesn't match usernames. Try email convention `{user}@netflix.com` or full name. |
| "I'll just use the username for everything." | Each system uses different identifiers. A GitHub username won't match in Jira or Pandora. Run the cascade. |
| "Sourcegraph found repos, that's enough to confirm identity." | Sourcegraph matches fuzzy. Verify the matched author string actually contains the right person's name/email. |
| "Slack search returned results mentioning them, so I found their activity." | Content mentions != authored by. Someone else may be discussing them. Note this limitation. |
| "I'll skip identity resolution for known teammates." | Even known teammates may use different handles across systems. Always resolve — it's fast and prevents silent mismatches. |
