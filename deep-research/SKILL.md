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

**Step 0f — Language Locus Detection (v4 — before adapter selection):**

Coordinator spawns 1 Haiku agent with this prompt:
```
Given the seed topic "{seed}", identify the 1–4 languages in which the AUTHORITATIVE primary literature on this topic is published. Consider:
- Academic: where does the leading research happen?
- Industry: where are the commercial leaders headquartered?
- Policy/legal: which jurisdictions write primary law on this?
- Community: where do practitioners discuss in their native language?
Output STRICT JSON:
{
  "authoritative_languages": ["en", "zh", "ja"],           // ISO 639-1
  "rationale_per_language": {"zh": "AI chip industry dominated by Chinese fabs"},
  "coverage_expectation": "en_dominant" | "bilingual" | "multilingual_required",
  "confidence": "high" | "medium" | "low"
}
Never output only ["en"] without justification — default en-only is a red flag, not a default answer.
```
Coordinator writes result to `state.json → language_locus`. If `coverage_expectation != "en_dominant"` OR `len(authoritative_languages) ≥ 2` OR `confidence: low` → cross-lingual retrieval fires in Phase 3.3. The Phase 1 pre-run scope declaration warns user: "This topic appears to span {N} languages ({list}); enable cross-lingual retrieval (adds ~$0.15/run)? [Y/n]".

**`--auto` default:** under `--auto`, cross-lingual retrieval is enabled automatically IF `coverage_expectation == "multilingual_required"` (explicit locus signal), skipped otherwise. This is the ONE Phase 0 gate `--auto` respects — skipping it silently would hide the language-gap caveat from autonomous runs. The decision + rationale is logged to `state.json → auto_decisions`.

**Translation validation (v4.1):** Every LLM-translated query is round-trip verified before firing. Haiku agent translates `query_en → query_xx`, then independently back-translates `query_xx → query_en_verify`. If semantic similarity between `query_en` and `query_en_verify` falls below a coarse-match threshold (shared keyword count ≥ 60% of original content words, excluding stopwords), the translation is marked `translation_failed: true` in `xlang_queries/{lang}.json` and that language's adapter round is skipped for this query. Three failed translations in the same language within a run auto-disable cross-lingual retrieval for that language and emit `COVERAGE_CAVEAT_TRANSLATION_UNRELIABLE: {lang}`. Prevents garbage queries entering adapters and laundering translation errors into coordinator confidence.

**Step 0g — Novelty Detection (v5 — cold-start gate):**

Index-based retrieval assumes agents have enough topic vocabulary to generate effective queries. For novel / cold-start topics, this assumption breaks: an agent that doesn't know canonical terms searches for adjacent-but-wrong concepts and reports confidently-empty findings. v5 detects this up front.

Coordinator spawns 1 Haiku agent with this prompt:
```
Topic: "{seed}"
Task: list up to 5 specific sources you recognize from memory — paper titles + authors, repo names + orgs, book titles + authors, or canonical blog post titles + authors. Include approximate year. Do NOT WebSearch. Do NOT fabricate.
Output STRICT JSON:
{
  "recalled_sources": [{"title": "...", "authors_or_org": "...", "year": 2022, "confidence": "high|medium|low"}, ...],
  "topic_novelty": "familiar" | "emerging" | "novel" | "cold_start",
  "rationale": "...",
  "known_canonical_terms": ["term1", "term2", ...]
}
Classification:
- familiar = 5+ high/medium-confidence sources with specific years
- emerging = 2-4 sources, mostly recent, some uncertainty
- novel = only vague patterns, 0-1 specific sources
- cold_start = topic unrecognized → return empty recalled_sources: []
```
**External source verification (v5.1 — NEW, the gate that makes v5 reliable):**

LLM self-report of novelty is unreliable — models confabulate plausible-sounding sources and return `familiar` when they should return `novel`. Coordinator performs external verification BEFORE accepting the classification:

1. For each `recalled_sources` entry with `confidence in {high, medium}` (skip `low`), fire 1 WebSearch query: `"{title}" {authors_or_org}`. Limit: 5 queries total (budget: ~$0.05 Haiku tier).
2. Count verification outcomes:
   - `verified`: WebSearch returns ≥1 result whose title is a clear match (shared-keyword overlap ≥ 60% AND author/org appears in result snippet OR URL)
   - `unverified`: no clear match (title drift, wrong author, no results)
3. **Override rule (coordinator, not agent):**
   - `verified_count ≥ 3 of ≤5 recalled` → accept self-report classification
   - `verified_count == 2` → downgrade one tier (familiar→emerging, emerging→novel); log `classification_overridden: partial_fabrication`
   - `verified_count ≤ 1` OR `recalled_sources` was empty AND self-report was `familiar/emerging` → **force classify `cold_start`** regardless of self-report; log `classification_overridden: source_verification_failed, original_claim: {self_report}`
4. Record both `self_report_novelty` and `verified_novelty` in `state.json → topic_novelty`. Subsequent phases use `verified_novelty`.
5. Emit per-source verification record to `state.json → source_verification_log` — required for audit trail.

**This turns Phase 0g from a self-report coin-flip into an externally-grounded gate.** A model that confabulates 5 plausible-sounding papers on a fabricated topic will see 0-1 verify, auto-reclassify `cold_start`, and correctly trigger Vocabulary Bootstrap. Cost: 5 WebSearch calls per run (~$0.05), negligible relative to the full-run cost.

Coordinator writes `verified_novelty` to `state.json → topic_novelty`. If `verified_novelty in {novel, cold_start}` → **Vocabulary Bootstrap mode activates** (Phase 2.5 below). If `cold_start` → Phase 1 dimension expansion is **deferred** until after bootstrap — cross-cutting dimensions like PRIOR-FAILURE / ACTUAL-USAGE are meaningless without topic vocabulary.

**Phase ordering (v5.1 fix):** Phase 0e (pre-mortem) ALWAYS runs AFTER Phase 2.5 (vocabulary bootstrap) when bootstrap fires. Pre-mortem on a cold-start topic without vocabulary produces generic platitudes; running it post-bootstrap lets it reason with discovered canonical terms.

**`--auto` default:** `novel` topics auto-proceed to bootstrap. `cold_start` under `--auto` emits `COVERAGE_CAVEAT_COLD_START_AUTONOMOUS` tagging the run for user review. The source-verification step fires unconditionally (including under `--auto`) — it is non-skippable because it prevents the silent-success failure mode.

**Interaction with sparse-topic mode (v5.1 specified):** `cold_start` classification short-circuits `sparse_topic_mode` Round-1 detection for this run — the coordinator knows the topic is sparse before Round 1 fires, skips the Round-1 yield check, applies sparse-topic budget adjustments from Round 1 onward, and tags `COVERAGE_CAVEAT_COLD_START` (not `COVERAGE_CAVEAT_SPARSE_TOPIC`) in the final report. Prevents the two modes from triggering the same budget-cut logic twice.

**Vocabulary-grounding enforcement (v5.1 — made real):** The `vocabulary_grounding` field on claims is validated externally, not self-reported. For any claim labeled `bootstrapped` or `discovered_mid_run`, coordinator runs a `grep -i "{term}"` check against `vocabulary_bootstrap.json` (for `bootstrapped`) or against round findings files (for `discovered_mid_run`). Mismatched labels → auto-relabeled `fabricated` and rejected at synthesis. The agent cannot self-launder confabulations.

### Phase 2.5 — Vocabulary Bootstrap + Browse-as-Retrieval (v5, conditional)

