# Evidence, Disconfirmation, and the Discriminating Probe

This file defines the core epistemics of deep-debug. Every hypothesis is evaluated against it. Every judge applies it. The coordinator uses it to rank and to decide when a hypothesis has earned the right to become a fix.

## Evidence Strength Hierarchy

Rank evidence from strongest to weakest. Stronger-tier evidence displaces weaker-tier evidence on the same claim.

| Tier | Kind | Examples |
|------|------|----------|
| **1** | Controlled reproduction / direct experiment / uniquely discriminating artifact | The failing test passes after the fix and fails before. A probe whose output uniquely identifies one hypothesis. |
| **2** | Primary artifact with tight provenance | Timestamped logs from the failing run. Trace events. Metrics. Benchmark outputs. Config snapshots. Git history. File:line behavior you just read. |
| **3** | Multiple independent sources converging | Three different tools (logs + trace + test run) agree on the same sequence of events. |
| **4** | Single-source code-path or behavioral inference | Reading the code and reasoning "this branch would explain the symptom" — fits, but has not been uniquely discriminated from alternatives. |
| **5** | Weak circumstantial clues | Naming similarity ("this is called `cache_flush`, and the bug is about staleness"). Temporal proximity ("the bug started after X was merged"). Stack-position guesses. |
| **6** | Intuition / analogy / speculation | "This reminds me of bug Y from three months ago." "The fact that the symptom happens here makes me think of Z." |

### Application rules

- **A higher tier displaces a lower tier on the same claim.** If tier-1 evidence (a test passes/fails) contradicts a tier-4 code-path inference, trust the test.
- **Low tiers cannot outrank high tiers by quantity.** Ten tier-5 circumstantial clues do not outweigh one tier-2 artifact that contradicts them.
- **`critic_confidence` is NOT evidence.** A hypothesis agent saying `CONFIDENCE: high` does not elevate the underlying evidence tier.
- **Judge's `EVIDENCE_TIER` field records the HIGHEST tier of supporting evidence** — not the average. If a hypothesis has tier-2 support AND tier-5 support, the tier is 2.

### Hierarchy applied to plausibility tiers

The judge's plausibility verdict is partially determined by evidence tier:

| Plausibility | Minimum evidence tier | Additional requirements |
|--------------|------------------------|-------------------------|
| `leading`    | 1 or 2                 | Falsifiable, all 5 validation checks pass, pass 1 + pass 2 both confirm |
| `plausible`  | 3                      | Falsifiable, survives validation, confirmed by judge |
| `disputed`   | —                      | Failed ≥1 validation check (usually falsifiability) |
| `rejected`   | —                      | Directly contradicted by tier-1 or tier-2 evidence via probe or primary artifact |
| `deferred`   | —                      | Probe would require more time/resources than the budget allows |

Evidence tier is necessary but not sufficient. A hypothesis with tier-1 evidence but no falsifiability claim cannot be `leading` — it's `disputed`.

---

## Disconfirmation Rules

**The Iron Law of evidence for deep-debug: every serious hypothesis must actively seek its strongest disconfirming evidence — not just confirming evidence.** Confirmation bias is the single most common failure mode of hypothesis-driven debugging; structural disconfirmation is how deep-debug corrects for it.

For every hypothesis that reaches the judge:

1. **Ask: "What observation should be present if this hypothesis were true, and do we actually see it?"**
   If the hypothesis predicts a specific log line / return value / state, the evidence file must record whether that prediction holds. A prediction that was never checked is not evidence for or against.

2. **Ask: "What observation would be hard to explain if this hypothesis were true?"**
   Name the observation that would contradict the hypothesis if it happened. This is the disconfirming prediction. The discriminating probe is the experiment that would produce or fail to produce this observation.

3. **Ask: "Has the disconfirming search been attempted?"**
   The hypothesis file has a `DISCONFIRMATION_ATTEMPTED: true|false` field. `false` means the hypothesis survives only because no one looked for disconfirming evidence. Its confidence stays low. The judge downgrades these automatically.

