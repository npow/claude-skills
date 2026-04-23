# Cross-Finding Coherence Integrator

Shared pattern for skills that fire N parallel critics and need cross-finding synthesis before severity classification. The integrator sits between critics and judges, reading ALL findings simultaneously to detect contradictions, coverage gaps, and emergent patterns that no single critic can see.

**Used by:** deep-qa (Phase 5.5.a-coherence, post-pass-1-drain pre-pass-2 — fires once across all rounds), deep-design (Step 5 pre-judge), deep-debug (Phase 3 pre-judge), deep-research (Phase 3.7 post-rounds pre-verification — research variant).

**Not used by:** team, ship-it, autopilot, loop-until-done (these use the parallel-review-panel pattern instead).

---

## Why this pattern exists

Parallel critics are intentionally isolated — they share no lateral communication, preventing groupthink. But isolation creates three blind spots that neither the critics nor the per-finding severity judge can catch:

1. **Cross-finding contradiction.** Critic A says "this component is over-specified" while Critic B says "this component is under-specified." Both file valid defects with plausible scenarios. A per-finding judge classifies each severity independently and both survive. The user sees two contradictory defects and loses trust in the report.

2. **Emergent pattern.** Critics 1, 3, and 5 each find a different manifestation of the same root cause (e.g., "contract X is assumed but never enforced" surfaces as a correctness defect, a security defect, and an edge-case defect). Filed separately, each is major. Recognized as a single root cause, the aggregate is critical. A per-finding judge sees each in isolation.

3. **Coverage gap between critics.** Each critic covers its assigned dimension. But the *intersection* of two dimensions — where Critic A's dimension meets Critic B's — is in neither critic's explicit scope. The quorum check verifies each dimension has a critic; it does not verify the seams between dimensions.

The integrator is the Google-bipartite-model's middle layer: it sees all output simultaneously and synthesizes across findings before any per-finding judgment occurs.

---

## The pattern

### When it fires

After all critics in a round complete (post-quorum-check, post-dedup) and BEFORE severity judges are spawned.

### Inputs

The integrator agent receives file paths only (never inline):

