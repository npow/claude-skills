# Output Format

## Surviving Idea Format

Present each NOVEL survivor immediately when it passes novelty checks. Do not batch — show it as soon as it passes.

```markdown
---
## [Idea Name] ✓ NOVEL  {tags: [PRIOR_ART_OVERLAP] [FEASIBILITY_UNVERIFIED] [NOVELTY_DISPUTED] [JUDGE_SUSPECT] [novelty_unverified] — apply only if triggered}

**Forcing function:** {INVERTER | BISOCIATOR | EDGE DESIGNER | TEMPORAL EXPLOITER | CONSTRAINT FLIPPER | [Level N combination]}
**Mutation level when found:** {0-4}
**Cycle:** {N}

### Derivation chain
{Explicit step-by-step: how the forcing function mechanism led to this specific idea. Minimum 3 causally-connected steps.}

### What it is
{2-3 sentences. Specific enough to write a landing page headline. Names concrete mechanism, specific user, specific outcome.}

### Core insight
{The non-obvious thing that makes this work — the thing you couldn't derive from "give me ideas". One sentence.}

### Target user
{Specific person, specific context — not a category}

### Why this doesn't exist
{Structural reason: assumption nobody questioned, technology gap, user nobody designed for, etc.}

### Why now
{What changed in the last 18 months that makes this viable — the specific enabler}

### Minimum viable implementation path
{1-3 sentences. Falsifiable — someone could try the first step and fail. Names specific tech, data sources, build artifacts, or measurable outcomes. If absent or judged hand-wave, tag `[FEASIBILITY_UNVERIFIED]` above.}

### Closest existing things
{What the prior-art search agent found — the nearest references with citations — and how this differs structurally. If verdict was `partial_match`, also tag `[PRIOR_ART_OVERLAP]` above and list the overlap below.}

### Novelty checks completed
- N4 (Forcing function — blind assessment + chain evaluation): PASS — {what the blind assessment found, why the chain is genuine}
- N1 (Exact existence search): PASS — {searches run, what was not found}
- N2 (Structural clone test): PASS — {why this isn't a domain-shifted version of X}
- N3 (Recency test): PASS — {why this wasn't viable 3 years ago + structural reason}
- Novelty judge (independent blind classification): `novel` — {one-sentence rationale from judge}
- Prior-art search (external-source verification): `no_match_found` — {queries run, refs cited or "NONE"}
---
```

**Note on N4 evidence:** The killer agent evaluates the idea in two passes (blind, then with chain). The N4 PASS entry must describe both: what the blind assessment concluded AND why the chain evaluation confirmed it. A one-line "derivation chain is explicit" is not sufficient N4 evidence.

**Tag semantics:**
- `[PRIOR_ART_OVERLAP]`: prior-art search returned `partial_match`. Idea still presented as survivor; the overlap is surfaced to the reader.
- `[NOVELTY_DISPUTED]`: novelty judge returned `disputed`. Idea is a near-miss, not a survivor; does not count toward target.
- `[JUDGE_SUSPECT]`: in this cycle the judge returned `novel` on ≥95% of ≥5 classifications. Treat survivors with skepticism.
- `[FEASIBILITY_UNVERIFIED]`: `minimum_viable_implementation_path` was missing or hand-wave. Coordinator could not confirm a falsifiable first step.
- `novelty_unverified`: prior-art search agent timed out, failed, or `SEARCH_UNAVAILABLE`. The no-match claim is unverified.

---

## Near-Miss Format (FLAGGED ideas)

Present at the end of the run. These are ideas that passed N4 and N1 but were flagged at N2 or N3.

```markdown
---
### [Idea Name] ~ NEAR MISS

**Flagged at:** {N2 | N3}
**Reason:** {Specific — what exists, what structural concern was raised}

**What it is:** {brief description}

**What differentiation it needs to survive:**
{Specific — not "be more unique" but "needs to solve the problem for the edge user with X constraint, which no existing product does because Y"}

**Path to NOVEL:**
{Concrete suggestion — what forcing function combination or constraint injection would push this past the flag}
---
```

---

## Final Report Format

Written to `deep-idea-report.md` after target survivors are reached or user stops.

```markdown
# Deep Idea Report: {domain}
**Run date:** {date}
**Total cycles:** {N} | **Mutation levels reached:** {max level}
**Survivors:** {M}/{target} | **Total ideas evaluated:** {count}
**Total agent calls:** {X}/{max_total_agent_calls} | **Opus calls:** {Y}/{max_opus_calls}
**Termination:** {Target reached | User stopped | Hard ceiling: [which one]}

## Survivors

{Each survivor in the Surviving Idea Format above}

## Near-Misses

{Top 3-5 FLAGGED ideas in Near-Miss Format}

## Kill Registry

Total killed: {N}
| Idea | Forcing Function | Failed Check | Kill Reason |
|------|-----------------|--------------|-------------|
| {name} | {function} | N1 | {existing product URL} |
| {name} | {function} | JUDGE_REJECT | {one-sentence judge rationale} |
| {name} | {function} | PRIOR_ART | {exact_match reference(s)} |

## Landscape Map

**What exists:** {summary of existing solutions}
**Core assumptions of all existing solutions:** {list}
**Recent enablers found:** {list}
**Unexplored edges identified:** {list}

## Mutation History

| Cycle | Level | Reason for escalation |
|-------|-------|----------------------|
| 1 | 0 | Starting state |
| 3 | 1 | 2 consecutive zero-survivor cycles; BISOCIATOR killed at N1 3 times |

## Cost Summary

| Phase | Agents | Model | Est. cost |
|-------|--------|-------|-----------|
| Landscape mapping | 3 | Haiku | ~$0.15 |
| Generation (Level 0, N cycles) | {5N} | Sonnet | ~${X} |
| Kill chain ({ideas} ideas) | {ideas} | Haiku | ~${Y} |
| Novelty judge ({novel_or_flagged} ideas) | {same} | Haiku | ~${J} |
| Prior-art search ({judge_survivors} ideas) | {same} | Haiku | ~${P} |
| Level 3 ({cycles} cycles) | {3×cycles} | Opus | ~${Z} |
| **Total** | | | **~${total}** |

## What worked

{Which forcing functions produced survivors and why — useful for follow-up runs}

## What to try next

{If not at target survivors: recommended domain pivots or constraint injections}
```

---

## Progressive disclosure during the run

While running (before final report), output these status updates:

**After each cycle:**
```
Cycle {N} complete | Mutation level: {L} | Survivors: {M}/{target}
This cycle: {X} NOVEL, {Y} FLAGGED, {Z} KILLED
Kill breakdown: N4: {a}, N1: {b}, N2: {c}, N3: {d}, TIMEOUT: {e}, PARSE_ERROR: {f}
Agent calls: {total}/{max_total} | Opus calls: {opus}/{max_opus}
```

**On mutation escalation:**
```
↑ Escalating to mutation level {N}: {reason}
Next cycle will use: {list of active forcing functions/combinations}
```

**On survivor found:**
```
✓ NOVEL idea found (cycle {N}, level {L}): [{Idea Name}]
[Full survivor format above]
```

**On hard ceiling hit:**
```
⛔ Hard ceiling reached: {which ceiling} ({value}/{max})
Presenting what was found.
```

**On domain pivot gate (Level 5):**
```
⚠ Mutation limit reached after {N} cycles.
[Full pivot gate prompt from LOOP.md — always requires user input]
```
