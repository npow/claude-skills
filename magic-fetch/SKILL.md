---
name: magic-fetch
description: Logs capability gaps as they arise during a session — what Claude couldn't do and exactly what tool, access, or data would have made it possible. Use when the user wants to capture integration needs, track where Claude hits walls, build a roadmap from blocked requests, log capability gaps, or says "remember what you couldn't do". Auto-activates when Claude is about to say it cannot access, fetch, or perform something.
argument-hint: "[optional: path to log file, default: ./magic-fetch.jsonl]"
---

# Magic Fetch

Captures capability gaps in real-time. When Claude hits a wall, it logs exactly what was needed — not just "I can't" but "here's what tool/API/access would have solved this." Over time this builds a prioritized integration roadmap written by the agent itself.

## Modes

This skill has two modes. Use whichever matches the user's intent.

**Capture mode** (default): activate at the start of a session to log gaps as they arise. See [CAPTURE.md](CAPTURE.md).

**Review mode**: summarize an existing log into a prioritized roadmap. See [REVIEW.md](REVIEW.md).

## Workflow — Capture mode

1. **Activate** — confirm the log file path (default: `./magic-fetch.jsonl`). Create it if it doesn't exist. Announce: "Magic fetch active. I'll log every capability gap to `{path}`."
2. **Proceed normally** — carry out all tasks as usual. Do not change behavior except for the logging step below.
3. **On every capability gap** — whenever Claude cannot perform a requested action due to missing tool, access, data, or permission, BEFORE or AFTER explaining the limitation to the user, append one JSON entry to the log. See [CAPTURE.md](CAPTURE.md) for the schema and examples.
4. **Never skip a gap** — if you said "I can't", "I don't have access", "I'm unable to", or "I don't know how to reach", a log entry is required. No exceptions.
5. **Confirm each log write** — after writing, output a single line: `[gap logged: {need_summary}]` so the user sees it in real-time.

## Workflow — Review mode

1. **Read the log** — load the JSONL file the user points to.
2. **Cluster by type** — group gaps by `capability_type`. See [REVIEW.md](REVIEW.md).
3. **Score by frequency + impact** — rank integration candidates. See [REVIEW.md](REVIEW.md).
4. **Output the roadmap** — produce a table of: rank, integration, frequency, example use cases, estimated complexity. See [REVIEW.md](REVIEW.md).

## Self-review checklist

- [ ] Log file path was confirmed with the user or defaulted to `./magic-fetch.jsonl`
- [ ] Every gap entry contains: timestamp, task, what was requested, what was missing, what would help
- [ ] No gap was silently dropped — every "I can't" has a corresponding log entry
- [ ] `[gap logged: ...]` confirmation was shown for each entry
- [ ] Review mode produces a ranked table, not a raw dump

## Golden rules

1. **Log before you explain.** Write the gap entry to the file before or alongside telling the user you can't do something. Never explain first and forget to log.
2. **Be specific about what's missing.** "No internet access" is useless. "GitHub API access to list commits for repo X" is useful. Every entry must name the specific data, endpoint, or permission needed.
3. **Include the user's intent.** The log must capture what the user was trying to accomplish, not just what Claude couldn't do. This is what makes the roadmap actionable.
4. **One entry per gap, not per turn.** If a single turn has 3 capability walls, log 3 entries.
5. **Never suppress gaps out of politeness.** If it would embarrass Claude to log it, that's exactly when to log it.
6. **Review produces a roadmap, not a list.** Gaps must be clustered, ranked, and presented as integration candidates with concrete next steps — not a raw log dump.

## Reference files

| File | Contents |
|------|----------|
| [CAPTURE.md](CAPTURE.md) | JSON schema for gap entries, detection patterns, examples |
| [REVIEW.md](REVIEW.md) | Clustering strategy, scoring rubric, roadmap output format |
