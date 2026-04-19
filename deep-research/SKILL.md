---
name: deep-research
description: Use when researching, investigating, or exploring a topic systematically with orthogonal multi-dimensional coverage and source-quality tiers. Trigger phrases include "research this deeply", "deep research on", "investigate this topic thoroughly", "explore this topic", "systematic research", "multi-dimensional research", "comprehensive research", "cover all angles of", "thorough research on", "deep dive into (research)", "exhaustive research". Spawns parallel agents across WHO/WHAT/HOW/WHERE/WHEN/WHY/LIMITS with risk-stratified spot-checking. Bounded by a user-controlled round budget with honest coverage reporting on what was and wasn't covered.
user_invocable: true
argument: The seed topic/question to research deeply
---

# Deep Research Skill

Systematically explore a topic using parallel agents across applicable orthogonal dimensions (WHO/WHAT/HOW/WHERE/WHEN/WHY/LIMITS). Unlike a quick research brief, this skill provides structured multi-dimensional coverage with source quality tiers and risk-stratified spot-checking. Coverage is bounded by a user-controlled round budget; the output honestly characterizes what was covered and what wasn't.

## Execution Model

This skill inherits the four execution-model contracts (files-not-inline, state-before-agent-spawn, structured-output, independence-invariant) from [`_shared/execution-model-contracts.md`](../_shared/execution-model-contracts.md). The shared file is authoritative; the elaborations below are the research-specific applications.

**Subagent watchdog:** every research-direction spawn (Scout, Researcher, Deep Dive) and every verification/summary spawn MUST be armed with a staleness monitor per [`_shared/subagent-watchdog.md`](../_shared/subagent-watchdog.md). This is the skill most vulnerable to silent multi-hour hangs (the 18-hour-silent-death failure mode). Use Flavor A with thresholds `STALE=10 min`, `HUNG=30 min` for Scout; `STALE=15 min`, `HUNG=45 min` for Researcher and Deep Dive (web fetches on slow sources legitimately sit quiet for a while). Never block on `TaskOutput(block=true)` without a watchdog armed against the spawn's output file. Contract inheritance: `timed_out_heartbeat` joins this skill's per-direction termination vocabulary; `stalled_watchdog` / `hung_killed` join `directions.{id}.status`. A watchdog-killed direction never contributes findings to the synthesis — it is reported as coverage-lost in the final report, not silently omitted.

- **Files not inline:** seed, direction definitions, per-direction research outputs, verification inputs, and fact-check evidence all live under `deep-research-{run_id}/`. Seed and coordinator summary are short enough to fit inline but are still written to disk so resume can reconstruct state.
- **State before agent spawn:** each research-direction spawn writes `directions.{id}.status = "in_progress"` and `spawn_time_iso` to `state.json` BEFORE the Agent tool call. Spawn failure records `spawn_failed`; resume re-reads state and replays.
- **Structured output:** research directions emit a per-finding block (claim + source tier + URL + attribution) between `STRUCTURED_OUTPUT_START/END` markers. Unparseable output → the direction is treated as `needs_retry` (fail-safe worst).
- **Independence invariant:** the coordinator orchestrates expansion and gap detection; source-quality tiering and citation spot-checking are delegated to an independent fact-verification agent (see Phase 4). The coordinator never rates source quality itself.

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

**Step 0d — Batched questioning:**
If both 0b (ambiguity) and 0c (under-specification) trigger — or any other clarifying question surfaces in Phase 0 — present ALL of them as a single numbered batch in one message. Never serially. The user answers once, then Phase 1 begins.

**Step 0e — Pre-mortem micro-round (blind-spot seeding):**
Before dimension expansion, spawn 1 Haiku agent with this prompt:
```
Given the seed "{seed}", list 5 concrete ways this research could miss the important insight.
Cover these angles:
 1. Wrong framing — the seed presupposes a conclusion that may be wrong
 2. Adjacent-effort blindness — parallel work that would duplicate or invalidate
 3. Stale assumption — something assumed true that has changed
 4. Baseline blindness — no measurement of what's being "improved"
 5. Strategic-timing blindness — planning window / roadmap / executive memo coincidence
Output to deep-research-premortem.md with one concrete claim per angle.
```
Coordinator reads pre-mortem.md; each flagged blind spot becomes an auto-seeded direction in Phase 1 with `priority=critical`.