**Activates when:** `state.topic_novelty in {novel, cold_start}`. Runs between Phase 2 (Initialize State) and Phase 3 (Research Rounds).

**Step A — Vocabulary Bootstrap (1 Haiku agent):**
```
Topic: "{seed}"
Goal: build a domain vocabulary before research starts.
Steps:
1. WebFetch `https://en.wikipedia.org/w/api.php?action=opensearch&search={url-encoded topic}&limit=5&format=json`
2. For each top-3 candidate article: WebFetch `https://en.wikipedia.org/wiki/{title}`
3. Extract per article:
   - Bolded terms in lead paragraph (aliases, variant spellings)
   - All H2/H3 section headings
   - First sentence of each section
   - "See also" entries
   - Page-bottom categories
4. Deduplicate to `vocabulary_bootstrap.json`:
   {
     "canonical_terms": [...],
     "aliases": {"canonical": ["variant1", ...]},
     "subtopics": [...],
     "adjacent_topics": [...],
     "categories": [...],
     "seed_urls_discovered": [...]
   }
Budget: 4 WebFetch max.
```
Vocabulary is handed to every subsequent research agent as `{vocabulary_path}` in their prompt: "Use canonical_terms + aliases in your queries — these are domain-insider names you didn't know."

**Wikipedia-zero-match fallback:** If no article matches, fallback to `https://en.wikipedia.org/wiki/Special:Search?search={topic}` HTML-scrape for related articles, AND flag `topic_novelty: verified_cold_start_no_wikipedia` — coordinator lowers expectations (max 2 rounds, `COVERAGE_CAVEAT_NO_WIKIPEDIA_SEED`) and proceeds with very limited breadth promises.

**Step B — Browse-as-Retrieval primitive (v5 — new orthogonal retrieval path):**
One dedicated agent per round for novel topics (Researcher tier) / emerging (Scout tier). Does NOT query indexes. Navigates like a researcher following citations/links.
```
Start at {seed_url} (from seed_urls_discovered, Wikipedia article preferred).
Navigate outbound body-text links (skip nav/footer/sidebar):
- Max 3 hops deep (seed = hop 0)
- Per page: WebFetch, extract body-text outbound links, pick 2-3 highest-signal (links anchored to subject-matter phrases, skip generic nav terms)
- Record every URL with hop_distance + anchor_text
- Never revisit a URL
- Stop when: budget exhausted (15 WebFetch max), 3 hops reached on all branches, or only nav links remain
Output: browse-retrieval.md with Source Table — every row tagged retrieval_path: browse_follow, hop_distance: N, anchor_text: "...".
PRIMARY output is URL+metadata set. Interesting claims encountered may be reported but aren't mandatory.
```
Yield is added to the Adapter Pool. Browse-found URLs are deduped against already-cited. **This is the first mechanism in the skill that emulates serendipitous discovery** — it finds sources the agent couldn't have queried for because it didn't know they existed.

**Step C — Vocabulary-grounding in Claims Register (v5):**
For novel-topic runs, every claim row adds field:
- `vocabulary_grounding`: `bootstrapped` (uses term from `vocabulary_bootstrap.json`) | `discovered_mid_run` (term surfaced in a finding) | `fabricated` (term not verified in any source). `fabricated` → claim rejected at synthesis.

**Cost impact:** Bootstrap adds 1 Haiku + ~4 WebFetch = ~$0.05. Browse-retrieval adds 1 agent/round at Sonnet tier + 15 WebFetch = ~$0.50/round when active. Only fires for novel/cold-start topics (typically <20% of runs). Expected additional cost: $0.05–$1.00 depending on novelty.

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

## Breadth Expansion Module

Inserts between Phase 3 (Research Rounds) and Phase 5 (Synthesis). Closes the retrieval-breadth gap with Claude-Research-style web products via observable, loudly-failing mechanisms — not infeasible ones.

### Phase 3.5 — Per-round Breadth Observability (runs after each round's dedup + unconsumed-leads sweep)

1. **URL-level dedup metric.** Coordinator reads every findings file's Source Table, aggregates `unique_urls_seen` across agents vs `total_searches_fired`. Computes:
   - `url_redundancy_ratio = (total_searches − unique_urls) / total_searches`
   - `unique_domains_this_round = distinct registrable-domain count`
   - `domain_entropy = Shannon entropy over domain counts` (computed as coordinator-state-level single-pass counter; no embeddings required)
   Writes these to `state.json → breadth_metrics[round_N]`.

2. **Rolling domain blocklist maintenance (with narrow-domain protection).** Coordinator tracks per-domain citation counts. Adds a domain to `blocked_domains` ONLY if:
   - It is in the top 5 by citation count this round, AND
   - It contributes `< 30%` of total citations across the full run-to-date (prevents blocklisting the only useful source in narrow-domain topics like arxiv-heavy academic, vendor-specific engineering, or single-standard-body policy), AND
   - It is not the sole source for any single-source claim
   Cap the list at 10 entries. Agents pass it via WebSearch's `blocked_domains` parameter. If no domain qualifies for blocklisting this round, that's a valid signal — record `blocklist_skipped: narrow_domain_regime` in `breadth_metrics` and proceed without domain diversity forcing.

3. **Sparse-topic auto-mode (trigger: after Round 1 only).** If Round 1 returns `unique_domains < 10 OR mean(directory_yield) == 0 across all agents`:
   - Set `sparse_topic_mode: true` in state.json
   - Disable directory-first step for subsequent rounds (already yielding nothing)
   - Halve the per-agent search budget allocation for counter-evidence (redirect to depth-first)
   - Tag the final report with `COVERAGE_CAVEAT_SPARSE_TOPIC`
   - Notify user at next round gate: "Sparse-web topic detected (N unique domains, D directories yielded 0). Continue with reduced breadth expectations? [y/N]"
   Sparse-topic mode is NEVER silently activated.

4. **Retrieval-path yield table (built per-round, surfaced in final report).** Coordinator aggregates per-source `retrieval_path` tags into a yield-per-path table:
   ```
   | path                | sources_found | unique_domains | yield_per_search |
   | directory           | 12            | 8              | 0.67             |
   | websearch           | 34            | 19             | 0.56             |
   | websearch+operator  | 9             | 7              | 0.78             |
   | citation-follow     | 6             | 5              | 0.83             |
   ```
   Low-yield paths in a given run are candidates for budget cut in next round.

### Phase 5 Pass 5 — Breadth Auditor (runs after synthesis, before final report)

Independent Haiku agent. Spawned with ONLY the aggregated Source Table and breadth_metrics — not the report text. Objective: attack the breadth claim.

**Inputs:**
- All Source Tables concatenated (URL + retrieval_path + publishing_entity + date)
- `state.json → breadth_metrics`

**Produces:**
```
BREADTH_VERDICT_START
unique_domains: N
unique_publishing_entities: M    (registrable-entity count, not domain — e.g. `*.blogspot.com` → single entity)
domain_entropy: E
temporal_range: {oldest_date} to {newest_date}
citation_cascade_risk: {none | weak | strong}
    (strong = ≥30% of "independent" sources trace to ≤3 original studies/authors)
unexplored_retrieval_paths: [list of paths with 0 sources]
languages_represented: {"en": N_en, "zh": N_zh, "ja": N_ja, ...}    (v4 — count per source_language)
missing_authoritative_languages: [list]    (v4 — intersection of state.language_locus.authoritative_languages minus languages_represented; empty if fully covered)
coverage_caveat_recommended: {none | sparse_topic | english_only | single_engine_monoculture | language_gap}
BREADTH_VERDICT_END
```

