# Synthesis

## Coordinator Summary (updated after each round)

**The coordinator MUST NOT accumulate raw critique files across rounds.**

After each round, write `deep-design-{run_id}/coordinator-summary.md` — a structured summary of ALL findings so far. This is the coordinator's ONLY source of prior-round context. Individual critique files are NOT read by the coordinator after being summarized.

Spawn a **Haiku subagent** to write this summary from the round's critique files — this keeps the coordinator context clean.

### Coordinator Summary Format

```markdown
## Round {N} Coordinator Summary

### Validated Flaws (accepted into redesign)
- [flaw_001] CRITICAL: {title} — {1-line root cause} — Status: {open|fixed}
- [flaw_002] MAJOR: {title} — {1-line root cause} — Status: {open|fixed}

### Disputed Flaws (failed validation — NOT redesigned)
⚠️ These MUST NOT be silently dropped:
- [flaw_003] MAJOR → DISPUTED: {title} — {dispute rationale}
- [flaw_004] CRITICAL → DISPUTED: contradicts flaw_001 — {which finding is likely wrong}

### Minor Flaws (noted, not redesigned unless trivial)
- [flaw_005] MINOR: {title} — {1-line description}

### Re-opened Flaws via GAP_REPORT
- [flaw_002] RE-OPENED by {angle_id}: fix insufficient — {gap_description}

### Coverage State
- Dimensions with ≥1 explored angle: {list}
- Dimensions not yet explored: {list}
- Required categories covered: {list}
- Required categories NOT yet covered: {list}
- Timed-out angles this round: {list or "none"}
- spawn_failed angles this round: {list or "none"}

### Design Changes This Round
- {what changed, which flaw motivated it, which spec version}

### Coverage Gaps This Round
- Cap-dropped angles: {angles suppressed by 1-angle cap, references suppressed_angles.jsonl}
- Never-generated: {MISSED_COVERAGE filings by critics}
- Failed angles: {angles that popped but failed quorum}
```

**Rules:**
- No word budget. The structure provides natural compression by section.
- Disputed flaws have a dedicated section — they cannot be silently omitted.
- Re-opened flaws via GAP_REPORT must be listed — they bypass dedup and must be re-fixed.
- Write the summary as a Haiku subagent to keep coordinator context clean.

---

## Coordinator Context Budget

The coordinator's effective per-round context should be:
- Coordinator summary: ~2-4k tokens
- Current round's mini-syntheses: ~1-3k tokens
- State file / frontier: ~1-2k tokens
- **Total: ~4-9k tokens** per round (vs. 50k–200k if accumulating raw critique files)

**Never read raw critique files in the coordinator session.** Let the summary and mini-syntheses carry the context.

---

## Independent Judges (Step 5)

**Independence invariant:** The coordinator does not evaluate. All load-bearing evaluation is delegated to independent agents.

### Fact Sheet Agent

Before severity classification, spawn an independent fact-sheet agent:
- Reads the current spec (by file path)
- Produces structured output as the **final line**:
  ```
  RECOVERY_BEHAVIORS: [{"component": "<canonical_name>", "behavior": "<description>"}, ...]
  ```
- Coordinator reads ONLY this structured line; free-text in the response is ignored
- If output is unparseable: `RECOVERY_BEHAVIORS: []` (empty, not coordinator fallback)
- Write the RECOVERY_BEHAVIORS to `deep-design-{run_id}/fact-sheet-round-{N}.json` for audit

**RECOVERY_MECHANISM_CITED validation:**
When a severity judge's output includes a claim that a recovery mechanism exists for a component:
- Check whether the component name appears in the RECOVERY_BEHAVIORS list
- Component names not in the list are treated as hallucinated → `mechanism_applies: false`
- This prevents severity downgrading based on fabricated mechanism references

### Severity Judge Agent — Two-Pass Blind Severity Protocol

