# Shared-Patterns Survey

Snapshot of recurring patterns across the skills in `/Users/npow/.claude/skills/`, captured on 2026-04-18 by an Explore agent. Purpose: preserve the extraction candidates so they survive context compaction.

**Status:** survey complete. Extracted patterns: `adversarial-judging.md`, `cross-finding-coherence.md`, `execution-model-contracts.md`, `parallel-review-panel.md`, `premortem-blind-spot-seeding.md`, `parallel-critic-quorum.md`, `subagent-watchdog.md`. Remaining candidates are pending user approval per bucket — extraction touches 7-9 skills per pattern and should be done in a controlled batch, not incidentally.

**Last updated:** 2026-04-23
**Source agent:** Explore survey (medium thoroughness) + Org-Bench coordination research (2026-04-23)

---

## High-value extractions (copy-paste-ready across 7-9 skills)

### 1. Structured Output Contract (`STRUCTURED_OUTPUT_START/END` markers)
- **Skills using it (9):** deep-qa, deep-design, deep-debug, proposal-reviewer, deep-plan, team, autopilot, loop-until-done, flaky-test-diagnoser
- **Consistency:** verbatim across all 9. Same phrasing: "Unparseable output → fail-safe critical/worst verdict."
- **Extraction target:** `_shared/structured-output-contract.md`
- **Estimated savings:** ~20 lines × 9 skills = ~180 lines of boilerplate removed.

### 2. Independence Invariant ("Coordinator orchestrates; never evaluates")
- **Skills using it (7):** deep-qa, deep-design, deep-debug, proposal-reviewer, deep-plan, team, autopilot
- **Consistency:** core principle stated identically in 7 skills. Always used to justify delegating severity classification / judge verdicts / approval gates to independent agents.
- **Extraction target:** `_shared/independence-invariant.md`
- **Estimated savings:** ~15 lines × 7 skills = ~105 lines.

### 3. State Written Before Agent Spawn
- **Skills using it (9):** deep-qa, deep-design, deep-debug, proposal-reviewer, deep-plan, team, autopilot, loop-until-done, flaky-test-diagnoser
- **Consistency:** verbatim contract — "write `spawn_time_iso` BEFORE the Agent tool call; record `spawn_failed` if error."
- **Extraction target:** `_shared/state-before-spawn-contract.md`
- **Estimated savings:** ~25 lines × 9 skills = ~225 lines.

### 4. Honest Termination Labels (exhaustive vocabulary)
- **Skills using it (9):** deep-qa, deep-design, deep-debug, proposal-reviewer, deep-plan, team, autopilot, loop-until-done, flaky-test-diagnoser
- **Consistency:** each skill has a fixed table of labels; exact phrasing varies by domain but structure is identical. Never "looks good", "no issues remain", "complete" without evidence.
- **Extraction target:** `_shared/termination-labels-pattern.md` — template + label-selection guidance, skills override the specific labels.
- **Estimated savings:** ~30 lines × 9 skills = ~270 lines (template savings; domain-specific labels still live in each skill).

### 5. All Data Passed Via Files, Never Inline
- **Skills using it (8):** deep-qa, deep-design, deep-debug, proposal-reviewer, deep-plan, team, autopilot, loop-until-done
- **Consistency:** verbatim contract in all 8. "Inline content is silently truncated — warn user."
- **Extraction target:** `_shared/files-not-inline-contract.md`
- **Estimated savings:** ~10 lines × 8 skills = ~80 lines.

**High-value total extraction savings: ~860 lines of boilerplate across 8 skills.**

---

## Medium-value extractions (repeat across 3-4 skills with divergent wording)

### 6. Adversarial Judging (4 mechanisms) — EXTRACTED
- **Skills (4 adopters, partial):** deep-qa (3 of 4 mechanisms), deep-design, deep-debug, proposal-reviewer
- **Status:** ✅ extracted to `_shared/adversarial-judging.md` — blind severity protocol, mandatory author counter-response, rationalization auditor, falsifiability drop. Adoption varies per skill (deep-qa adopts 3 of 4, intentionally diverges on falsifiability drop).

### 7. Pre-Mortem Blind-Spot Seeding — EXTRACTED
- **Skills (4):** deep-design (step 0), deep-qa (phase 0e), deep-research (phase 0e), deep-debug (phase 0e)
- **Pattern:** spawn 1 Haiku agent asking "list 5 ways this could miss the real insight" → output becomes critical-priority angles.
- **Status:** ✅ EXTRACTED (2026-04-18) to `_shared/premortem-blind-spot-seeding.md` — pattern structure + canonical prompt template + per-skill angle lists. Each skill keeps its own 5-angle domain-specific list inline.

