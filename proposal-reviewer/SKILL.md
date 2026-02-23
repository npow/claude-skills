---
name: proposal-reviewer
description: Critically reviews project proposals, grant applications, and business plans. Use when the user asks to review, critique, evaluate, or assess a proposal, pitch, grant application, or business plan for viability, competition, or flaws. Fact-checks claims, maps competitive landscape, identifies structural problems, and provides honest recommendations.
---

# Proposal Reviewer

Critically reviews proposals by fact-checking claims against primary sources, mapping the competitive landscape, identifying structural flaws, and delivering an honest viability assessment with actionable recommendations.

## Workflow

1. **Read the proposal** — read the full document before any analysis. Identify every factual claim, cited statistic, named competitor, and stated assumption.
2. **Extract claims** — build a structured list of every verifiable claim (numbers, CVEs, funding amounts, star counts, market stats, named research). See [FACT-CHECK.md](FACT-CHECK.md).
3. **Fact-check in parallel** — launch research agents to verify claims concurrently. Classify each as VERIFIED, PARTIALLY TRUE, UNVERIFIABLE, or FALSE. See [FACT-CHECK.md](FACT-CHECK.md).
4. **Map the competitive landscape** — research incumbents, adjacent products, funded startups, open-source alternatives, and platform vendor roadmaps. See [LANDSCAPE.md](LANDSCAPE.md).
5. **Identify structural flaws** — analyze business model, technical architecture, cost model, scope/timeline, team capacity, and sustainability. See [STRUCTURAL.md](STRUCTURAL.md).
6. **Assess market timing and platform risk** — determine whether the window is open, closing, or closed, and who could absorb this. See [LANDSCAPE.md](LANDSCAPE.md).
7. **Deliver the verdict** — present findings in the structured output format: fact-check table, landscape summary, flaw-by-flaw analysis, viability assessment, and recommendations. Separate fixable flaws from inherent risks.
8. **Rewrite if asked** — only rewrite the proposal when the user explicitly requests it. See [REWRITE.md](REWRITE.md).

## Self-review checklist

Before delivering, verify ALL:

- [ ] Every verifiable claim in the proposal has a fact-check verdict (VERIFIED / PARTIALLY TRUE / UNVERIFIABLE / FALSE) with a cited source
- [ ] At least 3 web searches were performed per major claim category (attacks, defenses, competitors, market stats)
- [ ] Competitive landscape includes at least: direct competitors, adjacent products, platform vendors who could build this, and well-funded startups in the space
- [ ] Every identified flaw has a classification: FIXABLE (with specific recommendation) or INHERENT RISK (with honest assessment)
- [ ] The viability verdict is one of: VIABLE AS-IS, VIABLE WITH CHANGES (list them), NOT VIABLE (explain why), or INSUFFICIENT INFORMATION
- [ ] No claim in the review itself is unverified — every assertion is backed by a source found during research
- [ ] The review addresses business model sustainability, not just technical feasibility
- [ ] Competitors the proposal fails to mention are explicitly called out
- [ ] The tone is direct and honest — no hedging with "perhaps" or "it might be worth considering"

## Golden rules

Hard rules. Never violate these.

1. **Verify before you judge.** Never assess a claim as true or false based on general knowledge. Perform a web search or launch a research agent for every verifiable claim. If you cannot find a primary source, classify the claim as UNVERIFIABLE — never guess.
2. **Show the evidence.** Every fact-check verdict must cite a specific source (URL, paper title, or publication name). "This appears to be accurate" is not a fact-check. "Confirmed by Microsoft Security Blog, February 10, 2026" is.
3. **Separate fixable from fatal.** Every identified flaw must be classified as FIXABLE (the proposal can be rewritten to address it) or INHERENT RISK (no amount of rewriting eliminates it). Never present a list of problems without this classification.
4. **Never rewrite unprompted.** Only rewrite the proposal when the user explicitly asks. The default output is analysis and recommendations, not a new draft.
5. **Research competitors the proposal doesn't mention.** The most dangerous competitors are the ones the author missed. Always search beyond what the proposal names.
6. **Be honest about viability.** If the idea is not viable, say so directly. Do not soften a "no" into a "maybe with significant changes." If it's a maybe, specify exactly what changes would make it viable.
7. **Distinguish the proposal from the idea.** A good idea with a bad proposal is different from a bad idea. A bad proposal with a good idea gets recommendations. A bad idea gets honest feedback and a suggestion to explore alternatives.

## Reference files

| File | Contents |
|------|----------|
| [FACT-CHECK.md](FACT-CHECK.md) | How to extract claims, classify them, verify with web search, and build the fact-check table |
| [LANDSCAPE.md](LANDSCAPE.md) | How to map competitors, assess market timing, identify platform risk, and find threats the proposal missed |
| [STRUCTURAL.md](STRUCTURAL.md) | How to analyze business model, technical architecture, cost model, scope/timeline, and sustainability |
| [REWRITE.md](REWRITE.md) | How to rewrite a proposal addressing identified flaws while preserving what works |
