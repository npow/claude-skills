---
name: monitor
description: |
  Health checking for services, pipelines, code, teams, or deployments.
  Parameterized by data source. Runs one-shot or recurring.
  Replaces 13 specialized monitoring skills with one parameterized skill.
user-invocable: true
allowed-tools: Bash, Read, Grep, WebSearch, WebFetch, Agent
---

# Monitor

## Strategy

1. Select preset (determines data source and key metrics)
2. Gather health data from the source
3. Compare against baseline/thresholds
4. Rate: healthy / degraded / critical
5. Format report
6. Alert if critical
7. If `--recurring`: schedule next run

Exit: report delivered. For recurring: runs until cancelled.


> **Note:** Placeholders like `{user_question}` in Agent prompts are filled by you (Claude)
> from the current task context. They are not template variables — read the user input,
> gather the relevant context, and substitute before spawning the agent.

## Agents

### GATHER phase

```
Agent(subagent_type="Explore", model="haiku", prompt="""
Gather health data for: {target}
Preset: {preset}

Data sources to check:
{preset_data_sources}

Key metrics to collect:
{preset_metrics}

Output: raw metrics with timestamps.
""")
```

### ASSESS + REPORT phase

```
Agent(model="sonnet", prompt="""
Health data:
{gathered_metrics}

Baseline (last {baseline_days} days):
{baseline_data}

1. Compare current vs baseline
2. Flag anomalies (>2 stddev from baseline)
3. Rate overall: HEALTHY / DEGRADED / CRITICAL
4. Format as a concise health report
""")
```

## Presets

| Preset | Sources | Metrics |
|---|---|---|
| `--service NAME` | Observability platform, tracing | Latency p50/p99, error rate, throughput, instance count |
| `--pipeline NAME` | Pipeline orchestrator | Success rate, SLA compliance, last failure |
| `--ci` | CI/CD platform | Build success rate, flaky test %, avg build time |
| `--deploy APP` | Deployment platform | Deploy state, canary score, pending constraints |
| `--ml FLOW` | ML platform | Run status, latest metrics, accuracy trend |
| `--code REPO` | Git history | TODO/FIXME count, test coverage, PR merge rate |
| `--deps REPO` | pip/npm audit, CVE DBs | Outdated count, critical CVEs, last updated |
| `--docs` | Documentation platform | Pages not updated in 90d, broken links |
| `--team NAME` | GitHub, Slack, Jira | PR velocity, open issues, Slack activity |
| `--oncall` | PagerDuty, incident log | Open incidents, MTTR, handoff notes |

## Cross-provider review

When cross-provider tools are available, run verification on a non-Claude model
in parallel for maximum blind-spot diversity.

## Flags

- `--recurring=INTERVAL` — repeat on schedule (daily, hourly, etc.)
- `--alert=CHANNEL` — notification channel for critical alerts
- `--baseline=N` — days of baseline data (default: 14)

## Examples

```
/monitor --service my-api
/monitor --pipeline etl-daily --recurring=daily
/monitor --ci --alert=#builds
/monitor --team platform-eng
/monitor --code --baseline=30
/monitor --oncall
```