---

### Phase 1: Seed Expansion (see DFS.md)

- **Sub-goal extraction (required before dimension expansion):** re-read the seed and identify distinct sub-goals (e.g. "iterate on existing X" + "spin up new Y" = 2 sub-goals; "compare A" + "decide B" + "document C" = 3 sub-goals). Each sub-goal gets **minimum 2 seed-specific directions** allocated during expansion. This prevents the common failure mode where a secondary sub-goal gets absorbed into general infrastructure research and never gets dedicated investigation. Record sub-goals in `state.json` under `seed_subgoals`; per-sub-goal direction coverage is tracked in the coordinator summary.
- Assess which dimensions from WHO/WHAT/HOW/WHERE/WHEN/WHY/LIMITS are applicable using the multi-context table (see DFS.md)
- Generate 2-4 directions per applicable dimension + cross-dimensional directions
- **REQUIRED cross-cutting dimensions** (fire on every run, regardless of seed type — these exist to break anchoring bias and catch structural blind spots):
  - **PRIOR-FAILURE** — "What has been tried in this space and failed? Look for deprecated repos, GRAVEYARD markers, abandoned PRs, killed projects, lessons-learned post-mortems."
  - **BASELINE** — "What is the current state of the thing this would improve? Measure it concretely before solutioning. Cadence, cost, pain points today."
  - **ADJACENT-EFFORTS** — "What parallel/competing work is happening right now? Who else is planning or building in this space? Check active design threads and in-progress PRs."
  - **STRATEGIC-TIMING** — "What planning windows, published roadmaps, or executive memos bear on this? Is there a time-sensitive coordination opportunity?"
  - **ACTUAL-USAGE** — "For any tool/framework/pattern claimed as 'official,' 'standard,' or 'canonical,' verify via independent code search — don't accept docs-only claims about what teams actually do."
  Each cross-cutting dimension gets ≥1 direction at priority=high, in addition to seed-specific directions.
- Maximum: 25 initial directions (cross-cutting dimensions count against this cap)
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
   - **On transient API errors (proxy ZlibError, 429, 503, ECONNRESET, timeout <30s):** auto-retry ONCE with the same prompt before marking `timed_out`. Record `retry_count: 1` in the direction entry. True infrastructure flakes cost one agent-slot to recover; persistent errors still fail to `timed_out` on the retry.
5. Collect ALL new directions from ALL completed agents BEFORE running dedup (see STATE.md)
6. Apply dedup against stable pre-round snapshot
7. Validate direction ID headers in completed findings files (see STATE.md)
8. **Unconsumed Leads Recovery:** scan every completed findings file for a `## Unconsumed Leads` section (required output — see FORMAT.md). Each lead = entity/team/concept/tool mentioned but not independently researched. Apply dedup against explored + frontier. Net-new leads become directions with `priority=high`. This pass fires BEFORE coverage evaluation so recovered leads can drive dimension coverage.
9. Update coordinator summary (see SYNTHESIS.md) — including cross-cutting dimension coverage table
10. Run round-level dimension re-assessment (see DFS.md), including cross-cutting dimensions
11. Increment round

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
2. **Coverage plateau:** No new dimensions for 3 consecutive rounds AND all frontier items have exhaustion ≥ 4 AND **blind-spot check passes** (all 5 cross-cutting dimensions have ≥1 explored direction AND unconsumed-leads count == 0)
3. **Budget soft gate:** `max_rounds` reached with non-empty frontier → prompt user to extend or stop (see DFS.md Step 5)
4. **Frontier actually empties** (possible because direction reporting is optional)

