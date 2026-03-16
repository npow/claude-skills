---
name: deep-research
description: Systematic multi-dimensional research on any topic using parallel agents with orthogonal dimension coverage, source quality tiers, and spot-checked verification
user_invocable: true
argument: The seed topic/question to research deeply
---

# Deep Research Skill

Systematically explore a topic using parallel agents across applicable orthogonal dimensions (WHO/WHAT/HOW/WHERE/WHEN/WHY/LIMITS). Unlike a quick research brief, this skill provides structured multi-dimensional coverage with source quality tiers and risk-stratified spot-checking. Coverage is bounded by a user-controlled round budget; the output honestly characterizes what was covered and what wasn't.

## Model Tier Strategy

Three tiers balance cost and quality. The coordinator (main session) always handles synthesis and gap detection — never delegated.

| Tier | Model | subagent_type | Used for | Est. cost/agent |
|------|-------|---------------|----------|-----------------|
| Scout | `haiku` | general-purpose + `model: "haiku"` | depth ≥ 2, priority=low, low-stakes verification directions | ~$0.05 |
| Researcher | `sonnet` | general-purpose + `model: "sonnet"` | depth 0–1, priority=high/medium, all seed directions | ~$0.30–0.60 |
| Deep Dive | `opus` | general-purpose + `model: "opus"` | ONLY for re-exploration (duplication=2) of directions with exhaustion_score ≤ 2 | ~$3–5 |

**Tier selection rules (applied at spawn time):**
```
if direction.depth == 0:                              → Researcher (sonnet)
elif direction.depth == 1 and priority == "high":     → Researcher (sonnet)
elif direction.depth == 1 and priority == "medium":   → Scout (haiku)
elif direction.depth >= 2:                            → Scout (haiku)
elif re_exploration and exhaustion_score <= 2:        → Deep Dive (opus)
else:                                                 → Scout (haiku)
```

**Expected cost for a full run:** ~$15–25 (vs ~$170 with all-Opus).

---

## Workflow

### Phase 0: Seed Validation (before anything else)

**Step 0a — Safety check:**
- Screen seed for harmful/illegal research requests
- If harmful: refuse immediately, do not expand

**Step 0b — Ambiguity check:**
- Does this seed have multiple plausible interpretations?
- If ambiguous: "I'm interpreting this as [X]. Alternatives: [Y, Z]. Proceed with X? [y/N/pick:Z]"
- User must confirm before any directions are generated

**Step 0c — Input validation:**
- If seed is not a researchable topic (single number, single proper noun without context): "Please provide more context: what aspect of [X] do you want researched?"

---

### Phase 1: Seed Expansion (see DFS.md)

- Assess which dimensions from WHO/WHAT/HOW/WHERE/WHEN/WHY/LIMITS are applicable using the multi-context table (see DFS.md)
- Generate 2-4 directions per applicable dimension + cross-dimensional directions
- Maximum: 25 initial directions
- Minimum dimension rule:
  - 0 applicable → error; prompt user to clarify
  - 1-2 applicable → warn user; ask if they want to continue
  - 3+ applicable → proceed normally

**Pre-run scope declaration (show before proceeding):**
```
Deep research: "{seed}"
Interpretation: [one-sentence interpretation]
Applicable dimensions ({N}): {list only applicable ones}
Initial directions: {count}
Estimated rounds needed: {low}–{high}
Suggested max_rounds: {recommendation with rationale}
Wall-clock estimate: {time range}

Set max_rounds [default {recommendation}]: _
Continue? [y/N]
```
User sets max_rounds explicitly — no hardcoded default.

**max_rounds recommendation formula:**
```
initial_directions = count of directions in Phase 1
min_rounds_to_cover_seed = ceil(initial_directions / 6)   # 6 agents/round
depth_multiplier = 1.5  # expect ~50% expansion from agent-discovered sub-directions
recommended = ceil(min_rounds_to_cover_seed * depth_multiplier)
recommended = max(recommended, 8)  # never suggest < 8 rounds
```
Example: 20 initial directions → ceil(20/6)=4 × 1.5=6 → recommend 8.
Example: 30 initial directions → ceil(30/6)=5 × 1.5=7.5 → recommend 8.

