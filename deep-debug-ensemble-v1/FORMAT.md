# Output Formats

## Hypothesis File

Written by each hypothesis agent to `deep-debug-{run_id}/hypotheses/{angle_id}.md`. Read by the independent judge and by the coordinator for the hypothesis table.

```markdown
# {angle_id}: {short restatement of the angle question}
**Dimension:** {dimension}
**Depth:** {depth}
**Parent:** {parent_id or "seed"}
**Cycle:** {cycle}
**Date:** {ISO timestamp}

## Hypothesis

### {hypothesis_id}: {short title ≤10 words}

**Mechanism:**
[2-4 sentence causal chain. "{cause} happens because {reason}, which leads to {symptom}." Be specific. Name file:line where the mechanism lives. Describe WHAT and WHY, not just the symptom.]

**Predictions:**
- If this hypothesis is true: [specific observable 1 — e.g. "running the test with INSTRUMENT=1 will log `projectDir=''` before the git init call"]
- If this hypothesis is true: [specific observable 2]
- If this hypothesis is true: [specific observable 3]
[At least 2 predictions. A prediction is an observable that the hypothesis COMMITS to — something you'd see if true, or NOT see if false.]

**Evidence For:**
| Tier | Source | Note |
|------|--------|------|
| 2 | {file:line or log line or timestamped artifact} | {why this supports the hypothesis} |
| 3 | {multiple independent sources} | {which sources converge} |
| 4 | {single-source inference} | {the inference and its weakness} |

**Evidence Against / Gaps:**
| Tier | Source | Note |
|------|--------|------|
| 2 | {file:line or observation} | {why this contradicts the hypothesis, or which prediction didn't hold} |

[REQUIRED. If you found NO evidence against, the section must say "Not yet disconfirmed — disconfirmation searches attempted: {describe}". An empty Evidence Against list without that note is a failed critique — the judge will reject it as non-adversarial.]

**Critical Unknown:**
[ONE sentence: the single fact that, if known, would most collapse uncertainty between this hypothesis and the next-best alternative. Not "needs more investigation" — name the specific fact.]

**Discriminating Probe:**
[ONE concrete experiment that would collapse uncertainty. Format:
- **What:** "Run `{command}` with `{instrumentation}`"
- **Distinguishes:** this hypothesis vs. {alternative-hypothesis-or-lane}
- **Expected if THIS hypothesis:** {observable A}
- **Expected if ALTERNATIVE:** {observable B}
- **Cost:** {minutes — should be ≤30 minutes}]

[A good probe runs in minutes, produces hard evidence (log line, return value, test result), and would produce measurably different results for this hypothesis vs. the next-best alternative. "Read the code more carefully" is NOT a probe.]

**Confidence:** {high | medium | low}
[Low = single-tier evidence, can be falsified by 1 observation. Medium = tier-2 evidence, survives first glance but needs a probe. High = tier-1 evidence AND at least one disconfirmation search attempted. A critic that files high on every hypothesis is a broken critic.]

---

## New Angles Discovered

1. **{question}** — Dimension: {existing_dim | NEW: new_dim_name} — Priority: {high/medium/low}
   Why: {1 sentence on why this angle matters}

[List 0–1 genuinely novel angles — not rephrased versions of this one. If none: "None — this hypothesis is the primary finding for this lane."]

## Mini-Synthesis

[REQUIRED. ≥3 sentences:
1. What this lane's investigation revealed about the symptom
2. How this finding relates to or differs from other explored angles (if known)
3. What this changes about the ranking of live hypotheses]

## Exhaustion Assessment

**Score: {1-5}**
- 1 = barely scratched the surface of this angle
- 2 = found obvious hypothesis but deeper alternatives likely exist
- 3 = covered the main hypothesis space for this dimension
- 4 = thorough, only minor angles remain
- 5 = this angle is fully explored, nothing significant left

**What's missing (if score < 4):**
[Specific sub-angles a follow-up critic should target]

---

STRUCTURED_OUTPUT_START
HYPOTHESIS_ID: {hypothesis_id}
DIMENSION: {dimension}
CONFIDENCE: high|medium|low
EVIDENCE_TIER_MAX: 1|2|3|4|5|6
FALSIFIABLE: true|false
DISCONFIRMATION_ATTEMPTED: true|false
NEW_ANGLES_COUNT: {0-1}
EXHAUSTION_SCORE: {1-5}
STRUCTURED_OUTPUT_END
```