**Blind-spot gate:** condition 2 CANNOT fire if any of PRIOR-FAILURE / BASELINE / ADJACENT-EFFORTS / STRATEGIC-TIMING / ACTUAL-USAGE is uncovered, or if unconsumed-leads count > 0. Dimension coverage alone is necessary but not sufficient for "coverage plateau."

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
10. **Mentioned-but-unexplored is a bug.** Entities/teams/tools named in a finding but not independently researched are unconsumed leads. Every round must drain them.
11. **"Official" claims need code-level verification.** Docs say what's policy; `search/code` says what's actual. For any paved-road / canonical / standard claim, verify adoption in production code before reporting.
12. **Blind-spot dimensions are required, not optional.** PRIOR-FAILURE, BASELINE, ADJACENT-EFFORTS, STRATEGIC-TIMING, ACTUAL-USAGE fire on every run. Coverage plateau cannot be claimed without them.

---

## Anti-Rationalization Counter-Table

The coordinator WILL be tempted to skip steps. These are the talking points it must reject.

| Excuse | Reality |
|---|---|
| "Coverage is good enough — we've hit most dimensions." | No. "Good enough" is the label for the termination check, not a reason to skip it. Run the coverage plateau check and emit the honest number. Under-coverage disclosed is fine; under-coverage hidden is a bug. |
| "This source looks fine — no need to assess its tier." | No. Every source gets a tier classification (primary/secondary/unverified). A blog post is not a primary source because it cites one. Tier drives Evidence Quality — skipping it silently inflates the report's credibility. |
| "A single citation is sufficient for this claim." | No. Single-source claims MUST carry `corroboration: single_source` and MUST be surfaced in the report's Single-Source Claims section. Never promote a single-source claim to "established fact." |
| "The source is recent enough — within a couple of years." | No. For fast-moving topics, `recency_class` is computed from the 12-month threshold, not from vibes. A 2-year-old paper on a fast-moving topic is `stale` and must be flagged. |
| "No need to search for counter-evidence — findings are consistent." | No. Consistency across a coordinator-generated framing is not evidence of truth. Every claim needs `counter_evidence_searched`. "I didn't find any" is a valid answer; "I didn't look" is not. |
| "A primary source confirmed it — we can call it settled." | No. A single primary source is still `single_source`. Independence check requires 2+ sources that do not cite each other and are not from the same publishing entity. One paper is not settled science. |
| "This forum post / personal blog counts as a citation." | No. `unverified` tier sources do NOT count toward corroboration. They may appear in the source table as context, but the claim's `corroboration` field only counts primary + secondary. |
| "Exhaustion threshold met — we're done with this direction." | No. Exhaustion ≥ 4 is one termination trigger, not a license to skip the coverage plateau check or the counter-evidence search. Exhaustion measures what was found, not what was missed. |
| "Honest coverage report can wait — the findings are the main product." | No. The coverage report IS the product. An overclaimed research report is worse than a short one. Termination label + Coverage % + Evidence Quality + single-source count are non-optional. |
| "Just one more round will close the gap." | No. The budget soft gate exists because "one more round" is how runs spiral. If the user wants more, they extend. The coordinator does not self-extend. |
| "The second agent repeated the first — that's corroboration." | No. Two agents reading the same sources is not independent corroboration. Independence is a source-level property, not an agent-level property. |
| "Counter-evidence was weak, so I didn't cite it." | No. Disconfirming evidence that was found MUST be cited inline with the claim and the field set to `yes_disconfirming_evidence_present`. Omitting it is selection bias dressed up as editorial judgment. |
| "I'll merge stale-source claims into the main text — flagging them is clutter." | No. Stale sources get counted and surfaced in the final report. The reader cannot assess freshness if the coordinator launders the date. |
| "The seed framing is obviously correct — I don't need a pre-mortem." | No. The most expensive research failures are framing errors. The Phase 0e pre-mortem costs ~agent.10 and catches the wrong-framing category before direction expansion. Skip it and you anchor the entire run on an unchecked premise. |
| "Entity X came up briefly but isn't worth a direction." | No. If it was named in a finding, it's a lead. Either dedupe it against explored directions (and record the dedupe decision) or spawn a direction. Silent skipping is how critical parallel efforts, adjacent teams, and competing tools routinely disappear from final reports. |
| "Docs say X is official — no need to verify with code." | No. ACTUAL-USAGE requires `search/code` (or equivalent) whenever the domain supports it. "Official" is about policy; code is about reality. Policy-only claims must carry `corroboration: single_source` and note "adoption unverified." |
| "Cross-cutting dimensions are optional for simple topics." | No. They exist to catch what the seed framing obscures. "Simple" topics are where the most framing errors hide — a narrow seed + skipped cross-cutting dimensions = confidently wrong report. |