Note: `max_rounds` is a **soft gate** — the skill will prompt to extend when reached with non-empty frontier. Set conservatively; you can always extend.

---

### Phase 2: Initialize State

- Create `deep-research-state.json` in CWD (see STATE.md for schema)
- Create `deep-research-findings/` directory
- Write lock file: `deep-research-{run_id}.lock`
- Print: "Starting deep research on: {seed} [run: {run_id}]"

---

### Phase 3: Research Rounds (see DFS.md)

**Before spawning each round — prospective gate:**
```
About to run Round {N}: {frontier_size} directions queued
Estimated tokens this round: ~{estimate} ({cost_estimate})
Total spent so far: ~{running_total}
Continue? [y/N/redirect:<focus>]
```
This fires BEFORE agents are spawned. User can prevent spend, not just observe it.
(Skip with `--auto` flag for autonomous runs.)

**Per round:**
1. Pop up to `max_agents_per_round` (6) highest-priority directions from frontier
2. Select model tier for each direction
3. Spawn agents in parallel with 8-minute timeout (see agent prompt template below)
4. On timeout: mark `timed_out`, DO NOT re-queue, DO NOT increment dedup counter
5. Collect ALL new directions from ALL completed agents BEFORE running dedup (see STATE.md)
6. Apply dedup against stable pre-round snapshot
7. Validate direction ID headers in completed findings files (see STATE.md)
8. Update coordinator summary (see SYNTHESIS.md)
9. Run round-level dimension re-assessment (see DFS.md)
10. Increment round

---

### Phase 4: Fact Verification (after final research round, before synthesis)

A dedicated verification pass runs before the final synthesis. See SYNTHESIS.md for full details.

**Step 4a — Claim extraction:**
- Extract the N most significant factual claims (N = min(20, total claims))
- Risk-stratified sampling priority: single-source primary → numerical/statistical → contested → corroboration candidates

**Step 4b — Citation spot-check:**
- Fetch each sampled URL; check (a) accessible, (b) attributed claim is stated in source text
- For numerical claims: compare EXACT numbers. Do NOT accept semantic similarity.
- Paywalled → "unverifiable — full text inaccessible"
- Accessible but claim not found → "citation mismatch — flag for manual verification"

**Step 4c — Corroboration independence check:**
- For claims cited by 3+ agents: verify sources are genuinely independent (different org, date, methodology)

---

### Phase 5: Synthesize (see SYNTHESIS.md)

**Pass 1 — Mini-syntheses** are written by each agent in their findings file (required).

**Pass 2 — Theme extraction:**
- Coordinator reads mini-syntheses only (not raw findings)
- A theme is valid ONLY if it requires findings from 2+ distinct dimensions
- Identifies meta-patterns, fundamental tradeoffs, consensus, genuine contradictions

**Pass 3 — Final report:** Write `deep-research-report.md` (see FORMAT.md)

**Pass 4 — QA pass (automatic offer):**
After writing `deep-research-report.md`:

```
QA pass available. Run deep-qa on this report? [y/N]
(Recommended: audits citation accuracy, logical consistency, coverage gaps,
and counter-evidence gaps that the research pass may not have self-checked.)
```

- If **y**: invoke deep-qa with `--type research` on `deep-research-report.md`
  - QA run_id: `{parent_run_id}-qa`
  - QA report written alongside: `deep-research-{run_id}-qa-report.md`
  - Fact verification in deep-qa complements (does not replace) the spot-check in Phase 4
- If **n**: skip. Final output remains `deep-research-report.md` alone.

---

### Phase 6: Termination Check (see DFS.md)

Terminate when ANY of these is true (any-of-4, not all-of-4):
1. **User chooses N at a round gate** (explicit user decision)
2. **Coverage plateau:** No new dimensions for 3 consecutive rounds AND all frontier items have exhaustion ≥ 4
3. **Budget soft gate:** `max_rounds` reached with non-empty frontier → prompt user to extend or stop (see DFS.md Step 5)
4. **Frontier actually empties** (possible because direction reporting is optional)

