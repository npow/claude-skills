# Proposal Rewriting

How to rewrite a proposal addressing identified flaws while preserving what works.

## Contents
- When to rewrite
- Rewrite principles
- Rewrite workflow
- Handling each flaw type
- What to preserve
- What to add
- Failure diagnosis

## When to rewrite

Only rewrite when the user explicitly asks. The default skill output is analysis and recommendations. Rewriting is a separate, opt-in step.

When the user asks to rewrite, confirm scope first:
- "Rewrite the whole proposal" → full rewrite
- "Fix the issues you found" → full rewrite addressing all FIXABLE flaws
- "Address the business model issue" → targeted rewrite of specific sections
- "Help me address the flaws" → same as full rewrite

## Rewrite principles

### 1. Fix what's broken, preserve what works

Do not rewrite sections that have no identified flaws. If the problem statement is strong, keep it. If the technical approach is sound but the cost model is wrong, rewrite the cost model and leave the technical sections intact.

### 2. Fix facts first

Before addressing structural flaws, correct all factual errors identified in the fact-check. Wrong facts undermine credibility even if the structure is perfect.

Factual corrections:
- Replace FALSE claims with the correct information
- Replace UNVERIFIABLE claims with verified alternatives or remove them
- Fix PARTIALLY TRUE claims to be fully accurate
- Add sources for all corrected claims

### 3. Address structural flaws in order of severity

Rewrite HIGH severity flaws first:
1. Business model / sustainability (if missing or broken)
2. Technical architecture (if fundamentally flawed)
3. Cost model (if unrealistic)
4. Scope / timeline (if unrealistic)
5. Competitive positioning (if missing competitors)

### 4. Acknowledge inherent risks explicitly

Do not pretend inherent risks don't exist. Add a section or paragraph that names them directly and explains how the project accounts for or survives them. Proposals that acknowledge risks are more credible than proposals that ignore them.

### 5. Maintain the author's voice

The rewrite should sound like a better version of the same author, not like a different person wrote it. Preserve:
- The overall narrative structure (unless it's a problem)
- Technical terminology the author uses
- The author's framing of the problem
- Section headings and organization (unless restructuring is needed)

## Rewrite workflow

### Step 1: Build the change list

For each FIXABLE flaw from the structural analysis:
- **Section affected**: which part of the proposal needs to change
- **Current text**: what it says now (quote or summarize)
- **Problem**: why it's wrong
- **Replacement**: what it should say instead

For each factual error from the fact-check:
- **Location**: where in the proposal
- **Current claim**: the incorrect text
- **Correction**: the accurate replacement with source

### Step 2: Identify new sections needed

Common additions:
- **Sustainability / business model section** — if the proposal has no plan beyond the grant
- **Competitive landscape section** — if competitors were missed
- **Cost analysis** — if costs weren't calculated
- **Hardware requirements** — if infrastructure needs weren't stated
- **Failure mode design** — if the architecture doesn't account for failures
- **Platform risk acknowledgment** — if the proposal ignores the possibility of being absorbed by a platform vendor

### Step 3: Execute the rewrite

Apply changes in this order:
1. Fix all factual errors (replace incorrect claims with verified facts)
2. Add missing sections (sustainability, competitive analysis, cost model)
3. Rewrite structurally flawed sections (scope reduction, architecture changes)
4. Adjust dependent sections (timeline changes may affect budget, deliverables may change with scope)
5. Update the conclusion/summary to reflect the revised proposal

### Step 4: Verify consistency

After rewriting, check:
- Do the deliverables still match the "What We Will Build" section?
- Does the timeline add up (sum of estimated weeks <= total weeks)?
- Does the budget match the new scope?
- Are all competitors mentioned in the landscape section?
- Are inherent risks acknowledged somewhere?
- Do preliminary results claims still match what was actually measured?

## Handling each flaw type

### Missing business model
Add a "Sustainability and Long-Term Viability" section. Structure it as:
- Phase 1: What the grant/initial funding covers
- Phase 2: How the project sustains itself (open-core, consulting, acquisition, etc.)
- Precedents: Name 2-3 similar projects and their sustainability path (both successes and failures)
- Risk acknowledgment: What happens if the sustainability plan doesn't work

### Unrealistic scope
Narrow the deliverables to what's achievable. The pattern:
- Pick the single most impactful integration/platform to support at launch
- Move everything else to "community contributions" or "Phase 2"
- Justify the choice (why this framework, why this database)
- Document the adapter pattern so expansion is possible

### Wrong cost model
Replace vague cost claims with calculated numbers:
- Cost per operation (with formula)
- Operations per day at target scale
- Monthly operating cost
- Comparison: "This is X% of the cost of [alternative approach]"

### Missing competitors
Add them to the competitive landscape section. For each:
- What they do
- How the proposal differentiates
- Whether they're complementary or directly competitive

### No failure modes
Add a "Failure Mode Design" section listing what happens when each component fails:
- Component X fails → behavior Y (fail-open, fail-closed, degrade, alert)
- Each failure mode should be a deliberate choice with stated reasoning

### Factual errors
Replace inline. Do not call attention to corrections in the body of the proposal — just fix them. If the correction is significant (e.g., wrong OWASP classification, fabricated CVE), note it in the summary to the user but not in the rewritten proposal itself.

## What to preserve

Never change these unless they're factually wrong or structurally broken:
- The core problem statement (if the problem is real)
- Preliminary results (if they're honestly reported)
- Team section (the author knows their own background)
- The fundamental technical approach (if it's sound — change the implementation details, not the concept)

## What to add

Always add these if they're missing:
- Honest acknowledgment of at least 2 inherent risks
- At least 1 competitor the original proposal didn't mention
- Cost calculations with actual numbers
- A sustainability plan that references precedents (both successful and failed)

## Failure diagnosis

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Rewrite is much longer than original | You're adding detail where the original was appropriately concise | Match the original's level of detail. Add new sections, but don't expand existing ones unnecessarily |
| Rewrite contradicts the preliminary results | Architectural changes may have invalidated the experimental setup | Update the preliminary results section to explain what was measured and how the new architecture differs |
| Timeline doesn't add up after scope changes | Scope was reduced but time was redistributed unevenly | Re-estimate from scratch using the scope estimation heuristic in STRUCTURAL.md |
| User asks to address an inherent risk as if it were fixable | The user may not accept that some risks can't be eliminated | Explain the difference. Offer mitigation strategies that reduce exposure without claiming to eliminate the risk |
| If none of the above | Document what you changed, what you preserved, and what you're unsure about. Present the uncertainty to the user |