4. **"Not yet disconfirmed" is NOT the same as "confirmed."**
   A hypothesis without disconfirming searches is `plausible` at best, never `leading`. Promotion to `leading` requires at least one disconfirmation search that came back empty (i.e., an attempted rebuttal that didn't succeed).

### Disconfirmation search techniques

- **Construct a counter-example scenario:** "If the race hypothesis is true, then running the test 50 times serially (no concurrency) should pass. Does it?"
- **Probe a distinguishing prediction:** "If the framework-contract hypothesis is true, `import X; X.get_lock_behavior()` should return `Y`. Does it?"
- **Historical check:** "If this is caused by commit `abc123`, then checking out `abc123^` should show the bug absent. Does it?"
- **Environmental check:** "If this is environmental, then the same code with production's config should fail locally. Does it?"

### Down-rank when...

Explicitly down-rank (shift from `leading` to `plausible`, or from `plausible` to `disputed`) when:

- Direct evidence contradicts the hypothesis
- Hypothesis survives only by adding new unverified assumptions (each additional assumption is a liability)
- Hypothesis makes no distinctive prediction compared with rivals
- A stronger alternative explains the same facts with fewer assumptions (Occam)
- Hypothesis's support is mostly tier-4 or lower while rival has tier-2 support on the same claim
- Hypothesis lost the rebuttal round (see below)
- Hypothesis converged into a parent hypothesis

The coordinator MUST record the reason for the down-rank in `hypotheses.{id}.falsification_note` or `hypotheses.{id}.rejection_reason`. "Down-ranked without reason" is a state invariant violation.

---

## Rebuttal Round

After the judge's pass 2 verdict on a cycle, if ≥ 2 hypotheses are at `leading` or `plausible`, run a rebuttal round between the leader and the strongest alternative.

**Purpose:** Force the leader to defend against the best challenge before it gets promoted to a fix. This catches cases where the leader's evidence is strong in isolation but actually shares mechanism with an overlooked alternative.

**Mechanics (independent agent — separate from judge):**

1. **Setup:**
   - Input: leader hypothesis file + alternative hypothesis file + current evidence file
   - Output file: `deep-debug-{run_id}/rebuttal-cycle{N}.md`
   - Agent tier: Sonnet (this is adversarial reasoning, not classification)

2. **Step 1 — Challenger's case:** Alternative hypothesis writes its strongest challenge to the leader. Format: "The leader predicts X; but evidence Y shows X is not observed. Therefore the leader is missing something." OR: "The leader's mechanism depends on assumption Z; if Z is false, the leader fails. Evidence shows Z is actually false because…"

3. **Step 2 — Leader's response:** Leader must answer with evidence, not assertion. Format: "The challenge fails because evidence W (tier 2, source: ...) shows..."

4. **Step 3 — Verdict:**
   - **Leader holds:** evidence-based response refutes the challenge → leader stays
   - **Leader weakened:** response is tier-4 or lower while challenge is tier-2 or higher → re-shuffle; the challenger becomes the new leader
   - **Leader falsified:** challenger's evidence directly contradicts a leader prediction → leader goes to `rejected`, challenger advances
   - **Inconclusive:** both sides have comparable evidence; neither wins → both remain at current tier, cycle advances to discriminating probe

5. **Step 4 — Convergence check:**
   - Do leader and challenger imply the **same causal mechanism** with different language? → merge into one hypothesis; note in `component_name_history`
   - Do they imply the **same next probe**? → merge probes; keep hypotheses separate only if their predictions differ on at least one other observable
   - Do they **sound similar but imply different probes**? → keep separate; these are genuinely distinct hypotheses that happen to share vocabulary

**Rebuttal agent prompt:** see SKILL.md §Agent Prompt Templates.

**Golden Rule for rebuttals:** Convergence requires either the same root-causal mechanism or independent evidence pointing to the same explanation. Similar language is NOT convergence — similar language with different mechanisms is a convergence-look-alike, a classic source of debugging confusion.

---

## The Discriminating Probe

The discriminating probe is what makes deep-debug different from a "hypothesize and try" loop. A probe is a **concrete experiment** whose result will distinguish the top two hypotheses. It is NOT "read more code" or "think harder."

### Criteria for a good probe

1. **Bounded time:** ≤30 minutes to execute (ideally ≤10)
2. **Hard evidence:** produces a log line, return value, test result, or artifact — not an interpretation
3. **Distinguishes:** the expected result differs measurably between the leader and the alternative
4. **Reversible or non-destructive:** reading state is fine; writing production state is not (requires user confirmation)
5. **Documented predictions:** BEFORE executing, the probe spec records the expected result for each hypothesis. Post-hoc rationalization is how probes get corrupted.

### Bad probes (reject)

- "Read the code more carefully." → this is gathered evidence; it doesn't collapse uncertainty.
- "Run the test 10 times and see." → unless the probe design includes specific ordering/timing variation, this is just repeated observation.
- "Add more logging and re-run." → this is instrumentation. If you don't know what the logs would distinguish, it's not a probe; it's a data-gathering step that goes in Phase 1, not Phase 4.
- "Ask the user." → this is a clarifying question for Phase 0, not a probe.
- "Look for similar bugs in git history." → this is historical search for Phase 1 recent-changes.

### Executing the probe

1. **Write the spec first** (`deep-debug-{run_id}/probes/probe_{id}.md` — see FORMAT.md §Discriminating Probe Specification). Spec includes: question, distinguishes-list, execution-method, expected-per-hypothesis, safety-check.
2. **Safety check:** if probe touches production data OR is irreversible → USER CONFIRMATION REQUIRED. Show the spec, wait for approval. If `--auto`, reject the probe and choose a safer alternative.
3. **Execute:**
   - Simple probe (run test, query DB, check file): coordinator runs directly
   - Complex probe (build artifact, multi-step instrumentation, replay): spawn `evidence-gatherer` agent with probe spec
4. **Record raw output** in `deep-debug-{run_id}/evidence.md` Probe Log section. No summarization. Paste the full output.
5. **Apply acceptance criterion:**
   - Result matches "expected if hypothesis A" → winner = A
   - Result matches "expected if hypothesis B" → winner = B
   - Result matches neither → inconclusive → may spawn second probe (hard-cap 3 per cycle)
   - Result contradicts BOTH → both hypotheses move to `rejected`; treat as judge rejected all; re-enter Phase 2 with updated evidence

6. **Update hypotheses:**
   - Winner → promoted to Phase 5 candidate (the fix)
   - Falsified → `status: "falsified_by_probe"` with `falsification_note` citing the probe
   - Not distinguished → stays at current plausibility; coordinator may design a second probe

### Probe count limits

- `max_probes_per_cycle = 3` (hard ceiling)
- Hitting the cap without a winner ⇒ cycle ends as `hypothesis_space_saturated`; increment `fix_attempt_count` (treating it as a failed fix for ceiling purposes); move to Phase 6
- Rationale: running probe 4, 5, 6 is pattern-fishing. At that point the hypothesis set is wrong — re-enter Phase 2 or escalate to Phase 7

---

## Cross-Check Lenses

After the initial evidence pass on a leader hypothesis, pressure-test with these lenses when they can surface a missed explanation. Each lens is a mental-model prompt — the coordinator (or an independent agent) reads the leader hypothesis through the lens and asks: "Does the lens reveal a challenge the direct evidence missed?"

Not every lens applies to every bug. Apply them when relevant.

### Systems lens
Queues, retries, backpressure, feedback loops, upstream/downstream dependencies, boundary failures, coordination effects.

Applied to leader: "Is there a queue or retry layer between where this symptom surfaces and where my leader locates the cause? Could the real cause be upstream/downstream, with the symptom being the system's reaction to it?"

### Premortem lens
Assume the current best explanation is incomplete or wrong. What failure mode would embarrass the trace later?

Applied to leader: "Imagine it's 3 days from now and we're re-opening this bug because the fix didn't hold. What's the most likely thing the current hypothesis missed?"

### Science lens
Controls, confounders, measurement bias, alternative variables, falsifiable predictions.

Applied to leader: "What would I need to control for to isolate this cause? Is there a confounder I haven't ruled out? Is my 'evidence' actually a measurement artifact?"

---

## Explicit Down-Ranking Guidance

When demoting a hypothesis's plausibility, the coordinator MUST record the reason. Valid reasons (each maps to a specific validation or rebuttal outcome):

| Reason | When to use |
|--------|-------------|
| `contradicted_by_primary_evidence` | Tier-1 or tier-2 evidence directly contradicts a prediction |
| `lacks_predicted_observation` | The hypothesis predicted observable X; disconfirmation search confirmed X is absent |
| `requires_ad_hoc_assumptions` | Hypothesis survives only by adding assumptions not supported by evidence |
| `explains_fewer_facts_than_alternative` | Alternative explains everything this hypothesis does, plus additional facts |
| `lost_rebuttal_round` | Leader weakened or falsified in rebuttal |
| `converged_into_parent` | Hypothesis merged with another; see merge record |
| `falsified_by_probe` | Probe result directly contradicts prediction |
| `failed_falsifiability_check` | Cannot construct a scenario where this hypothesis would be falsified |
| `failed_premise_check` | Framework/environment already precludes the scenario the hypothesis requires |
| `budget_deferred` | Probe would exceed budget; moved to `deferred` |

"Down-ranked because it didn't feel right" is NOT a valid reason. Every demotion is auditable.

---

## Summary contract

- **Every hypothesis** has evidence_for, evidence_against, critical_unknown, discriminating_probe, and confidence — all five fields populated, not placeholders
- **Every judge verdict** cites evidence tier and names the validation check that determined its pass 1 classification
- **Every probe** has a spec written BEFORE execution with expected-per-hypothesis results
- **Every down-rank** has a reason from the table above
- **Every disconfirmation search** is either attempted (and the result recorded) or explicitly deferred with rationale

If any of these are missing, the relevant step is incomplete. The coordinator re-runs that step rather than advancing.
