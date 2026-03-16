# Forcing Functions

Five orthogonal generation mechanisms plus two mutation-level operators (NEGATION STACKER, MICRO-NICHER). Each one forces a different structural path to novel ideas. An idea is only valid if it emerges from the mechanism — not from free association.

---

## What "derivation chain" means

Every idea must include a derivation chain: explicit, step-by-step reasoning showing how the forcing function mechanism produced this specific idea. A vague connection is not a derivation chain.

**Minimum required:** 3 explicit steps. A one-sentence chain is not a chain.

**Bad derivation chain (INVERTER):**
> "Existing tools assume real-time data, so we'll use historical data."

**Good derivation chain (INVERTER):**
> 1. All existing CI/CD observability tools assume: "the developer wants to know if their pipeline is broken NOW"
> 2. Inverting this assumption: "what if the developer wants to know WHY it broke HISTORICALLY — not now, but retrospectively across hundreds of runs?"
> 3. This leads to: a forensic CI analyzer that builds a statistical model of flakiness patterns across months of run history, not a real-time dashboard
> 4. Nobody has built this because all monitoring tools share the real-time assumption

If you cannot write a derivation chain this explicit (minimum 3 steps, each causally connected), the idea did not come from the forcing function.

---

## Killed ideas list format

When coordinators pass the killed ideas list to generators, include the **mechanism or assumption** that was tried, not just the title. This prevents INVERTER from re-inverting an already-exhausted assumption under a new name.

Format: `"{Idea Title}" — mechanism: {what forcing-function mechanism this used}`

Example: `"Forensic CI analyzer" — mechanism: INVERTER on real-time monitoring assumption`

---

## INVERTER

**Core mechanism:** Identify the core assumption shared by every existing solution. Negate it. Ask what product that negation naturally leads to.

**When to use:** When existing solutions all share a deeply embedded assumption that nobody questions because it "obviously" should be true.

**Step-by-step process:**
1. From the landscape map, list every major existing solution
2. For each: write one sentence stating its core assumption about the user, the problem, or the world
3. Find the assumption that ALL of them share (or nearly all) — this is the load-bearing assumption
4. Negate it: what is the opposite world?
5. In that opposite world, what product is natural and obvious?
6. Check: does this product already exist? (The inversion should feel slightly absurd — if it doesn't, the assumption wasn't really core)

**Examples of good inversions:**
- All email tools assume: "the user wants to send and receive messages." Inversion: "the user wants to NOT receive messages, but with social grace." → Inbox deferral as social tool
- All code review tools assume: "the developer wants feedback on their code." Inversion: "the developer wants to give feedback on the reviewer's feedback." → Review quality scoring for reviewers
- All logging tools assume: "the developer writes logs to find bugs." Inversion: "the system writes logs to prove compliance." → Audit-first logging design

**Derivation chain template:**
```
1. Core shared assumption: [statement]
2. Negation: [opposite]
3. In this negated world: [what is natural and obvious]
4. Specific product: [concrete description]
5. Why this doesn't exist: [structural reason the assumption persists]
```

---

## BISOCIATOR

**Core mechanism:** Find a structural isomorphism between the domain and an unrelated domain. Transplant a mechanism that works in the source domain into the target domain.

**When to use:** When the domain has a hard problem that another domain has already solved, but nobody noticed because the domains look unrelated.

**Step-by-step process:**
1. State the core hard problem in the target domain as abstractly as possible (e.g., not "debugging ML models" but "finding which input causes unexpected output in a complex system")
2. Brainstorm 3 unrelated domains that deal with the same abstract problem
3. For each: what is the mechanism that domain uses to solve it?
4. Pick the mechanism that is MOST UNLIKE anything in the target domain (not the most obvious analogy)
5. Transplant: apply that mechanism literally to the target domain
6. The friction of the transplant reveals the new product: what infrastructure/tool would you need to build for the mechanism to work in the new domain?

**Examples of good bisociations:**
- Abstract problem: "understanding why a distributed system failed" → Source domain: aircraft black box forensics → Mechanism: continuous ambient recording that can be rewound after a crash → Target product: always-on distributed system state recorder that snapshots causally-linked events for forensic replay
- Abstract problem: "getting honest feedback on creative work" → Source domain: clinical drug trials (double-blind) → Mechanism: remove the social relationship between reviewer and reviewed → Target product: anonymous-to-both-sides creative critique exchange with structured rubrics

**Anti-patterns:**
- "Uber for X" — structural metaphor (marketplace), not mechanism transplant
- Obvious analogies (using gamification for productivity — already saturated)
- Domains that are adjacent (using medical imaging techniques for industrial QA — already done)

**Derivation chain template:**
```
1. Abstract problem in target domain: [one sentence]
2. Unrelated source domain: [name]
3. Mechanism in source domain: [how they solve it]
4. Transplant: [mechanism applied literally to target domain]
5. What you'd need to build: [specific infrastructure/product]
6. Why this is non-obvious: [what makes the connection surprising]
```

