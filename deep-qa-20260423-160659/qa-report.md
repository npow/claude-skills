# QA Report: Parallel Review Panel (`_shared/parallel-review-panel.md`)

**Run ID:** 20260423-160659
**Artifact type:** skill
**Rounds completed:** 1 (6 critics, 4 QA dimensions)
**Coherence integrator:** yes (cross-finding analysis applied)
**Total findings:** 37 defects from critics + 4 coverage gaps from coherence = 41

---

## Executive Summary

The parallel review panel pattern has **sound architectural intent** — replacing a single-Oracle reviewer with 4 parallel specialized reviewers plus an independent meta-reviewer is the right design direction. However the implementation spec has **6 systemic weakness clusters** visible only when critic findings are combined across dimensions:

| # | Cluster | Severity | Defect Count |
|---|---------|----------|-------------|
| 1 | META_REVIEWER_ACCOUNTABILITY_VACUUM | Critical | 7 |
| 2 | INJECTION_SURFACE_TRIFECTA | Critical | 6 |
| 3 | FORMAT_CONTRACT_VOID | Critical | 5 |
| 4 | CROSS_LANE_CONFIRMATION_LAUNDERING | High | 6 |
| 5 | SMOKE_TEST_FORMAT_DISINTEGRATION | High | 5 |
| 6 | UNBOUNDED_LOOP_ARCHITECTURE | High | 5 |

Plus 3 standalone findings, 1 superseded finding, 1 contradiction pair, and 4 coverage gaps.

---

## Cluster Details

### 1. META_REVIEWER_ACCOUNTABILITY_VACUUM (7 findings)

The meta-reviewer is the single synthesis authority with:
- Zero failure modes for its own operation (unparseable output, never spawned)
- No structural constraint preventing re-analysis of the diff it receives
- No machine-verifiable citation requirement on dismissals
- 2v2 splits force it into original analysis with no tiebreaker rule
- "Independence" framing conflates context-independence (structural) with analysis-restraint (behavioral)

**Impact:** The meta-reviewer can silently override any reviewer finding, including unanimous ones, with no audit trail. Downstream skills treat its independence as a correctness guarantee when it is not.

### 2. INJECTION_SURFACE_TRIFECTA (6 findings)

The smoke-test reviewer has three undefended injection surfaces:
- Repro file: unconditional execution authority, no sandbox
- Spec file: golden paths derived from attacker-controlled content
- Build log: log-embedded prompt injection in agent context

Compounded by "EXECUTE, not ANALYZE" override that suppresses safety judgment, misleading PASS verdicts after injection, and zero content-isolation boundary anywhere in the spec.

**Impact:** Remote code execution through any of three input files. Successful injection produces a clean PASS verdict with no detection mechanism.

### 3. FORMAT_CONTRACT_VOID (5 findings)

The structured output format has no binding contracts:
- Variable field count (5 vs 7 fields for in-lane vs cross-lane)
- No VERDICT-DEFECT relationship constraint
- No DEFECT ID format specification
- No DEFECT_FINAL namespace anchor
- No cardinality rules

**Impact:** Every LLM agent implementing this format will produce structurally different output. Parsers will break on cross-lane defect lines. Deduplication across reviewers is impossible without semantic matching.

### 4. CROSS_LANE_CONFIRMATION_LAUNDERING (6 findings)

The cross-lane empowerment rule corrupts the confirmation pipeline:
- "Blocking" is undefined → open invitation to file
- No volume cap → lane inversion possible
- Table/prompt scope contradiction → systematic cross-lane scanning encouraged
- Same-evidence re-traversal counts as "independent" confirmation
- `confirmed_cross_lane` semantics undefined
- Cross-lane signal destroyed when primary finding is dismissed

**Impact:** Any finding can be laundered into `confirmed` status through cross-lane re-filing, or silently dropped through dismissal-dedup interaction.

### 5. SMOKE_TEST_FORMAT_DISINTEGRATION (5 findings)

Smoke-test was grafted onto a spec-reading protocol without completing integration:
- `SMOKE_TEST_BLOCKED` missing from the format block
- Token mismatch between reviewer and meta-reviewer (`SMOKE_TEST_BLOCKED` vs `smoke_blocked`)
- `approved` verdict requires golden paths but degraded mode leaves them unverified
- Smoke-test reviewer has no realistic cross-lane capability but rule applies
- All-approve + smoke-blocked conflated with clean pass

**Impact:** The execution-verification gate — the whole reason for adding a fourth reviewer — has no working integration with the structured output protocol.

### 6. UNBOUNDED_LOOP_ARCHITECTURE (5 findings)

Zero hard termination guarantees:
- `team` has no rejection cap (unlimited panel cycles)
- `ship-it` has no rejection cap
- Stacked loops (team + loop-until-done) compound to 50 agents worst case
- Timeout retry path has no retry cap
- No aggregate cost ceiling across all cycles

**Impact:** Worst case is 50 Sonnet agents on a single run. No mechanism to detect or prevent cost runaway.

---

## Standalone Findings

- **C4-D4 (major):** "Fresh panel every time" burns full context every cycle — intentional correctness-vs-cost tradeoff but unacknowledged
- **C4-D7 (minor):** Degraded mode still spawns meta-reviewer — documentation gap
- **C5-D4 (medium):** Exactly 2 reviewers time out — boundary condition in quorum rule not covered by failure modes table

---

## Coverage Gaps (from coherence integration)

1. **GAP-1:** No coordinator-side parse contract — consuming skills have no spec for how to parse and validate meta-reviewer output
2. **GAP-2:** Intra-reviewer budget priority between primary-lane and cross-lane scanning is undefined — reviewer can timeout having done the wrong work
3. **GAP-3:** Second-order injection chain: attacker → repro → smoke-test output → meta-reviewer context (complete chain, no critic filed it)
4. **GAP-4:** `review_unavailable` used in prose failure modes but absent from formal PANEL_VERDICT enum

---

## Contradiction Resolved

**DEFECT-9 vs C5-D2** on meta-reviewer behavior under degraded mode: DEFECT-9 claims the meta-reviewer has no valid verdict; C5-D2 claims it emits `approved`. Resolution: C5-D2 is correct about observable behavior (the LLM will emit `approved`); DEFECT-9 correctly identifies the normative contradiction (it *should not*).

---

## Benchmark Assessment

This QA run validates that the deep-qa workflow functions correctly after the coherence-integrator and parallel-review-panel changes:

1. **Critic spawning:** 6 parallel Sonnet agents completed successfully across all 4 required skill dimensions
2. **Coverage:** All 4 required categories covered (behavioral_correctness, instruction_conflicts, injection_resistance, cost_runaway_risk)
3. **Coherence integrator:** Successfully identified 6 emergent clusters, 1 contradiction, 1 supersession, and 4 coverage gaps that no individual critic caught — this is the key validation that the new cross-finding-coherence pattern adds value
4. **Structured output:** All critics produced parseable structured output with defect counts, severity ratings, and new angle suggestions

**Verdict:** Skills are functioning correctly. The coherence integrator is the standout — it elevated individual findings into systemic architectural insights (e.g., SMOKE_TEST_FORMAT_DISINTEGRATION as a cluster is far more actionable than 5 scattered findings across 3 critics).
