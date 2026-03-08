# Capture — Gap Entry Schema & Detection

## JSON Schema

Each gap is one line of JSONL (newline-delimited JSON):

```json
{
  "ts": "2026-03-08T14:23:01Z",
  "session_task": "Review the open PRs for the auth service",
  "requested": "List open pull requests for github.com/acme/auth-service",
  "missing": "GitHub API access — no tool available to query repository PRs",
  "capability_type": "code_repository",
  "would_need": "GitHub MCP server or PAT with repo:read scope",
  "impact": "high",
  "notes": "User would use this constantly — almost every debugging session involves PRs"
}
```

## Field definitions

| Field | Required | Description |
|-------|----------|-------------|
| `ts` | yes | ISO 8601 timestamp |
| `session_task` | yes | What the user was trying to accomplish (their goal, not the specific request) |
| `requested` | yes | The specific action Claude attempted |
| `missing` | yes | The exact capability, data, or permission that was absent |
| `capability_type` | yes | Category — see types below |
| `would_need` | yes | Concrete solution: MCP server name, API name, permission scope, file path, etc. |
| `impact` | yes | `high` / `medium` / `low` — how much this blocked the user's actual goal |
| `notes` | no | Any context about frequency, workarounds, or priority signals from the conversation |

## Capability types

Use exactly one of these values for `capability_type`:

- `code_repository` — GitHub, GitLab, Bitbucket: PRs, commits, branches, issues
- `code_execution` — running code in a remote env, a container, a specific runtime
- `external_api` — any third-party API (Datadog, Sentry, Stripe, Slack, etc.)
- `file_system` — files outside the working directory, remote paths, cloud storage
- `database` — query access to a DB, data warehouse, or cache
- `observability` — metrics, logs, traces, dashboards (Grafana, Datadog, etc.)
- `web_fetch` — fetching a URL, scraping a page, calling a public endpoint
- `authentication` — credentials, secrets, tokens, OAuth flows
- `internal_tool` — company-internal system with no public API
- `realtime_data` — live data: stock prices, weather, current status, deploys
- `human_approval` — requires a human decision or sign-off
- `other` — anything that doesn't fit above (add notes)

## Detection patterns

Log a gap whenever Claude's response would contain any of these patterns:

| Pattern | Example |
|---------|---------|
| "I don't have access to..." | "I don't have access to your GitHub repo" |
| "I can't fetch / retrieve / read..." | "I can't fetch the Datadog metrics" |
| "I'm unable to..." | "I'm unable to run this against your database" |
| "I don't have a tool for..." | "I don't have a tool to query Sentry" |
| "You'd need to provide..." | "You'd need to paste the logs here" |
| "I can't browse / open..." | "I can't open that URL" |
| "I don't know the current..." | "I don't know the current deploy status" |
| "This requires access to..." | "This requires access to your Slack workspace" |

**Also log** when Claude works around a gap silently — e.g., asks the user to paste something in that Claude should be able to fetch itself. The workaround IS the gap.

## Impact scoring guide

**high** — the gap directly blocked the user's primary goal for this session. The user had to either abandon the task or manually retrieve the data themselves.

**medium** — the gap required a workaround (user pasted data in, looked something up manually) but the task eventually completed.

**low** — the gap was incidental. The user's goal was accomplished without the missing capability.

## Writing the log entry

Use the Write or Edit tool to append to the JSONL file. Do not pretty-print — one JSON object per line.

After writing, output inline:
```
[gap logged: {would_need} — {capability_type}]
```

Example:
```
[gap logged: GitHub MCP server — code_repository]
```

## Examples

### Example 1: Repository access
User asks: "Show me the last 5 commits to this repo's main branch."

```json
{"ts":"2026-03-08T10:01:00Z","session_task":"Understand recent changes to the codebase","requested":"git log for remote repo github.com/acme/api","missing":"No git remote access — Claude can only read files in the working directory","capability_type":"code_repository","would_need":"GitHub MCP server with repo read access","impact":"high","notes":"User had to run git log themselves and paste the output"}
```

### Example 2: Metrics/observability
User asks: "What's the error rate for the payment service right now?"

```json
{"ts":"2026-03-08T11:15:00Z","session_task":"Investigate payment service degradation","requested":"Current error rate metrics for payment-service from Datadog","missing":"No Datadog MCP or API access","capability_type":"observability","would_need":"Datadog MCP server or API key with metrics:read scope","impact":"high","notes":"Core to incident investigation — would be called on every production issue"}
```

### Example 3: Workaround gap
User asks: "Can you check what version is deployed in prod?" Claude says: "Could you run `kubectl get deployment` and paste the output?"

```json
{"ts":"2026-03-08T12:30:00Z","session_task":"Verify deployment version before rollback","requested":"Current deployed version of auth-service in production","missing":"No Kubernetes / deployment system access","capability_type":"internal_tool","would_need":"kubectl MCP or internal deploy API","impact":"medium","notes":"User ran kubectl and pasted — workaround exists but adds friction"}
```
