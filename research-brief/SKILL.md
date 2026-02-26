---
name: research-brief
description: Produces a structured, evidence-based research brief on any topic. Use when the user asks to research, summarize, synthesize, or brief a topic — including "what do we know about", "give me a brief on", "research this topic", "background on", "landscape analysis", "due diligence on", or "deep dive into". Grounds all claims in real sources via web search.
allowed-tools: WebSearch
---

# Research Brief

Produces a structured, evidence-based research brief by searching broadly, seeking counterevidence, and synthesizing findings into a scannable document with cited sources.

## Workflow

1. **Clarify scope** — narrow the vague topic to a specific research question. If unclear, ask one clarifying question before proceeding. See [SEARCH.md](SEARCH.md).
2. **Search broadly** — run 3-5 web searches covering different angles: definition/background, recent developments, key players, use cases, and data/metrics. See [SEARCH.md](SEARCH.md).
3. **Search for counterevidence** — run at least one search for "[topic] problems", "[topic] failures", or "[topic] criticism". See [SEARCH.md](SEARCH.md).
4. **Read the sources** — review the content returned by each search. Note the claim, its source URL, and its implication for the research question.
5. **Synthesize** — identify patterns, conflicts, and gaps across all sources. Note what is well-evidenced, contested, or missing. See [FORMAT.md](FORMAT.md).
6. **Write the brief** — produce the brief in the exact output format, directly in the conversation as markdown. See [FORMAT.md](FORMAT.md).
7. **Self-review** — verify every claim in Key Findings has an inline citation. Verify Executive Summary is 4 sentences or fewer. Fix any violations before delivering.

## Self-review checklist

Before delivering, verify ALL:

- [ ] Executive Summary is exactly 2-4 sentences — no more
- [ ] Key Findings contains 5-10 numbered items
- [ ] Every Key Finding has an inline citation in the form [source name](url)
- [ ] Every citation URL was actually returned by a web search in this session
- [ ] At least one web search covered criticisms, failures, or risks of the topic
- [ ] Gaps and Risks section is present and contains at least 2 items
- [ ] Recommended Next Steps contains 3-5 items that are specific and actionable
- [ ] Sources section lists every URL cited in the brief
- [ ] No finding is a bare fact — each states an implication ("X is true, which means Y")

## Golden rules

Hard rules. Never violate these.

1. **No finding without a source.** Every item in Key Findings must have an inline citation linking to a URL returned by web search. Never assert a claim without a citation.
2. **Always search for counterevidence.** Run at least one search explicitly targeting problems, failures, or criticism. A brief with no risks found is incomplete, not thorough.
3. **Executive Summary is 4 sentences maximum.** If it runs longer, cut it. The summary must be scannable in under 30 seconds.
4. **Never cite a URL you have not retrieved in this session.** Only cite sources whose content was returned by a web search tool call. Do not cite from memory or training data.
5. **Findings are implications, not facts.** Each finding must state what the evidence means for the research question, not merely restate what the source says.
6. **Gaps and Risks is mandatory.** A brief without this section is not complete. If no risks surface, state that explicitly and explain why — but never omit the section.

## Reference files

| File | Contents |
|------|----------|
| [FORMAT.md](FORMAT.md) | Complete brief template, section-by-section writing guidance, citation format, and example finding structure |
| [SEARCH.md](SEARCH.md) | Search strategy: how to choose queries, how many to run, how to cover counterevidence, and how to handle conflicting sources |
