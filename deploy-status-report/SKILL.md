---
name: deploy-status-report
description: "Use when checking deployment status, Spinnaker deploys, canary results, what's deployed, pending rollouts, or generating a deployment report. Trigger phrases: deploy status, what's deployed, spinnaker status, canary results, deployment report, rollout status."
---

# Deployment Status Report

Produce an actionable report on Spinnaker deployment state using Delivery MCP tools.

## Configuration

Reads defaults from `~/.claude/skills/deploy-status-report/config.json` if it exists.

```json
{
  "apps": ["myapp1", "myapp2"],
  "lookback_days": 7
}
```

**Resolution order:** user prompt overrides > config.json > built-in defaults.

**At least one app must be set.** If none is set and the user didn't specify, ask once and save to config.json.

## Arguments

- **apps**: list of Spinnaker application names to check
- **lookback_days**: how far back to check executions (default: match your cadence — 1 for daily, 7 for weekly)

## Workflow

1. **Check Managed Delivery status.** For each app, invoke `delivery:delivery-managed-delivery` to get current deployed versions, pending deploys, constraint state (canary, deploy windows, depends-on), and verification results.

2. **Check recent pipeline executions.** For each app, invoke `delivery:delivery-spinnaker` to get recent pipeline execution history. Note any failed executions.

3. **Get canary details for failures.** For any app with a failed canary constraint, invoke `delivery:delivery-managed-delivery-canary` to get per-interval scores and region breakdown.

4. **Analyze failed executions.** For any failed pipeline execution, invoke `delivery:delivery-execution-failure-analysis` with the execution ID to get EFA results.

5. **Generate report.** Output markdown:

```
## Deployment Status Report — {date}
Period: last {lookback_days} days | Apps checked: {N}

### Summary
- Apps with blocked deploys: {count} | Failed canaries: {count} | Successful deploys: {count}

### Blocked Deploys
(For each: app, what's blocked, constraint type, details, Chap URL)

### Failed Canaries
(For each: app, canary score, failing metrics, analysis ID, Chap URL)

### Failed Pipeline Executions
(For each: app, pipeline name, failure reason from EFA, execution link)

### Successfully Deployed
(For each: app, current version, deploy time, regions)

### Pending
(For each: app, pending version, waiting on what constraint)
```

6. **Post to `#team-digests` channel if configured, never to a primary team channel.**

7. **Terminate.** Report is complete when all sections are populated.

## Design Principles

1. **Team-level only.** Aggregate to team level — it is the right granularity for a periodic digest. Individual-level detail (commits per person, PR count per author) is too noisy for a team report.
2. **Deterministic math first, LLM narrates only.** All classification (severity, flaky vs broken, pass/fail) must be computed deterministically from data. The LLM writes prose around the numbers but never assigns severity or makes classification judgments.
3. **Pair metrics with counter-metrics.** Never report velocity without stability. If showing deploy frequency, also show change failure rate. If showing PR throughput, also show rework rate.

## Golden Rules

1. **Check Managed Delivery first.** It gives the current state of what's deployed and what's pending. Pipeline history is supplementary.
2. **Always get canary details for failed canaries.** "Canary failed" without scores is not actionable. Call the canary skill.
3. **Always get EFA for failed executions.** "Pipeline failed" without EFA diagnosis is not actionable.
4. **Include Chap URLs.** Every blocked deploy and failed canary includes the Chap URL from the API response.
5. **Check ALL apps, not a sample.** Every configured app gets checked every run.
6. **Blocked deploys are the highest priority.** They represent work that's stuck. Surface them first.

## Anti-Rationalization Counter-Table

| Excuse | Reality |
|---|---|
| "The deploy looks fine, I'll skip the canary details." | If a canary failed or is pending, get the scores. "Looks fine" is not evidence. |
| "Pipeline failed but I didn't run EFA because the status is clear." | EFA gives the root cause. Status gives the outcome. You need both. |
| "I checked the main app, the others are probably fine." | Check ALL configured apps. A blocked deploy on a secondary app is still a blocked deploy. |
| "No Chap URL in the response, I'll skip the link." | Chap URLs are in the delivery tool responses. Look for them in the constraint and verification fields. |

## Termination Labels

| Label | Meaning |
|---|---|
| `report_complete` | All apps checked, blocked deploys detailed, canary scores included |
| `report_partial` | Some apps checked but errors prevented full coverage |
| `no_apps_configured` | No apps specified — need config.json or user input |
| `api_error` | Spinnaker/Delivery API unreachable |

## Self-Review Checklist

- [ ] All configured apps were checked
- [ ] Failed canaries have per-interval scores and Chap URLs
- [ ] Failed executions have EFA analysis
- [ ] Blocked deploys section appears first after summary
- [ ] Chap URLs present for all blocked/failed items
- [ ] Report has date header and app list noted
