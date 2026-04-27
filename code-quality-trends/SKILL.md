---
name: code-quality-trends
description: "Use when checking code quality trends, tech debt accumulation, TODO/FIXME growth, test coverage ratios, PR size distribution, or generating a code quality report. Trigger phrases: code quality, code trends, tech debt trends, quality report."

category: qa
capabilities: [trend-tracking, static-analysis]
input_types: [git-diff, code-path, repo]
output_types: [code, report]
complexity: moderate
cost_profile: low
maturity: beta
metadata_source: inferred
---

# Code Quality Trends Report

Produce a monthly trends report tracking code quality signals across repositories using Sourcegraph and GitHub CLI tools. The report measures TODO/HACK/FIXME accumulation, test file ratios, and PR merge patterns.

## Configuration

Reads defaults from `~/.claude/skills/code-quality-trends/config.json` if it exists.

```json
{
  "repos": [
    "github.com/myorg/repo1",
    "github.com/myorg/repo2"
  ],
  "lookback_days": 30
}
```

**Resolution order:** user prompt overrides > config.json > built-in defaults.

**At least one repo must be set.** If none is set and the user didn't specify, ask once and save to config.json.

## Arguments

- **repos**: list of repository names to track (Sourcegraph-compatible format)
- **lookback_days**: how far back to analyze (default: 30)

## Workflow

1. **Measure TODO/HACK/FIXME accumulation.** For each repo:
   - Use `keyword_search` with query `repo:^{repo}$ (TODO|HACK|FIXME)` to count current occurrences.
   - Use `diff_search` with `pattern="TODO|HACK|FIXME"`, `added=true`, `after="{lookback_days} days ago"`, `useRegex=true` to count newly added markers in the period.
   - Use `diff_search` with `pattern="TODO|HACK|FIXME"`, `removed=true`, `after="{lookback_days} days ago"`, `useRegex=true` to count removed markers in the period.
   - Net change = added - removed. Positive = accumulating debt. Negative = paying down debt.

2. **Measure test file ratio.** For each repo:
   - Use `keyword_search` with query `repo:^{repo}$ file:test type:path count:all` to count test files.
   - Use `keyword_search` with query `repo:^{repo}$ file:\.(py|java|ts|js|go|kt|scala)$ type:path count:all` to count source files (exclude test files).
   - Compute ratio: test files / (source files - test files). Report as percentage.

3. **Analyze PR size distribution.** For each repo, use `gh` CLI:
   - `gh pr list --repo {repo} --state merged --limit 100 --json additions,deletions,number,title,mergedAt` filtered to the lookback period.
   - Classify PRs: small (<50 lines), medium (50-250), large (250-1000), extra-large (>1000).
   - Compute: median PR size, percentage of XL PRs, total PRs merged.

4. **Measure PR merge rates and review turnaround.** For each repo, use `gh` CLI:
   - `gh pr list --repo {repo} --state merged --limit 100 --json createdAt,mergedAt,number` filtered to lookback period.
   - Compute: median time-to-merge (createdAt to mergedAt), PRs merged per week.
   - `gh pr list --repo {repo} --state open --json createdAt,number,title` to count stale open PRs (open > 7 days).

5. **Check for large files or binary additions.** Use `diff_search` with pattern matching large additions (files with >500 added lines in a single commit) during the period. Flag as potential code quality concern.

6. **Generate report.** Output markdown:

```
## Code Quality Trends — {date}
Repos: {repo list} | Period: last {lookback_days} days

### Summary
- Total PRs merged: {N} | Median PR size: {N} lines | XL PRs (>1000 lines): {N}%
- TODO/HACK/FIXME net change: {+/-N} | Current total: {N}
- Test file ratio: {N}%

### Tech Debt Markers (TODO/HACK/FIXME)
| Repo | Current Total | Added | Removed | Net Change | Trend |
|---|---|---|---|---|---|
(Per-repo breakdown with trend arrow)

### Test Coverage Ratio
| Repo | Test Files | Source Files | Ratio | Assessment |
|---|---|---|---|---|
(Per-repo breakdown)

### PR Size Distribution
| Repo | Small (<50) | Medium (50-250) | Large (250-1K) | XL (>1K) | Median |
|---|---|---|---|---|---|
(Per-repo breakdown)

### PR Velocity
| Repo | Merged/Week | Median Time-to-Merge | Stale Open PRs |
|---|---|---|---|
(Per-repo breakdown)

### Flags
(Any concerning signals: growing debt, shrinking test ratio, many XL PRs, stale PRs)
```

7. **Post to `#team-digests` channel if configured, never to a primary team channel.**

8. **Terminate.** Report is complete when all repos have all metrics computed.

## Design Principles

1. **Team-level only.** Aggregate to team level — it is the right granularity for a periodic digest. Individual-level detail (PRs per person, TODOs per author) is too noisy for a team report.
2. **Deterministic math first, LLM narrates only.** All counts, ratios, and distributions must be computed from actual search results and PR data. The LLM writes prose around the numbers but never invents counts or estimates ratios.
3. **Pair metrics with counter-metrics.** Never report PR velocity without PR size. Fast merges on huge PRs may indicate insufficient review. High test ratio without TODO trends misses the full picture.

## Golden Rules

1. **Count, don't estimate.** Every number comes from a Sourcegraph search or gh CLI result. Never say "approximately" — run the query and report the actual count.
2. **Net change matters more than absolute count.** 500 TODOs is not inherently bad; +50 TODOs this month is a trend worth flagging.
3. **PR sizes are lines changed (additions + deletions), not file count.**
4. **Use regex for debt markers.** `TODO|HACK|FIXME` must be searched with `useRegex=true` to catch all variants.
5. **Filter PRs to the lookback window.** Don't include PRs merged before the reporting period.
6. **Check ALL repos, not a sample.**

## Anti-Rationalization Counter-Table

| Excuse | Reality |
|---|---|
| "I estimated the TODO count from a sample of files." | Run the actual keyword_search. Sampling gives wrong numbers. |
| "PR sizes aren't available so I skipped that section." | The gh CLI returns additions and deletions for every PR. Compute the sum. |
| "Test ratio is hard to measure so I described it qualitatively." | Count test files. Count source files. Divide. It's arithmetic, not judgment. |
| "The repo has too many PRs to analyze all of them." | Use --limit 100 and note the sample size. 100 PRs is a representative sample for monthly trends. |
| "I listed the metrics but didn't flag any concerns." | The Flags section exists to surface concerning trends. If debt is growing or test ratio is shrinking, say so. |

## Termination Labels

| Label | Meaning |
|---|---|
| `report_complete` | All repos analyzed, all metrics computed, flags identified |
| `report_partial` | Some repos analyzed but search or CLI errors prevented full coverage — noted which |
| `no_repos_configured` | No repos specified — need config.json or user input |
| `api_error` | Sourcegraph or GitHub API unreachable |

## Self-Review Checklist

- [ ] TODO/HACK/FIXME counts come from actual Sourcegraph searches (not estimates)
- [ ] Net change computed from diff_search added vs removed counts
- [ ] Test file ratio computed from actual file counts
- [ ] PR size distribution computed from gh CLI data with additions+deletions
- [ ] PR velocity includes time-to-merge AND stale open PR count
- [ ] All configured repos were analyzed
- [ ] Flags section surfaces any concerning trends
