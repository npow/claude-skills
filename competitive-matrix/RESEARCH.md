# Research Process

How to identify players, choose evaluation dimensions, research each player, assign ratings, and handle stale or conflicting information.

## Contents
- Identifying and scoping the space
- Selecting players (5-10 rule)
- Choosing evaluation dimensions
- Running web searches
- Assigning ratings
- Handling stale or conflicting data
- Domain-specific dimension banks

---

## Identifying and scoping the space

Before researching, confirm the exact scope with the user if any of these are ambiguous:

- Is this a product category (e.g. "vector databases") or a vendor comparison (e.g. "AWS vs GCP vs Azure for ML")?
- What buyer persona cares? A startup CTO vs a Fortune 500 architect will weight dimensions differently.
- What is the time horizon? Current state (now) or roadmap (next 12 months)?

If the user's request is under-specified, ask one clarifying question before proceeding. Do not guess the scope.

---

## Selecting players (5-10 rule)

Target exactly 5-10 players. The right number depends on how fragmented the space is.

### How to build the list

1. Start with the players the user named or implied.
2. Add the 2-3 obvious market leaders if not already included.
3. Add 1-2 notable challengers or open-source alternatives.
4. Stop before 10. If you have more candidates, drop the least relevant.

### Exclusion criteria (drop a player if any apply)

- No longer actively maintained (last commit or release > 18 months ago)
- Acquired and folded into another product on the list
- Clearly out of scope for the buyer persona (enterprise-only vs. the user is a startup)
- Purely academic with no production deployments

### Note exclusions

After building the list, note any notable players you excluded and why. Example: "Excluded: Annoy (unmaintained), ScaNN (no managed offering)."

---

## Choosing evaluation dimensions

Dimensions must be specific to the domain. Generic dimensions like "Ease of use" or "Support" produce useless matrices.

### Rules for choosing dimensions

- Use 5 to 8 dimensions — never fewer, never more.
- Each dimension must be independently observable — two players can differ on it without implying one is universally better.
- Each dimension must have clear better/worse direction — higher throughput is better; higher latency is worse; more permissive license is usually better for open-source.
- Name dimensions as nouns, not questions: "Latency" not "Is it fast?"; "Pricing model" not "Is it affordable?"

### How to validate a dimension

Ask: "Can two reasonable people look at the same evidence and agree on the rating?" If the answer is no, the dimension is too vague. Replace it with something measurable.

### Dimension bank by domain

Use these as starting points. Adapt to the specific space.

**Developer tools / databases / infrastructure**
Latency, Throughput, Operational complexity, Pricing, Ecosystem / integrations, Documentation quality, Governance / license, Managed offering, Horizontal scalability

**SaaS / B2B products**
Pricing model, Free tier, API quality, Integration depth, Data privacy / compliance, Support tier, Customization, Vendor lock-in risk, Market presence

**AI / ML platforms**
Model coverage, Fine-tuning support, Latency, Pricing per token, Context window, Function calling, Safety / guardrails, Enterprise SLA, Open weights

**Cloud infrastructure**
Global region coverage, Pricing transparency, Compliance certifications, SLA uptime, Support tiers, Ecosystem breadth, Egress costs, Open-source alignment

**Open-source libraries / frameworks**
Maintenance activity, Documentation, Community size, Performance benchmarks, Test coverage, License, Plugin ecosystem, Enterprise support option

---

## Running web searches

Run at least one web search per player. The goal is to verify the current state of each player's rating on each dimension — not to find a source that confirms a pre-formed rating.

### Search strategy per player

For each player, run a search like:
- `[player] [dimension] 2025` — e.g. "Pinecone pricing 2025", "Weaviate latency benchmarks"
- `[player] review [current year]` — picks up recent user experience reports
- `[player] vs [closest competitor]` — surfaces comparative data

### What to look for

- Pricing pages: verify free tier, paid tier structure, per-unit costs
- Benchmark posts: throughput, latency, recall numbers
- GitHub: last commit date, open issues trend, contributor count
- Official docs: completeness, freshness, API reference depth
- Changelog / blog: recent feature additions confirm active development

### What to record

For each search, note:
- The source URL
- The date of the source
- The specific fact that affects the rating

This evidence is used in the Verdict column and post-matrix summary. You do not need to display sources in the HTML — include them in your text response.

---

## Assigning ratings

Map your research findings to the four-point scale. Apply each rating consistently across all players for the same dimension.

### Rating decision rules

| Rating | Use when |
|--------|----------|
| ✓✓ | Best-in-class among the players in this matrix; no meaningful gap to the next best |
| ✓ | Meets the standard; no significant gaps; typical for the category |
| ~ | Works but with notable limitations, trade-offs, or missing features |
| ✗ | Not supported, clearly behind peers, or a known pain point with no mitigation |

### Calibration: rate within the matrix, not against an absolute ideal

Ratings are relative to the other players in this matrix. If all players have mediocre docs, the best docs gets ✓ not ✓✓. Reserve ✓✓ for a player that is genuinely ahead of the field.

### The Verdict column

Write 5-10 words summarizing the player's overall positioning. The verdict should answer: "When would someone choose this player over the others?"

Examples of good verdicts:
- "Best managed option; expensive at scale"
- "Strong open-source; complex to self-host"
- "Ideal if already on Postgres"
- "Fast iteration speed; limited enterprise support"

Examples of bad verdicts:
- "Good" (too vague)
- "A solid choice for teams that need reliability and are willing to pay a premium for enterprise-grade support" (too long)

---

## Handling stale or conflicting data

### Stale data

If the most recent source for a dimension is more than 12 months old, rate the cell with ~ instead of ✓ or ✓✓ unless a more recent source confirms the older rating still holds. Note the staleness in your text summary.

### Conflicting data

If two sources contradict each other (e.g. one benchmark shows Player A wins on latency, another shows Player B wins):

1. Check recency — prefer the more recent source.
2. Check methodology — prefer controlled benchmarks over vendor-published ones.
3. If still unresolved, assign ~ and note the conflict in the summary.

### Vendor-published benchmarks

Treat vendor-published benchmarks as evidence of capability, not as ground truth. If the only latency data is from the vendor's own blog, note that. Prefer third-party benchmarks from community members or academic papers.

### Pricing page changes

Pricing changes frequently. If the user says pricing changed since your search, trust the user. Revise the cell and update the META date.
