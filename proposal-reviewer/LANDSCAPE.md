# Competitive Landscape Analysis

How to map competitors, assess market timing, identify platform risk, and find threats the proposal missed.

## Contents
- Research strategy
- Competitor categories
- Research execution
- Market timing assessment
- Platform risk analysis
- Building the landscape summary
- Failure diagnosis

## Research strategy

A proposal's competitive landscape section is almost always incomplete. Authors have blind spots: they know the competitors they've researched and miss the ones they haven't. The reviewer's job is to find what's missing.

### The five searches you must always run

For every proposal, run these searches regardless of what the proposal claims:

1. **The exact problem** — search for the problem the proposal claims to solve (e.g., "AI agent memory poisoning defense")
2. **Adjacent solutions** — search for broader category solutions that might cover this problem as a feature (e.g., "AI agent security platform")
3. **Platform vendor features** — search for whether major platforms (AWS, Azure, GCP, OpenAI, Anthropic, Meta, Google) have announced or shipped something similar
4. **Startup landscape** — search for recent funding rounds in the space (e.g., "AI security startup funding 2025 2026")
5. **Open source alternatives** — search GitHub and product hunt for tools addressing the same problem

### Parallel research execution

Launch multiple research agents concurrently. Each agent handles one competitor category. Use the Task tool with subagent_type "general-purpose" for each agent. Give each agent a specific, focused research mandate:

```
Agent 1: "Research direct competitors for [problem]. Find any product, open-source tool,
         or service that addresses [specific problem] directly. Check GitHub, Product Hunt,
         and security vendor product pages."

Agent 2: "Research adjacent competitors for [problem]. Find products in the broader
         [category] space that include [problem] as a feature. Check major security
         vendors: Palo Alto, CrowdStrike, SentinelOne, Check Point, Fortinet."

Agent 3: "Research platform vendor roadmaps for [problem]. Check if AWS, Azure, GCP,
         OpenAI, Anthropic, or Meta have announced, shipped, or acquired capabilities
         related to [problem]. Check recent announcements, blog posts, and product pages."

Agent 4: "Research the acquisition and funding landscape for [category]. Find recent
         acquisitions, funding rounds, and startup launches. Check Crunchbase, TechCrunch,
         and security trade publications."
```

## Competitor categories

Every competitor fits one of these categories. The proposal must address all five or it has blind spots:

### 1. Direct competitors
Products that solve the exact same problem for the exact same audience.
- **What to find**: product name, funding, pricing, feature set, adoption metrics
- **Key question**: why would a customer choose the proposal over this?

### 2. Adjacent competitors
Products in a broader category that include this problem's solution as one feature among many.
- **What to find**: how deep is their coverage of this specific problem?
- **Key question**: is the proposal's depth advantage worth a separate product, or will "good enough" from a broader platform win?

### 3. Platform vendors
AWS, Azure, GCP, OpenAI, Anthropic, Meta, Google — any platform that could add this as a native feature.
- **What to find**: announcements, roadmap items, blog posts, conference talks, recent acquisitions that signal intent
- **Key question**: will they build this in 6-12 months and make the proposal redundant?

### 4. Open-source alternatives
Free tools, academic prototypes, and community projects that address the same problem.
- **What to find**: GitHub stars, last commit date, maintainer activity, documentation quality, framework support
- **Key question**: is this usable as-is, or is there a real gap between this and production readiness?

### 5. The "do nothing" competitor
The option of not solving this problem at all.
- **What to find**: how are people currently handling this? Accepted risk? Manual processes? Workarounds?
- **Key question**: is the pain severe enough that people will actually adopt a solution?

## Research execution

### For each competitor found, record:

| Field | What to capture |
|-------|----------------|
| **Name** | Product or project name |
| **Category** | Direct / Adjacent / Platform / Open-source / Do-nothing |
| **Funding/Backing** | Funding raised, or parent company resources |
| **Feature overlap** | Which features of the proposal does this competitor cover? |
| **Feature gap** | What does the proposal offer that this competitor doesn't? |
| **Adoption** | GitHub stars, customers, revenue (if available) |
| **Recency** | Last update, last funding round, last product announcement |
| **Threat level** | HIGH (directly competitive, well-funded) / MEDIUM (partial overlap or early-stage) / LOW (different audience or deprecated) |
| **Mentioned in proposal?** | Yes/No — if No, flag as a blind spot |

