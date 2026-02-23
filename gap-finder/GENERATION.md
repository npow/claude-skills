# Idea Generation

How to generate high-quality idea batches in any domain.

## Idea template

Every idea must follow this format before entering the kill chain. Adapt field names to the domain but keep the structure:

```
### [Idea Name]
**One-liner**: [What the product does in one sentence]
**Recurring pain point**: [The specific frustration this solves, stated as a user quote]
**Core features** (3-4):
  - [Feature] — input: [what], output: [what]
  - [Feature] — input: [what], output: [what]
  - [Feature] — input: [what], output: [what]
**Why existing tools fail here**: [What gap this fills that current solutions miss]
**Who pays and why**: [Specific buyer persona — not "developers" but "engineering managers at 20-person teams who currently pay $X/mo for [existing tool]"]
**Pricing evidence**: [Name an existing product that charges for similar value + its price. "ChartMogul charges $100/mo" not "I think people would pay $19"]
**Free vs paid boundary**: [What's free (the hook) vs what requires a paid backend (storage, history, team features, alerts)]
**Revenue estimate**: [npm installs × 30% active × 5-10% convert × price = month-12 MRR]
```

If you cannot fill in all fields, the idea is too vague. Refine or discard before validation.

## Angle diversity requirement

Each batch of 5 ideas must draw from at least 3 different angles. Never generate 5 ideas from the same angle — they'll all die for the same reason.

## Universal generation angles

These work across any domain. Adapt to the specific space:

### Angle 1: Workflow friction
What multi-step process does the target user repeat frequently that involves manual coordination between tools? The product automates or shortens this workflow.

### Angle 2: Stale or scattered data
What information does the user need that is spread across multiple sources, changes frequently, or is hard to find? The product aggregates and surfaces it.

### Angle 3: Requires real computation
What questions can't be answered by reasoning or memory alone and require actually running/querying/measuring something?

### Angle 4: Cross-referencing
What insights require combining data from 2+ sources that nobody combines today? The product is valuable because it connects things.

### Angle 5: Expertise gap
What tasks require specialist knowledge that most users lack? The product encodes that expertise so non-specialists can get specialist-quality output.

### Angle 6: Compliance and correctness
What must the user get right (security, legal, standards, formatting) where mistakes are expensive and checking is tedious?

### Angle 7: Monitoring and alerting
What changes in the user's environment would they want to know about immediately but currently discover too late?

### Angle 8: Domain-specific verticals
What narrow audience has unique needs that horizontal tools serve poorly? Smaller market but less competition.

## Batch anti-patterns

Do not generate batches that:
- Are all variations on the same theme (5 "monitoring" ideas)
- Are all in the same vertical (5 "fintech" ideas)
- Are all the same product type (5 "CLI tools")
- Reuse killed ideas from gap-finder-state.md with superficial changes

## Idea quality gate

Before sending an idea to the kill chain, ask yourself:

1. Can I name a specific person who would use this weekly? (Not "developers" — which developer, doing what task?)
2. Does this require external data/computation the user can't get from an LLM prompt alone?
3. Is this specific enough that I could write a landing page headline for it?

If any answer is no, refine the idea or replace it.
