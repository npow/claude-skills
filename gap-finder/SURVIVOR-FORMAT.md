# Survivor Output Format

How to present ideas that pass the kill chain.

## Format for each survivor

```markdown
## [SURVIVOR] [Idea Name]

**One-liner**: [What the product does]

**Pain point**: "[User quote expressing the frustration]"
**Frequency**: [How often this pain occurs — daily/multiple times per week]
**Evidence**: [Link to Stack Overflow question, Reddit thread, or forum post showing demand]

### Competitor landscape
| Competitor | Status | Why we're different |
|-----------|--------|-------------------|
| [Name + URL] | [Active/Abandoned/Small] | [Specific differentiation] |

*[X] competitors found. [Assessment: open field / gap exists / narrow window]*

### Core features
1. **[Feature name]** — [What it does]. Input: [what]. Output: [what].
2. **[Feature name]** — [What it does]. Input: [what]. Output: [what].
3. **[Feature name]** — [What it does]. Input: [what]. Output: [what].

### Business model
- **Free tier (the MCP server)**: [What's free — the MCP tool calls themselves must be free. This is the hook.]
- **Paid tier (the backend SaaS)**: [What requires a paid backend — historical data, dashboards, team features, alerts, exports. Name the price and justify it.]
- **Pricing evidence**: [Name an existing product that charges for similar value. "ChartMogul charges $100+/mo for SaaS analytics" — not "I think people would pay $X"]
- **Who actually pays**: [Job title of the buyer. Individual devs rarely pay. Team leads, managers, founders, and companies pay. Whose budget does this come from?]
- **Revenue math**: [Estimated npm installs at month 12 × 30% active × 5-10% convert × price = MRR. If under $500/mo, be honest that this is a portfolio project, not a business.]

### Distribution
- **Channel 1**: [Where to reach users — registry, marketplace, community]
- **Channel 2**: [Second channel]
- **Launch content**: [One-sentence description of the launch post/demo]

### Build estimate
- **MVP scope**: [What to build first — the smallest useful version]
- **Tech stack**: [Key technologies]
- **Timeline**: [Weeks to MVP for a solo developer]
- **Infra cost**: [Monthly cost at 100-1000 users]

### Risks
1. [Biggest risk + how to mitigate]
2. [Second risk + mitigation]
```

## Final report format

After reaching 3 survivors or 10 batches, present:

```markdown
# Gap Finder Results: [Domain]

## Summary
- **Ideas evaluated**: [total count]
- **Ideas killed**: [count]
- **Ideas survived**: [count]
- **Batches run**: [count]

## Survivors (ranked by confidence)

[Survivor 1 — full format above]
[Survivor 2 — full format above]
[Survivor 3 — full format above]

## Graveyard (killed ideas)

| # | Idea | Kill reason | Killed at |
|---|------|------------|-----------|
| 1 | [Name] | [One-sentence reason] | Check [N] |
| 2 | [Name] | [One-sentence reason] | Check [N] |
...

## Patterns observed
- [What categories/angles were most productive]
- [What categories were dead ends]
- [Any meta-insights about the domain's gaps]
```

## Ranking survivors

Rank survivors by this priority order:
1. **Fewest competitors** — open field beats crowded market
2. **Highest pain frequency** — daily beats weekly
3. **Clearest monetization** — obvious paywall beats "maybe they'll pay"
4. **Easiest to build** — 1 week MVP beats 4 week MVP
5. **Best distribution** — existing marketplace/registry beats cold outreach
