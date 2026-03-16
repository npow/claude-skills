# Mutation Loop

The loop never gives up. When standard generation runs dry, it escalates through 5 mutation levels. When all mutation levels are exhausted, it reframes the domain and starts over. The answer exists — you haven't looked from the right angle yet.

---

## Hard Ceilings (non-negotiable, cannot be overridden by --auto)

```
max_total_agent_calls: 200     # absolute hard stop — all agents across all phases
max_opus_calls: 30             # Opus agents only (Levels 3-4)
max_cycles_per_level: 5        # max cycles at any single mutation level before forced escalation
max_reframes: 3                # max domain pivots before mandatory stop
```

When any ceiling is hit, the skill must stop and report what was found. These are hard stops — `--auto` does not bypass them. Display the ceiling reason in the final output.

---

## --auto mode rules

`--auto` skips the per-cycle prospective gate only.

`--auto` does **NOT** apply to:
- The pre-run declaration (Phase 0c) — always shown
- Level 5 domain pivot gate — **always requires user input under --auto**; if no input is available, abort and present survivors + near-misses
- Hard ceilings above — always enforced regardless of --auto

---

## State tracking

After each cycle, update the loop state in `deep-idea-state.json`:

```json
{
  "cycle": 5,
  "mutation_level": 2,
  "consecutive_zero_survivor_cycles": 2,
  "cycles_at_current_level": 3,
  "total_agent_calls": 47,
  "total_opus_calls": 6,
  "reframe_count": 0,
  "forcing_function_performance": {
    "INVERTER": { "cycles_used": 4, "survivors": 1, "last_kill_reason": "N2" },
    "BISOCIATOR": { "cycles_used": 4, "survivors": 0, "last_kill_reason": "N1" },
    "EDGE_DESIGNER": { "cycles_used": 4, "survivors": 2, "last_kill_reason": null },
    "TEMPORAL_EXPLOITER": { "cycles_used": 4, "survivors": 0, "last_kill_reason": "N3" },
    "CONSTRAINT_FLIPPER": { "cycles_used": 4, "survivors": 0, "last_kill_reason": "N4" }
  },
  "exhausted_signals": [
    { "function": "BISOCIATOR", "cycle": 3, "reason": "same mechanism keeps resolving to N1 kills" }
  ],
  "exhausted_functions": ["BISOCIATOR"],
  "saturated_subspaces": ["developer tools for enterprise"],
  "reframes_used": []
}
```

**New fields vs. original:**
- `cycles_at_current_level`: resets to 0 on level escalation; triggers `max_cycles_per_level` check
- `total_agent_calls`: incremented on every agent spawn; checked against hard ceiling
- `total_opus_calls`: incremented on every Opus spawn; checked against Opus ceiling
- `reframe_count`: incremented on every Level 5 domain pivot; checked against `max_reframes`
- `exhausted_signals`: log of generator EXHAUSTED signals with cycle and reason

---

## When to escalate mutation level

**Normal escalation trigger:** 2 consecutive cycles with zero survivors (from kill chain, not from EXHAUSTED signals).

**Per-level cap:** If `cycles_at_current_level >= max_cycles_per_level` (5), escalate regardless of survivor count at current level. This prevents a lucky occasional survivor from keeping the run stuck indefinitely at an expensive mutation level.

**All-EXHAUSTED trigger (special case):** If ALL active generators return EXHAUSTED in the same cycle, this is an immediate escalation trigger — skip the consecutive-zero-cycle counter. Go directly to the next mutation level. This is the one exception to "never skip a level": if you literally have no ideas to evaluate, the level is structurally done.

**EXHAUSTED signal handling:** When a generator reports `FORCING FUNCTION EXHAUSTED`:
- Log in `exhausted_signals`
- Count the function as producing 0 survivors for this cycle
- If the same function has returned EXHAUSTED 2+ consecutive cycles: mark it `exhausted_functions` and rotate it out
- Do NOT conflate EXHAUSTED cycles with zero-survivor cycles for the normal 2-cycle escalation trigger — they are tracked separately

**Never escalate without a logged reason.**

---

## Mutation Levels

### Level 0 — Standard (default starting state)

**Active generators:** All 5 (INVERTER, BISOCIATOR, EDGE DESIGNER, TEMPORAL EXPLOITER, CONSTRAINT FLIPPER) — 5 parallel agents

**What changes:** Nothing. This is the default.

**Escalate to Level 1 if:** 2 consecutive zero-survivor cycles OR all generators EXHAUSTED in the same cycle OR `cycles_at_current_level >= 5`.

---

### Level 1 — Amplify survivors, rotate exhausted

