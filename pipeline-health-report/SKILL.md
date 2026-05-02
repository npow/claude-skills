---
name: pipeline-health-report
description: "Use when checking data pipeline health, workflow status, Maestro failures, or generating a daily pipeline report. Trigger phrases: pipeline health, workflow status, data pipeline report, maestro health, pipeline check, are my workflows healthy."

category: report
capabilities: [static-analysis]
input_types: [repo]
output_types: [report, code]
complexity: moderate
cost_profile: low
maturity: beta
metadata_source: inferred
---

# Pipeline Health Report

Produce an actionable daily health report for Maestro data workflows using Kragle MCP tools.

## Configuration

See [`_shared/report-config.md`](../_shared/report-config.md) for the standard config resolution pattern.

**Config schema** (`~/.claude/skills/pipeline-health-report/config.json`):
- `owner`: workflow owner pattern string (e.g., `data.eng.myteam`)
- `workflow_id_pattern`: wildcard pattern string (e.g., `DSE.BILLING.*`)
- `workflow_ids`: list of explicit workflow ID strings
- `cluster`: `"prod"` or `"sandbox"` (default: `"prod"`)
- `limit`: max workflows to check (default: 50)

**Required scope:** at least one of `owner`, `workflow_id_pattern`, or `workflow_ids`.

## Arguments

Parse from user input, falling back to config.json:
- **owner**: workflow owner pattern — e.g. `data.eng.*`
- **workflow_id_pattern**: wildcard pattern — e.g. `DSE.BILLING.*`
- **workflow_ids**: explicit list of workflow IDs to check
- **cluster**: `prod` | `sandbox` (default: **prod** — never default to sandbox for health reports)
- **limit**: max workflows to check (default: 50)

## Workflow

1. **Discover workflows.** Use the configured scope to find workflows:
   - If `workflow_ids` is set: skip search, check each ID directly via `get_latest_instance`
   - If `workflow_id_pattern` is set: call `search_workflows` with `workflow_id_pattern` and cluster=prod
   - If `owner` is set: call `search_workflows` with `owner` and cluster=prod
   - If none is set and no config.json: ask the user once, then save their answer to config.json for future runs

2. **Check every workflow.** For EACH workflow returned, call `get_latest_instance` with cluster=prod. Record status: SUCCEEDED, FAILED, IN_PROGRESS, or no recent instance.

3. **Drill into failures.** For every FAILED instance, call `get_instance_failures` with cluster=prod. Extract: step_id, attempt number, status, and instance link. This step is MANDATORY — never report a failure without step-level detail.

4. **Check running durations.** For every IN_PROGRESS instance, call `get_instance_summary` with cluster=prod. Flag any instance running longer than 2 hours as "long-running."

5. **Generate report.** Output markdown with these sections in order:

```
## Pipeline Health Report — {date}
Cluster: {cluster} | Owner filter: {owner or "all"} | Workflows checked: {N}

### Summary
- Failed: {count} | In Progress: {count} | Succeeded: {count} | No Recent Run: {count}

### Failed Workflows
(For each: workflow_id, failed step, error summary, instance link)

### Long-Running Workflows
(For each: workflow_id, duration so far, instance link)

### In Progress
(Compact list: workflow_id, start time)

### Recently Succeeded
(Compact table: workflow_id, last success time)
```

6. **Deliver as HTML.** Follow the shared HTML delivery pattern in [`_shared/html-delivery.md`](../_shared/html-delivery.md). Report name: `pipeline-health`. TLDR includes workflows checked, failure count, and long-running instances.

7. **Terminate.** Report is complete when all sections are populated (even if a section says "None").

## Design Principles

1. **Team-level only.** Aggregate to team level — it is the right granularity for a periodic digest. Individual-level detail (commits per person, PR count per author) is too noisy for a team report.
2. **Deterministic math first, LLM narrates only.** All classification (severity, flaky vs broken, pass/fail) must be computed deterministically from data. The LLM writes prose around the numbers but never assigns severity or makes classification judgments.
3. **Pair metrics with counter-metrics.** Never report velocity without stability. If showing deploy frequency, also show change failure rate. If showing PR throughput, also show rework rate.

## Golden Rules

1. **Always cluster=prod.** Every Kragle MCP call passes cluster="prod" unless the user explicitly says sandbox. Sandbox workflows are tests, not production health.
2. **Never skip get_instance_failures.** Every FAILED workflow gets a get_instance_failures call. "Workflow X failed" without step detail is useless.
3. **Check ALL workflows, not a sample.** If search_workflows returns 50 results and you set limit=50, consider whether there are more. Increase limit or paginate.
4. **Failures first.** Report sections are ordered by severity. Failures at top, succeeded at bottom.
5. **Include links.** Every failed or in-progress workflow includes its instance_link from the API response. The reader must be able to click through without additional lookups.
6. **"All clear" is still a report.** When everything succeeded, produce the full report structure with counts and timestamps. One sentence is not a report.
7. **No invented data.** Every number in the report comes from a Kragle API response. Never estimate or infer workflow counts.

## Anti-Rationalization Counter-Table

| Excuse | Reality |
|---|---|
| "I spot-checked a few workflows and they look fine." | Check ALL workflows. A single missed failure defeats the purpose of the report. |
| "The workflow failed but I didn't call get_instance_failures because the status says it all." | FAILED status tells you nothing actionable. The step_id and error from get_instance_failures is what the on-call needs. Call it. |
| "I'll skip the sandbox/prod parameter since the default is fine." | The Kragle default is sandbox. Your report will silently cover test workflows. Always pass cluster="prod" explicitly. |
| "Everything succeeded so there's nothing to report." | The report IS the evidence. Write the full structure with counts and timestamps. |
| "There are too many workflows to check individually." | Increase the limit parameter. The report must cover the full set, not a sample. |
| "The instance link wasn't in the response." | It is — check the instance_link field in get_latest_instance and get_instance_failures responses. |

## Termination Labels

| Label | Meaning |
|---|---|
| `report_complete` | All workflows checked, all sections populated, failures have step-level detail |
| `report_partial` | Some workflows checked but API errors prevented full coverage — note which were skipped |
| `no_workflows_found` | search_workflows returned empty — owner pattern may be wrong |
| `api_error` | Kragle API unreachable or returning errors — report what was gathered before failure |

## Self-Review Checklist

Before delivering the report, verify:
- [ ] Every Kragle call used cluster="prod" (or user-specified cluster)
- [ ] Total workflows in Summary matches count from search_workflows
- [ ] Every FAILED workflow has get_instance_failures output (step_id + link)
- [ ] Every IN_PROGRESS workflow has duration from get_instance_summary
- [ ] Failed section appears before Succeeded section
- [ ] Instance links are present for all failed and in-progress workflows
- [ ] Report has a date header and owner filter noted
- [ ] HTML version uploaded to S3 with commuter link (unless `--no-html` or upload failed with noted fallback)
- [ ] Slack/chat delivery uses TLDR + link, not the full report