---

## EDGE DESIGNER

**Core mechanism:** Find the user that every existing solution in the domain ignores. Design specifically for that user. The product that serves them will look nothing like existing products because all design choices are made for the wrong person.

**When to use:** When the domain has a clearly assumed "normal" user, and the unexplored edges are structurally different enough to require a different product.

**Step-by-step process:**
1. From the landscape map, identify the implicit "design target user" of all existing solutions
2. List every assumption embedded in that target user (skill level, language, device, geography, budget, goals, constraints)
3. Flip ONE assumption that, when flipped, produces a user with genuinely different needs (not just different preferences)
4. Design the product from scratch for this user — let their constraints dictate all design choices
5. The product that results should look unfamiliar to someone designing for the "normal" user

**Examples of good edge users:**
- Domain: "developer tools" — everyone assumes: English-speaking, MacOS/Linux, experienced programmer. Edge: rural developer in a low-bandwidth environment using Windows → product: an offline-first, low-bandwidth dev toolchain that caches all dependencies locally
- Domain: "health tracking apps" — everyone assumes: motivated user who wants to improve. Edge: unmotivated patient who must track for compliance. → product: minimal-friction health logging via SMS/voice that doesn't require app opens
- Domain: "project management" — everyone assumes: manager/coordinator who assigns tasks. Edge: the people being assigned work → product: task negotiation tool where workers push back on timelines with evidence

**The test:** If your edge user can use an existing product with minor modifications, they're not a real edge. A real edge user needs different affordances, different data, different interaction model.

**Derivation chain template:**
```
1. Assumed "normal" user of all existing solutions: [description]
2. Implicit assumptions in that user: [list]
3. The assumption being flipped: [specific one]
4. Edge user this produces: [concrete description]
5. How their needs differ structurally (not just in preference): [specific list]
6. Product designed from scratch for them: [description]
7. Why this product looks unlike existing ones: [what design choices are different]
```

---

## TEMPORAL EXPLOITER

**Core mechanism:** Find a capability, dataset, regulation, or platform that became available in the last 18 months. Find a problem it newly makes tractable that was previously intractable or impractical.

**When to use:** When the landscape map reveals meaningful recent changes — new models, APIs, regulations, datasets, or infrastructure that existing products don't yet exploit.

**Step-by-step process:**
1. List recent enablers from the landscape map (new APIs, models, regulations, standards, datasets)
2. For each enabler: what problems does it newly make tractable? (Not "makes it easier" but "previously impossible or prohibitively expensive")
3. Pick the problem/enabler pair where the gap between "now possible" and "already built" is largest
4. Design a product that could only exist because of this specific enabler
5. The product must be broken without the enabler — if it would work the same way 3 years ago, it's not exploiting the enabler

**If landscape `recent_enablers` is empty:** Do NOT substitute the static list below as if it were landscape data. Report "FORCING FUNCTION EXHAUSTED: recent_enablers field is empty — TEMPORAL EXPLOITER requires landscape data." The static list below is for context only, not a substitute for real landscape mapping.

**Strong enablers to consider (as of early 2026) — CONTEXT ONLY, not a substitute for landscape data:**
- LLMs with reliable tool-use and structured output (for structured extraction from unstructured data)
- Multimodal models capable of video/audio analysis at low cost
- Sub-$1 vector database hosting (semantic search now trivially embeddable)
- Real-time voice AI with <300ms latency
- EU AI Act enforcement starting (creates compliance obligations and data needs)
- Open weights models that can run on-device (no API calls, offline, private)
- New FDA/CDC data APIs opened post-2024
- Satellite imagery APIs at meter-level resolution, now accessible via REST

**Anti-patterns:**
- "Use LLMs to summarize text" — this was possible and done 2 years ago
- "AI-powered chatbot" — enabler is too generic to produce a non-obvious idea
- Using an enabler that's already been heavily exploited in the target domain

**Derivation chain template:**
```
1. Specific enabler: [name, when it became available — from landscape map, not static list]
2. What it newly makes tractable: [what was previously impossible or impractical]
3. Problem/domain this unlocks: [specific]
4. Why this wasn't built before the enabler: [structural reason]
5. Product that exploits the enabler: [description]
6. Why it breaks without the enabler: [what would fail]
```

---

## CONSTRAINT FLIPPER

**Core mechanism:** Find the hardest constraint or worst limitation in the domain — the thing everyone workarounds, apologizes for, or treats as a necessary evil. Make it the feature. Design a product where the constraint is the core value proposition.

**When to use:** When the domain has a "known limitation" that everyone accepts — a constraint so embedded that nobody asks whether it could be useful.

**Step-by-step process:**
1. From the landscape map, identify the biggest shared limitation of all existing solutions (latency, cost, privacy loss, lock-in, complexity, etc.)
2. Ask: "Who would BENEFIT from this limitation rather than suffer from it?"
3. Design a product that delivers the limitation as a feature — where the limitation is what users pay for
4. The product must be coherent: the limitation must have genuine use value, not just be a consolation

