# Synthesis

## Coordinator Summary (updated after each round)

**The coordinator MUST NOT accumulate raw findings across rounds.**

After each round, write `deep-research-coordinator-summary.md` — a structured summary of ALL findings so far. This is the coordinator's ONLY source of prior-round context. Individual findings files are NOT read by the coordinator after being summarized.

### Coordinator Summary Format

```markdown
## Round {N} Coordinator Summary

### Mainstream Findings (dominant framing)
- [Dimension: key finding — source tier — confidence level]
- [Dimension: key finding — source tier — confidence level]

### Counter-Narratives and Contradictions
⚠️ These MUST NOT be discarded in compression:
- [Direction X vs Direction Y: what they disagree on — both framings preserved]
- [Minority-held finding: what it claims, why it matters even if minority]

### Numerical Claims (exact preservation required)
- [Direction X: "[exact quote of numerical claim]" — [source tier]]

### Coverage State
- Dimensions with ≥1 explored direction: {list}
- Dimensions not yet explored: {list}
- Dimensions where findings are shallow (exhaustion <3): {list}
- Timed-out directions this round: {list or "none"}

### Cross-Cutting Dimension Coverage (REQUIRED — blind-spot gate)
- PRIOR-FAILURE: covered | pending | uncovered
- BASELINE: covered | pending | uncovered
- ADJACENT-EFFORTS: covered | pending | uncovered
- STRATEGIC-TIMING: covered | pending | uncovered
- ACTUAL-USAGE: covered | pending | uncovered

### Unconsumed Leads Registry (carried forward across rounds)
Every entity mentioned in a finding but not yet independently researched:
- [Entity/concept]: [round first seen] — [status: `frontier` | `deduped_against_X` | `researched_in_Y`]

⚠️ Coverage plateau termination cannot fire while any cross-cutting dimension is `pending`/`uncovered` OR any unconsumed lead is `frontier`.
```

