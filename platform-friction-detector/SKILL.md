---
name: platform-friction-detector
description: "Use when scanning for silent user workarounds, platform friction signals, dependency removals, or users routing around your libraries. Trigger phrases: platform friction, user workarounds, who's dropping our libs, silent churn, friction scan, are users working around us."
---

# Platform Friction Detector

Scan downstream repos, PRs, commits, and Slack for signals that users are quietly working around your platform libraries instead of reporting problems. These silent workarounds represent untracked friction — users who hit a wall and routed around it without filing a bug.

## Configuration

Reads defaults from `~/.claude/skills/platform-friction-detector/config.json` if it exists.

```json
{
  "platform_packages": ["metaflow", "nflx-fastdata", "dagobah"],
  "platform_imports": ["from metaflow", "import metaflow", "from nflx_fastdata", "from dagobah"],
  "search_scope": "github.netflix.net/corp/*",
  "exclude_repos": ["corp/mlp-mlp", "corp/mli-metaflow-custom"],
  "slack_channels": [],
  "lookback_days": 30
}
```

**Resolution order:** user prompt overrides > config.json > built-in defaults.

**At least `platform_packages` must be set.** If not configured and user didn't specify, infer from context (team repos, recent work) or note the gap.

## Arguments

- **platform_packages**: package names your team owns that downstream users depend on
- **platform_imports**: import patterns to search for in diffs (auto-derived from packages if not set)
- **search_scope**: Sourcegraph repo pattern to search (default: `github.netflix.net/corp/*`)
- **exclude_repos**: your own platform repos to skip (signals in these are internal, not friction)
- **slack_channels**: channel IDs where users discuss your platform
- **lookback_days**: how far back to scan (default: 30)

## Search Robustness

Sourcegraph `diff_search` on `corp/*` times out for common patterns. Handle this:

1. **One package per query.** Never batch multiple packages into one diff_search. Search `"from metaflow"` separately from `"from dagobah"`.
2. **On timeout, narrow scope.** If `repos=["github.netflix.net/corp/*"]` times out, retry with `repos=["github.netflix.net/corp/algo*", "github.netflix.net/corp/ppp-*", "github.netflix.net/corp/dse-*", ...]` — break the wildcard into smaller prefixes.
3. **On second timeout, add count limit.** Retry with `count:10` to get partial results rather than nothing.
4. **Never let one failed query skip the rest.** A timeout on dagobah doesn't excuse skipping metaflow. Each package is searched independently.
5. **Record what timed out.** The report notes which packages had incomplete coverage and why.

## Workflow

1. **Scan for removed platform imports.** For EACH platform package independently, use Sourcegraph `diff_search` with `removed=true`:
   - `diff_search(pattern="from {package}", repos=[search_scope], removed=true, after="{lookback}")`
   - `diff_search(pattern="import {package}", repos=[search_scope], removed=true, after="{lookback}")`
   - On timeout: narrow repos scope per Search Robustness rules above.
   - Each hit is a potential workaround. Record: repo, file, author, date, what replaced it.

2. **Scan for dependency file changes.** Use Sourcegraph `diff_search` filtered to dependency files:
   - `diff_search(pattern="{package}", repos=[downstream_repos], removed=true, after="{lookback}")` with `file:requirements` or `file:pyproject.toml` or `file:setup.cfg`
   - A removed line in requirements.txt/pyproject.toml containing your package name is a strong signal.

3. **Scan for workaround language in commits.** Use Sourcegraph `commit_search` for commits mentioning your packages alongside friction words:
   - `commit_search(repos=[downstream_repos], messageTerms=["workaround {package}", "replace {package}", "remove {package}", "migrate from {package}", "instead of {package}", "drop {package}", "too heavy", "dependency conflict"])` filtered by date
   - Also search: "bypass", "hack", "temporary", "lightweight alternative"

4. **Scan for replacement patterns in added code.** Use Sourcegraph `diff_search` with `added=true` to find what replaced your library:
   - If step 1 found removed metaflow S3 imports, search the same repos for added `import boto3` or `from boto3` in the same time window
   - Common replacements: raw boto3 for S3 ops, raw requests for API calls, custom implementations of platform features

5. **Search Slack for friction signals.** If slack_channels configured, use `rag-slack-prod`:
   - Search for: "{package} broken", "{package} issue", "{package} conflict", "alternative to {package}", "can't use {package}", "{package} too heavy", "{package} dependency"
   - For each hit, fetch the full thread via `fetch-slack-thread` to get context

6. **Fetch PR context for each signal.** For every diff/commit signal found, resolve the PR:
   - Use `gh api repos/{org}/{repo}/commits/{sha}/pulls --hostname github.netflix.net` to find the associated PR
   - Get PR title, body, author — the PR description often explains the "why" behind the workaround