**Examples of good constraint flips:**
- Constraint: "Craigslist's interface is terrible." Flip: "The ugly interface signals trustworthiness — only real buyers bother, not automated scrapers." → Design product that intentionally uses friction as spam prevention
- Constraint: "Peer-to-peer tools are slow and unreliable." Flip: "For certain use cases, the lack of a central server is the security guarantee." → E2E encrypted tooling where the performance limitation IS the privacy proof
- Constraint: "LLMs hallucinate." Flip: "For creative writing assistants, hallucinations are unexpected variations — the wrong answer is a creative suggestion." → LLM-native creative brainstorming that intentionally surfaces hallucinations as hypotheticals
- Constraint: "No internet connection is a problem." Flip: "For certain regulated environments (hospitals, air-gapped systems), no internet is a requirement." → Fully offline tooling where the offline constraint is the compliance feature

**Anti-patterns:**
- "We'll fix the limitation later" — this is not flipping, this is deferring
- Flipping a minor limitation nobody cares about
- Claiming the limitation is a feature without specifying who values it

**Derivation chain template:**
```
1. Shared limitation of all existing solutions: [specific constraint]
2. User who benefits from this limitation: [who and why]
3. How the limitation becomes the value proposition: [mechanism]
4. Product that delivers the limitation as the feature: [description]
5. Why this user can't use existing products: [structural incompatibility]
6. Why this is non-obvious: [what makes the flip surprising]
```

---

## NEGATION STACKER (Level 1+ only)

**Core mechanism:** Take two successful inversions from prior cycles. Stack them: ask what product emerges when BOTH core assumptions are simultaneously wrong. The product must depend on the joint inversion — not just one assumption negated.

**When active:** Level 1 mutation and above. Requires at least one prior INVERTER survivor or FLAGGED idea to work from. If no prior inversions exist, report "NEGATION STACKER UNAVAILABLE: no prior inversions in state."

**Step-by-step process:**
1. From the state file, identify the two most interesting INVERTER results (survivors or FLAGGED ideas)
2. Extract the core assumption each one inverted
3. Ask: what world has BOTH of these assumptions simultaneously negated?
4. In that doubly-inverted world, what product is natural and obvious?
5. This product must be different from either individual inversion — if it's just one inversion with a footnote, the stack didn't produce anything new

**Derivation chain template:**
```
1. Inversion A (from prior cycle): [assumption + its negation]
2. Inversion B (from prior cycle): [assumption + its negation]
3. Joint inversion world: [what world has both negated simultaneously]
4. Product that is natural in this world: [specific description]
5. Why this product is different from either single inversion: [specific]
```

**Fallback if only one prior inversion:** Stack the one inversion with the CONSTRAINT FLIPPER's best constraint-as-feature. "What if the core assumption is wrong AND the biggest limitation is a feature?"

---

## MICRO-NICHER (Level 1+ only)

**Core mechanism:** Take a surviving or FLAGGED idea and shrink its target audience by 10x. Keep the exact mechanism — change only who it's for. The extreme niche often reveals underserved users that the general product cannot economically serve.

**When active:** Level 1 mutation and above. Prefers FLAGGED ideas (they were close but not quite novel enough — micro-niching often resolves the differentiation gap). Falls back to NOVEL survivors if no FLAGGED ideas exist.

**Step-by-step process:**
1. Select the strongest FLAGGED idea from prior cycles (or a NOVEL survivor if no FLAGGED exist)
2. Identify the target user of that idea
3. Find a sub-segment of that user population with an extreme constraint or extreme frequency of the same pain
4. Redesign the product purely for that sub-segment — remove features that don't serve them, add constraints their specific situation requires
5. The micro-niched product should be unusable by the general audience (if it's still useful to everyone, the niche isn't extreme enough)

**Derivation chain template:**
```
1. Source idea: [title + original target user]
2. Original target user segment: [description]
3. Extreme sub-segment: [who within that group has it 10x worse or 10x more frequently]
4. Constraint this sub-segment has that general audience doesn't: [specific]
5. Redesigned product for sub-segment: [what changes, what gets removed, what gets added]
6. Why this product is unusable/wrong for the general audience: [specific incompatibility]
```

---

## When a forcing function is exhausted

A forcing function is exhausted when:
- 2+ consecutive cycles of using it have produced only killed ideas
- The kill reason is always the same (e.g., "INVERTER keeps finding the same inversion")
- The derivation chains are getting shorter and vaguer (sign that the agent is forcing it)

**Signal format:** Report `FORCING FUNCTION EXHAUSTED: {reason}` — do NOT generate a weak idea to fill the slot.

**Coordinator action:** Log the EXHAUSTED signal in the state file under `exhausted_signals`. Track which forcing function and which cycle. This is distinct from a zero-survivor cycle — see LOOP.md for how EXHAUSTED signals interact with mutation escalation.
