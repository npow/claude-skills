---
name: ci-health-report
description: "Use when checking CI/CD health, Jenkins build failures, flaky tests, build success rates, or generating a CI health report. Trigger phrases: CI health, build failures, jenkins report, flaky tests, build health, are builds passing, CI status."

category: report
capabilities: [static-analysis]
input_types: [repo]
output_types: [report, code]
complexity: moderate
cost_profile: low
maturity: beta
metadata_source: inferred
---

# CI/CD Health Report

Produce an actionable weekly health report for Jenkins CI builds using Boost MCP tools. The report root-causes failures and groups them — a list of build numbers is not a report.

## Configuration

Reads defaults from `~/.claude/skills/ci-health-report/config.json` if it exists.

```json
{
  "repos": [
    {"hostType": "GHE", "projectKey": "corp", "repoSlug": "my-repo"}
  ],
  "controllers": ["mycontroller"],
  "job_name_contains": "my-team",
  "lookback_days": 7
}
```

**Resolution order:** user prompt overrides > config.json > built-in defaults.

**At least one scope must be set:** `repos`, `controllers`, or `job_name_contains`. If none set, ask once and save to config.json.

## Arguments

- **repos**: list of {hostType, projectKey, repoSlug} to check
- **controllers**: Jenkins controller names to scope search
- **job_name_contains**: substring match on job name
- **lookback_days**: how far back to check builds (default: match your cadence — 1 for daily, 7 for weekly)

## Workflow

1. **Discover jobs.** Use `search_jobs` with configured scope. Filter to ACTIVE state.

2. **Get recent builds.** For each job, call `search_builds`. Compute per-job: total builds, failures, success rate.

3. **Resolve what each build was building.** For each failed build, use the commitId to determine the PR or branch context. Use `gh pr list --search <commitSha>` or parse the triggerEventType + ref. The report must show linked PRs — not bare build numbers or commit SHAs. Construct the PR URL from the repo discovered in step 1: `https://github.netflix.net/{projectKey}/{repoSlug}/pull/{number}`. Format as Slack mrkdwn links: `<https://github.netflix.net/{projectKey}/{repoSlug}/pull/1234|PR #1234>: title`.

4. **Fetch build logs and root-cause failures.** For EVERY failed build:
   - Get the build UUID from the `id` field in search_builds results
   - Read the log via `ReadMcpResourceTool(server="netflix-ci-official", uri="build-log://{build_uuid}")`
   - This returns a presigned S3 URL — download it with `curl -sL "{url}" | tail -50`
   - Extract the actual error: test failure name, compilation error, timeout, setup failure, etc.
   - Classify each failure into a root cause category.
   - Capture the Jenkins build URL from the build result (construct from controller + job name + build number: `https://{controller}.build.netflix.net/job/{job_name}/{build_number}/`). Include this link in the report so readers can jump straight to the build console.
   - NEVER use WebFetch on Jenkins URLs — they're behind Meechum auth. Always use `build-log://`.

5. **Group failures by root cause.** Multiple builds may fail for the same reason (same test, same compilation error, same infra issue). Deduplicate. The report should say "TestWorkerRetry.test_timeout failed 5 times across 3 PRs" — not list 5 separate failures.

6. **Identify flaky vs broken.** A job is "flaky" if failure rate is 10-90% AND failures have multiple distinct root causes. A job is "broken" if failure rate >90% OR all failures share one root cause.

7. **Generate report.** Output markdown:

```
## CI/CD Health Report — {date}
Job: {job_name} | Controller: {controller} | Repo: {project}/{repo}
Period: last {lookback_days} days | Builds: {total} | Success rate: {pct}%

### Failure Root Causes (grouped)

#### 1. {root cause category} — {N} failures
Error: {actual error message or test name}
Affected PRs: <https://github.netflix.net/{project}/{repo}/pull/{number}|PR #{number}>: {title}, ...
Pattern: {infra flake / test bug / code bug / timeout}
Example log snippet: {2-3 key lines from the log}
Failed builds: <{jenkins_build_url}|Build #{number}>, ...

#### 2. {root cause category} — {N} failures
...

### Flaky Tests
(Tests that sometimes pass, sometimes fail — with pass/fail counts)

### Build Performance
- Median duration: {time} | P95: {time}
- Fastest: {time} | Slowest: {time}

### Healthy Builds
{N} builds succeeded across {N} PRs in the period.
```

8. **Deliver as HTML.** Follow the shared HTML delivery pattern in [`_shared/html-delivery.md`](../_shared/html-delivery.md). Report name: `ci-health`. TLDR includes job name, success rate, and top failure root cause.

9. **Terminate.** Report is complete when all failure root causes are grouped with log evidence.

## Design Principles

1. **Team-level only.** Aggregate to team level — it is the right granularity for a periodic digest. Individual-level detail (commits per person, PR count per author) is too noisy for a team report.
2. **Deterministic math first, LLM narrates only.** All classification (severity, flaky vs broken, pass/fail) must be computed deterministically from data. The LLM writes prose around the numbers but never assigns severity or makes classification judgments.
3. **Pair metrics with counter-metrics.** Never report velocity without stability. If showing deploy frequency, also show change failure rate. If showing PR throughput, also show rework rate.

## Golden Rules

1. **Root-cause every failure.** Fetch the build log. Extract the error. "Build failed" is not a root cause.
2. **Group by root cause, not by build.** 5 builds failing the same test is ONE issue, not five.
3. **Show what was being built — with links.** PR number + title as a clickable Slack mrkdwn link (`<url|PR #N>`), or branch name. Never bare build numbers or commit SHAs — those mean nothing to the reader.
4. **Log evidence is mandatory.** Every root cause group includes 2-3 key lines from the actual build log proving the classification.
5. **Flaky != broken.** Multiple distinct root causes with mixed pass/fail = flaky. Single root cause dominating = broken.
6. **Check ALL builds in scope, not a sample.**

## Anti-Rationalization Counter-Table

| Excuse | Reality |
|---|---|
| "I listed all the failures with their build numbers." | Build numbers are meaningless. Show PR context and group by root cause. A list of numbers is not a report. |
| "I classified the failure from the status alone." | FAILED status tells you nothing. The build log tells you what actually broke. Fetch it. |
| "Each failure is different so I listed them separately." | Did you actually read the logs? Multiple builds often fail the same test or hit the same infra issue. Group them. |
| "I can't fetch the build log." | The logUrl is in every build result. WebFetch it. If it's too large, fetch the tail. |
| "The PR context isn't available." | The commitId is in every build. Use `gh` CLI to find the associated PR. |

## Termination Labels

| Label | Meaning |
|---|---|
| `report_complete` | All builds checked, failures root-caused from logs, grouped by cause, PR context resolved |
| `report_partial` | Some builds checked but log fetch or PR resolution failed for some — noted which |
| `no_jobs_found` | search_jobs returned empty — scope may be wrong |
| `api_error` | Boost API unreachable or returning errors |

## Self-Review Checklist

- [ ] Every failure has a root cause extracted from the actual build log
- [ ] Failures are grouped by root cause, not listed per-build
- [ ] Every failure group shows affected PRs as clickable links (Slack mrkdwn `<url|PR #N>`: title), not bare numbers or build IDs
- [ ] Log evidence (2-3 lines) included for each root cause group
- [ ] Each failed build includes a clickable Jenkins build link
- [ ] Failure rates computed from actual build counts
- [ ] Report includes build performance stats (median, p95 duration)
- [ ] HTML version uploaded to S3 with commuter link (unless `--no-html` or upload failed with noted fallback)
- [ ] Slack/chat delivery uses TLDR + link, not the full report