**Two-Pass Blind Severity Protocol:**
1. Coordinator strips SEVERITY_CLAIM block from raw critic file → writes stripped version to `judge_inputs/{flaw_id}-stripped.md`
2. Judge receives: `{flaw_id, stripped_input_path, fact_sheet_path}` via strict schema. Validator enforces schema before spawn (unknown fields rejected; fail = conservative enforcement, not halt).
3. Judge writes independent verdict to `judge_verdicts/{flaw_id}-pass1.md` WITHOUT knowing critic's severity claim.
4. Coordinator then provides critic's severity claim (from `severity_claims/{flaw_id}.txt`) as second-pass context. Judge confirms, upgrades, or downgrades with rationale.
5. Final verdict = second-pass output.

**Judge prompt mandate:**
```
JUDGE MANDATE: You succeed by REJECTING or DOWNGRADING flaws. You fail by rubber-stamping. Your acceptance rate should approach, but not match, the critic's claim rate. A 100% acceptance rate is evidence of failure. Calibration: well-specified designs with 6 critics over one round expect 30-60% of claims accepted at claimed severity.
Apply each validation check (contradiction, premise, existence, nerf, falsifiability) as a genuine gatekeeper, not a pro-forma step. Reject unfalsifiable claims. Dispute flaws that contradict other accepted flaws.
```

### Severity Challenge Token

Each flaw gets one challenge if the coordinator disputes the judge's severity:
- Token states: `available` → `challenged` → `exhausted`
- Challenge timing constraint: challenges against flaws classified in round N-2 or earlier are rejected as untimely
- Once `exhausted`, no further challenges are accepted for that flaw
- **Challenge execution is delegated to an independent challenger agent.** The coordinator can request a challenge but cannot execute it.
- The challenger agent reads: original raw critic file + judge verdict + current spec.
- The challenger agent produces: CHALLENGE_UPHELD or CHALLENGE_REJECTED with rationale.
- **CORE_TENSION filing requires challenger agent confirmation** before the coordinator can reclassify a flaw as a core tension.

### GAP_REPORT Mechanism

Critics may file a GAP_REPORT to re-open a previously closed flaw:
```
GAP_REPORT: {"references_flaw_id": "flaw_007", "gap_description": "Fix only addresses the named component but the same invariant violation occurs in the orchestrator path"}
```
- GAP_REPORT **bypasses dedup** — it is not checked against the known-flaw-titles file
- GAP_REPORT does **NOT consume a challenge token**
- GAP_REPORT re-opens the flaw (`status: "open"`) with `gap_note` set
- The re-opened flaw must be addressed in the redesign phase like any other open flaw
- GAP_REPORT is logged in the coordinator summary under "Re-opened Flaws via GAP_REPORT"
- **GAP_REPORT cap: 2 per flaw per run globally** (not per-critic). Tracked in `flaws[id].gap_report_count` in state.json. Crash-safe because it's persisted.
- "Per flaw per run" means total across all critics for that flaw.
- A third GAP_REPORT on the same flaw → coordinator files a PERSISTENT_TENSION note instead of re-opening the flaw.

### Final-Round Pending Judge Sequencing

At Step 5, the coordinator checks: `current_round == max_rounds`?

**If NOT final round:**
- Timeout on judge run → fail-safe: `SEVERITY: critical`; flaw severity escalated
- This is the standard behavior

**If final round (current_round == max_rounds):**
- Any pending judge run **must complete before Step 5 finalizes**
- Coordinator waits for pending judge (blocking, up to 120s additional)
- Timeout in final round → retain ORIGINAL severity (do NOT escalate); log `CHALLENGE_TIMEOUT_FINAL_ROUND: {flaw_id}`
- Rationale: fail-safe critical at the last round produces unrecoverable state with no evidence basis

### Section-Impact Score Agent

When evaluating fixes, section-impact scores (how foundational is this spec section?) are assigned by an independent agent:
- Receives: spec section text + description of proposed fix
- Produces: `SECTION_IMPACT_SCORE: {1-5}` as structured output
- Coordinator does NOT assign this score — prevents self-serving deflation of foundational sections

