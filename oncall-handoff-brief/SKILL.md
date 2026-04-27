---
name: oncall-handoff-brief
description: "Use when preparing an on-call handoff, rotation brief, generating a handoff report, or summarizing what happened during an on-call shift. Trigger phrases: oncall handoff, on-call brief, handoff report, rotation handoff."

category: report
capabilities: [static-analysis]
input_types: [git-diff, repo]
output_types: [report, code]
complexity: moderate
cost_profile: low
maturity: beta
metadata_source: inferred
---

# On-Call Handoff Brief

Produce a comprehensive on-call rotation handoff brief that compounds signals from Atlas metrics, Spinnaker deploys, Maestro pipelines, and Slack incident threads. The brief gives the incoming on-call everything they need to know.

## Configuration

Reads defaults from `~/.claude/skills/oncall-handoff-brief/config.json` if it exists.

```json
{
  "atlas_app_names": ["myapp1", "myapp2"],
  "spinnaker_apps": ["myapp1", "myapp2"],
  "maestro_workflow_owners": ["data.platform.myteam"],
  "slack_channel_ids": ["C01ABC123", "C02DEF456"],
  "lookback_days": 7
}
```

**Resolution order:** user prompt overrides > config.json > built-in defaults.

**At least one signal source must be set.** If none is set and the user didn't specify, ask once and save to config.json.

## Arguments

- **atlas_app_names**: list of Atlas application names for metrics/alerts
- **spinnaker_apps**: list of Spinnaker application names for deploy status
- **maestro_workflow_owners**: list of Maestro workflow owners for pipeline health
- **slack_channel_ids**: list of Slack channel IDs for incident threads
- **lookback_days**: how far back to check (default: 7)

## Workflow

1. **Gather Atlas metrics.** For each `atlas_app_name`, use `observability_translate_to_asl` to build queries for key health signals:
   - Error rate: translate "error rate for {app}" to ASL, then graph with `observability_generate_atlas_graph` over the lookback period.
   - Latency: translate "p99 latency for {app}" to ASL, then graph.
   - Request volume: translate "request rate for {app}" to ASL, then graph.
   - Flag any metric that shows a sustained increase (>20% above the period average in the trailing 24h) as "trending up."

2. **Check Spinnaker deploys.** For each `spinnaker_app`, invoke `delivery:delivery-managed-delivery` to get current deployed versions and constraint state. Note:
   - Any blocked deploys (pending canary, failed verification)
   - Recent successful deploys (what version, when)
   - Failed canaries — get details via `delivery:delivery-managed-delivery-canary`

3. **Check Maestro pipelines.** For each `maestro_workflow_owner`, call `search_workflows` with `owner` and cluster="prod". Then for each workflow, call `get_latest_instance` with cluster="prod". For any FAILED instance, call `get_instance_failures` with cluster="prod" to get step-level detail.

4. **Search Slack for incidents.** For each `slack_channel_id`, use a Slack semantic search tool with query "incident outage SEV alert pages degradation" and metadata filter for `channel_id` and `thread_ts >= {lookback_epoch}`. Fetch full threads via `fetch-slack-thread` for any that match.

5. **Compile open items.** Identify anything that needs attention from the incoming on-call:
   - Unresolved incidents from Slack
   - Blocked deploys from Spinnaker
   - Failed pipelines from Maestro
   - Trending-up error rates from Atlas

6. **Generate report.** Output markdown:

```
## On-Call Handoff Brief — {date}
Rotation: {lookback_days}-day summary | Apps: {app list}

### Open Items (incoming on-call action needed)
(Prioritized list: what needs attention, why, link)

### Incidents During This Rotation
(For each: summary, status, Slack permalink, severity)

### Alerts & Metrics
(For each app: error rate trend, latency trend, notable spikes, Atlas graph links)

### Deployments
(For each app: current version, recent deploys, blocked deploys, canary status)

### Pipeline Health
(For each owner: total workflows, failed count, failed workflow details with step + link)

### Context for Next On-Call
(Free-form notes: known issues being worked on, upcoming risky changes, things to watch)
```

7. **Deliver as HTML.** Follow the shared HTML delivery pattern in [`_shared/html-delivery.md`](../_shared/html-delivery.md). Report name: `oncall-handoff`. TLDR includes open items count, incident count, and trending-up alerts.

8. **Terminate.** Report is complete when all four signal sources are checked and open items are compiled.

## Design Principles

1. **Team-level only.** Aggregate to team level — it is the right granularity for a periodic digest. Individual-level detail (who caused what incident, who deployed what) is too noisy for a handoff brief.
2. **Deterministic math first, LLM narrates only.** Metric trends (up/down/flat), failure counts, and deploy states must be computed from actual data. The LLM writes prose around the numbers but never invents severity or trend direction.
3. **Pair metrics with counter-metrics.** Never report error rate without request volume. A 50% error rate on 2 requests is different from 50% on 2 million. Always pair.

## Golden Rules

1. **Open Items section goes first.** The incoming on-call needs to know what requires immediate attention before reading history.
2. **Every signal source gets checked.** If Atlas is configured, check Atlas. If Spinnaker is configured, check Spinnaker. Don't skip a source because another looks fine.
3. **Always cluster=prod for Maestro.** Every Kragle MCP call passes cluster="prod". Sandbox workflows are not production health.
4. **Fetch full Slack threads for incidents.** RAG snippets are not enough to determine incident status. Use `fetch-slack-thread`.
5. **Include links everywhere.** Atlas graph URLs, Spinnaker Chap URLs, Maestro instance links, Slack permalinks. The reader must click through without additional lookups.
6. **"All clear" is still a report.** When everything is healthy, produce the full structure. A quiet rotation is valuable signal.

## Anti-Rationalization Counter-Table

| Excuse | Reality |
|---|---|
| "Atlas metrics look normal so I skipped the graphs." | Generate the graphs anyway. The incoming on-call needs a baseline reference, not your verbal assurance. |
| "No incidents in Slack, so I skipped that section." | Include the section with "No incidents" — that's positive signal the outgoing on-call should hand off. |
| "I checked pipelines but skipped get_instance_failures because the status is clear." | FAILED status tells you nothing actionable. The step_id and error detail is what the on-call needs. |
| "I only checked the main app, others are probably fine." | Check ALL configured apps and owners. A missed failure in a secondary app is still a failure. |
| "I'll write the context section from memory." | Context must be grounded in the data gathered above. Don't invent known issues — surface what the data shows. |

## Termination Labels

| Label | Meaning |
|---|---|
| `report_complete` | All signal sources checked, open items compiled, all sections populated |
| `report_partial` | Some sources checked but API errors prevented full coverage — noted which |
| `no_config` | No signal sources configured — need config.json or user input |
| `api_error` | One or more APIs unreachable — report what was gathered before failure |

## Self-Review Checklist

- [ ] All configured Atlas apps have metrics checked with graphs
- [ ] All configured Spinnaker apps have deploy status checked
- [ ] All Maestro workflows checked with cluster="prod", failures have step detail
- [ ] All Slack channels searched for incident threads with full thread fetch
- [ ] Open Items section appears first and is prioritized
- [ ] Every item has a clickable link (Atlas URL, Chap URL, instance link, permalink)
- [ ] Report has date header and app list noted
- [ ] HTML version uploaded to S3 with commuter link (unless `--no-html` or upload failed with noted fallback)
- [ ] Slack/chat delivery uses TLDR + link, not the full report
