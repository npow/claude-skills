# DFS Expansion Logic

## Phase 2a: Dimension Discovery

Given the seed topic, enumerate APPLICABLE dimensions. Use the multi-context table — each dimension means different things for different topic types:

| Dimension | For historical/social topics | For technical/scientific topics | For policy topics |
|-----------|-----------------------------|---------------------------------|-------------------|
| WHO | Key people, institutions, communities | Research groups, companies, standards bodies | Agencies, advocacy groups, legislators |
| WHAT | Events, phenomena, concepts | Techniques, approaches, architectures | Policies, regulations, mechanisms |
| HOW | Mechanisms, processes, causation | Algorithms, protocols, implementation | Enforcement, incentives, compliance |
| WHERE | Geography, context, settings | Deployment environments, infrastructure constraints | Jurisdictions, regulatory bodies |
| WHEN | Chronology, sequence | Maturity level, adoption windows, regulatory timeline, phase transitions | Legislative calendar, enforcement dates |
| WHY | Motivations, drivers | Tradeoffs, design constraints, optimization targets | Political economy, stakeholder incentives |
| LIMITS | Constraints, boundaries | Theoretical bounds, safety limits, known failures | Legal limits, enforcement gaps |

**For each dimension, explicitly assess:** "Does this dimension produce meaningful research directions for this specific seed?"
- Skip dimensions that don't apply — do NOT force directions
- WHEN is almost always applicable — it covers maturity, adoption stage, and timeline even for technical topics

**Minimum dimension rule:**
- 0 applicable dimensions → error; prompt user to clarify or broaden seed
- 1-2 applicable dimensions → warn: "This topic appears narrow — only {N} dimensions apply. Continue? [y/N]"
- 3+ applicable dimensions → proceed normally

Goal: 4-8 applicable dimensions. Each dimension should be explorable independently.

---

## Phase 2b: Cross-Product Expansion

For each applicable dimension, generate 2-4 specific research directions:
```
dimension: "HOW (technical)"
  → "What algorithms underlie the core mechanism?"
  → "What are the implementation constraints in production environments?"
  → "How does this compare to prior approaches mechanistically?"
```

Then generate CROSS-DIMENSIONAL directions (intersections):
```
"WHO × WHAT" → "Which organizations are driving which approaches, and why?"
"HOW × LIMITS" → "What implementation constraints create the known failure modes?"
```

**Maximum: 25 initial directions.** Fewer is better — leave budget for depth.

**Depth priority bonus:** Child directions (discovered by agents) get base priority +2 over same-tier siblings at the same depth level. This makes the priority queue implement genuine depth-first ordering.

---

## Phase 2c: Exhaustion Map

Create an explicit tracking structure:
```json
{
  "dimensions": {
    "HOW": {
      "description": "Implementation mechanisms and algorithms",
      "directions": ["dir_001", "dir_003", "dir_012"],
      "explored_count": 0,
      "status": "uncovered"
    },
    "WHEN": {
      "description": "Maturity level and adoption timeline",
      "directions": ["dir_002", "dir_005"],
      "explored_count": 1,
      "status": "partial"
    }
  }
}
```

After every round:
1. Update `explored_count` for each dimension
2. If any dimension has `explored_count == 0` → status = "uncovered", generate new directions with HIGH priority
3. If all dimensions have `explored_count >= 1` AND no new dimensions reported → "covered"

---

## Step 3: Research Round

```
for each round (1..max_rounds):

    # --- PROSPECTIVE GATE (fires before agents spawn) ---
    show user:
      "About to run Round {N}: {frontier_size} directions queued"
      "Estimated tokens this round: ~{estimate} ({cost})"
      "Total spent so far: ~{running_total}"
      "Continue? [y/N/redirect:<focus>]"
    if user says N: stop, synthesize now
    if user says redirect:<text>: add high-priority direction, then proceed

    # Pop highest-priority directions (batch)
    batch = frontier.pop(max_agents_per_round)  # up to 6

    # Take stable snapshot of frontier BEFORE modifying it
    pre_round_frontier_snapshot = copy(frontier)

    # Spawn agents in parallel — select model tier for each
    for direction in batch:
        model = select_model_tier(direction)
        agent = spawn_agent(
            question=direction.question,
            coverage_fingerprint=get_explored_titles(),      # dedup context only
            findings_summary=coordinator_summary,             # research context
            output_path=f"deep-research-findings/{direction.id}.md",
            model=model,
            timeout=8min
        )
        direction.status = "in_progress"

    # Wait for completion (8-minute timeout per agent)
    wait_all(agents, timeout=8min)

    # --- COLLECT ALL NEW DIRECTIONS BEFORE DEDUP ---
    all_new_directions = []
    for direction in batch:
        if timed_out:
            direction.status = "timed_out"
            # DO NOT re-queue; DO NOT increment dedup counter
            continue

        # Validate direction ID header
        validate_direction_id_header(direction)  # see STATE.md

        findings = read(direction.output_path)
        all_new_directions.extend(extract_new_directions(findings))
        direction.status = "explored"

    # --- DEDUP AGAINST STABLE PRE-ROUND SNAPSHOT ---
    # Sort batch by (priority DESC, hash DESC) for determinism
    all_new_directions.sort(key=lambda d: (-priority_rank(d), -hash(d.question)))

    for nd in all_new_directions:
        dedup_check(nd, against=pre_round_frontier_snapshot)  # see STATE.md

    # --- ROUND-LEVEL DIMENSION RE-ASSESSMENT ---
    reassess_skipped_dimensions()  # see below

    # --- UPDATE COORDINATOR SUMMARY ---
    update_coordinator_summary()  # see SYNTHESIS.md

    round += 1
```