### 8. Iron-Law Gate Before Transition — REJECTED
- **Skills (4):** deep-plan, team, autopilot, loop-until-done
- **Pattern:** "Phase N evidence files must exist on disk + parse cleanly before advancing to Phase N+1. Coordinator reads structured markers; missing evidence → blocked."
- **Status:** ❌ NOT EXTRACTED (2026-04-18 decision)
- **Rejection reason:** grep for `iron.law|iron_law` returned 22 files — the phrase is too general. Each skill's gate conditions are domain-specific (deep-plan: "no verdict until all claims have judge file"; team: "no phase-2 without phase-1 evidence file"; autopilot: "three-judge approval"; loop-until-done: "criterion green before story advance"). The shared pattern would be lowest-common-denominator prose thinner than what each skill already has. Revisit only if a concrete duplication surfaces across 3+ skills with near-identical wording.

### 9. Parallel Critic Pool (orthogonal dimensions + quorum + dedup) — EXTRACTED
- **Skills (4):** deep-design, deep-qa, deep-research, proposal-reviewer
- **Pattern:** spawn N independent agents on different dimensions in parallel; quorum if ≥M return parseable; dedup against stable pre-round snapshot; coverage check against required categories.
- **Status:** ✅ EXTRACTED (2026-04-18) to `_shared/parallel-critic-quorum.md` — spawn/collect/quorum/dedup/coverage phases + integration checklist. Each skill sets its own N, M, dimension taxonomy, and `is_duplicate` function.

### 10. Falsifiability Gate (concrete scenario + counter-response) — PARTIALLY EXTRACTED
- **Skills (4):** deep-design, proposal-reviewer, deep-plan, loop-until-done
- **Status:** counter-response + drop-not-downgrade covered in `_shared/adversarial-judging.md`. Scenario requirement NOT extracted separately (each skill defines scenario shape differently).

### 11. Subagent Watchdog (mtime-based staleness monitor) — EXTRACTED
- **Skills (10 adopters):** deep-qa, deep-debug, deep-research, deep-design, deep-plan, proposal-reviewer, team, autopilot, loop-until-done, flaky-test-diagnoser
- **Pattern:** every `run_in_background=true` spawn is paired with a Monitor tail (Flavor A) or in-line stat check (Flavor B) that treats output-file mtime age as ground truth. `TaskOutput` status reports PID liveness only, not progress — a stuck/deadlocked/spinning subagent stays `status: "running"` forever and the completion notification never fires.
- **Status:** ✅ EXTRACTED and ✅ FULLY WIRED (2026-04-18) to `_shared/subagent-watchdog.md` — contract + two implementation flavors + grading table + state schema additions + integration checklist. Cross-reference wired into all 10 adopters: deep-qa, deep-debug, deep-research, deep-design, deep-plan, proposal-reviewer, team, autopilot, loop-until-done, flaky-test-diagnoser. Tier-appropriate thresholds documented per skill (fast Haiku judges: 3/10 min; Sonnet critics: 5/20 min; long researchers/test-runners: 10-15/30-45 min).
- **Motivation:** the 18-hour-silent-death bug — coordinator blocked on `TaskOutput(block=true)` against a hung subagent with no path to detect staleness. Closing this gap is load-bearing for any skill that dispatches long-running subagents.

**Medium-value remaining extraction savings: ~600 lines.**

---

### 12. Cross-Finding Coherence Integrator — EXTRACTED
- **Skills (4):** deep-qa (Phase 5.5.a-coherence), deep-design (Step 5 pre-judge), deep-debug (Phase 3 Step 3a-coherence), deep-research (Phase 3.7 post-rounds)
- **Pattern:** after parallel critics/hypothesis-agents/researchers complete and before severity judges or synthesis, spawn a Sonnet integrator that reads ALL output simultaneously and annotates cross-finding relationships (contradictions, emergent patterns, coverage gaps). Research variant uses adapted vocabulary (CONVERGES replaces PATTERN_MEMBER, adds SOURCE_CONFLICT).
- **Status:** ✅ EXTRACTED (2026-04-23) to `_shared/cross-finding-coherence.md` — full pattern + research variant + prompt template + failure modes + integration checklist. Wired into deep-qa, deep-design, deep-debug, deep-research.
- **Motivation:** Org-Bench (Kun Chen, April 2026) showed Google's bipartite integrator layer (4 parallel middle reviewers seeing ALL worker output) outscored every other topology. Our parallel critics were intentionally isolated (preventing groupthink) but this created blind spots: contradictory findings survived independently, emergent patterns across dimensions were invisible, and inter-dimensional coverage gaps were unchecked. The integrator is the bipartite middle layer.