`max_rounds` is a **soft gate** — it prompts the user, it does not auto-terminate. Only `--auto` makes it a hard stop. Absolute hard ceiling is `max_rounds * 3`.

---

## Golden Rules

1. **Never spawn an agent without checking the state file first.** Dedup every direction.
2. **Direction reporting is optional.** Terminal node is valid output — do NOT force agents to invent directions.
3. **Frontier is priority-ordered.** Always pop highest-priority first. Children get +2 depth bonus.
4. **Two explorations max per direction.** Third+ is skipped.
5. **Prospective gate fires before spend.** Never spawn agents without showing the user cost estimate first (unless `--auto`).
6. **Coordinator context is bounded.** Never accumulate raw findings — use the structured coordinator summary.
7. **Every finding needs a source.** Web search URLs required. No training-data-only findings.
8. **Always specify model tier explicitly.** Never let agents default — cost spirals come from unintentional Opus usage.
9. **Verify numerics manually.** Flag all numerical claims in the spot-check; LLM number verification is unreliable.

---

## Self-Review Checklist

- [ ] State file is valid JSON after every round
- [ ] No direction has status "in_progress" after round completes
- [ ] Every findings file has: Findings + Source Table + Mini-Synthesis + New Directions (or "terminal node") + Exhaustion Assessment
- [ ] No direction explored > 2 times
- [ ] Prospective gate was shown before each round (or `--auto` was set)
- [ ] Coordinator summary updated each round (structured format, not freeform)
- [ ] Fact verification ran before final synthesis
- [ ] Final report includes Spot-Check Sample Results section with explicit limitations
- [ ] Final report uses termination label (User-stopped / Coverage plateau / Budget limit / Convergence)
- [ ] Two separate confidence scores in report (Coverage % + Evidence Quality)
- [ ] Model tier was correctly selected for each agent

---

## Agent Prompt Template

When spawning each research agent:

```
You are a research agent. Your task is to thoroughly research ONE specific direction.

**Your research question:** {direction.question}
**Dimension:** {direction.dimension}
**Depth:** {direction.depth} | **Priority:** {direction.priority}

**Coverage fingerprint (dedup only — do NOT let this anchor your findings):**
Already-explored directions: {list of explored direction titles}
These are listed so you avoid repeating them — NOT to constrain your conclusions.

**What we've found so far (research context):**
{coordinator_findings_summary}
Dominant framing so far: {dominant_framing}
⚠️ If your research points in a different direction, follow it. Do not assume the dominant framing is correct.

**Instructions:**
1. Use WebSearch to find papers, articles, docs, and discussions on this topic
2. Go deep — follow references, check citations, look for contradictions
3. Assess source quality for EACH source (primary / secondary / unverified) — see definitions below
4. Write your findings to: {findings_path}
5. Use the FORMAT specified: Findings, Source Table, Mini-Synthesis, New Directions, Exhaustion Assessment
6. Every claim needs a source URL
7. New directions are OPTIONAL — if this is a terminal node, write "None — terminal node."
8. Do NOT report new directions that are paraphrases of already-explored topics

**Source quality tiers:**
- `primary`: peer-reviewed research, official documentation, primary data — note specific evidence
- `secondary`: credible journalism, institutional reports (expert blogs require explicit credentials to qualify)
- `unverified`: forums, personal blogs, social media, paywalled sources (you can't read it = can't verify it)

**Search budget:** {8 searches for Haiku/Scout tier | 15 searches for Sonnet/Researcher tier}
```

---

## Two-Phase Deep Dive (optional, for low-exhaustion directions)

When a direction returns exhaustion_score ≤ 2:
1. **Scout pass** (Haiku, 5 searches): Identify 3-5 most relevant papers, return as short list
2. **Researcher pass** (Sonnet, 10 searches): Deep dive using scout's list as starting context

Costs ~$0.35 total vs $3-5 for Opus re-exploration.
Trigger: `exhaustion_score <= 2 AND duplication[direction] < 2`

---

## `--auto` Flag

When `--auto` is passed:
- All prospective round gates are skipped
- Runs to max_rounds
- ⚠️ No cost circuit breaker — set an appropriate max_rounds before starting