Coordinator reads ONLY the structured block; unparseable → fail-safe "citation_cascade_risk: strong, coverage_caveat_recommended: verify_manually." On timeout (>3min) or spawn failure → record `breadth_audit: unavailable` in final report header + preserve all v0 termination labels unchanged. Never block final report on auditor failure — the auditor is a quality gate, not a critical path.

**Termination gate (auditor has teeth):**
- If `citation_cascade_risk: strong` AND `unique_publishing_entities < 5` AND round budget remains → **block termination**. Inject ONE additional round targeted at cluster outliers: coordinator reads the dominant cluster's shared citations, generates 3–5 directions explicitly targeting outsiders/critics/alternative-authors of those sources, spawns them. This is the ONLY mechanism in the skill that reverses a termination decision. After the extra round, re-run the auditor; if cascade risk still strong, terminate anyway but tag the final report `COVERAGE_CAVEAT_CITATION_CASCADE_UNRESOLVED`.
- **v4 — Language gap gate:** If `missing_authoritative_languages` is non-empty AND round budget remains AND `state.language_locus.coverage_expectation != "en_dominant"` → **block termination**. Inject ONE additional round in cross-lingual mode targeting the missing languages: coordinator translates the top 5 outstanding directions into each missing language via LLM (writing translations to `xlang_queries/{lang}.json`), invokes language-specific adapter variants (see Cross-Lingual Adapter section), spawns research agents constrained to `source_language in {missing_languages}`. After the extra round, re-run the auditor; if gap persists, terminate but tag the final report `COVERAGE_CAVEAT_LANGUAGE_GAP: {list}`.
- Both gates may fire in sequence (cascade-resolution round first, then language-gap round). Each fires at most once per run. Both are suppressed after 1 firing under `--auto` to bound cost.
- If remaining budget < 1 round → skip injection, tag `COVERAGE_CAVEAT_CITATION_CASCADE_BUDGET_EXHAUSTED`.
- If `--auto` is set → injection fires automatically once per run; second injection suppressed.

The breadth auditor's verdict is appended verbatim to the final report as a new section: **Breadth Audit**. Gate actions and outcomes are recorded in `state.json → breadth_gate_log`.

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
13. **Breadth must fail loudly, never silently.** Every breadth mechanism (directory-first, operator-slicing, link-crawl, counter-evidence) emits a yield signal: the count of unique URLs it produced. Zero yield is a valid signal and drives adaptation (e.g. sparse-topic mode); a missing signal is a bug. Coordinator rejects any findings file without `directory_yield` and `retrieval_path` populated.
14. **Use native tool parameters, not prompt exhortations, for enforceable constraints.** Domain blocklist: WebSearch `blocked_domains` parameter. Domain allowlist: `allowed_domains`. LLMs ignore prompt-level instructions under search pressure; the API parameter cannot be ignored.
15. **Source-entity independence ≠ domain independence.** Two URLs on different domains owned by the same publishing entity (`*.substack.com`, blog-of-lab-X, media-conglomerate-syndication) are not independent sources for corroboration. The breadth auditor reports `unique_publishing_entities`, not just `unique_domains` — the tighter number.

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
1. **Retrieval adapters — multi-index parallel fanout (REQUIRED — breadth gate).** WebSearch is ONE retrieval path with ONE ranking bias. Real breadth requires hitting multiple indexes with different biases. The coordinator gives you a pre-fetched **Adapter Pool** in `{adapter_pool_path}` — a JSON file containing seed URLs already harvested from 3–5 adapters applicable to this topic (see Adapter Registry section). Start your research from that pool. Adapters that ran (each returns URLs, each tagged with `retrieval_path`):
   - `WebSearch` (Google-like index bias)
   - `SemanticScholarAPI` — `api.semanticscholar.org/graph/v1/paper/search` (citation-graph bias)
   - `ArxivAPI` — `export.arxiv.org/api/query` (pre-print bias, CS/physics/math)
   - `OpenAlexAPI` — `api.openalex.org/works` (bibliographic, covers non-CS)
   - `CrossrefAPI` — `api.crossref.org/works` (DOI-bibliography)
   - `HackerNewsAlgolia` — `hn.algolia.com/api/v1/search` (community/popularity bias)
   - `StackExchangeAPI` — `api.stackexchange.com/2.3/search` (practitioner Q&A bias)
   - `GitHubSearchAPI` — `api.github.com/search/repositories` + `/code` (implementation bias)
   - `WikipediaExternalLinks` — WebFetch Wikipedia page → grep `## External links` / `## Further reading` / `## See also` (human-curated)
   - `RedditJSON` — `www.reddit.com/search.json?q={topic}&sort=top&t=all` (community discussion)

   The coordinator selects applicable adapters by topic-class heuristic (see Adapter Registry section). You receive the deduplicated URL pool. If the Adapter Pool contains ≥5 primary-tier URLs, you MAY skip WebSearch entirely for this direction and spend budget on counter-evidence + depth WebFetch.

2. **LLM-as-retrieval-memory (orthogonal index — REQUIRED).** Search engines rank by PageRank-style popularity. Your training corpus ranked sources by a different signal entirely. Before any WebSearch, enumerate from memory: list 8–15 specific sources on this topic you recall (author names, paper titles, repo names, canonical blog posts, key books), each with approximate year + why it's relevant. Write them to `{llm_memory_seeds_path}`. Then WebFetch each to verify existence + extract URL. Verified seeds enter the Source Table with `retrieval_path: llm_memory_verified`. Unverified or fabricated ones are discarded and flagged — do NOT include them in findings. This is the single most orthogonal retrieval path available; it surfaces sources that are seminal-but-unranked, historical-but-deprioritized, or niche-expert-known-but-not-viral.

3. **Yield signals (mandatory for every path):** record per-path counts in the Source Table header: `adapter_pool_yield: N_i per adapter | llm_memory_verified: M | websearch_yield: W | total_unique_domains: D | total_unique_publishing_entities: E`. If any path yielded 0, tag it — the coordinator uses per-path zero-yield signals to drive sparse-topic detection and adapter-pool pruning. Silent path failure is a bug.
2. **WebSearch with operator slicing and native blocklist.** When you do use WebSearch:
   - **Working operators** (verified to be honored): `site:edu`, `site:gov`, `site:{specific-domain}`, `-site:{excluded-domain}`, `filetype:pdf`. Use these to cut into unexplored strata.
   - **Do NOT rely on** `inurl:`, `after:`, `before:`, `intitle:` — WebSearch silently drops these. For date constraints, put the year in the query text (e.g. `"X 2025"`, `"X 2020"`).
   - **Native domain blocklist** — pass already-cited domains via WebSearch's `blocked_domains` parameter (not prompt-exhortation). The coordinator supplies this list to you in `{blocked_domains}` below.
3. **When to search vs rely on training data:** WebSearch is REQUIRED for any factual claim that lands in your Claims Register — recency matters, training data is stale, and every claim needs an inline source URL (Source Table requirement). Training-data-only knowledge is acceptable ONLY for definitional/foundational context that frames or scopes the search. Findings that lack a fetched source are rejected at synthesis — do not report them.
4. **Search budget hygiene (soft target, NOT hard allocation):** the Adapter Pool is pre-fetched by the coordinator and does NOT consume your WebSearch budget. Your budget applies only to WebSearch + counter-evidence + depth-fetch. Target mix:
   - **Haiku (8 slots):** LLM-memory verification (up to 3 WebFetches) + counter-evidence for TOP 3 load-bearing claims + 2–3 WebSearch. If counter-evidence would exceed budget, document skipped claims with `counter_evidence_searched: no_budget_exhausted` — do NOT silently drop them.
   - **Sonnet (15 slots):** LLM-memory verification (up to 6) + counter-evidence per load-bearing claim + remainder WebSearch.
   This is a target. If Adapter Pool already yielded ≥5 primary-tier sources and LLM-memory verified ≥3, you MAY skip WebSearch entirely.