---

## Round-Level Dimension Re-Assessment

After each round, the coordinator re-checks previously-skipped dimensions in light of what was found:

1. Review findings from this round for evidence of dimensions that were initially skipped
2. If a skipped dimension now seems applicable: prompt user:
   "Round {N} findings on {topic} show evidence of {X}. Should the {DIMENSION} dimension be added? [y/N]"
3. If user confirms: generate directions for that dimension, add to frontier with HIGH priority

This corrects cold-start errors in the initial dimension assessment.

---

## Model Tier Selection

```python
def select_model_tier(direction, duplication_count):
    # Re-exploration of a shallow direction → only case for Opus
    if duplication_count == 2 and direction.exhaustion_score <= 2:
        return "opus"

    # Broad, high-value directions → Sonnet
    if direction.depth == 0:
        return "sonnet"
    if direction.depth == 1 and direction.priority == "high":
        return "sonnet"

    # Everything else → Haiku
    # (depth 1 medium, depth 2+, low priority, verification/confirmation)
    return "haiku"
```

**Search budget by tier:**

| Tier | Model | Max searches | Expected agent runtime |
|------|-------|-------------|----------------------|
| Scout | haiku | 8 | ~3–5 min |
| Researcher | sonnet | 12 | ~8–10 min |
| Deep Dive | opus | 18 | ~15–20 min |

---

## Step 4: Coverage Evaluation

After each round:
1. "What major angles of the seed topic are NOT yet covered?"
2. "Did any agent's findings reveal an entirely new framing?"
3. "Are existing frontier items sufficient, or do we need new top-level directions?"

If gaps found → generate new TOP-LEVEL directions (not sub-directions) with high priority.

---

## Step 5: Termination

**Any-of-4 termination — stop when the FIRST condition is true:**

1. **User chooses N at a prospective gate** (explicit user decision) → label: "User-stopped at round N"
2. **Coverage plateau:** No new dimensions for 3 consecutive rounds AND all frontier items have exhaustion score ≥ 4 → label: "Coverage plateau — frontier saturated"
3. **Budget soft gate:** `max_rounds` reached AND frontier is non-empty → show gate (below), do NOT auto-stop
4. **Frontier actually empties** (possible because direction reporting is optional) → label: "Convergence — frontier exhausted"

**`max_rounds` is a soft gate, not a hard stop.** When `max_rounds` is reached with frontier non-empty:
```
Budget limit reached (max_rounds={N}). Frontier still has {M} unexplored directions.
Top queued: {list top 5 by priority}
Options:
  [y] Extend by {recommended_extension} more rounds (~${cost_estimate})
  [+N] Extend by custom N rounds
  [n] Stop here and synthesize now
```
- If user says y/+N: update max_rounds, continue
- If user says n: stop, synthesize, label: "User-stopped at round N — {M} frontier directions unexplored"
- `--auto` flag overrides this gate and hard-stops at max_rounds (unattended runs)

**True hard stop:** `max_rounds * 3` as absolute ceiling (prevents runaway cost on `--auto` with growing frontier).

---

## Priority Ordering

Frontier items ordered by priority (highest first):
1. **Critical**: Directions for uncovered dimensions
2. **High**: Agent-reported high-priority directions from rich/surprising findings; children of current directions (+2 depth bonus)
3. **Medium**: Cross-cutting directions; depth-1 medium-priority
4. **Low**: Diminishing-returns areas, narrow sub-directions, depth-2+

Within same priority level:
- Lower depth (broader) over higher depth (narrower)
- Directions connected to more explored areas over isolated ones

---

## Direction Schema

```json
{
  "id": "dir_001",
  "question": "What implementation constraints create known failure modes in production?",
  "dimension": "LIMITS",
  "angle": "production failure modes",
  "parent": null,
  "priority": "high",
  "depth": 0,
  "source": "seed|agent|reexpansion",
  "status": "frontier|in_progress|explored|timed_out|saturated"
}
```

- `depth 0` = top-level from seed expansion
- `depth N` = discovered by depth-(N-1) agent
- Max depth: 3 (configurable). Prevents infinite recursion on tangents.