### Cross-Fix Consistency Checker (N-way)

For each round's proposed fixes before applying them:
- Write ALL proposed fixes to `deep-design-{run_id}/fixes-round-{N}.md`
- Spawn cross-fix checker with ALL fixes in one call (N-way check, not one-at-a-time)
- The checker examines fixes against each other AND against component_invariants
- Structured output (final lines):
  ```
  CONFLICT: {"fix_a": "fix_id_1", "fix_b": "fix_id_2", "description": "..."}
  ORDERING_EDGE: {"from": "component_a", "to": "component_b", "basis": "..."}
  OK
  ```
- Multiple CONFLICT or ORDERING_EDGE lines are allowed
- If output is unparseable → `CONFLICT: {"fix_a": "unknown", "fix_b": "unknown", "description": "assumed"}`
- Coordinator adds ORDERING_EDGE results to `ordering_graph.edges` in state.json
- Coordinator does NOT perform this check — same bias vector as severity judge bias

**Inter-round pass:** After the intra-round check, the cross-fix consistency agent also receives all prior-round accepted fix descriptions (from state.json `accepted_fixes` list) + the new redesigned spec. It checks whether any section of the new spec contradicts a prior-round fix intent. Reports: `REGRESSION: {prior_fix_id, spec_section, description}` or `OK`.

---

## Critic Context Injection

When spawning critics, provide TWO SEPARATE inputs — not one combined context:

**Input 1 — Coverage fingerprint (dedup only):**
```
Already-explored angles (do NOT repeat these — find NEW problems):
- [angle_001] Can a confused first-time user navigate the onboarding?
- [angle_002] Does the voting mechanic allow collusion?
...
These are listed so you avoid repeating them — NOT to constrain what you find.
```

**Input 2 — Known flaws file (with flaw IDs):**
```
Validated flaws found so far:
- [flaw_001] CRITICAL (fixed in v1): AI trivia exploit — restricted to open-ended questions
- [flaw_002] MAJOR (fixed in v1): Voting kingmaker — switched to secret simultaneous voting
- [flaw_003] DISPUTED: Grey rock undetectable — disputed; AI detection rate is 94%+

Dominant finding so far: {X}
⚠️ If your critique reveals a different pattern, follow it. Do not assume the dominant finding is correct.
```

**Why separate:** Mixing dedup context with flaw context causes anchoring — later critics converge on already-known failure modes instead of finding new ones.

**Flaw IDs are required:** Critics need flaw IDs (not just titles) to file GAP_REPORTs that reference specific flaws.

**All context passed via files, not inline.** Write known-flaws.md and angles/{id}.md before spawning. Inline content is silently truncated.

---

## Redesign Process

After each critique round, if validated critical or major flaws exist:

### 1. Flaw Triage
- Group flaws by root cause (multiple flaws may share the same root cause)
- Order by severity (critical first), then by how many downstream flaws they affect
- Identify flaw clusters: "these 3 flaws all stem from the same design assumption"
- Include re-opened flaws from GAP_REPORTs in this triage

### 2. Independent Redesign Agent (replaces coordinator self-redesign)

- Coordinator writes: ungrouped flaw ID list + raw critic file paths → `redesign_handoff_round_{N}.json`
- Coordinator writes: do-not-weaken list (mechanical read of all `component_invariants` in state.json, verbatim, no selection) → `do_not_weaken_round_{N}.json`
- Coordinator spawns independent redesign agent with these two files + current spec path
- Redesign agent reads raw critic files directly (not coordinator summaries)
- Redesign agent must:
  - Mark each change with `<!-- Fixed: <description> -->`
  - Enforce complexity budget: ≤2 new components/state fields rounds 1-2; ≤1 for rounds 3+
  - File DESIGN_TENSION for any fix requiring more components than the budget allows
  - NOT weaken any invariant on the do-not-weaken list