### 13. Parallel Review Panel — EXTRACTED
- **Skills (3 wired):** team (Step 5), loop-until-done (Step 7), ship-it (Phase 6)
- **Pattern:** replaces two-stage sequential review (spec-compliance → code-quality) with 4 parallel reviewers, each getting full context (spec + code + tests + build output) with a primary lens (spec-compliance, code-quality, smoke-test, integration-coherence). Cross-lane findings are tagged. Meta-reviewer resolves conflicts.
- **Status:** ✅ EXTRACTED (2026-04-23) to `_shared/parallel-review-panel.md` — full pattern + panel composition + smoke-test prompt template + meta-reviewer protocol + integration checklist. Wired into team, loop-until-done, ship-it. Autopilot NOT YET WIRED — listed as candidate consumer but still uses its own review protocol.
- **Motivation:** Org-Bench showed three failures in review structures: (1) Oracle's lane-specific reviewers all passed while the product didn't work (no end-to-end usage verification — addressed by smoke-test lens), (2) Google's 4 parallel integrators outperformed Apple's 1 serial reviewer (addressed by parallel execution), (3) sequential specialized review creates partial-context blindness (addressed by giving every reviewer full context with a primary lens, not a scope boundary).

---

## NOT worth extracting

### Model Tier Strategy (Coordinator Sonnet, Critic/Scout Haiku)
Too domain-specific. Deep-research optimizes for cost; deep-qa for depth-dependent routing. Shared reference would be lowest-common-denominator useless.

### Anti-Rationalization Counter-Tables
Each table's contents are domain-specific. "Inflate this to critical to be safe" (QA) is different from "the founders are impressive" (proposal). Tables derive from observed baselines, not shared.

### DFS (Depth-First Frontier Search)
Shared concept, completely different implementations. Deep-design is spec-driven; deep-qa defect-driven; deep-research has unconsumed-leads recovery. Extraction would create abstractions each skill has to override.

---

## Surprise finds (not on the original hypothesis list)

### A. File-Based Resume Protocol (5+ skills)
Skills: deep-qa, deep-design, deep-debug, loop-until-done, flaky-test-diagnoser, autopilot.
`state.json.generation` counter + pre-phase `spawn_time_iso` writes + resume replays from `last_completed_phase`. Each skill reimplements ~40-60 lines.
**Recommendation:** extract the generation-counter + spawn-time-write contract as a micro-pattern (~20 lines). Phase semantics stay in each skill. Suggested file: `_shared/state-generation-counter-pattern.md`.

### B. Per-Worker Evidence File Pattern (3+ skills)
Skills: team, loop-until-done, implicit in deep-qa. Before marking work complete, worker writes dated evidence files to a predefined path: `{skill}-{run_id}/exec/{worker}-{criterion}-{stage}.txt`.
**Recommendation:** file-naming conventions differ too much to extract the path structure, but the **principle** ("evidence exists on disk before status changes") could live in `_shared/iron-law-gate-pattern.md` (see extraction #8).

### C. Unconsumed-Leads Recovery (deep-research only)
Unique to deep-research, but solving a real problem (scope creep via name-dropping) that other adversarial skills might benefit from. Not extracting — flagging as a candidate pattern to propagate.

---

## Recommended extraction order

If the user approves further extraction, proceed in this order (low-risk → high-risk):

1. ✅ **DONE**: adversarial-judging.md (covers #6, #10 partial)
2. **#1 Structured Output Contract** — highest frequency (9 skills), lowest variance. Safest first extraction.
3. **#5 Files-Not-Inline Contract** — 8 skills, verbatim.
4. **#2 Independence Invariant** — 7 skills, verbatim. Combine with #6 adversarial-judging as `_shared/independence-and-judging.md`? Or keep separate? User decision.
5. **#3 State-Before-Spawn** + **Surprise A (generation counter)** — merge into `_shared/state-contracts.md`.
6. **#4 Termination Labels** — template, not enum. Each skill keeps its domain-specific labels.
7. **#7 Pre-mortem seeding**, **#8 Iron-law gate**, **#9 Parallel critic quorum** — medium-value batch.

---

## Cost/benefit summary

| Extraction | Lines saved | Skills touched | Risk |
|---|---|---|---|
| Adversarial judging (DONE) | ~60-70 | 2-4 | Low |
| Structured output contract | ~180 | 9 | Very low |
| Files-not-inline contract | ~80 | 8 | Very low |
| Independence invariant | ~105 | 7 | Low |
| State-before-spawn + generation counter | ~245 | 9 | Low |
| Termination labels template | ~270 | 9 | Medium (template, not content) |
| Pre-mortem seeding | ~400 (net after shared file) | 4 | Medium |
| Iron-law gate pattern | ~220 (net) | 4 | Medium |
| Parallel critic quorum | ~120 (net) | 4 | Medium |

**Total potential savings if all extracted: ~1620 lines of boilerplate removed across 9 skills.**

---

## Next action

Present the extraction candidates to user. Do NOT auto-extract — each touches 7-9 skills and should be batched under user review.