1. **All parseable critic output files** from this round (after dedup — the integrator sees the deduped finding set, not raw duplicates)
2. **The artifact/spec/evidence file** the critics were evaluating
3. **The known-findings file** (pre-round snapshot — so the integrator can see what's new this round vs. prior rounds)
4. **The dimension taxonomy** (required categories, which dimensions each critic covered)

### Agent specification

- **Model tier:** Sonnet (same tier as critics — the integrator is a synthesis peer, not a lightweight judge)
- **Independence:** The integrator is a fresh agent with no prior context. It reads all critic files in a single context window. It does NOT receive coordinator summaries or prior-round synthesis — only the raw critic output files and the artifact.
- **Spawn contract:** `spawn_time_iso` written before Agent call; output path pre-declared; `STRUCTURED_OUTPUT_START/END` markers required; unparseable output triggers fail-safe (all findings pass through to judge without coherence annotations — degraded but not blocked).

### Agent prompt template

```
You are a cross-finding coherence integrator. You have received the output of {N} independent critics who evaluated the same artifact from different dimensions. Your job is to synthesize ACROSS their findings — not to re-evaluate any single finding.

You are NOT a judge. You do not classify severity. You do not accept or reject findings. You identify relationships between findings that no single critic could see.

**Critic output files:** {list of file paths}
Read ALL of them before writing anything.

**Artifact file:** {artifact_path}
Reference for resolving ambiguities between critics.

**Known findings (pre-round):** {known_findings_path}
For distinguishing new-this-round from previously known.

**Dimension taxonomy:** {taxonomy_path}
For identifying inter-dimensional gaps.

**Produce exactly these sections:**

## Contradictions
For each pair of findings that make incompatible claims about the same component, behavior, or property:
- Finding A: {id} — claims {X}
- Finding B: {id} — claims {Y}
- Conflict: {why X and Y cannot both be true}
- Likely resolution: {which is better-evidenced, or whether both are partially right about different aspects}

If no contradictions: "None detected across {N} findings."

## Emergent Patterns
For each case where 2+ findings from different dimensions share a common root cause:
- Findings: {id_list}
- Shared root cause: {description}
- Aggregate severity implication: {why the pattern is more/less severe than individual findings suggest}
- Recommendation: {whether to file as a single root-cause finding or keep separate}

If no patterns: "No cross-dimensional patterns detected."

## Coverage Gaps
For each pair of adjacent dimensions where no critic examined the intersection:
- Dimension A: {name} — covered {aspects}
- Dimension B: {name} — covered {aspects}
- Uncovered intersection: {what falls between them}
- Risk: {what could be missed}

Generate a CRITICAL-priority angle for each gap (these feed back into the frontier for the next round).

If no gaps: "All dimensional intersections covered by at least one finding."

## Finding Annotations
For each finding in this round, emit ONE structured annotation line:

STRUCTURED_OUTPUT_START
FINDING|{finding_id}|{annotation}
  annotation is one of:
    STANDALONE — no cross-finding relationship detected
    CONTRADICTS|{other_finding_id}|{brief_reason}
    PATTERN_MEMBER|{pattern_id}|{root_cause_summary}
    SUPERSEDED_BY|{other_finding_id}|{brief_reason}
GAP|{dimension_a}|{dimension_b}|{gap_description}|{suggested_angle}
PATTERN|{pattern_id}|{finding_id_list}|{root_cause}|{aggregate_severity_suggestion}
STRUCTURED_OUTPUT_END

IMPORTANT:
- You succeed by finding real relationships. You fail by rubber-stamping "STANDALONE" on everything.
- You also fail by manufacturing false contradictions. Two findings about the same component from different angles are NOT contradictions unless they make incompatible claims.
- An integrator that reports zero contradictions, zero patterns, and zero gaps across 6+ findings from orthogonal dimensions is almost certainly not looking hard enough. At minimum, dimensional intersections should surface gaps.
- A finding can have multiple annotations (e.g., both CONTRADICTS and PATTERN_MEMBER). Emit one line per relationship.
```

### Outputs

1. **Coherence report file:** `{run_dir}/coherence/round-{N}-coherence.md` — the full sections above
2. **Structured annotations:** parsed from the `STRUCTURED_OUTPUT` block, attached to each finding in state.json before judges see them

### How downstream consumers use integrator output

**Severity judges** receive integrator annotations alongside the finding:
- `CONTRADICTS` → judge must evaluate whether the contradiction weakens the finding's evidence base
- `PATTERN_MEMBER` → judge sees the aggregate pattern and can upgrade severity if the root-cause warrants it
- `SUPERSEDED_BY` → judge can downgrade/reject if the superseding finding is stronger
- `STANDALONE` → no change to normal judge flow

**Coverage gaps** feed directly into the frontier as CRITICAL-priority angles for the next round. They do NOT create findings — they create angles that critics will investigate.

**Emergent patterns** are surfaced in the final report as a "Cross-Dimensional Patterns" section. The coordinator does not decide whether to merge findings — it presents the integrator's analysis and lets the user decide.

---

## Research variant (deep-research)

The core pattern above targets critic→judge workflows where findings are defects with severity. deep-research's parallel agents produce factual claims with evidence quality, not defects. The integrator's structure is identical — independent agent, reads all output simultaneously, annotates before downstream — but the vocabulary adapts.

### What changes

| Critic variant | Research variant | Why |
|---|---|---|
| `CONTRADICTS` | `CONTRADICTS` | Same: two claims assert incompatible facts. Synthesis must explicitly address the disagreement with source comparison, not silently pick one. |
| `PATTERN_MEMBER` | `CONVERGES` | Different: multiple dimensions independently corroborate the same conclusion. This is a high-confidence signal — synthesis highlights it, not buries it. |
| `SUPERSEDED_BY` | `SUPERSEDED_BY` | Same: one dimension's claim is a subset of another's more complete treatment. |
| `STANDALONE` | `STANDALONE` | Same. |
| `GAP` | `GAP` | Same: dimensional intersection not covered. Feeds into research frontier for next round (if rounds remain) or flagged as limitation in final report. |
| N/A | `SOURCE_CONFLICT` | New: two claims cite the same source but extract different numbers or conclusions. Flags for Phase 4 fact-verification priority. |

### Where it fires

After all research rounds complete (post Phase 3 dedup + unconsumed-leads sweep) and BEFORE Phase 4 (fact verification). This is Phase 3.7 in deep-research's workflow.

Unlike the critic variant which fires per-round, the research variant fires ONCE on the complete accumulated findings across all rounds. Rationale: research claims build on each other across rounds; a Round 3 finding may contradict a Round 1 finding that wasn't visible to per-round analysis.

### How downstream consumers use research annotations

**Phase 4 (fact verification)** receives annotations:
- `CONTRADICTS` / `SOURCE_CONFLICT` claims get priority in the spot-check queue — contradictions with unverified sources are the highest-risk claims
- `CONVERGES` claims can be sampled at lower rate (independent corroboration is itself evidence)

**Phase 5 Pass 2 (theme extraction)** receives annotations:
- `CONVERGES` clusters are pre-identified cross-dimensional themes — the coordinator doesn't need to re-discover them
- `CONTRADICTS` pairs become explicit "genuine contradictions" in the report (not silently resolved by narrative choice)
- `GAP` annotations become the "What this report does NOT cover" section items

**Phase 5 Pass 4 (QA offer)** — if coherence detected zero contradictions and zero gaps across 10+ claims from 4+ dimensions, the QA offer should note: "Coherence integrator found no cross-dimensional issues — QA may be less critical for this run."

---

## Failure modes and mitigations

| Failure | Mitigation |
|---|---|
| Integrator finds zero relationships (rubber-stamp) | If `STANDALONE` rate is 100% across 6+ findings: log `COHERENCE_SHALLOW` warning. Do not block — the findings still proceed to judges — but flag in the final report. |
| Integrator manufactures false contradictions | Judges independently evaluate each finding. A false `CONTRADICTS` annotation causes the judge to scrutinize the finding more carefully, which is a minor cost, not a wrong decision. The judge's verdict is authoritative, not the integrator's annotation. |
| Integrator is unparseable | Fail-safe: all findings proceed to judges without annotations. Log `COHERENCE_PARSE_FAILED`. Report proceeds in degraded mode — no cross-finding analysis in the final report, prominently flagged. |
| Integrator takes too long | Timeout: 120s (same as critic timeout). On timeout: fail-safe same as unparseable. |
| Research variant: all claims STANDALONE across 4+ dimensions | Same as critic variant: log `COHERENCE_SHALLOW`. Additionally, note in Phase 5 Pass 4 QA offer: "coherence integrator found no cross-dimensional relationships — QA recommended." |
| Research variant: CONTRADICTS floods (>40% of claims) | Likely a topic with genuine scholarly disagreement, not integrator failure. Synthesis should organize by "schools of thought" rather than trying to resolve. Flag `COHERENCE_HIGH_CONTRADICTION_RATE` for the report's methodology note. |

---

## What this pattern does NOT do

- It does NOT classify severity (that's the judge's job)
- It does NOT accept or reject findings (that's the judge's job)
- It does NOT replace the per-finding judge (judges still run on every finding)
- It does NOT have access to prior integrator output (each round is independent — no anchoring on prior synthesis)
- It does NOT communicate with critics (critics are already done; the integrator reads their frozen output)

The integrator is read-only on critic output and write-only on annotations. It is a pure synthesis step.

---

## Integration checklist

Each skill importing this pattern must:

- [ ] Fire the integrator AFTER dedup and BEFORE severity judges
- [ ] Pass ALL parseable critic output files (not a coordinator summary)
- [ ] Write integrator output to a dedicated `coherence/` subdirectory
- [ ] Attach structured annotations to findings in state.json before judge input files are written
- [ ] Include integrator annotations in judge input files (so judges see the cross-finding context)
- [ ] Feed coverage-gap angles into the frontier with CRITICAL priority
- [ ] Surface emergent patterns in the final report's "Cross-Dimensional Patterns" section
- [ ] Handle unparseable/timed-out integrator output as degraded (not blocked)
- [ ] Log `COHERENCE_SHALLOW` if STANDALONE rate is 100% across 6+ findings