**Active generators:** 6 parallel agents:
- Top 2 performing functions × 2 slots each (4 agents)
- NEGATION STACKER (1 agent)
- MICRO-NICHER (1 agent)

**Agent count note:** Level 1 spawns 6 generators, not 5. This is intentional and overrides Phase 2's default of 5.

**Tiebreaker for "top 2 by survivor count" when all are tied at 0:**
Use kill-chain proximity instead:
1. Functions with ideas that reached N2+ before dying rank above N1-only kills
2. Functions with ideas killed at N3 or N4 rank highest (got furthest through the chain)
3. If still tied: use alphabetical order as a deterministic fallback

**If fewer than 2 functions have any history:** Use EDGE DESIGNER and INVERTER as the default top-2.

**NEGATION STACKER and MICRO-NICHER** are defined in FORCING.md. Read their full definitions there before spawning.

**Escalate to Level 2 if:** 2 consecutive zero-survivor cycles at Level 1 OR `cycles_at_current_level >= 5`.

---

### Level 2 — Cross-function synthesis

**Active generators:** 5 parallel synthesis agents, each combining two forcing functions.

**Isolation carve-out:** Level 2 is the one exception to Golden Rule 8 (generator isolation). Synthesis generators are explicitly coordinator-mediated: the coordinator provides each agent with a brief summary description of what each prior forcing function explored (not the full ideas — just the mechanism used and the outcome). This is not agent-to-agent idea sharing; it is coordinator context injection of exploration history. This carve-out applies only at Level 2.

**Active combinations:**
1. INVERTER + TEMPORAL EXPLOITER: "An inversion that is only possible because of a recent enabler — an assumption that was reasonable 18 months ago but the new enabler now makes it worth inverting"
2. BISOCIATOR + EDGE DESIGNER: "Find a source domain that has already solved the problem for the edge user — transplant that mechanism"
3. CONSTRAINT FLIPPER + TEMPORAL EXPLOITER: "A constraint that BECAME a feature because of a recent enabler — the enabler changes who benefits from the constraint"
4. INVERTER + EDGE DESIGNER: "An inversion designed specifically for the edge user — what assumption is only valid for the 'normal' user, not the edge user?"
5. BISOCIATOR + CONSTRAINT FLIPPER: "A mechanism from a source domain that turned its constraint into a feature — apply that meta-pattern"

**Dual derivation chain requirement:** Level 2 ideas must include a derivation chain that explicitly names both forcing functions and shows how each contributed. N4's blind assessment still applies — the idea must not be producible by either forcing function alone.

**Escalate to Level 3 if:** 2 consecutive zero-survivor cycles at Level 2 OR `cycles_at_current_level >= 5`.

---

### Level 3 — Radical reframe (Opus tier)

**Active generators:** 3 parallel Reframe agents (Opus tier, 10-minute timeout each)

**Opus cost note:** Each Level 3 cycle costs ~$12-15. With `max_cycles_per_level = 5` and `max_opus_calls = 30`, Level 3 can run at most 5 cycles (15 Opus calls) before the per-level cap forces escalation. After Level 3 exhausts, Level 4 gets the remaining Opus budget (up to 15 calls = 3 cycles of 5 agents).

Agent A — **Stakeholder Inversion**: Who are all the stakeholders involved in this domain? The user, the operator, the regulator, the adjacent party, the negatively affected party. Now approach the domain from the perspective of the stakeholder who is MOST IGNORED by all existing products.

Agent B — **Business Model Reframe**: All existing solutions share a business model. What business model is STRUCTURALLY DIFFERENT? Design a product where the novelty IS the business model, not the feature set.

Agent C — **Problem Decomposition**: Take the target domain's core problem. Break it into 5 sub-problems. Pick the sub-problem that NO existing tool addresses. Build a product that ONLY solves that sub-problem perfectly.

**Prospective gate before EVERY Level 3 cycle (cannot be skipped by --auto):**
```
About to run Level 3 cycle {N}: 3 Opus agents (~$12-15 estimated)
Opus calls used so far: {X}/{max_opus_calls}
Total agent calls: {Y}/{max_total_agent_calls}
Continue? [y/N]
```

**Escalate to Level 4 if:** 2 consecutive zero-survivor cycles at Level 3 OR `cycles_at_current_level >= 5`.

---

### Level 4 — Inter-domain transplant (Opus tier)

**Active generators:** 5 parallel Inter-domain agents (Opus tier, 10-minute timeout each)

**Opus cost note:** Each Level 4 cycle costs ~$20-25. With remaining Opus budget after Level 3, typically 2-3 cycles maximum.

