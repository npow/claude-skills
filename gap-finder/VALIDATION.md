# The Kill Chain

6 validation checks. Every idea must pass all 6 to survive. Kill on first fatal failure and move to the next idea.

## Check 1: Competitor Search

**Goal**: Find existing products that solve the same problem.

**Process**:
1. Search the primary marketplace for the domain (npm/PyPI for dev tools, App Store for mobile apps, Chrome Web Store for extensions, ProductHunt for SaaS, etc.)
2. Search GitHub for open source implementations
3. Search Google for "[problem] tool" or "[problem] solution"

**Pass criteria**: Fewer than 2 direct competitors that are well-maintained and widely adopted. Having 1 small/unmaintained competitor is acceptable (you can outexecute). Having 0 is ideal but suspicious (maybe there's no demand — check harder).

**Kill criteria**: 2+ active, well-funded, or widely-adopted competitors already exist. The space is taken.

**Search queries to run** (adapt to domain):
- `[product concept] site:github.com`
- `[product concept]` on the relevant package registry
- `[product concept] alternative` on Google
- `[product concept]` on ProductHunt

**Record in state file**: List every competitor found with URL and status (active/abandoned/small).

## Check 2: Existing-Solution-Already-Works Test

**Goal**: Determine if the problem is already solved well enough by a general-purpose tool.

**Process**:
1. Ask: "Can a user solve this today with [mainstream tool] + 5 minutes of effort?"
2. For dev tools: Can an LLM already do this from its training data alone without external access?
3. For apps: Does a built-in OS feature or a major platform feature cover this?

**Pass criteria**: Existing solutions require significant manual effort (>15 min), specialized knowledge, or access to data the user doesn't have.

**Kill criteria**: A mainstream free tool already does this well enough. Or an LLM can produce equivalent output without needing external data/APIs.

**Examples of kills**:
- "MCP that explains error messages" — LLMs already do this from training data
- "App that converts units" — built into every phone's search bar
- "Tool that formats JSON" — `jq`, VS Code, every IDE does this

## Check 3: Recurring Pain Frequency

**Goal**: Verify the pain point occurs frequently enough to sustain a product.

**Process**:
1. Identify the specific user action that triggers the pain
2. Estimate how often the target user does this action
3. Search for evidence of the pain: Stack Overflow questions, Reddit complaints, GitHub issues, forum posts

**Pass criteria**: Target user encounters this pain at least weekly. Evidence exists of people complaining about it or asking for solutions online.

**Kill criteria**: Pain occurs monthly or less. Or no evidence of anyone complaining about it (which means either no pain exists or the audience is too small to find).

**Search queries**:
- `[pain point] site:stackoverflow.com`
- `[pain point] site:reddit.com`
- `[pain point] frustrating OR annoying OR tedious`

**Record in state file**: Frequency estimate + links to evidence of pain.

## Check 4: Monetization Viability

**Goal**: Determine if there's a realistic path from free users to paying customers.

**Reality check data (as of Feb 2026):**
- The only proven standalone paid MCP server (Ref) makes ~$500 MRR at $9/mo
- Most developers expect MCP servers to be free. Nearly everything in the MCP ecosystem is free or a free add-on.
- MCP supply is growing faster than demand (Madrona research)
- Developer tools get ~11.7% freemium→paid conversion (best in SaaS, but still means 88% never pay)
- The $5-10/mo range is a trap: thin margins, high churn, support-heavy customers
- Indie SaaS sweet spot is $19-49/mo, but this is unproven for MCP-native products
- The proven MCP business model is: free MCP server → paid SaaS backend (Context7/Upstash pattern), NOT charging for the MCP server itself

**Process**:
1. The MCP server itself must be FREE. The paid product is the backend service (dashboards, historical data, team features, alerts). If the only value is the MCP tool calls, it won't monetize.
2. Identify what the paid backend adds that requires persistent infrastructure (storage, computation, monitoring). One-shot tool calls are free. Ongoing data is paid.
3. Name a specific existing product that charges for similar value and verify the price. "I think people would pay $19/mo" is not evidence. "ChartMogul charges $100/mo for similar analytics" is evidence.
4. Estimate realistic revenue: (npm installs × 30% active × 5-10% convert × price). If month-12 MRR is under $200, the idea isn't a business — it's a portfolio project.

**Pass criteria**: Clear free MCP → paid SaaS boundary. Paid features require a backend you operate (storage, computation, monitoring). An existing paid product at a similar or higher price point proves willingness to pay. Estimated month-12 MRR exceeds $500.

**Kill criteria**:
- No natural paywall boundary — the MCP tool calls are the entire product (nothing to gate behind payment)
- The paid feature is a one-time output with no recurring value
- No existing product charges for similar value (unproven willingness to pay)
- Target audience is individual developers who historically don't pay for tools (vs. teams/managers/companies)
- Estimated month-12 MRR is under $200 even with optimistic assumptions

## Check 5: Technical Feasibility for Solo Builder

**Goal**: Confirm one person can build and maintain the MVP in 2-4 weeks.

**Process**:
1. Identify the core technical components
2. Check for available APIs, libraries, and data sources
3. Estimate the infrastructure cost at small scale

**Pass criteria**: MVP can be built with standard technologies, available APIs/data sources exist, and infrastructure costs at 100-1000 users are under $50/month.

**Kill criteria**: Requires a large dataset you don't have, an API that doesn't exist or costs too much, specialized hardware, regulatory approval, or more than one person to maintain.

## Check 6: Distribution Path

**Goal**: Verify you can reach the target users without a marketing budget.

**Process**:
1. Identify where the target users already congregate (subreddits, forums, Discord servers, registries, marketplaces)
2. Check if the product can be listed on a relevant marketplace/registry for free
3. Determine if the product is "show-don't-tell" — can you demo it in a tweet/post?

**Pass criteria**: At least 2 free distribution channels exist. The product can be demonstrated visually or in a short code snippet. A single blog post or social media post could drive first users.

**Kill criteria**: Target users don't congregate anywhere reachable. Product requires enterprise sales motion. Product can't be demonstrated without a 30-minute walkthrough.

## Kill chain execution order

Run checks in this order (cheapest/fastest kills first):

1. **Check 2** (Existing-Solution test) — kills ideas in 30 seconds without any search
2. **Check 3** (Recurring Pain) — quick gut check + one search
3. **Check 1** (Competitor Search) — requires 3+ searches, most time-consuming
4. **Check 5** (Technical Feasibility) — quick assessment
5. **Check 4** (Monetization) — requires thought about business model
6. **Check 6** (Distribution) — final check

## Saturation response (do NOT stop — adapt)

After every 2 batches, calculate kill-reason distribution. If >80% of ideas in the last 2 batches died at Check 1 (competitors), the current sub-space is saturated. Response:

1. Note which sub-space is saturated in the state file
2. DO NOT STOP. Shift strategy for the next batch:
   - Change the target user (developers → PMs, designers, DevOps, data analysts, non-tech users)
   - Change the business model (free MCP → something else entirely: paid API, marketplace, consulting tool)
   - Go hyper-niche (not "database tool" but "Shopify store migration tool" or "Kubernetes cost per namespace")
   - Combine two unrelated domains (e.g., "MCP + real estate data" or "MCP + construction compliance")
   - Target a GEOGRAPHY or LANGUAGE (MCP servers for Chinese dev ecosystem, LATAM SaaS tools)
3. Keep generating until 10 batches. The weird batches (7-10) are where non-obvious ideas live.

## Failure diagnosis

| Symptom | Cause | Fix |
|---------|-------|-----|
| Every idea in a batch dies at Check 1 | Generating ideas in a well-explored space | Switch to a different generation angle, niche vertical, or target user |
| Every idea dies at Check 2 | Generating features, not products — things LLMs/existing tools already handle | Focus on ideas requiring external data access or real computation |
| Every idea dies at Check 3 | Solving rare problems | Ask: "What did [specific user] do 3 times TODAY that was frustrating?" |
| Every idea dies at Check 4 | Generating hobbyist tools | Target professional users whose employers pay for tools |
| 2+ consecutive batches at 0 survivors, >80% Check 1 kills | Sub-space is saturated | Widen: change target user, business model, or go hyper-niche. Do NOT stop |
| Batches 8-10 still killing everything | Reaching deep into unexplored territory | Get weird. Combine unrelated domains. Target non-obvious users. Lower the competitor bar (1 small competitor is OK if you can outexecute) |
