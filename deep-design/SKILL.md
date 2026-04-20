---
name: deep-design
description: Use when designing, specifying, architecting, or drafting a design for any system, feature, product, protocol, game, or workflow, and you want adversarial stress-testing before writing code. Trigger phrases include "design this", "design the system", "architect this", "draft a design", "design a feature", "design spec", "stress-test the design", "battle-test the design", "find flaws in this design", "design review", "harden the design", "pressure-test the design", "think through the design". DFS-based flaw-finding with parallel critic agents that stress-test until coverage saturates. Output is a battle-tested design document with an honest coverage report.
user_invocable: true
argument: The design concept or idea to spec out (a game, product, system, protocol, etc.)
---

# Deep Design Skill

Adversarially stress-test a design. Given a concept, validate input, draft a spec, attack it with parallel critic agents across orthogonal dimensions, fix discovered flaws using independent judge agents, and repeat until coverage is saturated. Output is a battle-tested design document with an honest coverage report.

## Execution Model

All operations use Claude Code primitives. The following contracts are non-negotiable:

- **All data passed to agents via files, never inline.** Spec content, dedup lists, angle definitions, fact sheets — all written to disk before the agent prompt. Inline data is silently truncated.
- **State written before agent spawn, not after.** `spawn_time_iso` is written to state.json before the Agent tool call. Spawn failure records `spawn_failed` status. Resume uses persisted state, never in-memory reconstruction.
- **Structured output is the contract; free-text is ignored.** Every judge and checker produces machine-parseable structured lines as the final lines of output. Coordinator reads only structured fields. Unparseable output triggers fail-safe classification (critical or conflict). Critic output files MUST contain `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` markers; files without these markers are treated as failed (not partially consumed).
- **No coordinator self-review of anything load-bearing.** Fact sheets, severity classifications, cross-fix checks, form-switch dedup, section-impact scores — all delegated to independent agents. The coordinator orchestrates; it does not evaluate.
- **Termination labels are honest.** "Conditions Met" or "Max Rounds Reached" — never "no critical flaws remain." Coverage fraction includes the denominator caveat. Unverified sections are listed explicitly.

**Shared contracts:** this skill inherits the four execution-model contracts (files-not-inline, state-before-agent-spawn, structured-output, independence-invariant) from [`_shared/execution-model-contracts.md`](../_shared/execution-model-contracts.md). The items listed above are the skill-specific elaborations; the shared file is authoritative for the base contracts.

**Subagent watchdog:** every `run_in_background=true` spawn (parallel critics, severity judges, rebuttal agents) MUST be armed with a staleness monitor per [`_shared/subagent-watchdog.md`](../_shared/subagent-watchdog.md). Use Flavor A with thresholds `STALE=5 min`, `HUNG=20 min` for Sonnet critics; `STALE=3 min`, `HUNG=10 min` for Haiku judges. `TaskOutput` status is not evidence of progress — output-file mtime is. Contract inheritance: `timed_out_heartbeat` joins this skill's per-angle termination vocabulary; `stalled_watchdog` / `hung_killed` join `angles.{id}.status`. A watchdog-killed critique angle is reported as coverage-lost in the final coverage fraction — never silently dropped.

## Philosophy

Good design survives adversarial scrutiny. This skill treats design as a **generate-then-break** loop: draft a design, attack it from every angle, fix the flaws, then attack again. Each critic agent is an expert in one dimension (balance, UX, edge cases, narrative, technical feasibility, etc.) trying to find holes. Flaws discovered in one round feed redesign in the next.

## Workflow

### Step 0: Input Validation Gate

Before any work begins, validate the concept. **Batch any clarifying questions** — if multiple questions surface in this step (concept rubric ambiguity, core-claim confirmation, alternatives selection), present ALL of them as a single numbered batch in one message. Never serially. The user answers once, then Step 1 begins.

**Concept rubric** — reject if any of these apply:
- Too vague to critique ("make a good app") — request specificity
- Already fully specified (more of an implementation request than a design) — offer to run critique-only mode
- Requests harmful design (weapon, exploit, manipulation system) — decline

**Core claim extraction:**
1. Read the concept and extract a 1-2 sentence core claim: the specific thing this design does that similar designs do not
2. Run the **specificity test**: "Would this claim be true of a system that does [X] instead of [Y]?"
   - Select **2 domain-adjacent alternatives** in the same problem class as the concept but with different primary mechanisms
   - For `deep-design`, valid alternatives: collaborative (not adversarial) review, single-pass critique, sequential-agent critique
   - The claim must **fail** to apply to both alternatives before passing the specificity test
   - If interactive mode: show user the claim + 2 alternatives, ask for confirmation
   - If claim passes: set `core_claim_calibrated: true`, store `core_claim` and `core_claim_sha256` in state.json
   - If claim fails after 2 attempts: set `core_claim_calibrated: false`; Layer 2 drift checks run in **degraded mode** (tighter threshold + DRIFT_CHECK_DEGRADED tag) — do NOT skip them

**Concept summary field:** The concept summary sent to all critics is the core claim text verbatim as extracted and locked at this step. The coordinator may append context but cannot replace or paraphrase the locked text.

**Print:** `Starting deep design on: {concept} [run: {run_id}]`