7. **Classify and group signals.** For each signal, classify:
   - **Signal type**: `dependency_removal` | `import_replacement` | `workaround_commit` | `slack_friction` | `dependency_downgrade`
   - **Severity**: `high` (package fully removed) | `medium` (partial replacement or workaround) | `low` (discussion only, no code change)
   - **Root cause** (infer from PR body/commit message): dependency conflict, performance, complexity, missing feature, breaking change
   - Group by root cause — multiple users hitting the same issue = one problem, not N separate signals

8. **Generate report.** Output markdown:

```
## Platform Friction Report — {date}
Packages monitored: {list} | Period: last {lookback_days} days | Signals found: {N}

### Summary
- Dependency removals: {count} | Import replacements: {count} | Workaround commits: {count} | Slack friction: {count}

### Grouped by Root Cause

#### 1. {Root Cause} — {N} signals, severity: {high|medium|low}
What: {1-2 sentence description of the friction}
Evidence:
- {PR link}: {title} by {author} — {what they did}
- {PR link}: {title} by {author} — {what they did}
- {Slack thread permalink}: {summary}
Impact: {N} repos affected, {N} users impacted
Suggested action: {what the platform team should do}

#### 2. {Root Cause} — {N} signals
...

### Ungrouped Signals
(Signals that don't cluster into a clear root cause — may be one-off or need investigation)

### All Clear
(Packages with zero friction signals — positive confirmation)
```

9. **Deliver as HTML.** Follow the shared HTML delivery pattern in [`_shared/html-delivery.md`](../_shared/html-delivery.md). Report name: `friction-report`. TLDR includes package count, total signals found, and top root cause.

10. **Terminate.** Report is complete when all packages are scanned across all signal types and HTML uploaded (or fallback noted).

## Design Principles

1. **Group by root cause, not by signal type.** Three PRs removing metaflow S3 because of dependency conflicts is ONE problem, not three. The reader needs to understand friction themes, not raw signal counts.
2. **Deterministic classification first.** Signal type and severity are computed from code changes (removed import = high, Slack mention = low). The LLM infers root cause from PR descriptions but never invents signals.
3. **Show what replaced your library.** "User removed metaflow" is not actionable. "User replaced metaflow S3 with boto3 because of dependency weight" tells you what to fix.

## Golden Rules

1. **Removed imports are the strongest signal.** A user removing `from metaflow import S3` is definitive evidence of a workaround. Always scan for this first.
2. **Fetch the PR for every code signal.** The PR body explains the "why." A diff without context is just a change — the PR makes it a friction signal.
3. **Group by root cause.** Multiple users hitting the same issue = one problem to fix, with higher urgency.
4. **Include the replacement.** What did they use instead? This tells you what the user actually needed that your library didn't provide well enough.
5. **Scan ALL configured packages.** Don't stop after finding signals for the first package.
6. **"All clear" is valuable.** A package with zero friction signals is positive evidence that it's working well. Report it.

## Anti-Rationalization Counter-Table

| Excuse | Reality |
|---|---|
| "I found the removed imports, that's enough." | The PR body has the root cause. Fetch it. "They removed it" is not actionable without knowing why. |
| "Only one user removed the package, it's probably fine." | One visible workaround often means 5 users who struggled and stayed silent. Investigate. |
| "The Slack search didn't find anything, so users are happy." | Slack is noisy and rag-slack-prod is semantic search. Absence of Slack signal doesn't mean absence of friction. The code signals (removed imports) are definitive. |
| "I'll just search for the package name in diffs." | Undirected search returns both additions and removals. Filter `removed=true` for friction signals. |
| "The PR is too old to matter." | A workaround from 3 months ago that's still in production means the friction is ongoing. Age doesn't reduce severity. |
| "The search timed out so I'll skip that package." | Narrow the scope and retry. One package per query, smaller repo prefixes on timeout. A timeout is not a pass — it's incomplete coverage that must be noted. |

## Termination Labels

| Label | Meaning |
|---|---|
| `report_complete` | All packages scanned, all signal types checked, PRs fetched, grouped by root cause |
| `report_partial` | Some packages or signal types checked but errors prevented full coverage |
| `no_signals_found` | All packages scanned, zero friction signals — report "all clear" with scan details |
| `api_error` | Sourcegraph or GitHub API unreachable |

## Self-Review Checklist

- [ ] Every configured package was scanned for removed imports
- [ ] Dependency files (requirements.txt, pyproject.toml) were searched for removals
- [ ] PR context fetched for every code-based signal (not just the diff)
- [ ] Signals grouped by inferred root cause, not listed individually
- [ ] Each signal group includes what replaced the platform library
- [ ] Severity classification based on signal type (code change > Slack mention)
- [ ] Report date and lookback period noted in header
- [ ] "All clear" packages listed explicitly
- [ ] HTML version uploaded to S3 with commuter link (unless `--no-html` or upload failed with noted fallback)
- [ ] Slack/chat delivery uses TLDR + link, not the full report
