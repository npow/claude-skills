# Coherence Annotations

## Emergent Patterns (PATTERN_MEMBER clusters)

### Cluster A: SMOKE_TEST_FORMAT_DISINTEGRATION
**Members:** DEFECT-6, DEFECT-7, DEFECT-9, C2-D4, C5-D2

**Why this is emergent:** No single critic caught the full shape of the problem. Critic 1 found that `SMOKE_TEST_BLOCKED` is missing from the reviewer format block (DEFECT-6), and that the token name differs between reviewer output and meta-reviewer COVERAGE field (DEFECT-7). Critic 1 also found that the `approved` verdict condition references golden paths but degraded mode leaves them unverified (DEFECT-9). Critic 2 independently noted that the smoke-test reviewer has no realistic cross-lane capability but the rule applies to it anyway (C2-D4). Critic 5 found that all-reviewers-approve + smoke-test-blocked is conflated with a clean pass (C5-D2).

Together these reveal a single architectural failure: smoke-test was designed as a first-class execution gate but its integration into the structured output protocol was never completed. The token naming, the format block, the verdict semantics, the degraded-mode interaction, and the cross-lane rule exemption are all symptoms of smoke-test being grafted onto a spec-reading protocol rather than designed in from the start. No single critic saw all five dimensions of this.

---

### Cluster B: META_REVIEWER_ACCOUNTABILITY_VACUUM
**Members:** C5-D1, C5-D5, C5-D6, C6-D1, C6-D2, C6-D3, C6-D4

**Why this is emergent:** Critic 5 found three structural failure modes where the meta-reviewer either does not exist (C5-D6), produces unparseable output (C5-D1), or silently overrides unanimous reviewer consensus (C5-D5). Critic 6 found that the meta-reviewer's independence is unenforceable (C6-D1), that 2v2 splits force it into original analysis (C6-D2), that `dismissed` status has no citation format requirement (C6-D3), and that this creates false confidence in downstream skills (C6-D4).

The emergent pattern: the meta-reviewer is the single point of synthesis for the entire panel, but has no failure modes defined for its own operation, no structural constraint preventing it from being an unaccountable fifth reviewer rather than a neutral synthesizer, and no machine-verifiable citation requirement on its most powerful action (dismissal). The critics separately identified the meta-reviewer's operational fragility (Critic 5) and its analytical overreach (Critic 6) — combined, they describe an accountability vacuum at the top of the authority hierarchy.

---

### Cluster C: UNBOUNDED_LOOP_ARCHITECTURE
**Members:** C4-D1, C4-D2, C4-D3, C4-D5, C4-D6

**Why this is emergent:** All five are from the same critic (Critic 4) and individually are cost defects. But combined they reveal a structural property: the pattern has zero hard termination guarantees at any level — no rejection cap in `team`, no rejection cap in `ship-it`, no retry cap on timeout, no aggregate cost ceiling, and stacked loops that compound. This is not just a collection of missing caps; it is the absence of a termination philosophy. The pattern assumes all paths converge but provides no guarantee of it.

Note: C4-D4 (fresh panel every cycle) is intentionally excluded from this cluster — it is a correctness-vs-cost tradeoff, not a termination defect. It is STANDALONE.

---

### Cluster D: CROSS_LANE_CONFIRMATION_LAUNDERING
**Members:** C2-D1, C2-D2, C2-D3, C2-D5, DEFECT-8, C5-D7

**Why this is emergent:** Critic 2 found that "blocking" is undefined (C2-D1), that there is no volume cap (C2-D2), that the table and prompt instructions contradict each other about scope (C2-D3), and that cross-lane findings can manufacture false `confirmed` status via same-evidence-path re-traversal (C2-D5). Critic 1 found that `confirmed_cross_lane` vs. `confirmed` is undefined (DEFECT-8). Critic 5 found that a cross-lane finding on a dismissed primary defect has no defined resolution — the cross-lane signal is destroyed (C5-D7).

The emergent pattern: the cross-lane empowerment rule is the mechanism by which confirmation quality degrades. From filing (undefined threshold, no volume cap) to confirmation counting (same-evidence re-traversal counting as independent confirmation) to dismissal interaction (cross-lane signal destroyed when primary is dismissed), the entire confirmation pipeline is corrupted by a rule that was designed to extend coverage but instead allows any finding to be laundered into `confirmed` status or silently dropped. No single critic saw the full pipeline from filing to destruction.