The `STRUCTURED_OUTPUT_START`/`END` block is required. Files without it are treated as failed agent runs — re-spawn or mark `timed_out`.

**`FALSIFIABLE: false`** is a valid output — it means the hypothesis agent couldn't construct disconfirming conditions. The coordinator downgrades these to `disputed` automatically.

---

## Evidence File

Written during Phase 1 and updated by every probe in Phase 4. Lives at `deep-debug-{run_id}/evidence.md`. Append-only (new sections added; old sections never rewritten).

```markdown
# Evidence — Run {run_id}

## Symptom (locked)

{verbatim symptom text — matches state.json `symptom` field; sha256 verified}

## Reproduction

**Status:** {confirmed | intermittent | unreproducible}
**Command:** `{exact command}`
**Rate:** {every time | 1 in N | last observed {timestamp}}
**Steps:**
1. {step 1}
2. {step 2}

## Recent Changes Snapshot (Phase 1)

**Time window:** last 7 days (configurable)

**Commits affecting touched paths:**
```
{git log --since='7 days ago' --oneline -- <paths>}
```

**Dependency changes:**
{diff of lock files vs LKG, or "no changes"}

**Config / env changes:**
{diff of config files, or "no changes"}

## Boundary Instrumentation (Phase 1, if multi-layer)

### Layer 1: {layer name}
```
{instrumented output}
```
**Observation:** {1-sentence summary of what the layer saw}

### Layer 2: {layer name}
```
{instrumented output}
```
**Observation:** {1-sentence summary}

### Boundary where values diverge: {layer N → layer N+1}
**What enters:** {value}
**What exits:** {value}

## Probe Log (Phase 4 entries — appended per probe)

### probe_001 (Cycle 1)
**Question:** {what the probe was testing}
**Distinguishes:** {hyp_A} vs {hyp_B}
**Expected if {hyp_A}:** {observable}
**Expected if {hyp_B}:** {observable}
**Executed:** {ISO timestamp}
**Raw result:**
```
{exact probe output — log line, test result, DB query output, etc.}
```
**Verdict:** {winner: hyp_A | winner: hyp_B | inconclusive}
**Rationale:** {1 sentence}

### probe_002 (Cycle 1)
[same structure]

## Fix Attempts Log (Phase 5 entries — appended per fix)

### fix_001 (Cycle 1)
**Hypothesis:** {hyp_id}
**Failing test:** `{test-path}::{test-name}`
**Change:** {1 sentence summary}
**Diff:** `deep-debug-{run_id}/fixes/fix_001.diff`
**Verification:**
- failing test passes: {yes | no}
- full suite clean: {yes | no}
- regressions: {list or "none"}
**Outcome:** {verified | failed | partial | reverted}
```

---

## Judge Verdict

Written by the batched hypothesis judge to `deep-debug-{run_id}/judge-verdicts/batch_{cycle}_{batch_num}.md`.

```markdown
# Judge Verdict Batch — Cycle {cycle}, Batch {batch_num}

---

## Hypothesis: {hyp_001}
**Title:** {title}
**Dimension:** {dimension}

### Pass 1 — Blind Assessment
(Critic's confidence was stripped. Verdict formed from evidence alone.)

**Plausibility:** leading | plausible | disputed | rejected | deferred
**Evidence-tier-max considered:** {tier}
**Falsifiability check:** PASS | FAIL ({reason})
**Contradiction check:** PASS | FAIL ({reason, which hypothesis conflicts})
**Premise check:** PASS | FAIL ({which premise the design already addresses})
**Evidence-grounding check:** PASS | FAIL ({which predictions are unsupported})
**Simplicity check:** PASS | FAIL ({which assumption adds unnecessary complexity})

**Pass 1 rationale:** {2-4 sentences — name the specific evidence weighed and why this plausibility tier}

### Pass 2 — Given Critic Confidence
(Critic claimed: {high | medium | low})

**Pass 2 verdict:** CONFIRM | UPGRADE → {new tier} | DOWNGRADE → {new tier}
**Pass 2 rationale:** {2-3 sentences — was the critic's confidence justified, inflated, or underweighted?}

**Final plausibility:** {leading | plausible | disputed | rejected | deferred}

---

## Hypothesis: {hyp_002}
[same structure]

---

STRUCTURED_OUTPUT_START
---
HYP_ID: hyp_001
PLAUSIBILITY: leading|plausible|disputed|rejected|deferred
FALSIFIABLE: true|false
EVIDENCE_TIER: 1|2|3|4|5|6
PASS2_VERDICT: CONFIRM|UPGRADE|DOWNGRADE
---
HYP_ID: hyp_002
PLAUSIBILITY: ...
FALSIFIABLE: ...
EVIDENCE_TIER: ...
PASS2_VERDICT: ...
---
STRUCTURED_OUTPUT_END
```

