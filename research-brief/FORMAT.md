# Brief Format

This file defines the exact output format for a research brief, section-by-section writing guidance, the citation format, and an example finding structure.

## Contents
- Complete brief template
- Section-by-section writing guidance
- Citation format
- Example finding structure
- Common format failures

---

## Complete brief template

Produce this structure verbatim, substituting bracketed placeholders:

```markdown
# Research Brief: [Topic]
**Date:** [YYYY-MM-DD]  **Prepared by:** Claude

## Executive Summary
[2-4 sentences. The single most important finding, the key tension or risk, and one forward-looking implication.]

## Key Findings
1. **[Finding headline]** [1-2 sentence claim with inline citation]. This means [implication for the research question].
2. **[Finding headline]** ...
[5-10 findings total]

## Landscape / Context
[2-4 paragraphs. Who are the key players, frameworks, standards, or initiatives? What is the current state? What are the dominant approaches?]

## Gaps and Risks
- **[Gap or risk name]:** [What is unknown, contested, or risky. What assumption underlies the current evidence.]
- **[Gap or risk name]:** ...
[At least 2 items]

## Recommended Next Steps
1. **[Action]:** [1-2 sentence rationale for why this action, what it enables.]
2. **[Action]:** ...
[3-5 steps total]

## Sources
1. [Source name](url) — one-line description of what this source covers
2. ...
```

---

## Section-by-section writing guidance

### Title and header

Use the format `# Research Brief: [Topic]` exactly. The topic should be the specific research question, not the vague original input. For example:

- Input: "AI in healthcare" → Title: "Research Brief: AI Diagnostic Tools in Radiology — Adoption, Evidence, and Regulatory Status"
- Input: "quantum computing" → Title: "Research Brief: Quantum Computing Readiness for Enterprise Cryptography — 2025 Landscape"

### Executive Summary

Rules:
- Exactly 2-4 sentences. Count them. If there are 5, delete one.
- Sentence 1: The most important finding.
- Sentence 2: The key tension, risk, or caveat.
- Sentence 3 (optional): The forward-looking implication.
- Sentence 4 (optional): The most important recommended action.
- No inline citations. This section synthesizes; it does not cite.
- No bullet points. Prose only.

### Key Findings

Rules:
- 5-10 findings. Never fewer than 5, never more than 10.
- Each finding has three components: headline, claim+citation, implication.
- Use a bold headline phrase at the start of each finding.
- The citation must be an inline markdown link: `[source name](url)`.
- The implication must explain what the finding means for the research question, not just restate the source.
- Order findings by importance, not by the order you found them.

### Landscape / Context

Rules:
- 2-4 paragraphs. No bullet points in this section — prose only.
- Cover: key players (companies, researchers, standards bodies), dominant approaches or frameworks, the current state of practice or adoption, and historical context if relevant.
- This section contextualizes the findings — it does not repeat them.

### Gaps and Risks

Rules:
- Bullet list, not numbered.
- Each item: **Bold name:** explanation.
- Cover at least: one gap in available evidence, one contested or debated point, one assumption that could invalidate findings, and one external risk factor.
- If no risks were found in the literature, state: "**No documented failures found:** The search did not surface published criticisms or failures. This absence may reflect recency of the technology, publication bias, or genuinely low failure rates. Independent validation is recommended before relying on this conclusion."

### Recommended Next Steps

Rules:
- 3-5 numbered items.
- Each step: **Bold action verb phrase:** rationale.
- Steps must be specific: "Conduct a pilot study with 3 vendors using criteria X, Y, Z" is acceptable. "Do more research" is not.
- Steps should be sequenced — the first step enables the second.
- At least one step should address the most important gap or risk identified above.

### Sources

Rules:
- Numbered list.
- Each entry: `[Source name](url) — one-line description`.
- Include every URL cited anywhere in the brief.
- Do not include sources you searched for but did not cite.
- Do not include sources from memory or training data.

---

## Citation format

Inline citations appear immediately after the claim they support, within the same sentence:

```
The global market for X reached $4.2B in 2024, growing 34% year-over-year ([Gartner Market Report](https://gartner.com/...)).
```

Or with source name woven into the sentence:

```
According to [MIT Technology Review](https://technologyreview.com/...), the leading approach uses transformer-based architectures.
```

Never use footnote-style citations (`[1]`, `[2]`) in the brief body. Only inline links.

---

## Example finding structure

Input claim from source: "A 2024 Stanford study found that LLM-assisted diagnosis matched specialist accuracy in 73% of radiology cases."

Well-formed finding:

> **LLMs match specialist accuracy in nearly three-quarters of radiology cases.** A 2024 study found that LLM-assisted diagnosis achieved specialist-level accuracy in 73% of radiology cases ([Stanford HAI](https://hai.stanford.edu/...)). This means healthcare systems could use AI to triage specialist backlogs without sacrificing diagnostic quality — but the remaining 27% gap represents cases where AI under-performs and human review remains essential.

Poorly-formed finding (do not write this):

> AI is getting better at radiology. Studies show it's improving a lot and healthcare is interested in it.

---

## Common format failures

| Failure | What it looks like | Fix |
|---|---|---|
| Executive summary too long | 6-8 sentences of dense prose | Count sentences. Delete until 4 remain. |
| Finding with no citation | "Research shows that X is true." | Add `([Source](url))` immediately after the claim. |
| Finding is just a fact | "The market is $4.2B." | Add "This means [implication]." |
| Recommendations are vague | "Consider exploring partnerships." | Replace with: "Evaluate 3 specific vendors by [criteria] before Q3." |
| Sources section is missing | Brief ends after Next Steps | Add the Sources section with every cited URL. |
| Citations from memory | URL that wasn't in search results | Remove the claim or search again to find a real source. |