---

### Cluster E: FORMAT_CONTRACT_VOID
**Members:** DEFECT-1, DEFECT-2, DEFECT-3, DEFECT-4, DEFECT-5

**Why this is emergent:** These five defects from Critic 1 are individually format ambiguity issues, but combined they reveal that the structured output format has no binding contracts at any layer: the field count is variable (DEFECT-1), the VERDICT-DEFECT relationship is unconstrained (DEFECT-2 and DEFECT-3), the DEFECT ID has no format (DEFECT-4), and the DEFECT_FINAL ID has no namespace anchor (DEFECT-5). Critic 5's DEFECT-3 (inconsistent reviewer output) is the observable downstream consequence of this void — a reviewer can emit `VERDICT|approved` + critical DEFECT lines because the format contract that would prohibit it does not exist. The cluster name captures the fact that these are not five separate oversights but the collective absence of a parse contract.

Note: C5-D3 (reviewer produces logically inconsistent output) is a behavioral symptom of this cluster but comes from a different critic — see SUPERSEDED_BY annotation below.

---

### Cluster F: INJECTION_SURFACE_TRIFECTA
**Members:** DEFECT-3-01, DEFECT-3-02, DEFECT-3-03, DEFECT-3-04, DEFECT-3-05, DEFECT-3-06

**Why this is emergent:** All six are from Critic 3 and form a self-contained injection cluster. However the cluster is emergent in the cross-critic sense because Critic 2's new angle C (timeout-within-budget priority) and Critic 4's new angle on context-size scaling both implicitly assume the smoke-test reviewer is operating in good faith — none of those critics recognized that the reviewer itself is a compromised execution environment. The trifecta (repro + spec + build log as injection surfaces) plus the EXECUTE override plus the misleading PASS verdict plus the absence of any isolation mention collectively mean the pattern has an undefended remote-code-execution surface. This becomes visible cross-critic because Cluster A (smoke-test format disintegration) means the SMOKE_TEST_BLOCKED signal — the only graceful degradation path — is itself broken, leaving no fallback when injection occurs.

---

## Contradictions (CONTRADICTS pairs)

### Contradiction 1: C2-D3 vs. C2-D3's own internal resolution
This is an intra-critic contradiction, not inter-critic. It is noted in Cluster D above and not annotated as CONTRADICTS — it is a spec contradiction, not a finding contradiction.

### Contradiction 2: C5-D2 vs. DEFECT-9 — conflicting claims about what `approved` means under degraded mode

**DEFECT-9** (Critic 1) claims: the meta-reviewer "cannot issue `approved`" in degraded mode because golden paths are unverified — the spec creates a genuine contradiction between the verdict rule and the degraded mode allowance, leaving the meta-reviewer with no valid verdict to issue.

**C5-D2** (Critic 5) claims: the meta-reviewer WOULD issue `PANEL_VERDICT|approved` in this scenario, because the quorum rule allows proceeding with three approvals and the failure modes table does not override the verdict rule. The consuming skill treats this as a clean approval.

These make **incompatible factual claims** about meta-reviewer behavior under the same scenario (all non-blocked reviewers approve + smoke-test blocked). DEFECT-9 says the meta-reviewer is stuck with no valid verdict; C5-D2 says the meta-reviewer produces `approved`. Both cannot be the correct description of what the spec causes the agent to do. The resolution: C5-D2 is more accurate about observable behavior (the meta-reviewer will emit `approved` because the quorum rule permits it) while DEFECT-9 correctly identifies the normative contradiction (it *should not* emit `approved` but nothing stops it). DEFECT-9 overstates the behavioral deadlock; C5-D2 understates the normative problem.

**Annotation:** DEFECT-9 CONTRADICTS(C5-D2) on the specific claim of behavioral outcome under degraded mode.

---

## Superseded Findings (SUPERSEDED_BY pairs)

### C5-D3 SUPERSEDED_BY DEFECT-2 + DEFECT-3

**C5-D3** (Critic 5): "Reviewer produces logically inconsistent structured output — `VERDICT|approved` + critical DEFECT lines. Meta-reviewer has no rule for intra-reviewer contradiction."