The coordinator reads ONLY the structured block. Unparseable → fail-safe `PLAUSIBILITY: disputed` for that hypothesis. Never `rejected` on unparseable — never accidentally reject a potentially-valid hypothesis on parse error.

### Plausibility tiers

- **leading** — evidence-tier ≤2, falsifiable, survived all 5 validation checks, pass 1 + pass 2 both confirm. Candidate for promotion to Phase 4 probe or Phase 5 fix.
- **plausible** — evidence-tier 3, falsifiable, survived validation, confirmed by judge. Competes with leading hypotheses; needs a discriminating probe to advance.
- **disputed** — failed ≥1 validation check (usually falsifiability or contradiction), or judge downgraded. Stays in registry with rationale, never silently dropped. May be re-examined with new evidence.
- **rejected** — directly contradicted by probe evidence or known-false via primary-tier source. Moves to graveyard.
- **deferred** — probe would require more time/resources than this run's budget. Documented as open investigation path, not pursued.

---

## Rebuttal Round Transcript

Written at end of Phase 3 to `deep-debug-{run_id}/rebuttal-cycle{N}.md` when ≥2 hypotheses are at `leading` or `plausible`.

```markdown
# Rebuttal — Cycle {N}

**Leader (Pass 2 verdict):** {hyp_001} — {title}
**Strongest alternative:** {hyp_002} — {title}

## Challenge by alternative

{hyp_002}'s challenge to {hyp_001}:
[1-3 sentences — the strongest contrary evidence or missing-prediction argument that the alternative can make against the leader. Independent agent (separate from judge) writes this.]

## Leader's response

{hyp_001}'s response to the challenge:
[1-3 sentences — leader must answer with evidence, not assertion. If leader has no evidence-based response, it's a failed rebuttal.]

## Outcome

- **Leader holds:** reasons {evidence cited in response}
- **Leader weakened — ranks re-shuffled:**
  - New leader: {hyp_002}
  - {hyp_001} plausibility: {new tier}

## Convergence / Separation Note

{One of:}
- **Genuinely separate hypotheses:** {hyp_001} and {hyp_002} imply different mechanisms AND different discriminating probes. Keep separate.
- **Converged on parent explanation:** {hyp_001} and {hyp_002} reduce to {parent explanation}. Merging into {merged hypothesis}.
- **Convergent language, divergent mechanism:** They sound similar but imply different probes — keep separate despite overlap.
```

---

## Discriminating Probe Specification

Coordinator writes this BEFORE executing the probe (in Phase 4) to `deep-debug-{run_id}/probes/probe_{id}.md`. The evidence-gatherer agent (if the probe is complex) reads this spec; simpler probes are run directly by coordinator.

```markdown
# Probe {id} (Cycle {N})

**Question:** {what the probe tests}

**Distinguishes:**
- Hypothesis A: {hyp_id} — {short title}
  - Prediction if true: {observable}
- Hypothesis B: {hyp_id} — {short title}
  - Prediction if true: {observable}

**Execution method:**
- Tool: {bash | test runner | DB query | instrumentation | git command}
- Command: `{exact command}`
- Environment: {where to run: local, CI, staging, etc.}
- Setup required: {any prerequisites}

**Expected time:** {minutes}

**Acceptance criterion for result:**
- If result looks like {observable A} → winner = hypothesis A
- If result looks like {observable B} → winner = hypothesis B
- If result is ambiguous → inconclusive → re-probe

**Safety check:**
- Is this probe reversible? {yes | no}
- Does it touch production data? {yes | no}
- If no to the first or yes to the second → USER CONFIRMATION REQUIRED before execution

---

## Result (filled after execution)

**Executed at:** {ISO}
**Raw output:**
```
{exact output — no summarization, no interpretation}
```

**Verdict:** {winner: hyp_A | winner: hyp_B | inconclusive}
**Rationale:** {1 sentence connecting raw output to the acceptance criterion}
```

