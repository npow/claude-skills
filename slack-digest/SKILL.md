---
name: slack-digest
description: "Use when generating a weekly Slack digest, summarizing channel activity, finding key discussions, or checking what happened in Slack. Trigger phrases: slack digest, slack summary, channel digest, what happened in slack."
---

# Slack Digest

Produce a weekly digest of key Slack threads from configured channels using rag-slack-prod MCP tools. The digest surfaces high-engagement threads, groups by topic, and highlights unanswered questions.

## Configuration

Reads defaults from `~/.claude/skills/slack-digest/config.json` if it exists.

```json
{
  "channel_ids": ["C01ABC123", "C02DEF456"],
  "lookback_days": 7
}
```

**Resolution order:** user prompt overrides > config.json > built-in defaults.

**At least one channel must be set.** If none is set and the user didn't specify, ask once and save to config.json.

## Arguments

- **channel_ids**: list of Slack channel IDs to scan
- **lookback_days**: how far back to search (default: 7)

## Workflow

1. **Compute time window.** Calculate the epoch timestamp for `now - lookback_days` using `date -d "{lookback_days} days ago" +%s`. This becomes the `thread_ts` filter lower bound.

2. **Search each channel for threads.** For each channel_id, call `rag-slack-prod` with a metadata filter combining `channel_id == {id}` AND `thread_ts >= {epoch}`. Use a broad query like "discussion update question issue decision" to cast a wide net. Request `size=20` results per channel.

3. **Fetch full thread context.** For each thread returned, use `fetch-slack-thread` with the permalink to get the full thread (all replies, not just the matched snippet). Count replies per thread — this is the engagement signal.

4. **Classify threads.** For each thread, determine:
   - **Topic category**: incident, decision, question, announcement, discussion, or request
   - **Engagement level**: high (10+ replies), medium (4-9 replies), low (1-3 replies)
   - **Resolution status**: resolved (answer given, decision made), unresolved (question still open, no conclusion), or informational (no resolution needed)
   - Classification is based on thread content: questions end with `?` or start with "does anyone", "how do we"; decisions contain "let's go with", "we decided", "agreed"; incidents contain "incident", "outage", "SEV", "pages".

5. **Identify unanswered questions.** A thread is "unanswered" if: it was classified as a question AND has fewer than 3 replies AND no reply contains a clear answer (code block, link, or statement without a trailing `?`).

6. **Group threads by topic category.** Within each category, sort by engagement (highest first).

7. **Generate report.** Output markdown:

```
## Slack Digest — {date}
Channels: {channel names or IDs} | Period: last {lookback_days} days | Threads analyzed: {N}

### Summary
- Total threads: {N} | High engagement: {N} | Unanswered questions: {N}

### Unanswered Questions (action needed)
(For each: channel, thread summary, who asked, when, permalink)

### Key Decisions
(For each: thread summary, decision outcome, participants, permalink)

### Incidents & Outages
(For each: thread summary, status, permalink)

### Active Discussions
(For each: thread summary, reply count, key participants, permalink)

### Announcements & FYI
(Compact list: summary, permalink)
```

8. **Post to `#team-digests` channel if configured, never to a primary team channel.**

9. **Terminate.** Report is complete when all channels are searched and threads are grouped with permalinks.

## Design Principles

1. **Team-level only.** Aggregate to team level — it is the right granularity for a periodic digest. Individual-level detail (messages per person, reply count per author) is too noisy for a team report.
2. **Deterministic math first, LLM narrates only.** Thread counts, reply counts, and engagement levels must be computed from actual thread data. The LLM writes summaries around the numbers but never invents engagement metrics.
3. **Pair metrics with counter-metrics.** Never report activity volume without resolution rate. If showing total threads, also show how many were resolved vs left open.

## Golden Rules

1. **Fetch full threads, not just snippets.** The RAG result is a snippet. Use `fetch-slack-thread` to get the complete conversation before classifying.
2. **Unanswered questions go first.** They represent work stuck waiting for input. Surface them before everything else.
3. **Include permalinks for every thread.** The reader must be able to click through to the original conversation.
4. **Count replies from the actual thread, not from RAG metadata.** RAG returns relevance-matched snippets, not engagement data. The full thread fetch gives the real reply count.
5. **Check ALL configured channels, not a subset.**

## Anti-Rationalization Counter-Table

| Excuse | Reality |
|---|---|
| "I searched the channel and summarized the top results." | RAG results are relevance-ranked, not engagement-ranked. You must fetch full threads to count replies and assess engagement. |
| "There were too many threads so I sampled a few." | Increase the size parameter. The digest must cover the full set of significant threads. |
| "I classified the thread from the snippet alone." | Snippets miss context. Fetch the full thread before classifying resolution status. |
| "No unanswered questions found, so I skipped that section." | Still include the section with "None" — it's positive signal that questions are getting answered. |
| "I can't get the channel name from the ID." | Use the channel_id in the report. The reader knows their own channels. Don't block on cosmetic lookups. |

## Termination Labels

| Label | Meaning |
|---|---|
| `report_complete` | All channels searched, threads fetched and classified, grouped with permalinks |
| `report_partial` | Some channels searched but thread fetch failed for some — noted which |
| `no_threads_found` | No threads in the time window — channels may be low-traffic or IDs wrong |
| `api_error` | Slack RAG API unreachable or returning errors |

## Self-Review Checklist

- [ ] Every configured channel was searched
- [ ] Full threads were fetched (not just RAG snippets) for classification
- [ ] Reply counts come from actual thread data
- [ ] Unanswered questions section appears first after summary
- [ ] Every thread entry includes a permalink
- [ ] Threads are grouped by topic category, sorted by engagement within each group
