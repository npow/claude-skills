# Search Strategy

This file defines how to choose search queries, how many searches to run, how to cover counterevidence, and how to handle conflicting or sparse sources.

## Contents
- Scope clarification: narrowing the topic before searching
- Query selection: how to pick searches
- Required search coverage
- Counterevidence searches
- Handling conflicting sources
- Handling sparse or thin results
- Failure diagnosis

---

## Scope clarification: narrowing the topic before searching

Before running any searches, convert the user's vague topic into a specific research question.

A good research question:
- Names the specific domain or application context ("AI in radiology" not "AI in healthcare")
- Specifies the stakeholder perspective ("for enterprise buyers" not "for everyone")
- Implies what a useful answer looks like ("What is the state of regulatory approval for AI diagnostic tools in the EU?")

If the user's request is vague (e.g., "research AI"), ask one clarifying question:

> "To focus the brief: are you researching [option A], [option B], or something else? And is the goal to understand the current landscape, evaluate a specific decision, or something else?"

If the user's request is already specific, proceed directly to searching without asking.

---

## Query selection: how to pick searches

Run 3-5 searches total, each covering a different angle. Never run the same angle twice with slightly different wording — that wastes searches on the same evidence pool.

### The five angles

Cover as many of these as the topic warrants:

| Angle | Example query for "LLM agents in enterprise software" |
|---|---|
| Definition / overview | "LLM agents enterprise software 2024 overview" |
| Recent developments | "LLM agents enterprise software 2025 latest" |
| Key players and adoption | "companies deploying LLM agents enterprise use cases" |
| Data and metrics | "LLM agent enterprise adoption statistics survey" |
| Counterevidence | "LLM agents enterprise failures problems limitations" |

### Query construction rules

- Use concrete nouns, not generic terms ("transformer fine-tuning cost" not "AI training")
- Include a year when looking for current state ("2024" or "2025") to surface recent material
- Vary specificity: one broad query, two medium, one narrow
- For regulated domains: include "regulation", "compliance", or "FDA", "EU AI Act" as appropriate

---

## Required search coverage

Every research brief requires at minimum:

1. One background/overview search — establishes what the topic is and the current consensus
2. One recent-developments search — surfaces what changed in the last 12-18 months
3. One key-players search — identifies who is doing what (companies, institutions, frameworks)
4. One counterevidence search — explicitly targets failures, risks, and criticisms
5. One data/metrics search (if quantitative claims are needed) — verifies statistics

For a narrow or well-understood topic, 3 searches may suffice. For a broad or contested topic, run all 5.

---

## Counterevidence searches

Always run at least one counterevidence search. This is non-negotiable — a brief that only found supportive evidence is not complete.

### Counterevidence query templates

Replace [topic] with the specific research topic:

- `[topic] problems limitations`
- `[topic] failures case studies`
- `[topic] criticism concerns`
- `[topic] risks challenges`
- `[topic] hype reality gap`
- `[topic] vs alternatives comparison`

### What to do with counterevidence

If counterevidence contradicts a finding: note the conflict explicitly in the finding ("however, X study found the opposite") and in Gaps and Risks.

If counterevidence surfaces a failure: include it in Gaps and Risks with a summary of what failed and why.

If counterevidence searches return nothing relevant: note this in Gaps and Risks — the absence of documented criticism should be stated, not ignored.

---

## Handling conflicting sources

When two sources contradict each other, do not silently pick one.

### Protocol for conflicting sources

1. Identify which source is more authoritative (peer-reviewed > industry report > news article > blog post)
2. Identify which source is more recent (prefer newer for rapidly evolving topics)
3. State the conflict in the finding: "X claims Y ([source]), but Z found the opposite ([source]). This conflict likely reflects [methodology difference / market segment difference / definitional difference]."
4. Include the conflict in Gaps and Risks as a contested point

### Source authority hierarchy

From most to least authoritative:
1. Peer-reviewed academic papers
2. Government or regulatory publications
3. Major research firms (Gartner, Forrester, McKinsey, IDC)
4. Primary company data (official announcements, SEC filings, earnings calls)
5. Established technology journalism (MIT Technology Review, The Information, Bloomberg)
6. Industry blogs and analyst commentary
7. General news outlets

When citing a lower-authority source, prefer to corroborate it with a higher-authority source or note the authority level.

---

## Handling sparse or thin results

If searches return few or no relevant results:

1. Broaden the query — the topic may be too narrow ("GPT-4 in radiology triage" → "AI in radiology 2024")
2. Use adjacent terms — synonyms or related concepts ("LLM agents" → "AI copilots", "autonomous AI", "AI assistants")
3. Search the vendor or domain directly — if the topic involves a specific company or regulation, search that entity
4. Try a different time frame — remove the year constraint if results are thin
5. After 2 broadening attempts: state in Gaps and Risks that evidence is sparse and explain what was searched

Do not fabricate findings to fill gaps. If the evidence base is thin, say so.

---

## Failure diagnosis

| Symptom | Likely cause | Fix |
|---|---|---|
| All findings agree with each other, no tension | Counterevidence search not run or too narrow | Run "[topic] criticism failures problems" explicitly |
| Findings are vague and general | Queries were too broad | Rerun with more specific queries including year and domain |
| Source URLs are not real pages | Cited from memory instead of search results | Only cite URLs that appeared in web search tool output |
| Brief covers too many topics | Scope not narrowed before searching | Re-read the research question. Is it one question or five? |
| No data or statistics found | Did not run a metrics-specific search | Run "[topic] statistics data percentage adoption survey 2024" |
| Gaps and Risks section is empty | Only searched supportive sources | Run at least one counterevidence search and re-populate the section |
| If none of the above: | State what was searched, what was found, and what gap remains. Ask the user if a different angle would be more useful. | |