5. Go deep — follow references, check citations, look for contradictions
6. Assess source quality for EACH source (primary / secondary / unverified) — see definitions below
7. Record each source's publication date, publishing entity, AND `retrieval_path` (one of: `directory`, `websearch`, `websearch+operator`, `citation-follow`). The `retrieval_path` field is required — the coordinator uses it to audit how breadth was actually achieved.
8. For every load-bearing factual claim: run a counter-evidence search. Record the outcome as `yes_none_found`, `yes_disconfirming_evidence_present` (cite the disconfirming source inline), or `no_search_skipped` (only for definitional claims)
9. Write your findings to: {findings_path}
10. Use the FORMAT specified: Findings, Claims Register, Source Table (with `retrieval_path` column), Mini-Synthesis, New Directions, Exhaustion Assessment. Include a Source Table header line: `directory_yield: N | websearch_yield: M | unique_domains: D`.
11. Every claim row in the Claims Register needs:
    - `corroboration`: `single_source` | `two_independent_sources` | `three_or_more_independent_sources` (sources independent iff they don't cite each other AND aren't from the same publishing entity; unverified-tier sources don't count)
    - `counter_evidence_searched`: one of the three values above
    - `recency_class`: `fresh` | `stale` | `undated` (freshest source wins for the claim)
12. Every claim in text needs an inline source URL
13. New directions are OPTIONAL — if this is a terminal node, write "None — terminal node."
14. Do NOT report new directions that are paraphrases of already-explored topics
15. **Unconsumed Leads (required — do NOT skip):** scan your findings for every named entity (team, tool, repo, person, framework, project) that you mentioned but did NOT independently research. Report them in a `## Unconsumed Leads` section with one line each: `- <entity>: <why it's worth researching>`. If genuinely none: write "None — all referenced entities were core to this direction's scope." The coordinator uses this section to drain missed leads across rounds.
16. **"Official" claims require code-level verification:** for any claim that something is "official," "standard," "canonical," "paved road," or "the way X is done at <org>," run at least one code search (e.g. `search/code` or equivalent) to verify ACTUAL adoption in production code. If you can only find docs but no code, mark the claim `corroboration: single_source` and note "policy-only, adoption unverified" in the Claims Register.
17. **Restricted-access document handling:** when you encounter a source behind auth (Google Docs, Confluence, Notion, internal wikis, paywalls, Slack threads), try the domain-appropriate authenticated tool first in this order: (a) domain-specific MCP tool if one is available for this source type (e.g. `mcp__google-docs`, `mcp__jira`, `mcp__slack`), (b) internal search/gh API, (c) WebFetch as last resort. If NONE work, do NOT silently drop the source — record it in `## Unconsumed Leads` with status `access_blocked` and a one-line note describing (i) what the document is expected to contain based on context, (ii) which tool would resolve it. Never fabricate content from a document you could not access. The coordinator uses `access_blocked` leads to surface a "Known blind spots" section in the final report.

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

---

## v6 Additions — Reliability, Iteration, Validation

### Adapter Drift Detection

APIs silently change response shapes (field renames, pagination breaks, rate-limit thresholds). v4.1 validates connectivity once; v6 validates *semantic correctness*.

Each adapter in the Registry declares a `canary` triple stored in `_shared/adapter_canaries.json`:
```
{
  "name": "SemanticScholarAPI",
  "canary_query": "transformer neural network",
  "expected_min_results": 10,
  "required_top_level_fields": ["data", "total"],
  "required_per_result_fields": ["title", "year", "authors"],
  "last_verified_iso": "2026-03-14"
}
```
On first use in a run, coordinator fires the canary query. Parse failure / missing fields / below-threshold result count → `adapter_drift_suspected`. Adapter marked unavailable for this run, logged to `state.json → adapter_drift_log`, and `COVERAGE_CAVEAT_ADAPTER_DRIFT: {name}` emitted in final report. If >3 adapters drift in the same run → `SYSTEM_ALERT: probable_mass_api_change` surfaced to user at next round gate (recommend canary refresh before continuing).

### Iterative Gates (v6 upgrade from v4's one-shot)

v4.1 cascade-gate and language-gap-gate fired at most once. v6 allows bounded iteration:

- Each gate has `max_iterations: 3` (hard cap).
- After each injected round, re-run the auditor. If the triggering condition persists AND iteration_count < 3 AND budget remains ≥ 1 round → fire again.
- Exponential cost check: each iteration N costs roughly 1.5× the previous (because injected directions target increasingly-specific cluster outliers / missing languages — narrower = more searches). Coordinator computes projected remaining cost per iteration; user gate at iteration_count ≥ 2 even under `--auto`.
- `gate_iteration_log` in `state.json` records: `{gate_type, iteration, trigger_reason, round_budget_remaining, outcome: {resolved|persists|abandoned_budget}}`.

### Retrieval-Path Attribution Validation (v6)

`retrieval_path` in the Source Table is agent-reported in v1–v5. Agent lazy-labels every URL `websearch` because it's default. v6 adds coordinator-side cross-check:

- Coordinator records a `retrieval_path_ledger` per round: every URL that entered Adapter Pool is tagged with the actual mechanism that produced it (`directory`, `adapter:{name}`, `browse_follow`, `llm_memory_verified`, `citation-follow`).
- At round-end, coordinator diffs agent-reported `retrieval_path` against ledger. Mismatches → auto-corrected to ledger value + logged to `retrieval_path_mismatch_log`. Three mismatches from the same agent in a run → that agent's future findings are flagged `retrieval_path_self_report_untrusted` in final report.
- The Breadth Auditor's `yield_per_path` table uses ledger values, not agent reports — so breadth claims can't be laundered through mislabeling.

### Independent Synthesis Critic (Phase 5 Pass 6, v6)

v0–v5 Phase 5 Pass 2 theme extraction and Pass 3 final-report writing are coordinator-done (with mini-syntheses as input, not raw findings). Coordinator bias → cherry-picked theme confirmation.

v6 adds Pass 6: **Synthesis Critic** (Sonnet, independent).
- Input: final report draft + ALL raw findings files + coordinator summary
- Output:
  ```
  SYNTHESIS_VERDICT_START
  themes_claimed_vs_evidenced: [{theme, supporting_findings_count, contradicting_findings_count, verdict: supported|weak|contradicted}]
  claims_omitted_from_report: [list of high-severity claims in findings NOT reflected in report]
  claims_overclaimed: [list of report claims lacking findings support]
  framing_drift: {score_0_to_1, rationale}
  SYNTHESIS_VERDICT_END
  ```
- Coordinator MUST incorporate critic verdict: `contradicted` themes → demoted to "contested" in final report; `claims_overclaimed` → downgraded or removed; `framing_drift > 0.3` → report tagged `COVERAGE_CAVEAT_COORDINATOR_FRAMING_DRIFT`.
- Coordinator cannot suppress Synthesis Critic output — verdict appended verbatim to report as "Synthesis Audit" section.

### Stop-the-Line Compound Trigger (v6)

Sometimes topics are malformed, fabricated by the user, or genuinely unresearchable. v5.1 accumulates caveats silently. v6 detects saturation:

If ≥3 of the following fire concurrently:
- `COVERAGE_CAVEAT_SPARSE_TOPIC`
- `COVERAGE_CAVEAT_COLD_START`
- `COVERAGE_CAVEAT_LANGUAGE_GAP_PARTIAL`
- `COVERAGE_CAVEAT_ADAPTER_DRIFT` (≥2 adapters)
- `SYSTEM_ALERT: probable_mass_api_change`
- `classification_overridden: source_verification_failed`
- Breadth Auditor `citation_cascade_risk: strong` AND post-injection `persists`

→ coordinator halts further rounds and emits `RUN_HALTED_TOPIC_APPEARS_ILL_FORMED` with: (a) caveat list, (b) what WAS found, (c) recommendation: "Either the seed topic is malformed, the information does not exist in accessible sources, or infrastructure has degraded. Refine the seed or consult the adapter_drift_log before retrying."

Prevents burning budget on runs where every signal says "we can't research this."

### Claim-Temporal Consistency Check (v6)

Every claim row with a temporal qualifier ("as of", "in 2025", "current", "recently") is validated:
- If claim text contains year/date: source's `publication_date` must be within ±12 months (unless claim itself is historical, detected by "in 1999" vs "as of 2025" structure).
- Mismatches → `temporal_inconsistency: true`; claim downgraded to `corroboration: single_source` regardless of actual source count (because temporal drift invalidates corroboration logic).
- Check runs at Phase 4 fact-verification, not at agent-side — coordinator-owned.

### Per-Theme Weighted Evidence Quality (v6)

Final report's single "Evidence Quality" score (v0–v5) conflates strong themes with weak ones. v6 decomposes:

For each theme in the final report:
- Weighted evidence score = `mean(per_claim_weight)` where `per_claim_weight = source_tier_score × corroboration_multiplier × recency_factor × (1 - retrieval_path_self_report_untrusted_penalty)`
- `source_tier_score`: primary=1.0, secondary=0.6, unverified=0.2
- `corroboration_multiplier`: single_source=0.5, two_independent=1.0, three_or_more=1.4
- `recency_factor`: fresh=1.0, stale=0.5, undated=0.3
- Each theme in final report carries its own evidence-quality score, not one run-wide average. Reader sees which themes are load-bearing vs. which are gossamer.

### Golden Rules Appended (v6 — #16–#18)

16. **Adapter connectivity ≠ adapter correctness.** A 200 OK response with junk JSON is worse than a 404. Canary-verify semantic shape per run.
17. **Retrieval-path labels are coordinator-owned, not agent-owned.** Trust the ledger, not the self-report. An agent's credibility degrades with every mismatch.
18. **Compound caveats mean the run is broken.** Three concurrent `COVERAGE_CAVEAT` tags is a stop-the-line signal, not a license to write a confidently-caveated report.

### Anti-Rationalization Counter-Table Additions (v6)

| Excuse | Reality |
|---|---|
| "Adapter returned 200, we're good." | No. Check the canary fingerprint. APIs silently rename fields; 200 with junk JSON is a worse failure mode than 404. |
| "The gate fired once, we're done with that kind of issue." | No. v6 iterates gates up to 3×. One failed injection doesn't mean the problem isn't solvable — it means this specific injection didn't solve it. |
| "Agent said the source came from citation-follow, that's what the report says." | No. Coordinator's retrieval ledger is authoritative. Agent self-reports are advisory until validated against the ledger. |
| "The caveats are all surfaced — we did our job." | No. Three or more compound caveats = topic is ill-formed. Halt, don't launder. |
| "Evidence Quality is 0.7, the report is solid." | No. Per-theme weighted scores reveal which themes are load-bearing. A single average hides weak themes under strong ones. |
| "Synthesis is mini-synthesis-based — critics already reviewed it." | No. Synthesis Critic (Pass 6) reviews FINAL REPORT against RAW FINDINGS to catch theme extraction bias, not just critique quality. Independence-invariant applies at synthesis too. |

---

## v7 Additions — Adversarial-Robustness, Cross-Round Learning, Hallucination Gating

### Adversarial-Source Heuristics (v7 — at Fact Verification)

Commercial / SEO-gamed / astroturfed / content-farm sources can pass v0–v6 filters if they have primary-source-shaped metadata. v7 adds automatic down-ranking signals applied at Phase 4 fact-verification:

For each source in Source Table, coordinator computes:
- `domain_age_months`: WebFetch `https://web.archive.org/web/{date}/*/domain.tld` → first-seen timestamp. If <6 months → `new_domain_risk: true`
- `sibling_density`: WebSearch `site:domain.tld` + count results. If >100k results with near-identical URL patterns (heuristic: >5 URLs sharing a stem like `/reviews/`, `/guides/`, `/best-{word}`) → `content_farm_risk: true`
- `press_release_signature`: body text starts with "[CITY, STATE] –" or contains the phrase "For immediate release" or identical lead paragraphs appear on ≥3 other domains → `syndication_detected: true`
- `affiliate_link_density`: count of `?ref=`, `/aff/`, `?tag=`, `?utm_`, shortener-redirect patterns in outbound links. If >30% of outbound links are affiliate → `commercial_intent_high: true`

Sources with ≥2 risk flags → downgraded to `unverified` tier regardless of claimed tier; contribute 0.2× to corroboration weight. Flagged in final report's Single-Source Claims section as `[ADVERSARIAL_SOURCE_RISK]`.

### Agent-Level Hallucination Probe (Phase 3.75, v7)

Phase 4 (fact-verification) spot-checks report-level claims. Between them, agent findings can contain fabricated URLs, misattributed quotes, or invented statistics that pass dedup and appear primary-tier.

Phase 3.75 runs after each round's agent output, before unconsumed-leads recovery:
- For each agent, random-sample 3 of its load-bearing claims (those with `corroboration != single_source` to avoid redundancy with Phase 4 single-source flagging)
- WebFetch the cited URL, grep for claim text (±20% keyword overlap allowed)
- If claim text NOT findable in source → mark `hallucination_suspected: true` on that claim, downgrade `corroboration` one tier, log to `hallucination_log`
- If ≥2 of 3 sampled claims fail for the same agent → mark that agent's remaining findings `agent_credibility_degraded`; coordinator surfaces "Agent-level hallucination risk" as a caveat
- Budget: 3 WebFetch per agent per round = ~18 extra calls/round at scale, ~$0.30/round

### Cross-Round Direction Momentum (v7)

v0–v6 treats every round independently except via unconsumed-leads. v7 adds explicit learning across rounds:

After each round, coordinator computes per-dimension yield: `(unique_primary_sources / search_budget_spent)`. The highest-yield dimension gets `momentum_bonus: +1 priority tier` for directions in subsequent rounds. The lowest-yield dimension gets `anti_momentum: -1 priority tier` (directions deprioritized, not eliminated).

Written to `state.json → dimension_momentum`. Resets every 3 rounds to prevent over-fitting. Golden Rule 19: coordinator never eliminates a dimension based on momentum alone — the cross-cutting mandatory dimensions always run at least once.

### Per-Subtopic Locus Refinement (v7)

v4's `language_locus` and v3's topic-class heuristic are classified once per run. For topics with multiple sub-goals (extracted in Phase 1 sub-goal extraction), each sub-goal gets its own locus determination:

After sub-goal extraction, coordinator fires one additional Haiku call per sub-goal (reusing the Phase 0f + Phase 0g prompts, scoped to the sub-goal question). Writes `state.json → subgoal_locus[{subgoal_id}]`. Adapter pool for directions owned by a given sub-goal uses that sub-goal's locus, not the seed-level locus.

Cost: +1 Haiku per sub-goal beyond the first = ~$0.02/sub-goal. Prevents the multi-era / multi-domain topic from getting locked into a single locus determined by the loudest sub-goal.

### User Pivot Injection (v7)

v0–v6 user interaction is binary at gates: continue / stop. v7 adds mid-run pivot: at any round gate, user may respond `redirect:{refined_seed_or_focus}`. Coordinator:
- Writes refined seed to `state.json → pivot_log`
- Re-runs Phase 0f + Phase 0g + Phase 1 dimension re-assessment (NOT Phase 0b/0c/0e — those stay locked from original seed)
- Preserves existing findings but marks them `pre_pivot_context`
- Round counter resumes (pivot does not reset max_rounds)
- Final report includes both pre-pivot and post-pivot findings with a `PIVOT_BOUNDARY` section marker

Prevents the user from having to abandon a half-good run to restart.

### Claim-Provenance Graph (v7)

For topics with ≥20 claims in final report, coordinator emits a provenance graph (GraphViz DOT or JSON adjacency) as `claim_provenance.dot`:
- Nodes: claims (red=contradicted, yellow=single_source, green=three_or_more, blue=disputed)
- Edges: claim→source (weighted by corroboration), claim→claim (when one claim cites another via the Claims Register)
- Detects: (a) cascading dependencies (multiple "independent" claims trace to 1-2 originals — surfaces as `COVERAGE_CAVEAT_CITATION_CASCADE_GRAPHICAL`), (b) orphan claims (no incoming/outgoing edges — low-context findings)
- Appended to final report as a link. User can render locally.

Complements Breadth Auditor's `citation_cascade_risk` with an actually-visualizable artifact.

### Cost-per-Unique-Source Metric (v7)

Coordinator tracks per-agent `cost_per_unique_url = (tokens_consumed * $per_token + searches_fired * $per_search) / unique_urls_contributed`. Surfaced in final report's Provenance Audit section.

Agents whose cost-per-unique-URL exceeds 2× the round median are flagged `inefficient_retrieval`. Over multiple runs, this feeds back to the Adapter Registry: adapters consistently contributing inefficient agents get deprioritized.

### Temporal-Source-Cluster Detection (v7)

If ≥60% of cited sources in the final report fall within a single 6-month window, emit `COVERAGE_CAVEAT_TEMPORAL_CLUSTER: {window}`. This catches runs that unintentionally capture a hype-cycle snapshot rather than a longitudinal view. User may rerun with explicit date-range directions to resolve.

### Golden Rules Appended (v7 — #19–#21)

19. **Momentum is a bias correction, not a filter.** Cross-cutting mandatory dimensions run every round regardless of momentum. A zero-yield dimension in round N may yield in round N+1 with refined queries.
20. **Agent hallucination is a tier-1 failure mode.** Spot-check every agent's non-single-source claims every round. A confident agent fabricating 2 of 3 sampled claims poisons the entire run if un-flagged.
21. **Commercial intent ≠ invalid source.** Adversarial-source flags DOWNGRADE, they do not reject. A content farm article may still cite a real primary source — use the flag to adjust confidence, not to discard.

### Anti-Rationalization Counter-Table Additions (v7)

| Excuse | Reality |
|---|---|
| "The source has a clean URL, looks legit." | No. Check domain age, sibling density, syndication. A 3-month-old `.com` with 100k SEO-shaped URLs is not a primary source. |
| "The agent cited a real URL, the claim's fine." | No. Phase 3.75 hallucination probe verifies the claim APPEARS in the source. Cited ≠ supported. |
| "This dimension yielded nothing last round — skip it." | No. Momentum is a priority adjustment, not a filter. Cross-cutting dimensions run every round. |
| "One Language Locus classification is enough for the whole topic." | No. Sub-goal-scoped locus catches multi-era/multi-domain drift. Cost per sub-goal is $0.02. |
| "User feedback at gates is continue-or-stop." | No. v7 adds `redirect:{focus}` pivot injection. Coordinator re-scopes without losing accumulated findings. |
| "Final report has 40 claims, we're well-corroborated." | No. Render the provenance graph. If 40 claims trace to 3 original studies, cascading is hidden by raw count. |
| "Evidence Quality is averaged — 0.7 means strong." | v6 addressed this per-theme. v7 adds per-source cost efficiency. An agent producing one primary source for $1.50 is fine; one producing 20 duplicates for $2 is not. |
| "All sources are from 2025, that's current." | No. Temporal-cluster detection: 60% in 6 months = hype-cycle snapshot. Flag + consider rerun with date-range directions. |

---

## v8 Additions — Synthesis-Bias Gating, Reproducibility, Cross-Run Efficiency

### Contrarian Pre-Synthesis Pass (Phase 4.5, v8)

Before Phase 5 synthesis, spawn a Contrarian Agent (Sonnet, independent). Its one job: argue against the dominant framing the coordinator summary has converged on.

Inputs: all mini-syntheses + coordinator summary's current dominant_framing field + full Claims Register.
Prompt:
```
The coordinator summary claims the dominant framing of this research is: "{dominant_framing}".
Your job: argue the strongest case AGAINST this framing using ONLY evidence already in the findings. If the evidence doesn't support a strong counter-case, say so explicitly.

Output:
COUNTER_CASE_START
counter_framing: "..."
supporting_findings: [{finding_id, claim_summary}, ...]   // must cite actual findings, not fabricate
strength_vs_dominant: strong | moderate | weak | no_viable_counter
overlooked_angles: [angles the dominant framing dismisses or doesn't address]
COUNTER_CASE_END
```
Coordinator rules:
- `strength_vs_dominant: strong` → dominant framing demoted; final report presents BOTH framings as contested, with a "Framing Debate" section
- `strength_vs_dominant: moderate` → dominant framing retained but report adds "Alternative framing" subsection listing counter-findings
- `strength_vs_dominant: weak` → counter framing listed as "Minority view" in appendix
- `no_viable_counter` → dominant framing confirmed, BUT coordinator logs this outcome for audit (a "no viable counter" result on every run signals Contrarian Agent is rubber-stamping; threshold >80% → agent prompt revision required in skill-level maintenance)

Independence-invariant applies — Contrarian Agent output is never edited by coordinator, appended verbatim to final report as "Contrarian Audit" section.

### Run Reproducibility Hash (v8)

At Phase 2 (Initialize State), coordinator computes:
```
run_fingerprint = sha256(seed || adapter_registry_versions || model_ids_per_tier || date_iso || user_invocation_string)
```
Written to `state.json → run_fingerprint`. Surfaced at top of final report.

Two runs with matching fingerprints but different outputs = LLM non-determinism (expected, minor), OR underlying source state changed (flag).
Different fingerprints cannot be compared directly — final report explicitly notes "Reproducibility: results are a snapshot; fingerprint {hash}".

If user attempts to resume a run with a mismatched fingerprint (e.g. adapter versions have drifted since original run) → coordinator warns and offers fresh start or continue-with-caveat.

### Cross-Run Adapter State Cache (v8)

v4.1 adapter_validation_log is per-run. v8 persists a rolling 30-day cache in `~/.claude/deep-research-cache/adapter_health.jsonl`:
```
{"adapter": "SemanticScholarAPI", "last_success": "2026-04-19T14:30:00Z", "last_failure": null, "drift_detected_count_last_30d": 0}
{"adapter": "HAL", "last_success": null, "last_failure": "2026-04-19T14:22:00Z", "error": "403", "drift_detected_count_last_30d": 3}
```
At Phase 3.3 adapter selection, coordinator reads the cache:
- Adapter `last_failure` within last 24h AND no success since → skip probing (already known broken), save the canary call
- Adapter `drift_detected_count_last_30d ≥ 3` → require explicit user opt-in at Phase 1 to include (chronic-unreliable adapter)
- Success persisted; next run reuses confidence
Cache file is user-local, not skill-local — one user's broken adapters don't affect others.

### Perspective-Lens Labeling (v8)

Every source in the Source Table gets a `perspective_lens` tag at coordinator-review time:
- `academic` (university, peer-reviewed journal, pre-print archive)
- `industry` (vendor, product company, consultancy white paper)
- `government` (gov regulator, standards body, public policy)
- `community` (forums, individual practitioners, blog, open-source)
- `media` (journalism, news outlet, trade press)
- `adversarial_intent_risk` (v7 flagged)
Classification uses domain heuristic + LLM spot-check for ambiguous cases.

Final report's per-theme weighted evidence score (v6) now also reports `perspective_distribution`: `{academic: 40%, industry: 30%, ...}`. A theme with 100% industry perspective on a "best practices" topic is flagged `COVERAGE_CAVEAT_SINGLE_PERSPECTIVE`. Complements Breadth Auditor — catches framing bias the auditor misses because all sources are different URLs but from the same perspective class.

### Semantic-Staleness Check (v8)

For claims that use domain jargon, coordinator runs a 1-call Haiku check per unique term: "Is this term the currently-preferred name for {concept} as of {current_year}, or has it been superseded? If superseded, by what?"

Claims using superseded jargon (e.g. "artificial general intelligence" where the current field term is "frontier models") → tagged `semantic_staleness_risk: true` and flagged in report. Prevents confidently-cited sources with dated vocabulary from anchoring modern claims.

Cost: ~5 Haiku calls per run per run = $0.02. Only fires for topics with identifiable domain jargon (detected by >=3 claims sharing same technical terms).

### Coverage-Confidence Decoupling (v8)

v0–v7 blur `Coverage %` (how many angles explored) with `Evidence Quality` (how strong evidence per angle). v8 decomposes final report header into:
- `breadth_score`: 0–1, fraction of applicable dimensions explored
- `depth_score`: 0–1, mean per-direction exhaustion score
- `corroboration_score`: 0–1, fraction of claims with ≥2 independent sources
- `counter_evidence_score`: 0–1, fraction of claims where counter-evidence was actively searched
- `fabrication_risk_score`: 0–1, inverse of hallucination-probe pass rate (v7)
- `perspective_diversity_score`: 0–1, Shannon entropy over perspective_lens distribution (v8)
- `temporal_diversity_score`: 0–1, inverse of temporal cluster concentration (v7)

Header reads: `Coverage: breadth=0.82, depth=0.67, corroboration=0.71, counter_evidence=0.58, fabrication_risk=0.12, perspective_diversity=0.45, temporal_diversity=0.62`. User gets honest orthogonal signals, not a single summary score that averages them.

### Golden Rules Appended (v8 — #22–#24)

22. **Dominant framing survives because it wasn't challenged.** Contrarian Pre-Synthesis is non-optional. A report that says "framing confirmed" without a Contrarian Audit section has not verified its own framing.
23. **Single-perspective-class coverage on a multi-stakeholder topic is a framing failure.** A 100%-industry report on "best practices" is an industry whitepaper, not research. Flag and force explicit acknowledgment.
24. **Confidence scores are orthogonal, not averaged.** Breadth, depth, corroboration, counter-evidence, fabrication-risk, perspective diversity, temporal diversity are different questions. A single composite score hides weak axes under strong ones.

### Anti-Rationalization Counter-Table Additions (v8)

| Excuse | Reality |
|---|---|
| "The framing is obvious from findings." | No. Contrarian Agent argues against it using the same findings. If it can build even a moderate case, your "obvious" framing isn't. |
| "No need to hash the run — findings speak for themselves." | No. Reproducibility fingerprint captures which adapter versions + models generated the findings. Without it, re-running 30 days later might produce different results from silently-changed APIs. |
| "Adapters are checked per run — we're good." | v4.1's per-run canary is fine but wastes calls on known-broken adapters. v8 cross-run cache saves budget and flags chronic-unreliable. |
| "All our sources are legit primary papers." | Check perspective_lens distribution. Primary + 100% academic on an applied topic = industry perspective absent = framing hole. |
| "The term is well-known in the field." | Semantic-staleness check: terms get superseded. A 2015-era canonical term cited in a 2026 report signals the research found old material. |
| "Coverage is 0.82, we're good." | Decompose: breadth, depth, corroboration, counter_evidence, fabrication_risk, perspective_diversity, temporal_diversity. 0.82 average can hide any one at 0.3. |
| "The contrarian agent said 'no viable counter' — case closed." | Rubber-stamping pattern. If this fires on every run, the Contrarian Agent prompt needs revision. Track the rate. |

---

## Ceiling assessment (v8)

After v8, the remaining known gaps require either:
1. **External infrastructure** the skill cannot conjure (embedding models, vector DBs, MCP servers for CNKI/Baidu, authenticated paywall access)
2. **Human judgment** the skill cannot replace (final-answer question "is this a good research report for MY purpose")
3. **Tool-level changes** outside the skill's scope (WebSearch index choice, WebFetch reliability, LLM hallucination rates)

Iterations v6→v7→v8 each added ~4-8 mechanisms of decreasing marginal impact. Further versions would increasingly add ceremony without reaching new retrieval surface, bias classes, or failure modes that the current spec doesn't already observe and caveat. The skill's coverage of observable failure modes is effectively saturated relative to what its available tools can reach.

---

## Adapter Registry (v3)

Each adapter is a deterministic fetch recipe. The coordinator (Phase 3.3, before agent spawn) selects applicable adapters by the topic-class heuristic below, runs them in parallel, deduplicates URLs, writes results to `deep-research-{run_id}/adapter_pools/direction-{id}.json`, and passes the path to the research agent.

### Topic-class → adapter bundle heuristic

Coordinator LLM-classifies topic into ONE of: `cs_research | non_cs_academic | engineering | policy_legal | business_finance | community_opinion | historical | general`. Bundle picked accordingly:

| Topic class | Primary adapters | Secondary (if budget allows) |
|---|---|---|
| cs_research | ArxivAPI, SemanticScholarAPI, GitHubSearchAPI | PapersWithCode, HackerNewsAlgolia |
| non_cs_academic | SemanticScholarAPI, OpenAlexAPI, CrossrefAPI | WikipediaExternalLinks |
| engineering | GitHubSearchAPI, StackExchangeAPI, HackerNewsAlgolia | WebSearch-with-operator |
| policy_legal | WebSearch-with-operator (`site:gov`, `filetype:pdf`), WikipediaExternalLinks | RedditJSON (public-comment threads) |
| business_finance | WebSearch-with-operator, WikipediaExternalLinks | HackerNewsAlgolia |
| community_opinion | RedditJSON, HackerNewsAlgolia, StackExchangeAPI | WebSearch |
| historical | WikipediaExternalLinks, WebSearch-with-operator | OpenAlexAPI |
| general | WebSearch, WikipediaExternalLinks, HackerNewsAlgolia | SemanticScholarAPI |

### Adapter spec (each)

```
name: string
applicable_topic_classes: [string, ...]
endpoint: URL template with {topic} placeholder
method: "webfetch_json" | "webfetch_html" | "websearch"
parse_rules: JSONPath or HTML selector → list of {url, title, year?, snippet?}
yield_signal: per-call count + unique-URL count written to adapter_pools/{direction}.json header
failure_mode: on 403/404/timeout → record `adapter_failed: {name}, reason: ...` in pool JSON, continue with other adapters
```

### Concrete adapters

```
ArxivAPI:
  endpoint: https://export.arxiv.org/api/query?search_query=all:{topic}&max_results=20
  method: webfetch_html (Atom XML)
  parse: grep <entry><id>https://arxiv.org/abs/...</id> + <title> + <published>

SemanticScholarAPI:
  endpoint: https://api.semanticscholar.org/graph/v1/paper/search?query={topic}&limit=20&fields=title,year,authors,url
  method: webfetch_json
  parse: JSONPath $.data[*]

OpenAlexAPI:
  endpoint: https://api.openalex.org/works?search={topic}&per-page=20
  method: webfetch_json
  parse: JSONPath $.results[*].{doi,title,publication_year,host_venue.display_name}

CrossrefAPI:
  endpoint: https://api.crossref.org/works?query={topic}&rows=20
  method: webfetch_json
  parse: JSONPath $.message.items[*].{DOI,title,published-print}

HackerNewsAlgolia:
  endpoint: https://hn.algolia.com/api/v1/search?query={topic}&tags=story&hitsPerPage=30
  method: webfetch_json
  parse: JSONPath $.hits[*].{url,title,points,created_at}

StackExchangeAPI:
  endpoint: https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=votes&q={topic}&site=stackoverflow
  method: webfetch_json
  parse: JSONPath $.items[*].{link,title,score,creation_date}

GitHubSearchAPI:
  endpoint: https://api.github.com/search/repositories?q={topic}&sort=stars&per_page=15
  method: webfetch_json
  parse: JSONPath $.items[*].{html_url,full_name,description,stargazers_count,updated_at}
  note: unauthenticated rate limit 10 req/min — coordinator enforces

WikipediaExternalLinks:
  endpoint: https://en.wikipedia.org/wiki/{url-encoded-topic}
  method: webfetch_html
  parse: grep sections "## External links", "## Further reading", "## See also" → extract <a href>

RedditJSON:
  endpoint: https://www.reddit.com/search.json?q={topic}&sort=top&t=all&limit=25
  method: webfetch_json
  parse: JSONPath $.data.children[*].data.{permalink,title,score,subreddit}

WebSearch-with-operator:
  primitive: WebSearch with `{topic} site:edu OR site:gov OR filetype:pdf`
  parse: tool-native
```

### Failure & cost guards

- Any adapter call that returns `403 | 404 | timeout | empty` is recorded as `adapter_failed` in the pool JSON — coordinator never retries the same adapter within a run
- Per-run adapter call budget: 5 adapters × 1 call per direction = 5 webfetches per direction at Phase 3.3. Total for 20 initial directions: ~100 adapter calls ($0.50 at free API rates, ~30s wall-clock with parallelization)
- If ≥ 3 of 5 adapters fail for a given direction, coordinator tags the direction `low_pool_yield` — the research agent compensates by shifting its budget to WebSearch

---

## Cross-Lingual Adapter Extension (v4)

Activated when `state.language_locus.authoritative_languages` contains non-`en` entries. For each non-`en` language in the locus, coordinator:

1. **Translates seed query into target language** via LLM (Haiku) before firing language-specific adapters. Writes translations to `xlang_queries/{lang}.txt`. Each WebSearch / API call is tagged with `query_language`.

2. **Picks language-specific adapter variants:**

**Status honesty (v4.1):** Of the 15 language-specific endpoints originally proposed, only **2 classes** are verified working via WebFetch from Claude Code: (a) `{lang}.wikipedia.org` and (b) `OpenAlexAPI` with `filter=language:{xx}`. HAL, SciELO, J-STAGE, CiNii, Baidu Scholar, CNKI were tested live and all returned 403 / redirects / ECONNREFUSED / auth walls. **Do not add an adapter to this table without a successful live probe recorded in `state.json → adapter_validation_log`.** Non-academic / community / industry content in non-EN languages is reached via WebSearch country-TLD operators (verified working), NOT via specialized scrapers.

| Language | **Working adapters (verified)** | **Fallback: WebSearch country-TLD** | Tested-broken (do NOT use) |
|---|---|---|---|
| zh | `ZhWikipedia` + `OpenAlexAPI filter=language:zh` | `site:cn OR site:tw OR site:hk` + `site:zhihu.com` | CNKI (paywall), Baidu Scholar (redirect) |
| ja | `JaWikipedia` + `OpenAlexAPI filter=language:ja` | `site:jp` | CiNii (redirect), J-STAGE (ECONNREFUSED) |
| ko | `KoWikipedia` + `OpenAlexAPI filter=language:ko` | `site:kr` | — |
| de | `DeWikipedia` + `OpenAlexAPI filter=language:de` | `site:de OR site:at OR site:ch` | — |
| fr | `FrWikipedia` + `OpenAlexAPI filter=language:fr` | `site:fr OR site:ca OR site:be` | HAL (403) |
| es / pt | `EsWikipedia` / `PtWikipedia` + `OpenAlexAPI filter=language:es|pt` | `site:es OR site:mx OR site:ar` / `site:br OR site:pt` | SciELO (403) |
| ar | `ArWikipedia` + `OpenAlexAPI filter=language:ar` | `site:sa OR site:ae OR site:eg` | AskZad (paywall) |
| other | `{lang}.wikipedia.org` + `OpenAlexAPI filter=language:{xx}` | Country-TLD site operators | Check `adapter_validation_log` before adding new ones |

**Adapter validation protocol (v4.1, mandatory):** Before any cross-lingual adapter runs for the first time in a run, the coordinator performs a 1-call live probe. If probe returns non-2xx OR empty body within 10s, the adapter is marked `unavailable_this_run` in `state.json → adapter_validation_log` and skipped for the remainder of the run. This prevents the language-gap gate from injecting rounds that quietly 403 on every adapter and then declaring the gap "unresolved."

**Honest scope of cross-lingual coverage:** With verified-working adapters only, v4.1 reliably reaches:
- Non-EN academic metadata (via OpenAlex)
- Non-EN encyclopedia content (via per-language Wikipedia)
- Non-EN community / industry / news (via WebSearch country-TLD operators — breadth varies by WebSearch index bias)

v4.1 does NOT reliably reach: paywalled non-EN databases (CNKI, AskZad), JS-heavy non-EN archives (CiNii, J-STAGE), region-blocked sources (Baidu Scholar). These are flagged in the final report as `COVERAGE_CAVEAT_LANGUAGE_GAP_PARTIAL` with the specific source types unreachable.

3. **Source-language tagging.** Every source entering the Source Table gets `source_language` (ISO 639-1):
   - URL TLD heuristic first (`*.de`, `*.jp`, `*.cn`)
   - Domain-specific default if known (`zh.wikipedia.org` → `zh`)
   - LLM content inspection as fallback (cheap — 100-char prefix check)
   Unknown → `source_language: und` (undetermined). Uncoverted `und` sources are surfaced in the final report under "Language-ambiguous sources."

4. **Cross-lingual synthesis.** Non-`en` findings enter the coordinator summary with LLM-translated English abstracts, preserving the original-language URL + a `[translated_from: {lang}]` tag. Native-language quotes are retained verbatim for the final report's Evidence section.

5. **Cost impact.** ~$0.10–0.20 additional per run when cross-lingual mode activates. LLM translation of 5 seed queries × 3 non-`en` languages ≈ 15 × ~$0.005 Haiku calls = $0.075. Adapter fetches add ~10–15 WebFetch calls. Gated by user consent at Phase 1 scope declaration; skipped entirely for `en_dominant` topics.
