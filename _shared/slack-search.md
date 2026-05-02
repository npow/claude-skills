# Standard Slack Search Workflow

Report skills that pull data from Slack all follow the same three-step search pattern. Each skill defines its own query terms and channel scope, but the mechanics are identical.

## Step 1: Compute Time Window

Calculate the epoch timestamp for the lookback boundary:

```bash
date -d "{lookback_days} days ago" +%s
```

This epoch becomes the `thread_ts` lower-bound filter in the next step.

## Step 2: Search via `rag-slack-prod`

For each channel ID in scope, call the Slack semantic search tool (`rag-slack-prod`) with:

- **query**: the skill-specific search terms (e.g., `"incident outage SEV alert"` for oncall-handoff, `"discussion update question issue decision"` for slack-digest)
- **metadata filter**: combine `channel_id == {id}` AND `thread_ts >= {epoch}`
- **size**: request enough results to cover the channel's activity (typically `size=20` per channel)

RAG results are relevance-ranked snippets, not full conversations. They establish which threads exist but do not provide complete context.

## Step 3: Fetch Full Threads via `fetch-slack-thread`

For every thread returned by the search, call `fetch-slack-thread` with the thread's permalink to retrieve the complete conversation (all replies, not just the matched snippet).

Why this is mandatory:
- **Reply counts** come from the full thread, not from RAG metadata.
- **Resolution status** (answered vs. unanswered, resolved vs. open) requires reading the entire thread.
- **Engagement level** is computed from actual reply count, not relevance score.

## Key Rules

1. **Always fetch full threads.** Never classify, count, or summarize based on RAG snippets alone.
2. **One query per channel.** Don't batch multiple channel IDs into a single search call.
3. **Respect the time window.** The `thread_ts` filter ensures only threads from the lookback period are included.
4. **Public channels only.** Never search DMs or private channels.
5. **Permalinks are mandatory.** Every thread referenced in the report includes its Slack permalink so the reader can click through.
