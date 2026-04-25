---
name: dependency-audit
description: "Use when auditing dependencies, checking for outdated packages, reviewing security vulnerabilities, scanning for CVEs, or checking dependabot/renovate PR status. Trigger phrases: dependency audit, security audit, outdated dependencies, CVE check."
---

# Dependency Audit Report

Produce a monthly dependency and security audit report across configured repositories using Sourcegraph search and GitHub CLI tools. The report identifies outdated dependencies, known CVE references, and pending dependency update PRs.

## Configuration

Reads defaults from `~/.claude/skills/dependency-audit/config.json` if it exists.

```json
{
  "repos": [
    "github.netflix.net/myorg/repo1",
    "github.netflix.net/myorg/repo2"
  ]
}
```

**Resolution order:** user prompt overrides > config.json > built-in defaults.

**At least one repo must be set.** If none is set and the user didn't specify, ask once and save to config.json.

## Arguments

- **repos**: list of repository names to audit (must match Sourcegraph and gh CLI format)

## Workflow

1. **Identify dependency files.** For each repo, use `list_files` to check for:
   - Python: `requirements.txt`, `requirements.in`, `pyproject.toml`, `setup.py`
   - Java/Kotlin: `build.gradle`, `build.gradle.kts`, `dependencies.lock`, `gradle.lockfile`
   - JavaScript/TypeScript: `package.json`, `package-lock.json`, `yarn.lock`
   - Go: `go.mod`, `go.sum`
   - Read the primary dependency files with `read_file` to catalog declared dependencies.

2. **Search for known CVE references.** For each repo, use `keyword_search` with query `repo:^{repo}$ CVE-` to find any explicit CVE references in code, comments, or config. Also search with `nls_search` for `repo:^{repo}$ vulnerability advisory security patch` to find security-related mentions.

3. **Search for outdated dependency patterns.** Use `keyword_search` for common staleness signals per ecosystem:
   - Python: `repo:^{repo}$ file:requirements pinned versions` — look for `==` pinned versions that may be outdated.
   - Java: `repo:^{repo}$ file:build.gradle` — check for deprecated dependency declarations.
   - JS: `repo:^{repo}$ file:package.json` — read and identify major version gaps.

4. **Check dependency update PRs.** For each repo, use `gh` CLI:
   - `gh pr list --repo {repo} --state open --label "dependencies" --json number,title,createdAt,author` to find dependabot/renovate PRs.
   - `gh pr list --repo {repo} --state open --search "author:dependabot author:renovate bump update" --json number,title,createdAt,author` as a fallback if no label exists.
   - Classify: how many are open, how old is the oldest, are any security-critical (title contains "security" or "CVE").

5. **Check for deprecated or removed packages.** Use `keyword_search` to search for known deprecated patterns:
   - `repo:^{repo}$ (deprecated|end-of-life|EOL|no longer maintained)` in dependency-adjacent files.

6. **Generate report.** Output markdown:

```
## Dependency Audit — {date}
Repos audited: {N}

### Summary
- Repos with open dependency PRs: {N} | Total open dependency PRs: {N}
- Repos with CVE references: {N} | Security-critical PRs: {N}
- Oldest unmerged dependency PR: {age in days}

### Security Findings
(For each CVE reference found: repo, file, CVE ID, context snippet, severity if known)

### Open Dependency Update PRs
| Repo | PR | Title | Age (days) | Security? |
|---|---|---|---|---|
(All open dependabot/renovate PRs across repos, sorted by age descending)

### Stale Dependency PRs (> 30 days open)
(For each: repo, PR number, title, age, why it might be stuck)

### Dependency Ecosystem Summary
| Repo | Ecosystem | Dependency File | Declared Deps | Pinned | Floating |
|---|---|---|---|---|---|
(Per-repo breakdown of dependency management approach)

### Flags
(Concerning signals: old unmerged security PRs, CVEs in code, no dependency update mechanism)
```

7. **Post to `#team-digests` channel if configured, never to a primary team channel.**

8. **Terminate.** Report is complete when all repos are audited and findings compiled.

## Design Principles

1. **Team-level only.** Aggregate to team level — it is the right granularity for a periodic digest. Don't attribute dependency debt to individuals.
2. **Deterministic math first, LLM narrates only.** PR counts, ages, and CVE occurrences must be computed from actual API data. The LLM summarizes but never invents severity ratings or vulnerability assessments.
3. **Pair metrics with counter-metrics.** Never report open dependency PRs without showing merge rate. If showing CVE references, also show whether they've been addressed.

## Golden Rules

1. **Security PRs go first.** Any dependency PR with "security" or "CVE" in the title gets flagged and surfaced at the top.
2. **Age is the key metric for dependency PRs.** A 3-day-old PR is routine. A 90-day-old PR is a risk. Sort by age, flag anything over 30 days.
3. **Don't assess vulnerability severity yourself.** Report what's found (CVE IDs, PR titles) and let the reader assess. The LLM is not a security scanner.
4. **Check ALL repos, not a sample.** Every configured repo gets a full audit.
5. **No dependency update mechanism is itself a finding.** If a repo has no dependabot/renovate PRs and no recent dependency changes, flag it — dependencies are frozen, not up-to-date.

## Anti-Rationalization Counter-Table

| Excuse | Reality |
|---|---|
| "No CVEs found so dependencies are secure." | Absence of CVE references in code does not mean absence of vulnerabilities. Report what you found and note the limitation. |
| "I checked the main repo, the others are small." | Audit ALL configured repos. Small repos with outdated dependencies are still a risk. |
| "There are too many dependency PRs to list." | List them all in the table. The reader needs the complete picture to prioritize. |
| "I can't determine if dependencies are outdated without a registry lookup." | You can report: pinned versions, dependency PR age, and absence of update mechanisms. That's actionable without registry lookups. |
| "The repo uses a custom dependency system so I skipped it." | Report what dependency files exist and note the non-standard setup. Don't silently skip. |

## Termination Labels

| Label | Meaning |
|---|---|
| `report_complete` | All repos audited, CVE search done, dependency PRs cataloged, flags raised |
| `report_partial` | Some repos audited but errors prevented full coverage — noted which |
| `no_repos_configured` | No repos specified — need config.json or user input |
| `api_error` | Sourcegraph or GitHub API unreachable |

## Self-Review Checklist

- [ ] All configured repos were audited
- [ ] CVE keyword search was run on every repo
- [ ] Dependency update PRs were checked via gh CLI for every repo
- [ ] PR ages computed and stale PRs (>30 days) flagged
- [ ] Security-critical PRs identified and surfaced first
- [ ] Dependency ecosystem summary shows what files exist per repo
- [ ] Flags section surfaces repos with no update mechanism