When the coordinator finds itself about to reach for any of these excuses: it stops, updates the structured field, and proceeds the right way. The extra structure is the cost of honest output.

---

## Self-Review Checklist

- [ ] State file is valid JSON after every round
- [ ] No direction has status "in_progress" after round completes
- [ ] Every findings file has: Findings + Claims Register + Source Table + Mini-Synthesis + New Directions (or "terminal node") + Exhaustion Assessment
- [ ] Every claim in every Claims Register has `corroboration`, `counter_evidence_searched`, and `recency_class` set (no nulls, no defaults)
- [ ] No direction explored > 2 times
- [ ] Prospective gate was shown before each round (or `--auto` was set)
- [ ] Coordinator summary updated each round (structured format, not freeform)
- [ ] Fact verification ran before final synthesis
- [ ] Final report includes Spot-Check Sample Results section with explicit limitations
- [ ] Final report includes Single-Source Claims section (every `single_source` claim listed and tagged `[SINGLE_SOURCE_CAVEAT]` inline)
- [ ] Final report includes Skipped Counter-Evidence Searches section (every `no_search_skipped` claim listed)
- [ ] Final report includes Stale-Source Claims section (every `stale` / `undated` claim listed with threshold noted)
- [ ] Final report uses termination label (User-stopped / Coverage plateau / Budget limit / Convergence)
- [ ] Two separate confidence scores in report (Coverage % + Evidence Quality)
- [ ] Topic velocity recorded in state and surfaced in final report header
- [ ] Model tier was correctly selected for each agent
- [ ] Phase 0e pre-mortem ran before Phase 1 expansion; pre-mortem.md flags seeded as critical directions
- [ ] All 5 cross-cutting dimensions (PRIOR-FAILURE, BASELINE, ADJACENT-EFFORTS, STRATEGIC-TIMING, ACTUAL-USAGE) have ≥1 explored direction at termination
- [ ] Every findings file has a `## Unconsumed Leads` section (may be "None — ...")
- [ ] Unconsumed Leads Recovery ran after each round (leads scanned, deduped, net-new leads added to frontier)
- [ ] "Coverage plateau" termination blocked unless blind-spot gate passes (cross-cutting dims + zero unconsumed leads)
- [ ] Final report includes Cross-Cutting Dimension Coverage table
- [ ] For every "official/standard/canonical" claim, the findings file notes whether code-level usage was verified

---

## Agent Prompt Template

When spawning each research agent:

```
You are a research agent. Your task is to thoroughly research ONE specific direction. Think carefully and step-by-step — source quality assessment, counter-evidence searching, and Claims Register classification are load-bearing decisions that drive the final report's credibility. This is harder than it looks; do not rush.

**Your research question:** {direction.question}
**Dimension:** {direction.dimension}
**Depth:** {direction.depth} | **Priority:** {direction.priority}
**Topic velocity:** {topic_velocity}   (recency threshold: {recency_threshold_months} months; sources older than this are `stale`)

**Coverage fingerprint (dedup only — do NOT let this anchor your findings):**
Already-explored directions: {list of explored direction titles}
These are listed so you avoid repeating them — NOT to constrain your conclusions.

**What we've found so far (research context):**
{coordinator_findings_summary}
Dominant framing so far: {dominant_framing}
⚠️ If your research points in a different direction, follow it. Do not assume the dominant framing is correct.

**Instructions:**
1. Use WebSearch to find papers, articles, docs, and discussions on this topic
   - **When to search vs rely on training data:** WebSearch is REQUIRED for any factual claim that lands in your Claims Register — recency matters, training data is stale, and every claim needs an inline source URL (Source Table requirement). Training-data-only knowledge is acceptable ONLY for definitional/foundational context that frames or scopes the search (e.g. "what is X" before searching "X 2025 latest developments"). Findings that lack a fetched source are rejected at synthesis — do not report them.
   - **Search budget hygiene:** plan each search before firing. Each WebSearch costs against your tier budget; counter-evidence searches share that budget, so redundant or speculative searches push you out of budget before counter-evidence checks. If a search returns nothing useful, refine before re-firing — don't burn the budget on rephrasings.
2. Go deep — follow references, check citations, look for contradictions
3. Assess source quality for EACH source (primary / secondary / unverified) — see definitions below
4. Record each source's publication date AND publishing entity — needed for the independence and recency checks
5. For every load-bearing factual claim: run a counter-evidence search. Record the outcome as `yes_none_found`, `yes_disconfirming_evidence_present` (cite the disconfirming source inline), or `no_search_skipped` (only for definitional claims)
6. Write your findings to: {findings_path}
7. Use the FORMAT specified: Findings, Claims Register, Source Table, Mini-Synthesis, New Directions, Exhaustion Assessment
8. Every claim row in the Claims Register needs:
   - `corroboration`: `single_source` | `two_independent_sources` | `three_or_more_independent_sources` (sources independent iff they don't cite each other AND aren't from the same publishing entity; unverified-tier sources don't count)
   - `counter_evidence_searched`: one of the three values above
   - `recency_class`: `fresh` | `stale` | `undated` (freshest source wins for the claim)
9. Every claim in text needs an inline source URL
10. New directions are OPTIONAL — if this is a terminal node, write "None — terminal node."
11. Do NOT report new directions that are paraphrases of already-explored topics
12. **Unconsumed Leads (required — do NOT skip):** scan your findings for every named entity (team, tool, repo, person, framework, project) that you mentioned but did NOT independently research. Report them in a `## Unconsumed Leads` section with one line each: `- <entity>: <why it's worth researching>`. If genuinely none: write "None — all referenced entities were core to this direction's scope." The coordinator uses this section to drain missed leads across rounds.
13. **"Official" claims require code-level verification:** for any claim that something is "official," "standard," "canonical," "paved road," or "the way X is done at <org>," run at least one code search (e.g. `search/code` or equivalent) to verify ACTUAL adoption in production code. If you can only find docs but no code, mark the claim `corroboration: single_source` and note "policy-only, adoption unverified" in the Claims Register.
14. **Restricted-access document handling:** when you encounter a source behind auth (Google Docs, Confluence, Notion, internal wikis, paywalls, Slack threads), try the domain-appropriate authenticated tool first in this order: (a) domain-specific MCP tool if one is available for this source type (e.g. `mcp__google-docs`, `mcp__jira`, `mcp__slack`), (b) internal search/gh API, (c) WebFetch as last resort. If NONE work, do NOT silently drop the source — record it in `## Unconsumed Leads` with status `access_blocked` and a one-line note describing (i) what the document is expected to contain based on context, (ii) which tool would resolve it. Never fabricate content from a document you could not access. The coordinator uses `access_blocked` leads to surface a "Known blind spots" section in the final report.

**Source quality tiers:**
- `primary`: peer-reviewed research, official documentation, primary data — note specific evidence
- `secondary`: credible journalism, institutional reports (expert blogs require explicit credentials to qualify)
- `unverified`: forums, personal blogs, social media, paywalled sources (you can't read it = can't verify it)

**Search budget:** {8 searches for Haiku/Scout tier | 15 searches for Sonnet/Researcher tier}
(Counter-evidence searches count against the budget — plan accordingly.)
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