---

## Architectural Question (Phase 7)

Written by the architect agent to `deep-debug-{run_id}/architectural-question.md` when Phase 7 triggers.

```markdown
# Architectural Question

## Situation

After {N} cycles of deep-debug on "{symptom}":
- Hypotheses explored: {count}
- Fix attempts: {count} — all failed
- Pattern observed: {each fix revealed a new problem in a different location | fixes required massive refactoring | each fix broke something else}

## The architectural question

{1-3 sentences naming the pattern-level question, e.g. "The symptom keeps moving because state is shared across {N} call sites without coordination. The question isn't 'where's the bug' — it's 'should this state be shared at all?'"}

## Possible architectural changes

### Alternative 1: {name}
**Change:** {1-2 sentences describing the structural change}
**Resolves:** {which failed fixes this would address and why}
**Cost:** {sketch of refactoring scope — files touched, test impact, migration complexity}
**Risk:** {what could break in migration}

### Alternative 2: {name}
[same structure]

### Alternative 3: {name}
[same structure]

## Recommendation

{Which alternative the architect recommends and why, or "Each has tradeoffs — user should weigh based on {factors}"}

## What to do next

The coordinator is halted. To proceed:
- Review the alternatives above
- Select one (or propose your own)
- Re-invoke deep-debug with `--hypothesis-override={chosen-approach}` AND note in the symptom that the architectural decision was made

⚠️ Do NOT attempt Fix #4 under the current hypothesis set. Three failed fixes is evidence that the hypothesis space is wrong, not that one more try will work.
```

---

## Final Debug Report

Written in Phase 8 by Sonnet subagent to `deep-debug-{run_id}/debug-report.md`. This is the user-facing deliverable.

