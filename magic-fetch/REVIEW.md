# Review — Turning the Gap Log into a Roadmap

## When to run review mode

The user invokes `/magic-fetch review [path]` or says "show me what you couldn't do" or "what integrations do I need?"

## Step 1 — Load and parse the log

Read the JSONL file line by line. Each line is one gap entry. Parse into a list of objects.

If the file is empty or missing: tell the user no gaps have been captured yet and offer to activate capture mode.

## Step 2 — Cluster by capability_type

Group all entries by their `capability_type`. Count frequency per type. Within each cluster, collect all unique `would_need` values.

## Step 3 — Score each cluster

For each `capability_type` cluster, compute a priority score:

```
score = (high_count * 3) + (medium_count * 1) + (low_count * 0)
```

Where `high_count`, `medium_count`, `low_count` are the number of entries at each impact level within the cluster.

Sort clusters descending by score.

## Step 4 — Identify integration candidates

Within each cluster, identify the most specific `would_need` value. Group near-duplicate `would_need` entries (e.g., "GitHub MCP" and "GitHub API with read scope" → same integration).

## Step 5 — Output the roadmap

Produce a ranked table followed by per-integration details.

### Roadmap table

| Rank | Integration | Type | Gaps Logged | Impact | Example Use Case |
|------|-------------|------|-------------|--------|-----------------|
| 1 | GitHub MCP server | code_repository | 12 | 8 high, 4 med | List open PRs, view commits |
| 2 | Datadog MCP server | observability | 8 | 7 high, 1 low | Error rates, service latency |
| ... | | | | | |

### Per-integration detail (top 5 only, or all if ≤10 total)

For each top-ranked integration:

```
### 1. GitHub MCP server
Type: code_repository
Total gaps: 12 (8 high impact)
Sessions affected: 6

What the agent kept needing:
- List open PRs for a repo
- View commit history for a branch
- Check CI status on a PR
- Read file contents at a specific commit

Concrete install path: https://github.com/github/mcp-server
Estimated integration complexity: low (MCP server, add to .mcp.json)
```

## Output rules

- Always produce the ranked table first — it's the TL;DR
- Include the raw gap count and session count (distinct `session_task` values per cluster)
- Name a concrete install path or API for each integration (don't just say "add Datadog" — say how)
- If two integrations would both solve the same gaps, note that and let the user decide
- End with: "Based on X gaps across Y sessions, the highest-leverage first integration is: **Z**."

## Complexity estimation guide

**low** — MCP server exists, add to `.mcp.json`, no custom code needed
**medium** — API exists, needs an MCP wrapper or small integration script
**high** — internal tool, proprietary API, or requires auth flow / credential management
