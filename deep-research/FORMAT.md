# Output Formats

## Per-Direction Findings File

Each research agent writes to `deep-research-findings/{direction_id}.md`:

```markdown
# {direction_id}: {research question}
**Dimension:** {dimension}
**Depth:** {depth}
**Parent:** {parent_id or "seed"}
**Researched:** {date}
**Topic velocity:** {fast_moving | stable}   [inherited from run-init config flag]

## Findings

[Detailed findings. Every factual claim must have an inline source link: [Paper Name](url)]

[Structure with subheadings as needed.]

### Sub-topic A
[findings...]

### Sub-topic B
[findings...]

## Claims Register

[REQUIRED. One row per load-bearing factual claim in the Findings section.
A "claim" is any statement of fact that would change the report's conclusions if wrong.
Opinions, framings, and summary sentences are NOT claims.]

| Claim ID | Claim (one sentence) | Sources (ids) | corroboration | counter_evidence_searched | recency_class |
|----------|----------------------|---------------|---------------|---------------------------|---------------|
| c1 | ... | s1 | single_source | yes_none_found | fresh |
| c2 | ... | s1, s4 | two_independent_sources | yes_disconfirming_evidence_present | stale |

**Field definitions:**

- `corroboration` — one of:
  - `single_source` — one source supports the claim
  - `two_independent_sources` — two sources, independent per the rule below
  - `three_or_more_independent_sources` — three or more, all pairwise independent

  **Independence rule:** Two sources are independent iff (a) neither cites the other, AND (b) they are not from the same publishing entity (same org, same author, same parent corporation, same pre-print server thread). `unverified`-tier sources do NOT count toward corroboration even if present in the source table.

- `counter_evidence_searched` — one of:
  - `yes_none_found` — a counter-evidence search was run; no disconfirming sources found
  - `yes_disconfirming_evidence_present` — disconfirming source(s) found and MUST be cited inline with the claim in Findings
  - `no_search_skipped` — no counter-evidence search performed (this will be flagged by the coordinator; use only when the claim is definitional/tautological)

- `recency_class` — computed from source date + topic velocity:
  - If `Topic velocity: fast_moving` at run init: sources older than 12 months from run date → `stale`, else `fresh`
  - If `Topic velocity: stable`: sources older than 36 months → `stale`, else `fresh`
  - If source has no date: `undated` (treated as `stale` for gate purposes)
  - A claim's `recency_class` is the FRESHEST among its sources (one fresh source is enough to mark the claim fresh)

## Key Sources
| Source ID | Source | Type | Tier | Publishing entity | Publication date | Paywalled? | Snippet or full-text? | Relevance |
|-----------|--------|------|------|-------------------|------------------|------------|-----------------------|-----------|
| s1 | [Name](url) | paper/blog/repo/docs | primary/secondary/unverified | e.g. arXiv / NYT / Google Research | YYYY-MM-DD or "undated" | yes/no | snippet/full | Brief note |

**Tier definitions:**
- `primary`: peer-reviewed research, official documentation, primary data — note specific evidence
- `secondary`: credible journalism, institutional reports (expert blogs: explicit credentials required)
- `unverified`: forums, personal blogs, social media, paywalled sources (can't read it = can't verify it)

## Mini-Synthesis

[REQUIRED. ≥3 sentences covering:]
[1. What this direction contributes to understanding the seed topic]
[2. How it connects to or diverges from other explored directions]
[3. What it contradicts or complicates]

[This section is what the coordinator reads for synthesis — make it count.]

## New Directions Discovered

1. **{question}** — Dimension: {existing_dim | NEW: new_dim_name} — Priority: {high/medium/low}
   Why: {1 sentence on why this is worth exploring}

[List 2-5 genuinely novel directions. NOT paraphrases of already-explored topics.]
[If this is a terminal node: "None — this direction is a terminal node."]

## Unconsumed Leads

[REQUIRED section. Scan your own Findings for every named entity (team, tool, repo, person, framework, project, initiative) that you referenced but did NOT independently research. Each such entity is a lead the coordinator will consider as a new direction.]

- **{entity}**: {why it's worth researching — 1 line}

[Include everything you mentioned in passing but didn't verify or deep-dive. Examples: "a team named X came up in a doc", "tool Y was referenced but not inspected", "person Z has been active in this space".]
[If there are genuinely no unconsumed leads — every referenced entity was core to your scope and fully researched — write: "None — all referenced entities were core to this direction's scope and independently verified."]

**Why this section exists:** agents routinely mention entities in passing while answering their assigned direction. Without a structured recovery mechanism, those entities silently disappear — even when they're critical to understanding the seed topic. This section forces every agent to surface them so the coordinator can promote, dedup, or consciously drop each one.

## Exhaustion Assessment

**Score: {1-5}**
- 1 = barely scratched the surface
- 2 = found some key results but major gaps remain
- 3 = covered the main points, some depth
- 4 = thorough coverage, only minor gaps
- 5 = comprehensive, nothing significant left to find

**What's missing (if score < 4):**
[Specific gaps that a follow-up exploration should target]
```