**DEFECT-2** (Critic 1): "`VERDICT` field admits `approved` with defects present — no constraint stated." DEFECT-2 identifies the exact missing contract that permits C5-D3's scenario, including the downstream consequences of a meta-reviewer receiving a self-contradicting reviewer output.

**DEFECT-3** (Critic 1): "Zero DEFECTs with `rejected` verdict is valid per format." This covers the symmetric case: the format has no cardinality enforcement in either direction.

C5-D3 adds one specific failure path (the meta-reviewer trusts the VERDICT line and loses a critical defect) that DEFECT-2 implies but does not enumerate explicitly. However, the root cause is entirely identical, the remediation is a subset of DEFECT-2's remediation, and all failure modes C5-D3 lists flow mechanically from the gap DEFECT-2 identifies. C5-D3 adds nothing that a reader of DEFECT-2 would not independently derive.

**Annotation:** C5-D3 SUPERSEDED_BY(DEFECT-2)

---

### C6-D1 and C6-D4 relationship

C6-D4 ("independence framing creates false confidence in downstream skills") is the *consequence* of C6-D1 ("independence is instructional not structural"). C6-D4 adds no new root cause — it describes what happens when skills import a pattern built on the false premise identified in C6-D1. However, C6-D4 makes a distinct observable claim (downstream skills' correctness arguments are invalidated) that C6-D1 does not cover. This is a PATTERN_MEMBER relationship (both in Cluster B) rather than supersession; C6-D4 is not a strict subset of C6-D1.

**Annotation:** Both remain in Cluster B. Not SUPERSEDED_BY.

---

## Coverage Gaps (GAP findings)

### GAP-1: No coordinator-side parse contract — the pattern specifies what structured output to produce but not what to do when parsing fails at the coordinator
**Description:** The pattern specifies structured output formats for reviewers and the meta-reviewer. But the consuming coordinators (team Step 5, loop-until-done Step 7, ship-it Phase 6) are given no parse contract — no definition of what fields are required vs. optional, what to do when a required field is missing, or how to validate that `DEFECT_FINAL` count matches what the reviewers filed. Critic 5 surfaces this implicitly in its "New Angles" section but does not file it as a defect. No critic filed a defect on the coordinator-side contract. From the combined view: the pattern defines the producer contract (reviewer and meta-reviewer output) but is silent on the consumer contract (how coordinators parse and validate that output). This means a coordinator that silently ignores missing fields, or defaults to `approved` when `PANEL_VERDICT` is absent, is operating within the spec — exactly the failure mode C5-D6 describes for the missing meta-reviewer.

### GAP-2: Reviewer timeout interaction with cross-lane analysis budget is unspecified
**Description:** Critic 2 notes (New Angle C) that reviewers have 180s budgets and the unlimited-scope framing encourages active cross-lane scanning. Critic 4 covers timeout retries (C4-D5) as a cost defect. Neither critic filed a defect on the intra-reviewer priority ordering: when a reviewer's primary-lane checklist and its cross-lane scanning compete for the same 180s budget, there is no rule for which takes priority. The observable failure: a reviewer times out having completed extensive cross-lane analysis but an incomplete primary-lane checklist. The panel receives a timed-out primary reviewer and possibly a cross-lane finding from that reviewer's partial output. The quorum calculation treats this as a reviewer timeout — but the reviewer *did* produce output, just for the wrong lane. No critic covered the case where a partially-completed reviewer output (cross-lane work done, primary lane incomplete) enters the quorum calculation.

### GAP-3: Second-order injection via reviewer output files is unaddressed
**Description:** Critic 3 identifies three injection surfaces (repro, spec, build log) in the smoke-test reviewer's input. Critic 3's New Angle 3a explicitly surfaces a second-order path: compromised smoke-test reviewer → crafted output file → meta-reviewer prompt injection. But Critic 3 did not file this as a formal DEFECT — it is a new angle only. No other critic covered it. From the combined view, injection Cluster F (DEFECT-3-01 through DEFECT-3-06) establishes that the smoke-test reviewer is a compromised execution environment. Given that its output file feeds into the meta-reviewer's context, the injection chain is complete: attacker controls repro → controls smoke-test output → controls meta-reviewer verdict. This is a distinct defect not covered by any of the 37 filed findings.

### GAP-4: `review_unavailable` is used in prose failure modes but is not a formal PANEL_VERDICT enum value
**Description:** Critic 5 surfaces this in its New Angles section (angle 3) but does not file it as a defect. No critic filed a defect on this gap. From the combined view: the pattern's failure modes table uses `review_unavailable` as a terminal state in at least two rows (3+ timeout, and implicitly for meta-reviewer failure), but this value does not appear in the formal `PANEL_VERDICT` enum (`approved`, `rejected_fixable`, `rejected_unfixable`). Consuming skills must handle it but have no format contract for it. This is structurally parallel to the SMOKE_TEST_BLOCKED format gap (DEFECT-6) — a value defined in prose but missing from the structured output spec — but for a different token and from a different direction (output to coordinator rather than reviewer to meta-reviewer).

---

## Standalone Findings

The following defects have no meaningful cross-finding relationship and are genuinely independent:

- **C4-D4**: "Fresh panel every time" mandate eliminates incremental cost savings. This is a deliberate correctness-vs-cost tradeoff that no other critic addresses. The underlying design choice (no anchoring) is not contradicted by any other finding and is not part of the loop-termination cluster.
- **C4-D7**: Degraded mode still spawns meta-reviewer (no cost reduction). This is a minor documentation gap specific to cost expectations in degraded mode. No other critic intersects with this specific point.
- **C5-D4**: Exactly 2 reviewers time out (boundary condition in quorum rule). This is a boundary condition in the quorum logic that no other critic identified. It is not part of the cost loop cluster (it's a correctness gap) and not part of the meta-reviewer cluster (it's about quorum, not meta-reviewer behavior).

---

## Per-Defect Annotation Table

| Defect ID | Annotation |
|---|---|
| DEFECT-1 | PATTERN_MEMBER(FORMAT_CONTRACT_VOID) |
| DEFECT-2 | PATTERN_MEMBER(FORMAT_CONTRACT_VOID) |
| DEFECT-3 | PATTERN_MEMBER(FORMAT_CONTRACT_VOID) |
| DEFECT-4 | PATTERN_MEMBER(FORMAT_CONTRACT_VOID) |
| DEFECT-5 | PATTERN_MEMBER(FORMAT_CONTRACT_VOID) |
| DEFECT-6 | PATTERN_MEMBER(SMOKE_TEST_FORMAT_DISINTEGRATION) |
| DEFECT-7 | PATTERN_MEMBER(SMOKE_TEST_FORMAT_DISINTEGRATION) |
| DEFECT-8 | PATTERN_MEMBER(CROSS_LANE_CONFIRMATION_LAUNDERING) |
| DEFECT-9 | CONTRADICTS(C5-D2) + PATTERN_MEMBER(SMOKE_TEST_FORMAT_DISINTEGRATION) |
| C2-D1 | PATTERN_MEMBER(CROSS_LANE_CONFIRMATION_LAUNDERING) |
| C2-D2 | PATTERN_MEMBER(CROSS_LANE_CONFIRMATION_LAUNDERING) |
| C2-D3 | PATTERN_MEMBER(CROSS_LANE_CONFIRMATION_LAUNDERING) |
| C2-D4 | PATTERN_MEMBER(SMOKE_TEST_FORMAT_DISINTEGRATION) |
| C2-D5 | PATTERN_MEMBER(CROSS_LANE_CONFIRMATION_LAUNDERING) |
| DEFECT-3-01 | PATTERN_MEMBER(INJECTION_SURFACE_TRIFECTA) |
| DEFECT-3-02 | PATTERN_MEMBER(INJECTION_SURFACE_TRIFECTA) |
| DEFECT-3-03 | PATTERN_MEMBER(INJECTION_SURFACE_TRIFECTA) |
| DEFECT-3-04 | PATTERN_MEMBER(INJECTION_SURFACE_TRIFECTA) |
| DEFECT-3-05 | PATTERN_MEMBER(INJECTION_SURFACE_TRIFECTA) |
| DEFECT-3-06 | PATTERN_MEMBER(INJECTION_SURFACE_TRIFECTA) |
| C4-D1 | PATTERN_MEMBER(UNBOUNDED_LOOP_ARCHITECTURE) |
| C4-D2 | PATTERN_MEMBER(UNBOUNDED_LOOP_ARCHITECTURE) |
| C4-D3 | PATTERN_MEMBER(UNBOUNDED_LOOP_ARCHITECTURE) |
| C4-D4 | STANDALONE |
| C4-D5 | PATTERN_MEMBER(UNBOUNDED_LOOP_ARCHITECTURE) |
| C4-D6 | PATTERN_MEMBER(UNBOUNDED_LOOP_ARCHITECTURE) |
| C4-D7 | STANDALONE |
| C5-D1 | PATTERN_MEMBER(META_REVIEWER_ACCOUNTABILITY_VACUUM) |
| C5-D2 | CONTRADICTS(DEFECT-9) + PATTERN_MEMBER(SMOKE_TEST_FORMAT_DISINTEGRATION) |
| C5-D3 | SUPERSEDED_BY(DEFECT-2) |
| C5-D4 | STANDALONE |
| C5-D5 | PATTERN_MEMBER(META_REVIEWER_ACCOUNTABILITY_VACUUM) |
| C5-D6 | PATTERN_MEMBER(META_REVIEWER_ACCOUNTABILITY_VACUUM) |
| C5-D7 | PATTERN_MEMBER(CROSS_LANE_CONFIRMATION_LAUNDERING) |
| C6-D1 | PATTERN_MEMBER(META_REVIEWER_ACCOUNTABILITY_VACUUM) |
| C6-D2 | PATTERN_MEMBER(META_REVIEWER_ACCOUNTABILITY_VACUUM) |
| C6-D3 | PATTERN_MEMBER(META_REVIEWER_ACCOUNTABILITY_VACUUM) |
| C6-D4 | PATTERN_MEMBER(META_REVIEWER_ACCOUNTABILITY_VACUUM) |

### New findings from coherence integration (GAPs)

| Gap ID | Description |
|---|---|
| GAP-1 | No coordinator-side parse contract for consuming skills |
| GAP-2 | Intra-reviewer budget priority between primary-lane analysis and cross-lane scanning is undefined |
| GAP-3 | Second-order injection via reviewer output files into meta-reviewer context (complete injection chain) |
| GAP-4 | `review_unavailable` used in failure mode prose but absent from formal PANEL_VERDICT enum |

---

## Cluster Membership Summary

| Cluster | Member Count | Member IDs |
|---|---|---|
| FORMAT_CONTRACT_VOID | 5 | DEFECT-1, DEFECT-2, DEFECT-3, DEFECT-4, DEFECT-5 |
| SMOKE_TEST_FORMAT_DISINTEGRATION | 5 | DEFECT-6, DEFECT-7, DEFECT-9, C2-D4, C5-D2 |
| META_REVIEWER_ACCOUNTABILITY_VACUUM | 7 | C5-D1, C5-D5, C5-D6, C6-D1, C6-D2, C6-D3, C6-D4 |
| UNBOUNDED_LOOP_ARCHITECTURE | 5 | C4-D1, C4-D2, C4-D3, C4-D5, C4-D6 |
| CROSS_LANE_CONFIRMATION_LAUNDERING | 6 | C2-D1, C2-D2, C2-D3, C2-D5, DEFECT-8, C5-D7 |
| INJECTION_SURFACE_TRIFECTA | 6 | DEFECT-3-01, DEFECT-3-02, DEFECT-3-03, DEFECT-3-04, DEFECT-3-05, DEFECT-3-06 |
| STANDALONE | 3 | C4-D4, C4-D7, C5-D4 |
| SUPERSEDED | 1 | C5-D3 |
| CONTRADICTS pair | 2 | DEFECT-9 ↔ C5-D2 |
| GAP (new) | 4 | GAP-1, GAP-2, GAP-3, GAP-4 |

**Total accounted for:** 37 original defects + 4 new GAP findings = 41 findings in the integrated view.

Note: DEFECT-9 and C5-D2 each carry a dual annotation — they are both PATTERN_MEMBER(SMOKE_TEST_FORMAT_DISINTEGRATION) AND CONTRADICTS(each other). The contradiction is on their behavioral-outcome claims; their membership in the smoke-test cluster is on their root-cause domain. These are orthogonal dimensions and both annotations are valid simultaneously. The per-defect table uses the most actionable annotation for each (CONTRADICTS, since it is a stronger relationship requiring resolution than cluster membership alone).