**Process:**
1. Identify 5 unrelated domains that have solved hard coordination/optimization/discovery problems recently
2. For each: describe the core mechanism (not the product — the abstract mechanism)
3. Apply each mechanism to the target domain as literally as possible
4. Each agent receives: one source domain, its solved problem, its mechanism — returns exactly one idea

**Source domain selection criteria:**
- Must be structurally UNLIKE the target domain
- Must have a specific solved problem (not "medicine is interesting" but "triage protocols in mass casualty events solve the problem of resource allocation under uncertainty")
- The mechanism must not already be well-known in the target domain

**Prospective gate before EVERY Level 4 cycle (cannot be skipped by --auto):**
```
About to run Level 4 cycle {N}: 5 Opus agents (~$20-25 estimated)
Opus calls used so far: {X}/{max_opus_calls}
Total agent calls: {Y}/{max_total_agent_calls}
Continue? [y/N]
```

**Escalate to Level 5 if:** 2 consecutive zero-survivor cycles at Level 4 OR `cycles_at_current_level >= 5` OR Opus ceiling reached.

---

### Level 5 — Domain pivot (requires user input, always)

After Level 4 escalation trigger, the domain framing itself is the problem. Show the user:

```
⚠ Mutation limit reached after {N} total cycles.
Survivors found: {M} | Near-misses (FLAGGED): {F}
Total cost estimate: ~${total} ({opus_count} Opus calls, {sonnet_count} Sonnet calls)
Reframes used: {R}/{max_reframes}

The current domain framing "{domain}" appears to be a local minimum. Options:

[1] Pivot the domain: restate the core problem at a higher level of abstraction
    e.g., "developer tools for ML" → "tools for people who build unreliable systems"
[2] Constraint injection: add a hard constraint that forces a different solution space
    e.g., "must work offline", "must work for non-technical users", "must cost nothing to operate"
[3] Present what we have: show all survivors + top near-misses and stop
[4] Custom direction: [user specifies]
```

**--auto behavior at Level 5:** This gate always requires user input. Under `--auto`, the skill pauses and waits. If unattended (no response within a reasonable timeout), automatically select option [3] — present what was found and stop. Never auto-select option [1] or [2] in --auto mode, as this would restart the run without cost awareness.

**If user chooses [1] or [2]:**
- Increment `reframe_count`
- If `reframe_count >= max_reframes` (3): present what was found and stop
- Reset `mutation_level` to 0 and `consecutive_zero_survivor_cycles` to 0
- Reset `cycles_at_current_level` to 0
- Do NOT reset `total_agent_calls`, `total_opus_calls`, or the hard ceilings — these carry over
- Update domain/constraints in state file
- Show updated pre-run declaration with cumulative cost to date before restarting

---

## Anti-give-up rules

**Never say "the space is exhausted."** The space is not exhausted — your current framing is exhausted.

**Never stop without at least 3 near-misses presented.** FLAGGED ideas are valuable. Present them with notes.

**Never skip a mutation level.** Exception: all-EXHAUSTED cycle (see above). The "never skip" rule applies to the normal consecutive-zero-survivor escalation path.

**The weird cycles are where non-obvious ideas live.** Cycles 1-2 produce the least surprising ideas. Cycles 6+ (Level 3-4) produce the structurally unusual ones. Don't stop early.

---

## Saturation response

After 2 consecutive zero-survivor cycles where >80% of kills are at N1 (exact existence):

1. Note which sub-space is saturated in state file
2. Escalate mutation level immediately (do not wait for another cycle)
3. In the escalated cycle: explicitly avoid the saturated sub-space by changing the target user, mechanism, or business model

---

## Kill reason diagnosis

| Symptom | Cause | Mutation response |
|---------|-------|-------------------|
| All ideas killed at N4 | Generators defaulting to free association | Level 1: strengthen forcing function constraints |
| All ideas killed at N1 | Sub-space saturated | Level 1 + note saturated sub-space, change target user |
| All ideas killed at N2 | Generating domain-shifted clones | Level 2: cross-function synthesis |
| All ideas killed at N3 | Generating ideas with no "why now" | Level 1: extra TEMPORAL EXPLOITER slots |
| All forcing functions EXHAUSTED | Framing exhausted at current level | Immediate escalation (skip zero-survivor counter) |
| Level 3-4 still failing | Domain is genuinely wrong | Level 5: domain pivot gate |

---

## Mutation log format

After each mutation, append to state file:
```json
{
  "cycle": 5,
  "escalation": "Level 0 → Level 1",
  "reason": "2 consecutive zero-survivor cycles; BISOCIATOR killed at N1 for 3 cycles straight",
  "performance_at_escalation": {
    "total_cycles": 4,
    "total_survivors": 1,
    "total_agent_calls": 32,
    "total_opus_calls": 0
  }
}
```