---

## Final Report: `deep-research-report.md`

```markdown
# Deep Research Report: {seed topic}
**Generated:** {date}
**Rounds completed:** {N}
**Termination:** {User-stopped at round N | Coverage plateau | ⚠️ Budget limit reached | Convergence}
**Directions explored:** {count} ({timed_out} timed out)
**Dimensions covered:** {count}/{total applicable}
**Coverage:** {N}%
**Evidence Quality:** {opinion-heavy | mixed | primarily-sourced}
**Topic velocity:** {fast_moving | stable}   [run-init config; drives `recency_class` threshold]

**Claim-level integrity counts:**
- Single-source claims: {N}   [surfaced in Single-Source Claims section]
- Claims with counter-evidence search skipped: {N}   [surfaced in Skipped Counter-Evidence Searches]
- Claims backed by at least one stale source: {N}   [surfaced in Stale-Source Claims]
- Claims with disconfirming evidence cited inline: {N}

> ⚠️ [Only if budget limit reached]: Coverage may be incomplete. Uncovered dimensions: {list}.

## Executive Summary
[3-5 paragraphs for someone who will NOT read the full report.]
[Include the key finding, the key uncertainty, and the key gap.]
[If the Time-Sensitive Coordination Windows section below is non-empty, the single earliest deadline MUST appear in paragraph 1 of this summary — the reader should not have to scroll to know if action is required this week.]

---

## Time-Sensitive Coordination Windows

[REQUIRED section. Scan all findings for dated events, deadlines, planning-window closings, meeting dates, draft-memo submission windows, PR merge targets, OKR input windows, or any time-bounded coordination opportunity surfaced by the STRATEGIC-TIMING cross-cutting dimension. Every such item goes here, sorted by earliest deadline first, with the window size computed from the run date.]

| Event / Deadline | Date | Window from run date | Source (direction ID) | Why it matters |
|------------------|------|---------------------:|-----------------------|----------------|
| {event description} | YYYY-MM-DD | {N} days | dir_XXX | {1 line — what's won/lost if this window closes unanswered} |

**Window classifications:**
- `≤ 7 days`: **CRITICAL** — flag in Executive Summary paragraph 1
- `8–30 days`: **ACTIVE** — surface prominently in Executive Summary
- `31–90 days`: **PLANNING** — note in Executive Summary closing
- `> 90 days`: **STRATEGIC** — inline mention only

If this section is empty: write "None — no time-sensitive coordination windows surfaced in findings." (The STRATEGIC-TIMING dimension SHOULD have surfaced at least one item; an empty section may indicate the dimension under-performed — flag for follow-up.)

**Coordinator validation rule:** after the final report is written, the coordinator MUST check that every `CRITICAL`/`ACTIVE` entry in this table appears verbatim or is directly referenced in the Executive Summary. If not, revise the Executive Summary before finalizing.

---

## Research Landscape

### Theme 1: {name}
**Contributing dimensions:** {list — must be 2+ for a valid cross-cutting theme}
**Maturity:** {theoretical | research | pre-production | production-ready}

[2-5 paragraphs synthesizing this theme.]

#### Key Sources
- [Paper](url) — {tier} — {1 line summary}

#### Open Questions
- {questions unresolved within this theme}

### Theme 2: {name}
[same structure]

...

### Dimension Summaries (single-dimension findings)

#### {Dimension Name}
[Findings from this dimension that didn't fit a cross-cutting theme]

---

## Cross-Cutting Analysis

### Fundamental Tradeoffs
[Core tensions: e.g., cost vs. accuracy, interpretability vs. performance]

### Contradictions
[Where sources/approaches disagree — present both sides with source quality noted]
[Flag asymmetric quality: "View A backed by 3 primary sources; View B backed by 1 opinion source"]

### Consensus
[What the field broadly agrees on]

### Meta-Patterns
[Patterns emerging across multiple themes]

---

## Spot-Check Sample Results
Checked: {X} of {Y} claims ({X/Y}%)
Sampling strategy: risk-stratified (single-source primary + numerical + contested)

Results:
- Citations accessible and matching: {N}
- Citations inaccessible (paywalled/404): {N}
- Citation mismatches flagged: {list with brief note}

⚠️ IMPORTANT LIMITATIONS:
- Numerical/statistical claims: LLM comprehension is UNRELIABLE for exact number verification.
  Claims with specific figures should be manually verified against cited source.
- This is a spot-check, not a comprehensive audit. {Y - X} claims were not checked.
- For high-stakes decisions, independently verify all primary claims.

---

## Single-Source Claims  `[SINGLE_SOURCE_CAVEAT]`

[REQUIRED section. Every claim with `corroboration: single_source` is listed here, tagged
`[SINGLE_SOURCE_CAVEAT]` in the report body where it appears, and repeated here verbatim.
Never promote a single-source claim to "established fact" in the Executive Summary or Consensus.]

| Claim | Sole source | Tier | Why corroboration was not obtained |
|-------|-------------|------|-------------------------------------|
| {claim text} | [Name](url) | primary/secondary | e.g. "only paper on this subclaim", "paywalls on alternatives" |

If this section is empty: write "None — every claim has two or more independent sources."

---

## Skipped Counter-Evidence Searches

[REQUIRED section. Every claim with `counter_evidence_searched: no_search_skipped` is listed.]

| Claim | Reason search was skipped | Direction ID |
|-------|---------------------------|--------------|
| {claim text} | e.g. "definitional", "tautological", "time budget exhausted" | dir_XXX |

If non-empty: "⚠️ These claims were not stress-tested for disconfirming evidence. Treat as weaker than claims that survived a counter-evidence search."

If empty: write "None — every claim was subjected to a counter-evidence search."

---

## Stale-Source Claims

[REQUIRED section. Every claim whose `recency_class` is `stale` or `undated` is listed.
Threshold is 12 months for fast-moving topics, 36 months for stable topics — set at run init.]

| Claim | Source(s) | Source date | Why still included |
|-------|-----------|-------------|---------------------|
| {claim text} | [Name](url) | YYYY-MM-DD or "undated" | e.g. "canonical reference", "no newer source available" |

If non-empty: "⚠️ Fast-moving topic; {N} claims rely on sources older than the freshness threshold. Re-verify before acting on these."

If empty: write "None — all claims have at least one fresh source."

---

## Coverage Assessment

| Dimension | Directions Explored | Coverage | Notes |
|-----------|-------------------|----------|-------|
| {dim} | {count} | full/partial/minimal | {timed out / shallow} |

### Known Gaps
[What aspects were NOT adequately covered? exhaustion score < 3?]
[What would a follow-up research run focus on?]

---

## All Sources

### Papers / Primary Research
- [Name](url) — tier: primary — cited by: {direction IDs}

### Articles / Secondary
- [Name](url) — tier: secondary — cited by: {direction IDs}

### Unverified / Paywalled
- [Name](url) — tier: unverified — cited by: {direction IDs}

---

## Methodology
- Seed: {seed}
- Rounds: {N} of {max_rounds}
- Directions explored: {count} ({timed_out} timed out, {saturated} saturated)
- Model tiers used: Sonnet (depth 0-1 high), Haiku (depth 1 medium, depth 2+), Opus (re-dives only)
- Termination: {reason}
```