### Step 1: Initialize

- Generate run ID: `$(date +%Y%m%d-%H%M%S)` — e.g., `20260314-153022`
- Create directory structure:
  - `deep-design-{run_id}/state.json` — run state (see STATE.md for schema)
  - `deep-design-{run_id}/critiques/` — one file per critique angle
  - `deep-design-{run_id}/specs/` — versioned spec files
  - `deep-design-{run_id}/logs/` — `frontier_pop_log.jsonl` and `coverage_gaps.jsonl`
  - `deep-design-{run_id}/spec.md` — final output (written at Step 8)
- Write initial state.json with `core_claim`, `core_claim_sha256`, `core_claim_calibrated` from Step 0
- The spec template must include `CORE_MECHANISM_START` / `CORE_MECHANISM_END` delimiters enclosing the section describing the core mechanism. These delimiters are the reference boundary for Layer 1 drift comparison and must not be removed or moved by any agent.

### Step 2: Initial Design Draft

- Analyze the concept to understand core intent, target audience, and constraints
- Write `deep-design-{run_id}/specs/v0-initial.md` — a structured first-pass design covering:
  - Core concept & elevator pitch
  - Key mechanics/features
  - User/player flow
  - High-level technical approach
  - Known open questions
- This is deliberately a FAST draft — good enough to critique, not polished

### Step 3: Dimension Discovery (see DFS.md Phase 3a-3c)

- Enumerate CRITIQUE DIMENSIONS using the design-specific framework
- Required dimension categories (at least one angle per category must be explored):
  - **correctness** — does the design work as claimed?
  - **usability/UX** — can users actually use it?
  - **economics/cost** — is it affordable/sustainable?
  - **operability** — can it be operated/maintained?
  - **security/trust** — can it be abused or corrupted?
- Generate 2-4 critique angles per dimension; cap frontier at 40 angles total
- Depth-diversity rule: when displacing to stay under cap, cannot displace a dimension's only remaining depth-0 OR depth-1 angle
- **Each angle definition written to state.json at discovery time with:** `{angle_id, dimension, question, discovery_source: "coordinator_initial|critic_suggested", discovery_round, rationale}`. Angle definitions are immutable once written.
- **Frontier pop decisions logged** in `deep-design-{run_id}/logs/frontier_pop_log.jsonl`: `{angle_id, round, timestamp, score, reason}`
- **Stability trigger:** "no new DIMENSION CATEGORIES for 2 consecutive rounds" (not merely "no new angles")
- Build exhaustion map; populate frontier with all critique angles, priority-ordered
- Write state file

### Step 4: Critique Round

**Prospective gate (fires BEFORE spawning critics):**

The coordinator outputs a gate summary and STOPS. The user continues the conversation to proceed. This is the standard Claude Code turn-boundary interaction model — there is no blocking `[y/N]` prompt.

Gate content:
> Round {N+1}: up to {agents} agent calls × ~{token_estimate}k tokens/agent = structural bound ~${bound}. Spent so far: ~${cumulative}. Projected total to max_rounds: ~${projection}.

Projection includes: 6 spec-derived critics + 1 outside-frame critic + (estimated flaws × 2 judge calls) + 1 redesign agent (estimated at 3× critic cost) + 1 invariant-validation agent, with spec growth factor.

If any flaw is in `pending_user_acknowledgment` state, the gate prominently displays the proposed tension and requests explicit acknowledgment before proceeding.

User options at gate: continue the conversation (proceed), stop (triggers final synthesis), or redirect focus via message.

Stall handling: if no user response at a gate for 2 or more consecutive turns, the run auto-proceeds to final synthesis (not continuation).

**Autonomous mode:** Gate is skipped. `max_rounds` defaults to 3. Hard budget cap = $10 total. If budget is exceeded mid-round, that round completes, then the run terminates. CORE_TENSION flaws remain in `pending_user_acknowledgment` state in the final spec and cannot be silently reclassified.