**Note on GAP_REPORT:** Re-opened flaws from GAP_REPORTs are included in the ungrouped flaw ID list passed to the redesign agent. The GAP_REPORT cap (2 per flaw per run globally) is tracked in `flaws[id].gap_report_count` in state.json; a third GAP_REPORT on the same flaw routes to PERSISTENT_TENSION instead of re-opening.

### 3. Invariant-Validation Agent (after each redesign, before next round)

After each redesign:
- Spawn invariant-validation agent with: `component_invariants` from state.json + `ordering_graph` + new spec version
- Agent produces per-invariant: `INVARIANT_OK: {key}` or `INVARIANT_VIOLATION: {key, invariant, spec_section, evidence}`
- Also verifies: for each `<!-- Fixed: ... -->` annotation in new spec, annotated text still satisfies original fix intent. Stale annotations: `STALE_ANNOTATION: {spec_section, original_fix, deviation}`.
- Also runs inter-round regression check: receives prior-round accepted fix descriptions + new spec → `REGRESSION: {prior_fix, spec_section, description}` or `OK`.
- `component_invariants` in state.json is append-only — coordinator cannot modify existing entries. Only invariant-validation agent and redesign agent may write new entries.
- Violations block round advancement (treated as critical flaws requiring immediate redesign).
- Unparseable output → assume violation (fail-safe).

### 4. N-way Consistency Check (independent agent)
After all fixes are designed:
- Delegate to cross-fix consistency checker (see above), including inter-round pass
- If CONFLICT returned: treat as new critical flaw, redesign before proceeding
- If ORDERING_EDGE returned: add to ordering_graph, check for cycles
- If REGRESSION returned: treat as critical flaw, redesign before proceeding
- Coordinator does NOT perform this check

### 5. Component Invariant Store Update
After applying fixes:
- For each affected component, update `component_invariants[component_name]`
- Set `constraint_direction`:
  - `"tightened"` if this fix adds constraints or narrows behavior
  - `"relaxed"` if this fix removes constraints or widens behavior
  - `"neutral"` if no directional change
- If direction is `"relaxed"` and `tightened_rounds` is non-empty: log DIRECTION_REVERSAL warning
- Track `tightened_rounds` (append current round if direction is "tightened")

### 6. Component Rename Detection and Key Migration
When rebuilding the canonical component inventory from the new spec:
- For each component in the new spec, check if it semantically matches an existing `component_invariants` key under a different name
- Detection uses semantic equivalence (the same mechanism as Tier 2 angle dedup)
- If a rename is detected:
  - Atomically rename the `component_invariants` key to the new canonical name
  - Log in `component_name_history`: `{old_name, new_name, migration_round, detection_basis: "semantic_equivalence"}`
  - Add old_name → new_name to `component_name_aliases`
- Semantic normalization (mapping new-fix alias names to canonical names during check time) is a SEPARATE operation — it does NOT migrate historical keys. These are distinct steps; neither substitutes for the other.

### 7. Concept Drift Check
Before writing the updated spec:

**SHA256 role clarification:** SHA256 stored at Step 0 is anti-tampering ONLY. It detects coordinator modification of the stored core claim text. It does NOT detect semantic drift. If mismatch: CORE_CLAIM_TAMPERED, halt.

**Layer 1 — Semantic comparison:**
- Compare text within CORE_MECHANISM_START/END delimiters to stored core claim
- Uses semantic similarity (cosine or equivalent). Base threshold: 0.80.
- DRIFT_WARNING if similarity < 0.80; DRIFT_CRITICAL if < 0.65 (halts redesign, routes to PERSISTENT_TENSION)
- Degraded mode (uncalibrated core claim): threshold = 0.95. Tag: DRIFT_CHECK_DEGRADED.