### Determining threat level

| Signal | Threat level |
|--------|-------------|
| Well-funded ($10M+), active development, direct feature overlap | HIGH |
| Active development, partial overlap, or same space but different approach | MEDIUM |
| Archived/inactive, different audience, or only tangentially related | LOW |
| Platform vendor with announced intent or recent acquisition in the space | HIGH (platform risk) |
| Platform vendor with no signals but obvious capability to build | MEDIUM (platform risk) |

## Market timing assessment

After mapping competitors, assess the market window:

### Window is OPEN when:
- No direct competitor has meaningful adoption (>1000 users)
- Platform vendors have not announced or shipped a solution
- The problem is validated by recent incidents, advisories, or standards
- Attack tooling exists but defense tooling does not

### Window is CLOSING when:
- Direct competitors exist but are early-stage (<2 years, <$10M funding)
- Platform vendors have made acquisitions in the space but haven't shipped features yet
- Multiple startups are entering the space simultaneously

### Window is CLOSED when:
- A well-funded direct competitor has meaningful adoption
- A platform vendor has shipped a native solution
- The problem is being addressed by an industry standard or framework feature

### Window assessment format

Present the assessment as:

```
MARKET WINDOW: [OPEN / CLOSING / CLOSED]
EVIDENCE:
- [Bullet point with specific evidence]
- [Another bullet point]
TIME HORIZON: Estimated [X] months before [specific threat] materializes
IMPLICATION FOR PROPOSAL: [What this means for timing, scope, or strategy]
```

## Platform risk analysis

Platform risk is the probability that a platform vendor (AWS, OpenAI, Meta, etc.) will build this as a native feature and make the proposal redundant.

### Signals that platform risk is HIGH:
- Platform vendor has acquired a company in the space
- Platform vendor has published research or blog posts on the topic
- Platform vendor has established a working group or foundation for the topic
- The feature is a natural extension of the platform's existing capabilities
- The feature addresses a problem the platform's customers are vocal about

### Signals that platform risk is LOW:
- The feature requires deep domain expertise the platform doesn't have
- The feature serves a niche audience the platform doesn't prioritize
- The feature conflicts with the platform's business model
- No signals of platform interest in recent announcements or acquisitions

### Platform risk format

```
PLATFORM RISK: [HIGH / MEDIUM / LOW]
MOST LIKELY PLATFORM THREAT: [Which vendor, what they might build]
TIMELINE ESTIMATE: [When they could ship, based on signals]
MITIGATION: [How the proposal accounts for or survives this risk]
```

## Building the landscape summary

The final output has three parts:

### 1. Competitor table

| Competitor | Category | Threat | Feature Overlap | Key Differentiator | In Proposal? |
|-----------|----------|--------|----------------|-------------------|-------------|
| Name | Direct/Adjacent/etc. | HIGH/MED/LOW | What overlaps | What's different | Yes/No |

### 2. Blind spots

List every competitor or threat NOT mentioned in the proposal. For each:
- Why it matters
- How it affects the proposal's competitive positioning

### 3. Market timing + platform risk

Combine the window assessment and platform risk analysis into a single paragraph that answers: "Is the timing right, and how long does the team have before the window closes?"

## Failure diagnosis

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Can't find any competitors | Search terms are too specific. The proposal may have invented a category name | Search for the underlying problem in plain language, not the proposal's terminology |
| Found too many competitors (>15) | Search terms are too broad, or the category is crowded | Narrow to the proposal's specific approach and target audience. Group similar competitors |
| All competitors are open-source with low adoption | The space may be too niche for commercial products, or it's very early | This is actually a positive signal for the proposal — note it as a market opportunity |
| Platform vendor shipped something during your research | The landscape is actively changing | Flag immediately as a critical finding. This may change the viability assessment |
| Competitor's feature claims don't match their actual product | Marketing vs. reality gap | Check the actual product documentation, GitHub repo, or demo — not just the landing page |
| If none of the above | Record what you searched, what you found, and what you expected. Present gaps to the user |