**Spawn critics:**
- Pop up to 6 (`max_agents_per_round`) highest-priority critique angles from frontier using the declared scoring function. Selection policy is explicit and auditable via `logs/frontier_pop_log.jsonl`.
- **Also spawn 1 outside-frame critic (slot #7)** seeded from the original concept description ONLY (not the current spec). See "Outside-Frame Critic Prompt Template" section below.
- **Concept summary field sent to all critics = core claim text verbatim** (locked, not paraphrased). Coordinator may append context but cannot replace or paraphrase the locked text.
- Write all required data to files before spawning: latest spec, known-flaw-titles file (with flaw IDs), angle definitions
- For each angle, write angle to state.json with `spawn_time_iso` set **before** calling Agent tool
- Spawn background Agent (subagent_type: general-purpose) with file paths — not inline content
- Critic output files are content-addressed at `critiques/{angle_id}-{critic_agent_id}.md` — coordinator CANNOT overwrite these files
- If Agent tool returns an error (tool limit, spawn refused): record `status: "spawn_failed"`, `spawn_time_iso: null` in state.json; do NOT record as "spawned"; resume retries spawn

**Quorum:** Round complete if ≥ 4 of 6 spec-derived critics return parseable output within timeout. Outside-frame critic is tracked separately and does not affect quorum denominator.

**Timeout scaling:** 120s base; 180s for rounds 3+; ×1.5 for specs exceeding 3,000 words.

**Output integrity:** Critic output files MUST contain `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` markers. Files without these markers are treated as failed (not partially consumed).

**Circuit breaker:** If ≥ 3 consecutive rounds have any critic failures, halt immediately, log `SYSTEM_FAILURE_ROUND`, notify user at turn boundary, allow retry or abort.

**After completion:**
- For each completed agent: read critique file, extract flaws, new angles, dedup, update state
- **Spec-derived critics may suggest at most 1 new angle per round** (not 1-3). New angles are logged with `discovery_source: "critic_suggested"` and are immutable once written.
- **Severity classification delegated to independent judge agent** — coordinator does not classify; unparseable judge output → fail-safe critical
- **Section-impact scores assigned by independent agent** — not coordinator; prevents self-serving deflation of foundational section scores
- **Form-switch dedup check performed by consistency checker** — not coordinator
- Run coverage evaluation: identify uncritiqued dimensions, generate new angles if needed
- Update running synthesis
- Increment round

### Step 5: Synthesis with Independent Judges

For each round's flaws before redesign:

**Fact sheet agent (independent):**
- Spawn a fact-sheet agent that reads the current spec and produces structured output:
  ```
  RECOVERY_BEHAVIORS: [{"component": "<name>", "behavior": "<description>"}, ...]
  ```
  This must be the **final structured line** of the agent's output. Coordinator reads ONLY this line; unparseable = empty list (not coordinator fallback text).
- When evaluating `RECOVERY_MECHANISM_CITED` in judge output: the component field must appear in the RECOVERY_BEHAVIORS list. Names not in the list are treated as hallucinated → `mechanism_applies: false`.

**Severity judge (independent) — two-pass blind severity protocol:**
1. The coordinator strips the `SEVERITY_CLAIM` block from the raw critic file to produce `judge_input/{flaw_id}.md`. The original critic file remains immutable. The stripping is recorded in state.json as `judge_input_stripped: true`.
2. A judge agent receives only: `{flaw_id, judge_input_file_path, fact_sheet_path}` — a strict schema enforced by a validator before spawn. If validator fails: conservative enforcement (reject unknown fields, continue).
3. The judge first classifies severity without knowing the critic's severity claim (pass 1), writes an independent verdict to `judge_verdicts/{flaw_id}.md`.
4. The coordinator then provides the critic's severity claim (from `severity_claims/{flaw_id}.txt`) as a second-pass prompt. The judge confirms, upgrades, or downgrades with rationale in a second-pass addendum.
5. See "Judge Prompt Template" section below for required adversarial mandate.

**Challenge token:**
- Challenge execution is delegated to an independent challenger agent — the coordinator can request but cannot execute challenges.
- Each flaw gets one challenge token if the coordinator disputes severity.
- The challenger reads the original critic file + judge verdict + current spec and renders an independent decision.
- Challenge timing: challenges against flaws classified in rounds N-2 or earlier are rejected as untimely.

**GAP_REPORT mechanism:**
- Critics may file `GAP_REPORT: {"references_flaw_id": "<flaw_id>", "gap_description": "<what the fix missed>"}` to re-open a closed flaw whose fix was insufficient.
- GAP_REPORT bypasses dedup, does NOT consume challenge token, re-opens flaw for re-fix.
- **GAP_REPORT cap: max 2 GAP_REPORTs per flaw per run (globally, not per-critic).** Tracked in `flaws[id].gap_report_count` in state.json (persisted). A third GAP_REPORT for the same flaw causes the coordinator to file a `PERSISTENT_TENSION` note instead of re-opening.

**Final-round pending judge sequencing:**
- At Step 5, check: is `current_round == max_rounds`?
- If yes (final round): any pending judge run MUST complete before Step 5 finalizes
- Timeout in final round: retain ORIGINAL severity (not fail-safe critical); log `CHALLENGE_TIMEOUT_FINAL_ROUND: {flaw_id}`
- Timeout in non-final round: fail-safe critical escalation applies

**Flaw validation (coordinator reads structured outputs, applies these checks):**
1. **Contradiction check:** Does this flaw contradict another flaw? Contradictory flaws indicate at least one is misdiagnosed.
2. **Premise check:** Would this flaw manifest in practice, or does the design's existing strengths already handle it?
3. **Existence check:** Would cutting the flawed feature produce a better design than patching it?
4. **Nerf check:** Does the proposed fix weaken a core strength? If so, look for a format-level redesign instead.
5. **Falsifiability check:** Is this flaw verifiable/falsifiable? Reject unfalsifiable claims (e.g., "this might be slow" with no scenario, "users might not like this").

Flaws that fail validation are downgraded to "disputed" with a rationale. Disputed flaws are not redesigned but are noted explicitly.

### Step 6: Redesign Phase

After flaw validation, if accepted critical or major flaws exist:

**Independent redesign agent (coordinator does NOT write the updated spec):**
1. Coordinator writes ungrouped flaw ID list + raw critic file paths to a hand-off file (no coordinator theme labels, groupings, or summaries).
2. Coordinator spawns an independent redesign agent that reads raw critic files directly.
3. Redesign agent receives:
   - Accepted flaw list: IDs + paths to raw critic files
   - Current spec path
   - Do-not-weaken list: mechanical projection of the full `component_invariants` array from state.json, verbatim, in written order — no coordinator selection or omission
4. The redesign agent performs its own internal grouping. It is the sole authoring agent for spec changes.
5. Redesign agent marks each change with `<!-- Fixed: <description> -->`.
6. Redesign agent prompt includes: "You MUST NOT weaken any invariant on the do-not-weaken list. If a fix requires weakening one, file a DESIGN_TENSION instead. You MUST NOT remove or move CORE_MECHANISM_START/END delimiters."
7. See "Redesign Agent" section below.

**Complexity budget per round:**
- Rounds 1–2: ≤ 2 new components or state fields per redesign
- Rounds 3+: ≤ 1 new component or state field per redesign
- Budget overflows → redesign agent files DESIGN_TENSION (appears in open issues)
- Complexity delta tracked in state.json.

**CORE_TENSION path:**
- Before filing a CORE_TENSION, the challenger agent must confirm it's a genuine irresolvable tension (not just a difficult fix).
- Final-round CORE_TENSION → `UNACKNOWLEDGED_TENSION` in final spec (not silent reclassification).

**N-way co-round consistency check (independent agent):**
- Write ALL proposed fixes for this round to a single file
- Spawn cross-fix checker with all fixes in one call; it checks fixes against each other AND against component_invariants
- Coordinator does NOT perform this check
- Structured output: `CONFLICT: {fix_a, fix_b, description}` or `OK`; `ORDERING_EDGE: {from, to, basis}` for new dependencies
- Unparseable → `CONFLICT: assumed`

**Component invariant store (state.json):**
- `component_invariants[key]` stores: `{invariant, constraint_direction: "tightened"|"relaxed"|"neutral", tightened_rounds: [N, ...]}`
- `component_invariants` is append-only; coordinator-write-prohibited. Only the invariant-validation agent and redesign agent may write entries.
- DIRECTION_REVERSAL warning when constraint_direction = "relaxed" and tightened_rounds is non-empty
- Per-component invariants cannot store cross-component ordering constraints; those go in `ordering_graph`

**Ordering graph:**
- `ordering_graph: {edges: [{from, to, established_round, basis}]}` stored in state.json
- Start empty (`edges: []`); add edges ONLY from cross-fix checker's structured `ORDERING_EDGE` output
- Cross-fix checker detects cycles when new edges are added
- Do NOT infer ordering edges from prose

**Component invariant key migration (at inventory-rebuild time):**
- When rebuilding the canonical component inventory from the new spec, detect renames via semantic equivalence
- If a component's canonical name changed: atomically rename the corresponding `component_invariants` key to the new canonical name in the same state write
- Log old→new in `component_name_history`
- Semantic normalization (at check time) handles new-fix aliases → canonical; key migration handles canonical → new-canonical on rename. These are distinct operations; neither substitutes for the other.

**Concept drift check:**
- **SHA256 role — anti-tampering ONLY:** Verify `core_claim_sha256` matches SHA256 of stored `core_claim` text before using it as drift reference. Mismatch triggers `CORE_CLAIM_TAMPERED` and halts the run. SHA256 detects bit-level modification of the stored string. It does NOT detect semantic drift.
- **Layer 1 — semantic comparison:** Compare text within `CORE_MECHANISM_START`/`CORE_MECHANISM_END` delimiters against stored `core_claim` embedding. Base threshold: 0.80 — below this, `DRIFT_WARNING` is issued. Critical threshold: 0.65 — below this, `DRIFT_CRITICAL` triggers, halting redesign and routing affected flaws to PERSISTENT_TENSION.
- **Layer 2 — discriminating test:** Compare current spec to core claim using 2 domain-adjacent alternatives. Alternatives are refreshed every 2 rounds of major redesign but only against the original concept (not the current spec). Original alternatives are retained permanently as baseline.
  - If `core_claim_calibrated: false`: run with 50% tighter threshold (effective threshold 0.95) + tag as DRIFT_CHECK_DEGRADED. Do NOT skip.
  - If `core_claim_calibrated: true`: run normally (base threshold 0.80).

**After redesign — Invariant-Validation Agent (NEW, runs before next round):**
See "Invariant-Validation Agent" section below. Violations block round advancement (treated as critical flaws).

**Write updated spec:**
- `deep-design-{run_id}/specs/v{N}-post-round-{round}.md`
- Written by the redesign agent, not the coordinator
- The next critique round uses this updated spec

**Print summary:** `{N} flaws found, {M} validated, {K} disputed, {J} fixed in redesign`

### Step 7: Termination Check (see DFS.md Step 6)

**Primary termination mechanism: `max_rounds` (default 5).** All runs are expected to complete at `max_rounds` unless early exit fires first. "Conditions Met" is early exit — achievable but not the expected path.

**Early exit (all conditions must be true — this is a quality signal, not the expected path):**
1. All 5 required dimension categories have ≥ 1 angle that reached "explored" status (`quorum_met: true`)
2. No new DIMENSION CATEGORIES discovered by spec-derived critics for 2 consecutive rounds (outside-frame critic new-category discoveries do not reset this clock)
3. No open critical flaws (excluding those tagged `accepted_with_tension` or in `pending_user_acknowledgment` state)

**Hard stop:** `max_rounds` (default 5) → label "Max Rounds Reached"

Note: "no major flaws unfixed" is tracked as a quality metric but is NOT a hard termination gate — major flaws may be accepted with rationale.

Note: "frontier empty" is NOT a termination condition. The frontier fill rate (up to +8 angles/round with outside-frame critic) exceeds drain rate (6/round) in most domains, making an empty frontier structurally unreachable under normal operation.

### Step 8: Final Spec

- **Do NOT read all raw critique files** — use the coordinator summary + per-critique mini-syntheses + latest spec + state file
- Spawn a Sonnet subagent to write `deep-design-{run_id}/spec.md`
- Termination label: "Conditions Met" or "Max Rounds Reached" — never "no critical flaws remain"
- Coverage report must include: dimensions covered, required categories covered, honest coverage caveats section, list of unverified sections, list of open issues at termination
- Includes: resolved flaws, disputed flaws, accepted tradeoffs, open questions, implementation notes

### Step 9: QA Pass (automatic offer)

After writing `deep-design-{run_id}/spec.md`, offer a QA pass:

```
QA pass available. Run deep-qa on this spec? [y/N]
(Recommended: catches specification gaps, underspecified components, and implementation
inconsistencies that design critics — focused on the design process — may have missed.)
```

- If **y**: invoke deep-qa with `--type doc` on `deep-design-{run_id}/spec.md`
  - QA run_id: `{parent_run_id}-qa`
  - QA report written to: `deep-design-{run_id}/qa-report.md`
  - The QA pass is read-only — it does NOT modify the spec
- If **n**: skip. Final output remains `deep-design-{run_id}/spec.md` alone.

Note: deep-qa targets the **final spec as a document** — it finds defects in completeness,
consistency, and feasibility, not the design decisions themselves (those were deep-design's domain).

## Golden Rules

1. **Critics must be adversarial.** An agent that says "looks good" is a failed critic. Push agents to find REAL problems, not cosmetic issues.
2. **Every flaw needs a concrete scenario.** "This might be unbalanced" is not a flaw. "A user who does X in situation Y breaks the system because Z" is a flaw.
3. **Fixes must address root causes.** The fix for "trivia questions make it too easy for bots" is not "ban trivia" — it's redesigning the question/interaction system.
4. **Check fixes for cascading effects.** Every fix is a design change. Design changes can introduce new flaws.
5. **Classify honestly.** Don't inflate minor flaws to critical. Don't downgrade critical flaws to minor.
6. **The design is never perfect — it's "good enough."** Termination means coverage is saturated, not zero flaws.
7. **Maintain design coherence.** Fixes must be consistent with the core concept. If a fix contradicts the core vision, flag the tension.
8. **Validate flaws before accepting them.** A flaw is only real if it survives the falsifiability check, contradiction check, and premise check. Cross-check every flaw against the full set of critiques — contradictory flaws indicate at least one is misdiagnosed.
9. **Never nerf what you can redesign.** Ask: "Can I change the FORMAT or CONTEXT so the strength doesn't matter?" Redesign the battlefield, don't handicap the fighters.
10. **Question whether the feature should exist at all.** Before fixing a flawed mechanic, ask: "Does this mechanic earn its place?" Removing a broken feature is often better than patching it.
11. **Critique what's missing, not just what's there.** The most dangerous flaws are often omissions — components referenced but not specified. A label ("prompt pool," "matchmaking system") is not a design.
12. **Independence invariant.** The coordinator orchestrates; it does not evaluate. Any load-bearing evaluation (severity classification, fact verification, cross-fix consistency, section-impact scoring) must be performed by an independent agent with no stake in the outcome.
13. **Judges must be adversarial too.** An independent judge that rubber-stamps critical claims is as useless as a critic that rubber-stamps good design. A 100% acceptance rate from a judge is evidence of failure.
14. **Input transparency.** Log all angle definitions with source and rationale. The independence invariant protects outputs — you must audit inputs.

## Anti-Rationalization Counter-Table

These are excuses agents use under pressure to inflate "good" verdicts on weak designs. Each row is a defensive entry — when you catch yourself thinking the excuse, look at the reality.

| Excuse | Reality |
|---|---|
| "This is just an MVP — we'll iterate" | MVPs ship and ossify. The design must work in v1, not v3. Underspecified components do not self-resolve after launch. |
| "Users will understand the limitation" | Users do not read docs. Test the failure mode via concrete scenario, not assumed goodwill. |
| "This edge case is unlikely" | Unlikely × scale = certain. Apply the falsifiability check: construct the scenario where it manifests. |
| "We can patch it later" | Later is now in six months. The existence check applies: if patching is inevitable, redesign instead. |
| "The critic is being pedantic" | If the critic produced a falsifiable scenario, the flaw is real. Apply the 5 validation checks, not dismissal. |
| "This component is well-understood — no need to spec it" | A label ("matchmaking system", "prompt pool") is not a design. Underspecification IS a critical flaw per Golden Rule 11. |
| "The judge accepted everything — the critics were thorough" | A judge with 100% acceptance rate is broken (Golden Rule 13). Expected acceptance is 30-60%. Re-read pass-1 + pass-2 verdicts. |
| "Outside-frame critic is overkill — the spec-derived critics covered it" | Spec-derived critics are bounded by the spec's vocabulary. The outside-frame critic is non-optional; its absence is a quorum failure mode. |
| "Just one more round will resolve this tension" | DRIFT_CRITICAL or PERSISTENT_TENSION at round N means design fundamentals are off. File CORE_TENSION and escalate — do not loop. |
| "Concept drift detection is overzealous — the spec still sounds right" | Layer 1 + Layer 2 thresholds are explicit (0.80 / 0.65). Disagreement requires honestly changing the threshold, not bypassing the check. |
| "The fix weakens an invariant but the old invariant was too strict" | Invariants are append-only and coordinator-write-prohibited. Relaxing one triggers DIRECTION_REVERSAL. File DESIGN_TENSION, do not silently relax. |
| "I'll classify this flaw for the judge — the agent is slow" | Severity classification MUST be delegated (Golden Rule 12 / Independence invariant). Coordinator self-classification is an invariant violation. |
| "GAP_REPORT keeps firing on the same flaw — the critic is stuck" | Third GAP_REPORT triggers PERSISTENT_TENSION by design. That is the signal the fix cannot close the gap — escalate, do not suppress. |
| "Quorum is close enough — 3 of 6 is fine" | Quorum is ≥ 4 of 6 spec-derived critics. Close-enough is a failed round; do not paper over with the outside-frame critic (tracked separately). |

When you catch ANY of these in your reasoning, stop and apply the relevant validation gate (falsifiability, premise, contradiction, nerf, existence checks) or independence delegation.

## Self-Review Checklist

- [ ] State file is valid JSON after every round
- [ ] `generation` counter incremented after every state write
- [ ] `core_claim_sha256` stored at Step 0; verified before each drift check
- [ ] No critique angle has status "in_progress" after round completes
- [ ] No `spawn_failed` angles treated as "spawned" — resume retries spawns, not waits
- [ ] Every critique file has: Flaws + Severity + Scenario + Suggested Fix + Mini-Synthesis + New Angles
- [ ] No critique angle explored > 2 times
- [ ] All critical flaws have a resolution (fixed, accepted, or disputed with rationale)
- [ ] All major flaws have a resolution or explicit acceptance with rationale
- [ ] Disputed flaws are documented in coordinator summary — not silently dropped
- [ ] Final spec does NOT read raw critique files — uses coordinator summary + mini-syntheses
- [ ] Final spec is internally consistent (no fix contradicts another fix)
- [ ] Final spec traces each design decision to the flaw that motivated it
- [ ] No stale `component_invariants` keys from renamed components (migration logged in `component_name_history`)
- [ ] Ordering graph edges sourced only from cross-fix checker structured output — not inferred from prose
- [ ] Termination label is "Conditions Met" or "Max Rounds Reached" — never "no critical flaws remain"
- [ ] Coverage report includes unverified sections and open issues
- [ ] GAP_REPORT counts persisted in state.json `flaws[id].gap_report_count` (not in-memory only)
- [ ] Invariant-validation agent ran after this round's redesign
- [ ] Judge prompt includes adversarial mandate
- [ ] Prospective gate uses turn-boundary model (not blocking prompt)
- [ ] Concept summary sent to critics matches core claim verbatim
- [ ] Frontier pop decisions logged in `logs/frontier_pop_log.jsonl`
- [ ] Outside-frame critic spawned this round

## Critic Agent Prompt Template

When spawning each spec-derived critic agent, use this prompt structure. All data passed via file paths — not inline.

```
You are an adversarial design critic. Your job is to BREAK this design — find flaws, exploits, edge cases, and failure modes. Do NOT be nice. Do NOT say "overall this is good." Find REAL problems.

**Your critique dimension:** {angle.dimension}
**Your specific angle:** {angle.question}
**Design concept:** {concept_summary}

(concept_summary is the locked core claim text verbatim — it has not been paraphrased.)

**Current design spec file:** {spec_file_path}
Read this file to get the full spec.

**Known flaws file:** {known_flaws_file_path}
Read this file for flaw IDs and titles. Do NOT repeat any flaw with these IDs.

**Before filing flaws — Diagnostic Inquiry (REQUIRED):**

Answer each of these through the lens of your critique dimension BEFORE producing flaws. These MUST appear as a "Diagnostic Answers" section in your output file, above the Flaws section.

1. What is the mechanism this dimension depends on, and does the spec specify it (vs. merely name it)?
2. What is the most realistic consumer/user scenario in this dimension, and what does that scenario require that the spec must provide?
3. What assumption does the design make about this dimension that is not stated in the spec?
4. If this dimension's worst-case scenario occurs, which specific component in the spec absorbs the impact — and does the spec actually give that component the mechanism to do so?
5. What does the spec claim about this dimension that, if wrong, invalidates the core mechanism?

The Diagnostic Answers section forces you off auto-pilot before proposing flaws. Flaws that contradict your own diagnostic answers are likely misdiagnosed and will be dropped at validation.

**Instructions:**
1. Read the design carefully through the lens of your specific critique dimension
2. Think about real users — what would they ACTUALLY do? (not what the designer hopes)
3. Construct concrete scenarios where the design fails
4. For each flaw, provide:
   - A clear title
   - Severity: critical (design-breaking) / major (significantly degrades) / minor (polish)
   - A specific scenario demonstrating the flaw
   - WHY it's a problem (the root cause, not just the symptom)
   - A suggested fix direction
5. Find every load-bearing flaw — **no cap**. Quality and signal density matter more than count. Exclude nitpicks: cosmetic issues, stylistic preferences, prose polish, taste-based wording quibbles, and "this could be more elegant"-class concerns. Every filed flaw must name a concrete failure mode or risk to a real consumer — not a taste preference. A 15-flaw critique padded with cosmetics is worse than a 3-flaw critique of load-bearing defects.
6. If you believe a previously-closed flaw was insufficiently fixed, file a GAP_REPORT:
   `GAP_REPORT: {"references_flaw_id": "<flaw_id>", "gap_description": "<what the fix missed>"}`
   This bypasses the dedup list and does not consume a challenge token.
7. Report **1 new critique angle** you discovered (genuinely novel, not rephrased). If you have more than 1 new angle, choose the most novel one; suppress the rest and include a MISSED_COVERAGE note for each suppressed angle.
8. Write findings to: {critique_path}
9. Use the FORMAT specified in FORMAT.md

**Structured output format:** Your output file MUST include STRUCTURED_OUTPUT_START and STRUCTURED_OUTPUT_END markers enclosing all machine-readable fields. Files without these markers are treated as failed.

**Severity claim format:** After STRUCTURED_OUTPUT_END, include a SEVERITY_CLAIM block with your severity assertions for each flaw. This block will be stripped before the judge receives your output, enabling blind severity assessment.

FALSIFIABILITY REQUIREMENT: Every flaw must be falsifiable — it must be possible to construct a scenario where the flaw manifests AND a scenario where it does not. Claims like "users might not like this" or "performance could be slow" without a specific threshold and mechanism are not flaws — they are concerns. Unfalsifiable concerns should be filed as minor notes, not flaws.

IMPORTANT: You succeed by finding real problems. You fail by rubber-stamping the design. Think like:
- A min-maxing user looking for exploits
- A confused first-time user who didn't read instructions
- A hostile actor trying to abuse the system
- An engineer who has to actually build this — "where does this data actually come from?"
- A product person measuring engagement/retention

CRITICAL — AVOID THESE COMMON CRITIC MISTAKES:
- **Don't contradict yourself or other findings.** If the design has a strength that handles your flaw, acknowledge it.
- **Question your own premise.** For each flaw, ask: "Is this actually a problem in practice, or only in a vacuum?"
- **Don't default to nerfing.** If something is too strong, the fix is usually to change FORMAT or CONTEXT.
- **Ask whether the feature should exist.** Before proposing a fix, consider: would cutting it produce a better design?
- **Your suggested fix is a suggestion, not a prescription.** Focus on clearly identifying the PROBLEM.
- **Critique what's missing, not just what's there.** If a component is referenced but not designed, that's an underspecification flaw. A label is not a design.

**Calibration:**
- **Good application**: Constructing a realistic consumer scenario that breaks a specific invariant in the spec. Identifying a load-bearing component referenced by name but never specified — a label, not a design. Finding a contradiction between two sections that both claim to govern the same behavior. Flagging a mechanism the spec describes by outcome but not by how the outcome is produced.
- **Taken too far**: Treating every unstated edge case as a critical flaw — specs cannot enumerate every case and shouldn't try. Flagging every aspirational claim ("scalable", "robust") as a false guarantee. Rejecting the design because it makes a conscious tradeoff that favors one axis over another — tradeoffs are design choices, not flaws. Demanding implementation detail at the design layer. Inflating "could be clearer" to critical.
```

## Outside-Frame Critic Prompt Template

When spawning the outside-frame critic (slot #7), use this prompt structure. This critic is seeded from the original concept description ONLY — not the current spec.

```
You are an adversarial outside-frame critic. Your job is NOT to critique the spec as written. Your job is to identify what a working implementation of this concept would NEED that this spec never mentions.

**Original concept description:** {original_concept_description}

(You are NOT given the current spec. Do not ask for it. Your value comes from being unconstrained by the spec's vocabulary and framing.)

**Question to answer:** What would a working implementation of [{concept_name}] need that this spec never mentions?

**Instructions:**
1. Think about the concept from first principles — what does it actually require to work in practice?
2. Consider: infrastructure, operations, user onboarding, failure recovery, dependencies, regulatory/legal, team/org requirements, data sources, integrations
3. For each missing element, explain:
   - What it is
   - Why it is necessary for the concept to work
   - Why the spec might have omitted it
4. You may suggest up to **2 new critique angles** for the spec-derived critic pool. These angles must be genuinely novel dimensions not visible from within the spec's vocabulary.
5. Write findings to: {critique_path}
6. Use the FORMAT specified in FORMAT.md

**Structured output format:** Your output file MUST include STRUCTURED_OUTPUT_START and STRUCTURED_OUTPUT_END markers. Files without these markers are treated as failed.

Your new-category discoveries do NOT reset the early-exit stability clock (which tracks spec-derived critic discoveries only). This exemption makes early exit achievable while preserving your value for discovering missing dimensions.

IMPORTANT: You succeed by identifying genuine gaps. You fail by critiquing what the spec says. Your angle is orthogonal to the spec-derived critics — you bring outside context they cannot.
```

## Judge Prompt Template

When spawning a severity judge, use this prompt structure.

```
You are an independent severity judge. Your job is to assess whether a filed design flaw is valid and correctly classified. You are NOT a rubber-stamp. You are a gatekeeper.

**You succeed by REJECTING or DOWNGRADING flaws. You fail by rubber-stamping.**

A 100% acceptance rate is evidence of failure. Well-specified designs with 6 critics over one round expect 30-60% of claims accepted at claimed severity. Your acceptance rate should approach, but not match, the critic's claim rate.

**Pass 1 input:**
- Flaw description: {judge_input_file_path} (severity field stripped — you will assess severity independently)
- Fact sheet: {fact_sheet_path}

**Pass 1 instructions:**
Assess the flaw using all 5 validation checks as genuine gatekeepers (not box-ticking):

1. **Contradiction check:** Does this flaw contradict another accepted flaw? If yes, at least one is misdiagnosed.
2. **Premise check:** Would this flaw actually manifest in practice? Does the design's existing structure already handle it?
3. **Existence check:** Would removing the flawed feature improve the design? If so, the fix is removal — not patching.
4. **Nerf check:** Does the proposed fix assume worst-case behavior that the design structure already constrains? If so, reject the fix direction.
5. **Falsifiability check:** Can you construct a concrete scenario where this flaw manifests AND a scenario where it does not? If not, the claim is unfalsifiable — reject or downgrade to minor note.

Assign your independent severity: critical / major / minor / rejected.

Write your pass 1 verdict to: {verdict_path}

**Pass 2 input (provided after pass 1 verdict is written):**
- Critic's original severity claim: {severity_claim_path}

**Pass 2 instructions:**
Review your pass 1 verdict against the critic's claim. You may:
- Confirm your verdict (with rationale for agreement or disagreement with the critic's claim)
- Upgrade your severity if the critic's evidence reveals something you underweighted in pass 1
- Downgrade your severity if the critic's claim is inflated relative to your independent assessment

Write your pass 2 addendum to the same verdict file. The final severity is your pass 2 conclusion.

**Calibration:** A critical flaw blocks correct operation or breaks a core guarantee. A major flaw significantly degrades value or creates a meaningful failure mode. A minor flaw is an edge case, cosmetic, or easily mitigated in practice. If the flaw is real but minor, classify it minor — do not inflate to signal diligence.
```

## Redesign Agent

The redesign agent is an independent subagent responsible for ALL spec changes. The coordinator does not write the updated spec.

**Inputs:**
- Hand-off file containing: flat ungrouped accepted flaw IDs + raw critic file paths (no coordinator theme labels, summaries, or groupings)
- Current spec path
- Do-not-weaken list: full `component_invariants` array verbatim from state.json, in written order — no coordinator selection or omission

**Outputs:**
- New versioned spec at `deep-design-{run_id}/specs/v{N}-post-round-{round}.md`
- Each change marked with `<!-- Fixed: <description> -->` annotation (contractual obligation)
- DESIGN_TENSION filings (if complexity budget exceeded or fix would weaken an invariant)

**Independence status:** Fully independent for redesign decisions. Receives no coordinator framing of flaw causes. Performs its own internal grouping.

**Constraints:**
- MUST NOT weaken any invariant on the do-not-weaken list
- MUST NOT remove or move CORE_MECHANISM_START/END delimiters
- Complexity budget enforced per round (≤2 new components/fields rounds 1-2; ≤1 for rounds 3+)
- If a fix requires weakening an invariant OR exceeds complexity budget → file DESIGN_TENSION instead

## Invariant-Validation Agent

After each redesign, BEFORE the next critique round, spawn the invariant-validation agent.

**Inputs:**
- `component_invariants` from state.json
- `ordering_graph` from state.json
- New versioned spec

**Outputs:**
For each invariant:
```
INVARIANT_OK: {key}
INVARIANT_VIOLATION: {key, invariant, spec_section, evidence}
```

For each `<!-- Fixed: FIX-X -->` annotation in the new spec:
```
VERIFIED: {fix_id, annotation_location}
STALE: {fix_id, annotation_location, reason}
```

Inter-round cross-fix check (receives all prior-round accepted fix descriptions from state.json + new spec):
```
REGRESSION: {prior_fix_id, spec_section, description}
OK
```

**Failure escalation:**
- `INVARIANT_VIOLATION` blocks round advancement (treated as critical flaws requiring immediate fix before proceeding)
- Unparseable output → assumed violation (fail-safe)
- Agent spawn failure → treated as invariant violation (blocking), not quorum failure
- The circuit breaker does not apply to invariant-validation agent failures

**Independence status:** Fully independent. Its findings are not subject to coordinator review or override.

---

*Supplementary files: DFS.md (frontier management), FORMAT.md (critique file format), STATE.md (state schema detail)*