```markdown
# Debug Report

**Symptom:** {one-paragraph symptom}
**Run ID:** {run_id}
**Termination:** {label from the 7-label vocabulary — never "probably fixed"}
**Cycles completed:** {N} of {max_cycles}
**Total hypotheses:** {count} ({leading}, {plausible}, {disputed}, {rejected}, {deferred})
**Probes executed:** {count}
**Fix attempts:** {count}
**Invocation:** {interactive | --auto | --hard-mode}

> ⚠️ [Show if any required category is uncovered, regardless of termination label]:
> Coverage incomplete. Required categories not explored: {list}. The conclusion may have an alternative root cause in an uncovered dimension. See §Known Gaps.

---

## Executive Summary

[3-5 paragraphs: the resolved cause (if any), the key evidence, what this bug taught about the codebase, what defense-in-depth layers would prevent recurrence. Written for someone who will NOT read the full report.]

---

## Resolved Cause (if Termination == "Fixed")

**Root cause:** {mechanism — from the leading hypothesis's mechanism field}
**Hypothesis ID:** {hyp_id} (Cycle {N})
**Evidence tier:** {tier}
**Probe that confirmed:** {probe_id}
**Fix:** {fix_id} — {change summary}
**Verification:** failing test `{test}` now passes; full suite clean

### Defense-in-Depth Suggestions

Following the fix, consider adding validation at these layers to make the bug structurally impossible (see TECHNIQUES.md §Defense-in-Depth):
- Layer 1 (entry validation): {specific suggestion}
- Layer 2 (business logic): {specific suggestion}
- Layer 3 (environment guard): {specific suggestion if applicable}
- Layer 4 (instrumentation): {specific suggestion}

---

## Environmental Conclusion (if Termination == "Environmental")

**Investigation summary:** {what was investigated}
**Evidence supporting environmental cause:** {list}
**Retry / monitoring contract:**
- Retry policy: {specific backoff, max attempts, idempotency requirement}
- Monitoring: {alerts to add, metrics to emit, logs to ship}
- Escalation: {when does an environmental failure become a code bug? e.g. "if retry rate exceeds X per Y, re-open as code bug"}

---

## Architectural Escalation (if Termination == "Architectural escalation required")

See `architectural-question.md` for the full analysis. Summary:
- Pattern observed: {description}
- 3 architectural alternatives proposed
- Recommendation: {alternative X or "user decision"}

---

## Timeline

### Cycle 1
- **Hypotheses generated:** {list with dimensions}
- **Judge accepted:** {list}
- **Judge rejected:** {list with rationale}
- **Rebuttal winner:** {hyp_id} or "leader held"
- **Probes:** {probe_id} — {verdict}
- **Fix attempt:** {fix_id} — {outcome}

### Cycle 2
[same structure]

### Cycle 3
[same structure]

---

## Hypothesis Registry

### Leading (if fix verified: the accepted cause)

| ID | Dimension | Title | Plausibility | Mechanism (1-line) |
|----|-----------|-------|--------------|---------------------|
| {hyp_id} | {dim} | {title} | leading | {1 line} |

### Plausible (competed but didn't win)

| ID | Dimension | Title | Why it didn't win |
|----|-----------|-------|-------------------|
| {hyp_id} | {dim} | {title} | {probe outcome or judge rationale} |

### Disputed (failed validation — NOT silently dropped)

| ID | Dimension | Title | Dispute reason |
|----|-----------|-------|-----------------|
| {hyp_id} | {dim} | {title} | {which check failed + why} |

### Rejected (falsified by probe or contradicted by primary evidence)

| ID | Dimension | Title | Falsification |
|----|-----------|-------|---------------|
| {hyp_id} | {dim} | {title} | {probe {id} showed {result}, contradicting {prediction}} |

### Deferred (could not probe within budget)

| ID | Dimension | Title | Why deferred | To investigate: |
|----|-----------|-------|--------------|-----------------|
| {hyp_id} | {dim} | {title} | {reason} | {specific probe that was too expensive} |

---

## Coverage Assessment

| Dimension | Explored? | Hypotheses | Notes |
|-----------|-----------|-----------|-------|
| code-path | ✓ | 3 | |
| data-flow | ✓ | 2 | |
| recent-changes | ✓ | 1 | |
| environment | ✗ | 0 | **Not investigated — alternative root cause may exist here** |
| framework-contract | ✓ | 2 | |
| concurrency-timing | ✓ | 1 | |
| measurement-artifact | ✗ | 0 | **Not investigated** |
| architectural-coupling | ✓ | 1 | |

### Required Category Coverage

| Category | Covered | Notes |
|----------|---------|-------|
| correctness | ✓ | |
| environment | ✗ | No angle explored — if fix fails to hold, re-run with environment focus |
| concurrency | ✓ | |
| architecture | ✓ | |

### Known Gaps

[What was NOT adequately investigated. If exhaustion_score < 3 for any dimension, list explicitly. If any required category is uncovered, warn that an alternative root cause may exist.]

---

## Methodology

- Run ID: {run_id}
- Cycles: {N} of {max_cycles} (hard_stop at {hard_stop})
- Model tiers: Sonnet for hypothesis agents + rebuttal + architect; Haiku for judge + evidence-gatherer + pre-mortem + summary
- Evidence strength hierarchy: see EVIDENCE.md
- Validation checks applied: falsifiability / contradiction / premise / evidence-grounding / simplicity

⚠️ Honest caveats:
- Hypotheses are self-enumerated from the symptom and the code — an unknown mechanism cannot be considered
- Critics share the same model blind spots; systematic failures may not surface
- "Fixed" means the reproducing test passes and the suite is clean — NOT that every alternative hypothesis was disconfirmed
- A fix that passes the test but doesn't address the root cause will re-surface; the Defense-in-Depth suggestions reduce that risk
```

---

## Agent Prompt Files (references)

Each agent's prompt template is defined in SKILL.md §Agent Prompt Templates. The coordinator writes the per-spawn prompt to `deep-debug-{run_id}/prompts/{agent_type}_{id}.md` before calling the Agent tool. Injecting data via files (not inline) is non-negotiable.