**Rules:**
- No word budget. The structure provides natural compression by section.
- Counter-narratives and numerical claims have dedicated sections — they cannot be silently omitted.
- Write the summary as a subagent (spawn a Haiku agent to write it from the round's findings) to keep the coordinator context clean.

---

## Coordinator Context Budget

The coordinator's effective per-round context should be:
- Coordinator summary: ~2-4k tokens
- Current round's findings (mini-syntheses only): ~1-3k tokens
- State file / frontier: ~1-2k tokens
- **Total: ~4-9k tokens** per round (vs. 500k–1M if accumulating raw findings)

**Never read raw findings files in the coordinator session.** Let the summary and mini-syntheses carry the context.

---

## Summary Injection for Research Agents

When spawning agents, provide TWO SEPARATE inputs — not one combined context:

**Input 1 — Coverage fingerprint (dedup only):**
```
Already-explored directions (do NOT repeat these):
- [dir_001] What adaptive budget allocation strategies exist?
- [dir_002] How does compression affect reasoning quality?
...
These are listed so you avoid repeating them — NOT to constrain what you find.
```

**Input 2 — Findings summary (research orientation):**
```
What we've found so far:
- [dir_001] Budget forcing: monotonic improvement with Wait tokens; TALE achieves 68% reduction
- [dir_002] Compression: TokenSkip 30-40% reduction; CoT-Valve enables controllable compression
Dominant framing: [X]
⚠️ If your research points in a different direction, follow it. Do not assume the dominant framing is correct.
```

Keep each line to ~20 words. The agent needs orientation, not full context.

**Why separate:** Mixing dedup context with findings context causes framing anchoring — later agents converge on what earlier agents found instead of exploring independently.

---

## Two-Pass Final Synthesis

### Pass 1 — Per-Agent Mini-Synthesis (written by each research agent)

Each agent appends to its findings file (see FORMAT.md):
```
## Mini-Synthesis
[3-5 sentences: what this direction contributes to understanding the seed topic,
how it connects to other directions already explored, what it contradicts]
```

**Coordinator validation after receiving findings:**
- Length check: must be ≥3 sentences. If not, coordinator generates one-sentence placeholder:
  `[coordinator-generated mini-synthesis — lower confidence: {1-sentence summary}]`
- Contradiction check: if mini-synthesis appears to contradict the Findings section, flag it:
  `⚠️ [dir_XXX] mini-synthesis flagged for Pass 2 attention — may contradict findings`

### Pass 2 — Theme Extraction (coordinator, from mini-syntheses only)

**Coordinator reads mini-syntheses ONLY — not raw findings.** This keeps context bounded.

**Theme validity criterion:** A theme is valid ONLY if it requires findings from 2+ distinct dimensions to describe.
- If only one dimension contributes → it is a "dimension summary," not a cross-cutting theme
- Process: for each candidate theme, list which dimensions contribute. If < 2 → demote to dimension summary section.

**Outputs:**
- Cross-cutting themes (with contributing dimensions listed)
- Dimension summaries (single-dimension findings)
- Meta-patterns (approaches appearing across multiple themes)
- Fundamental tradeoffs
- Genuine contradictions (with source quality differential noted)

---

## Fact Verification (spawned as dedicated subagent — Haiku)

Run after the final research round, before synthesis. Spawn as a **Haiku subagent** — this is URL-fetching and text comparison, not synthesis.

**Claim extraction and risk-stratified sampling priority:**
1. Primary-tier claims with no corroborating sources (highest risk — single source of truth)
2. Numerical/statistical claims (any tier) — exact number comparison required
3. Claims that contradict another agent's findings (contested claims)
4. Corroboration candidates (3+ agents citing same claim) — check independence

**Citation spot-check:**
- For each sampled URL: fetch, check (a) accessible, (b) attributed claim is in source text
- For numerical claims: "Compare EXACT numbers. Do NOT accept semantic similarity — flag 'number mismatch — manual verification required' if they don't match exactly."
- Paywalled → "unverifiable — full text inaccessible"

**Corroboration independence check:**
- For claims cited by 3+ agents: verify different organizations, dates, methodologies
- Flag: "apparent corroboration — may share a common source" if all point to same originating study

**Output (written by the verification subagent to a file, read by coordinator for inclusion in report):**
```
## Spot-Check Sample Results
Checked: {X} of {Y} claims ({X/Y}%)
Sampling strategy: risk-stratified (single-source primary + numerical + contested)

Results:
- Citations accessible and matching: {N}
- Citations inaccessible (paywalled/404): {N}
- Citation mismatches flagged: {list with brief note}

⚠️ IMPORTANT LIMITATIONS:
- Numerical/statistical claims: LLM comprehension is UNRELIABLE for exact number verification.
  Claims with specific figures should be manually verified against cited source.
- This is a spot-check, not a comprehensive audit. {Y - X} claims were not checked.
- For high-stakes decisions, independently verify all primary claims.
```

---

## Final Report

Write `deep-research-report.md` — see FORMAT.md for the full template.

The coordinator passes the following to the final synthesis subagent (Sonnet):
1. Coordinator summary (structured, from `deep-research-coordinator-summary.md`)
2. All mini-syntheses (extracted from findings files)
3. Spot-check results
4. State file (for coverage stats)

The final synthesis subagent reads raw findings files only if needed for specific claims — not as primary input.

### Contradiction Handling

When findings from different directions contradict:
- DO NOT resolve the contradiction — present both views
- Note the source quality for each position (asymmetric quality must be flagged)
- If possible, identify WHY they disagree (different timeframes, different benchmarks, different definitions)
- Flag for reader: "This is an active area of disagreement"

Example:
```markdown
### Contradiction: Latent reasoning effectiveness
- **dir_003 (Coconut):** Latent reasoning regresses on math tasks (GSM8K -8 points) [primary source]
- **dir_015 (CoLaR):** RL-based latent compression IMPROVES math (+5.36% on MATH) [primary source]
- **Note:** Different mechanisms — Coconut replaces ALL text reasoning; CoLaR selectively compresses parts.
  Quality differential: both primary. Disagreement is genuine and unresolved.
```
