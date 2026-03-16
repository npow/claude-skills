# Output Formats

## Per-Direction Findings File

Each research agent writes to `deep-research-findings/{direction_id}.md`:

```markdown
# {direction_id}: {research question}
**Dimension:** {dimension}
**Depth:** {depth}
**Parent:** {parent_id or "seed"}
**Researched:** {date}

## Findings

[Detailed findings. Every factual claim must have an inline source link: [Paper Name](url)]

[Structure with subheadings as needed.]

### Sub-topic A
[findings...]

### Sub-topic B
[findings...]

## Key Sources
| Source | Type | Tier | Paywalled? | Snippet or full-text? | Relevance |
|--------|------|------|------------|-----------------------|-----------|
| [Name](url) | paper/blog/repo/docs | primary/secondary/unverified | yes/no | snippet/full | Brief note |

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

> ⚠️ [Only if budget limit reached]: Coverage may be incomplete. Uncovered dimensions: {list}.

## Executive Summary
[3-5 paragraphs for someone who will NOT read the full report.]
[Include the key finding, the key uncertainty, and the key gap.]

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
