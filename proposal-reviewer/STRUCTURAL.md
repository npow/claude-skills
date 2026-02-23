# Structural Flaw Analysis

How to identify structural problems in business model, technical architecture, cost model, scope/timeline, team capacity, and sustainability.

## Contents
- Analysis framework
- Business model analysis
- Technical architecture analysis
- Cost model analysis
- Scope and timeline analysis
- Team capacity analysis
- Sustainability analysis
- Flaw classification
- Failure diagnosis

## Analysis framework

Structural flaws are problems with how the proposal is designed, not whether its claims are accurate. A proposal with 100% verified claims can still have a fatal structural flaw (e.g., no business model, or a cost structure that doesn't scale).

For each dimension below, ask the core question, look for the red flags, and classify any finding as FIXABLE or INHERENT RISK.

## Business model analysis

**Core question**: How does this become sustainable after the initial funding/grant runs out?

### Red flags

| Red flag | What it means | Severity |
|----------|--------------|----------|
| No revenue model mentioned | Author hasn't thought about sustainability | HIGH — fixable if a viable model exists for the space |
| "Open-source under MIT license" with no commercial plan | Anyone can take the work and monetize it without obligation | HIGH — fixable by changing license or adding commercial layer |
| Revenue model requires massive adoption first | Chicken-and-egg problem — need users to make money, need money to get users | MEDIUM — common in OSS, address with a phased plan |
| Revenue model conflicts with open-source promise | e.g., "open-source but pay for the good features" can alienate community | MEDIUM — address with clear open-core boundaries |
| Sole revenue path is acquisition | Building to be acquired is a strategy, but not a business model | MEDIUM — acceptable if stated honestly |
| No comparison to similar business models | Author doesn't know if this model works in this space | LOW — fixable with research |

### What to look for

- Does the proposal mention revenue, pricing, or monetization?
- Is there a precedent for this business model in this space? (Name specific companies that used the same model — did it work?)
- Does the license choice support the commercial plan?
- Is there a Phase 2 after the initial funding?

## Technical architecture analysis

**Core question**: Can this actually be built as described, and will it work at production scale?

### Red flags

| Red flag | What it means | Severity |
|----------|--------------|----------|
| Single point of failure with no fallback | If component X fails, everything fails | HIGH — fixable by adding failure modes |
| Dependency on a single external provider with no abstraction | If OpenAI goes down or changes pricing, the product is dead | HIGH — fixable by making the interface provider-agnostic |
| Cost scales linearly (or worse) with usage | Every user interaction costs money with no ceiling | HIGH — may be inherent depending on architecture |
| Latency budget not accounted for | Adding 2 seconds to every operation may be unacceptable | MEDIUM — fixable by profiling and optimizing, but must be acknowledged |
| Architecture requires capabilities that don't exist yet | "We'll fine-tune a model to do X" when X hasn't been demonstrated | HIGH — may be inherent risk |
| No consideration of adversarial evasion | Security tool doesn't account for attackers adapting to the defense | MEDIUM — fixable by adding an adversarial evaluation |

### What to look for

- Does every component have a failure mode? What happens when it fails?
- Does the cost model have an upper bound, or does it grow without limit?
- Is the latency budget realistic for the target use case?
- Are there hard dependencies on specific providers, models, or infrastructure?
- For security tools: does the proposal account for adversarial adaptation?

## Cost model analysis

**Core question**: What does it cost to run this at the scale the proposal envisions, and who pays?

### Red flags

| Red flag | What it means | Severity |
|----------|--------------|----------|
| No cost analysis | Author hasn't calculated operating costs | HIGH — fixable by adding the analysis |
| API costs estimated at "low" without numbers | Vague cost claims hide expensive operations | HIGH — fixable by calculating actual costs |
| Cost per operation * expected operations > budget | The math doesn't work | HIGH — may require architectural changes |
| No distinction between development costs and operating costs | $10K in API credits for development ≠ $10K/year to run in production | MEDIUM — fixable by separating the two |
| Hardware requirements not stated | Users may need expensive infrastructure the proposal doesn't mention | MEDIUM — fixable by adding hardware requirements section |

### Cost calculation method

For proposals involving API calls:
1. Identify every operation that makes an API call
2. Estimate cost per call (input tokens * input price + output tokens * output price)
3. Estimate calls per user interaction
4. Estimate interactions per day at target scale
5. Multiply: cost/call * calls/interaction * interactions/day * 30 = monthly cost

For proposals involving infrastructure:
1. Identify compute requirements (GPU, CPU, memory, storage)
2. Map to cloud pricing (AWS/GCP/Azure on-demand rates)
3. Estimate utilization (is the GPU idle 90% of the time?)
4. Calculate monthly infrastructure cost

Present the result: "At [target scale], this costs approximately $X/month to operate."

## Scope and timeline analysis

**Core question**: Can the proposed team build everything described in the proposed timeline?

### Red flags

| Red flag | What it means | Severity |
|----------|--------------|----------|
| N integrations in M weeks by 1 person | Each integration is a full engineering project (learning the API, building the adapter, testing edge cases, maintaining compatibility) | HIGH — fixable by reducing scope |
| ML training pipeline as a side task | Fine-tuning models is unpredictable in timeline. "Week 2: fine-tune classifier" is optimistic | HIGH — fixable by removing ML or making it the primary focus |
| "Documentation and release" crammed into final week | Documentation always takes longer than expected. Final week is for emergencies | MEDIUM — fixable by distributing doc work |
| No buffer time | Every week is fully allocated. No slack for unexpected problems | MEDIUM — fixable by adding buffer |
| Milestone dependencies not mapped | If week 2 slips, does week 4 still work? | MEDIUM — fixable by mapping dependencies |
| Scope creep disguised as features | The deliverables section promises more than the "What We Will Build" section describes | MEDIUM — fixable by aligning sections |

### Scope estimation heuristic

For each deliverable, estimate complexity:

| Deliverable type | Solo developer estimate |
|-----------------|----------------------|
| Core library with single framework integration | 3-4 weeks |
| Each additional framework integration | 1-2 weeks per framework |
| Each additional database/store integration | 1 week per store |
| ML model fine-tuning (including data prep) | 2-4 weeks |
| Benchmark suite (200+ cases, labeled) | 2-3 weeks |
| Technical report / paper | 2-3 weeks |
| Documentation and deployment guide | 1-2 weeks |
| LLM prompt engineering and optimization | 1-2 weeks |

Sum the estimates. If the sum exceeds the timeline by more than 30%, the scope is unrealistic.

## Team capacity analysis

**Core question**: Does the team have the skills and bandwidth to execute?

### Red flags

| Red flag | What it means | Severity |
|----------|--------------|----------|
| Solo developer with enterprise-scale scope | One person building production integrations for 3+ frameworks | HIGH — fixable by reducing scope |
| No relevant domain experience mentioned | Building a security tool without security background, or an ML tool without ML experience | MEDIUM — depends on the complexity |
| Team section is a placeholder | "[Your name here]" suggests the team hasn't been assembled | MEDIUM — concerning for execution confidence |
| Team is entirely academic | Building a production tool without production engineering experience | MEDIUM — may underestimate operational complexity |

## Sustainability analysis

**Core question**: What happens to this project in 12 months?

### Red flags

| Red flag | What it means | Severity |
|----------|--------------|----------|
| No plan beyond the grant period | The project dies when funding runs out | HIGH — fixable by adding sustainability plan |
| OSS tool with no maintainer commitment | Who fixes bugs? Who updates for new framework versions? | HIGH — fixable by defining maintenance plan |
| Relies on volunteer community contributions for critical features | "Community will build adapters" — they probably won't | MEDIUM — fixable by reducing dependency on community |
| No comparison to similar projects that died | Ignoring history (Rebuff, etc.) suggests unawareness of the graveyard | MEDIUM — fixable by acknowledging and differentiating |

### Sustainability models that work in this space

| Model | Example | Viability |
|-------|---------|-----------|
| Open-core (OSS core + commercial managed service) | Guardrails AI, HashiCorp (pre-license change) | PROVEN — standard path for security tooling |
| Acquisition target (build adoption, get acquired) | Protect AI → Palo Alto, Lakera → Check Point | PROVEN — but not a business model, it's an exit strategy |
| Foundation/consortium backed | Linux Foundation, CNCF projects | WORKS for infrastructure, RARE for security tools |
| Pure OSS with consulting | Small shops, freelancers | FRAGILE — doesn't scale |
| VC-funded commercial product | Lasso Security, NeuralTrust | PROVEN — but requires significant traction for fundraising |

## Flaw classification

After analyzing each dimension, classify every finding:

### FIXABLE flaws

A flaw is FIXABLE if:
- The proposal can be rewritten to address it
- The underlying idea remains viable after the fix
- The fix doesn't require fundamental changes to the approach

For each FIXABLE flaw, provide:
- **What's wrong**: one sentence
- **Why it matters**: what happens if it's not fixed
- **How to fix it**: specific recommendation
- **Impact on proposal**: what sections need to change

### INHERENT RISKS

A risk is INHERENT if:
- No amount of rewriting eliminates it
- It's a fundamental property of the market, technology, or timing
- The team must accept it and plan around it

For each INHERENT RISK, provide:
- **What the risk is**: one sentence
- **Probability**: HIGH / MEDIUM / LOW
- **Impact if realized**: what happens
- **Mitigation**: how to reduce exposure (not eliminate)

## Failure diagnosis

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Can't determine if a flaw is fixable or inherent | The flaw spans multiple dimensions (e.g., business model AND technical architecture) | Break it into sub-flaws. Each sub-flaw is usually clearly fixable or inherent on its own |
| Every flaw seems fixable | You may be underestimating the difficulty of the fixes, or missing inherent risks | Apply the "pre-mortem" test: assume the project failed in 12 months — what killed it? The answer is usually an inherent risk you're not seeing |
| Every flaw seems fatal | You may be holding the proposal to an unrealistic standard | Compare to similar successful projects. Did they have the same flaws? How did they survive? |
| Can't assess technical feasibility | The architecture description is too vague | Flag "insufficient technical detail" as a flaw. Recommend the author specify: components, interfaces, failure modes, and cost per operation |
| If none of the above | Document what you analyzed, what you found ambiguous, and what additional information would resolve the ambiguity. Present to the user |