**Layer 2 — Discriminating test:**
- Compare current spec mechanism to both calibrated alternatives
- Alternatives refreshed every 2 rounds of major redesign (originals kept permanently; refreshed alternatives supplement, don't replace)
- If `core_claim_calibrated: true`: run with standard threshold
- If `core_claim_calibrated: false`: run with degraded-mode threshold (0.95) + tag as DRIFT_CHECK_DEGRADED
- **Do NOT skip Layer 2 when uncalibrated** — the cases where the baseline is weakest require more conservative checking, not less

### 8. Write Updated Spec
- Copy the previous spec version
- Apply all fixes
- Update the Design Decisions Log with new entries (each decision traced to the flaw that motivated it)
- Write to `deep-design-{run_id}/specs/v{N}-post-round-{round}.md`

---

## Coverage Gaps Log

After each round, log to `logs/coverage_gaps.jsonl` (three classes):
1. **Cap-dropped angles:** critic had additional new angles but the 1-angle-per-critic-per-round cap limited filing (references `suppressed_angles.jsonl`)
2. **Never-generated:** critic's MISSED_COVERAGE filings — what the critic couldn't explore given its angle scope
3. **Failed angles:** popped but failed quorum

This log is also summarized in the Coordinator Summary under "Coverage Gaps This Round."

---

## Final Synthesis (Step 8)

### Two-Pass Process

**Pass 1 — Per-critic mini-syntheses (written by each critic agent)**

Each critic appends a mini-synthesis to their critique file (see FORMAT.md). Required, ≥3 sentences covering:
- What failure modes this angle revealed
- How it connects to or differs from other explored angles
- What it changes about understanding the design

**Coordinator validation after receiving critiques:**
- Length check: must be ≥3 sentences. If not, coordinator generates placeholder:
  `[coordinator-generated mini-synthesis — lower confidence: {1-sentence summary}]`
- Contradiction check: if mini-synthesis contradicts the Flaws section, flag it for attention

**Pass 2 — Final synthesis (coordinator, from mini-syntheses + coordinator summary only)**

**Coordinator does NOT read raw critique files for final synthesis.** Inputs:
1. Coordinator summary (`coordinator-summary.md`) — all validated flaws, disputed flaws, design changes
2. All mini-syntheses extracted from critique files
3. State file (for coverage stats, component_name_history, ordering_graph)
4. Latest spec version (the designed artifact)

Spawn a **Sonnet subagent** to write `deep-design-{run_id}/spec.md` from these inputs. The subagent reads raw critique files only if needed for specific claims — not as primary input.

### Final Spec Honest Termination Requirements

The final spec **must** include:
- Termination label: `"Conditions Met"` or `"Max Rounds Reached"` — never `"no critical flaws remain"`
- Coverage fraction: `{N} of {M} dimensions discovered in this run` with explicit caveat that M is self-enumerated
- Unverified sections list (sections fixed but not independently re-verified due to queue displacement)
- Open issues at termination (anything unresolved when hard stop hit)
- Honest coverage caveats section (critics share the same model blind spots; self-enumerated dimensions; convergence ≠ correctness)

---

## Flaw Resolution Categories

- **Fixed**: The design was changed to address this flaw. Link to spec version.
- **Disputed**: Failed one of the validation checks (contradiction / premise / existence / nerf / falsifiability). Not redesigned, but documented. See Step 5 of SKILL.md.
- **Accepted**: The flaw is real but the tradeoff is acceptable. Document why.
- **Won't Fix**: Out of scope or conflicts with core design goals. Document why.
- **Open**: Not yet resolved (only in non-converged reports).

---

## Design Evolution Tracking

The final spec should make the design EVOLUTION visible:
```markdown
### How the design evolved

**v0 (initial):** Basic concept — lobby of AI agents, human tries to blend in
**v1 (post-round-1):** Added structured interaction phases to prevent trivia exploits
**v2 (post-round-2):** Redesigned voting to prevent collusion; added asymmetric information
**v3 (post-round-3):** Added narrative framing and progression system for retention
```
