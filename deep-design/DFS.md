# DFS Critique Expansion Logic

## Phase 3a: Dimension Discovery

Given the design concept, enumerate CRITIQUE DIMENSIONS — orthogonal axes of attack. Use this structured enumeration:

| Frame | Question | Example (for "reverse Turing test game") |
|-------|----------|------------------------------------------|
| MECHANICS | How do the core interactions work? Are they exploitable? | Voting rules, question types, turn structure |
| BALANCE | Is it fair? Can one side dominate trivially? | AI can ask trivia only bots know; human always loses |
| UX/FLOW | Can a real user navigate this without confusion? | How does a new player understand the rules mid-game? |
| EDGE CASES | What happens at the boundaries? | All AIs vote the same; human disconnects; 1v1 scenario |
| INCENTIVES | Do the rewards/punishments drive desired behavior? | Is it rational to stay silent? To always vote randomly? |
| DEGENERATE STRATEGIES | What's the min-max / cheese / grief approach? | Human copies bot speech patterns exactly; bots collude |
| NARRATIVE/THEME | Does the experience match the intended feeling? | Is it actually tense? Or tedious? Does the premise hold? |
| TECHNICAL | Can this actually be built? What's hard? | Real-time AI inference latency; concurrent game state |
| SCALABILITY | Does it work at different sizes/loads? | 3 players vs 100; 1 game vs 10k concurrent |
| ACCESSIBILITY | Who is excluded? What barriers exist? | Language, disability, platform, skill floor |
| RETENTION | Why would someone play/use this more than once? | Does it get stale? Is there progression? Variety? |
| SOCIAL/ETHICAL | What could go wrong socially or ethically? | Harassment, data privacy, psychological manipulation |

Goal: 8-12 orthogonal dimensions. Each dimension should be critiqueable independently.

**Dimension selection is concept-dependent.** For a game design, all 12 above are relevant. For an API design, swap NARRATIVE for DEVELOPER EXPERIENCE and BALANCE for ERROR HANDLING. Adapt the framework to the domain.

**Required dimension categories** — at least one dimension per category must be explored before termination:
- **correctness** — does the design work as claimed?
- **usability/UX** — can users actually use it?
- **economics/cost** — is it affordable/sustainable?
- **operability** — can it be operated/maintained?
- **security/trust** — can it be abused or corrupted?

Track `required_categories_covered` in state.json. Uncovered required categories have CRITICAL priority.

**Angle definition logging:**
Every angle added to the frontier is written to state.json with:
- discovery_source: "coordinator_initial" | "critic_suggested" | "outside_frame"
- discovery_round: N
- rationale: 1-sentence reason this angle was selected/generated
Angle definitions are immutable once written. The coordinator cannot modify them.

## Phase 3b: Cross-Product Expansion

For each dimension, generate 2-4 specific critique angles:
```
dimension: "balance"
  → "Can the AI agents trivially identify the human by asking questions only AIs can answer?"
  → "Can the human exploit predictable AI behavior patterns to appear more AI-like?"
  → "Is the voting mechanism susceptible to kingmaker dynamics?"
  → "Does going first/last confer a systematic advantage?"
```

Then generate CROSS-DIMENSIONAL angles:
```
"balance × degenerate" → "Is there a dominant strategy that always wins for humans OR AIs?"
"UX × edge cases" → "What happens to the UX when a player disconnects mid-interrogation?"
"incentives × retention" → "Do the incentive structures encourage replay or one-and-done?"
```

Target: 20-40 initial critique angles. Hard cap: 40 angles in frontier at any time.

## Phase 3c: Exhaustion Map

Create an explicit tracking structure:
```json
{
  "dimensions": {
    "balance": {
      "description": "Fairness and competitive equilibrium",
      "required_category": "correctness",
      "angles": ["angle_001", "angle_003", "angle_012"],
      "explored_count": 0,
      "status": "uncovered"
    },
    "edge_cases": {
      "required_category": null,
      "angles": ["angle_002", "angle_005"],
      "explored_count": 1,
      "status": "partial"
    }
  },
  "required_categories_covered": {
    "correctness": false,
    "usability_ux": false,
    "economics_cost": false,
    "operability": false,
    "security_trust": false
  }
}
```

After every round:
1. Update `explored_count` for each dimension
2. Update `required_categories_covered` for any newly-explored category
3. If any dimension has `explored_count == 0` → status = "uncovered", generate new angles, add to frontier with CRITICAL priority
4. If any required category has zero explored angles → add angles targeting that category with CRITICAL priority
5. If all dimensions have `explored_count >= 1` AND no new dimensions → "covered"

## Step 4: Critique Round

```
for each round (1..max_rounds):
    # Pop highest-priority angles
    batch = frontier.pop(max_agents_per_round)  # up to 6

    # Write all required data to files BEFORE spawning
    write_file(f"deep-design-{run_id}/known-flaws.md", get_known_flaw_ids_and_titles())
    for angle in batch:
        write_file(f"deep-design-{run_id}/angles/{angle.id}.md", angle)

    # Spawn critics in parallel — write state BEFORE each spawn
    for angle in batch:
        # CRITICAL: write state BEFORE Agent tool call, not after
        state.angles[angle.id].status = "in_progress"
        state.angles[angle.id].spawn_time_iso = now_iso()
        write_state(state)

        try:
            agent = spawn_critic(
                spec_file=f"deep-design-{run_id}/specs/{current_spec_version}.md",
                angle_file=f"deep-design-{run_id}/angles/{angle.id}.md",
                known_flaws_file=f"deep-design-{run_id}/known-flaws.md",
                output_path=f"deep-design-{run_id}/critiques/{angle.id}.md"
            )
        except AgentSpawnError:
            # Spawn refused (tool limit, etc.) — NOT a timeout, NOT "spawned"
            state.angles[angle.id].status = "spawn_failed"
            state.angles[angle.id].spawn_time_iso = null
            write_state(state)
            # Resume: retry spawn (don't wait loop against non-existent agent)

    # Spawn outside-frame critic (slot #7) — always spawned, regardless of frontier
    spawn_outside_frame_critic(
        concept_description=state.core_claim,  # NOT current spec
        output_path=f"critiques/outside-frame-round-{round}.md"
    )

    # Timeout scaling
    base_timeout = 120
    if round >= 3: base_timeout = 180
    if word_count(current_spec) > 3000: base_timeout = int(base_timeout * 1.5)

    # Wait for completion
    wait_all(agents, timeout=base_timeout)

    # Quorum rule: round complete if >= 4 of 6 spec-derived critics succeed
    spec_critics = [a for a in agents if a.type == "spec_derived"]
    successful = [a for a in spec_critics if parseable_output(a)]
    if len(successful) < 4:
        # Failed critics re-enter frontier at elevated priority
        for failed in spec_critics - successful:
            failed.angle.priority = "critical"
            frontier.push(failed.angle)

    # Process results
    for angle in batch:
        if angle.status == "spawn_failed":
            continue  # Will be retried on resume

        critique = read(angle.output_path)
        flaws = extract_flaws(critique)
        gap_reports = extract_gap_reports(critique)  # GAP_REPORT structured lines
        new_angles = extract_new_angles(critique)

        for gap in gap_reports:
            # Re-open a closed flaw if its fix was insufficient
            if gap.references_flaw_id in state.flaws:
                state.flaws[gap.references_flaw_id].status = "open"
                state.flaws[gap.references_flaw_id].gap_note = gap.gap_description
                # Bypasses dedup — does NOT consume challenge token

        for flaw in flaws:
            # Severity classification by independent judge agent — NOT coordinator
            severity = spawn_severity_judge(flaw, fact_sheet_file)
            add_to_flaw_registry(flaw, severity)

        # Each spec-derived critic may file at most 1 new angle
        new_angles_from_critic = extract_new_angles(critique)[:1]  # cap at 1
        # Log suppressed angles
        if len(extract_new_angles(critique)) > 1:
            log_coverage_gap(type="cap_dropped", suppressed=extract_new_angles(critique)[1:])

        for na in new_angles_from_critic:
            hash = tier1_hash(na.question)
            if duplication[hash] < 2:
                tier2 = tier2_semantic_check(na, pre_round_snapshot)
                if tier2 != DUPLICATE:
                    frontier.push(na)
                    duplication[hash] = (duplication[hash] or 0) + 1

        angle.status = "explored"

    # Circuit breaker
    if consecutive_rounds_with_failures >= 3:
        halt("SYSTEM_FAILURE: 3 consecutive rounds with critic failures")
        notify_user_at_turn_boundary()

    # Redesign phase
    critical_flaws = [f for f in new_flaws if f.severity == "critical"]
    major_flaws = [f for f in new_flaws if f.severity == "major"]

    if critical_flaws or major_flaws:
        redesign(critical_flaws + major_flaws)
        write_updated_spec(round)

    round += 1
```

## Step 5: Coverage Evaluation

After each round, the coordinator asks:
1. "What required dimension categories have NOT been covered?"
2. "What dimensions of this design have NOT been stress-tested?"
3. "Did any critic's findings reveal an entirely new attack surface?"
4. "Are the fixes from the redesign phase introducing new vulnerabilities?"

If gaps found → generate new TOP-LEVEL critique angles with critical priority.

## Step 6: Termination

**max_rounds is the PRIMARY termination mechanism.** The following are EARLY EXIT conditions —
the run terminates before max_rounds if ALL three are satisfied simultaneously:

**Early Exit Condition 1 — Required category coverage:**
All 5 required categories have explored_count >= 1:
- correctness, usability/UX, economics/cost, operability, security/trust

**Early Exit Condition 2 — Convergence:**
No NEW dimension categories discovered for 2 consecutive rounds.
(Tracked via `rounds_without_new_dim_categories` in state.json, NOT `rounds_without_new_dimensions`)
Note: outside-frame critic discoveries DO NOT count toward this stability trigger.

**Early Exit Condition 3 — Critical flaw resolution:**
No critical flaws with status "open".
Flaws with status "accepted_with_tension" or "pending_user_acknowledgment" are EXCLUDED from this check.

**Early exit label:** "Conditions Met"
**max_rounds label:** "Max Rounds Reached"
**Never:** "No critical flaws remain"

Note: "frontier empty" is no longer a termination condition. Under normal operation with
critics generating new angles, the frontier does not empty. Removing it as a condition
makes termination honest about how the run actually ends.

**Hard stop:** `max_rounds` (default 5) → label "Max Rounds Reached". Final spec MUST list unresolved flaws, uncovered dimensions, and open issues.

## Priority Ordering

Frontier items are ordered by priority (highest first):
1. **Critical**: Uncovered required categories; dimensions with zero explored angles; angles targeting known critical flaws; angles targeting dimensions where previous round had quorum failure (only 4/6 succeeded); INVARIANT_VIOLATION items from invariant-validation agent
2. **High**: Angles examining recent redesign changes (checking fix quality); required categories with shallow coverage
3. **Medium**: Cross-cutting angles connecting multiple dimensions
4. **Low**: Polish-level angles, narrow sub-angles

Within the same priority level, prefer:
- Lower depth (broader) over higher depth (narrower)
- Angles targeting dimensions with fewer explored angles

## Displacement Rule (when frontier is at cap)

When frontier is at 40 angles and a new angle needs to be added, displace the lowest-priority angle. Constraints:
- **Cannot displace a dimension's only remaining depth-0 angle** — must have at least one depth-0 angle per dimension at all times
- **Cannot displace a dimension's only remaining depth-1 angle when no depth-0 angles remain for that dimension** — prevents inadvertent depth-stranding
- **Cannot displace any angle from a required category** if that category has zero explored angles

If no angle can be displaced under these constraints, cap prevents adding new angle; log `FRONTIER_FULL_DISPLACEMENT_BLOCKED`.

## Angle Schema

```json
{
  "id": "angle_001",
  "question": "Can AI agents trivially identify the human by asking factual trivia?",
  "dimension": "balance",
  "required_category": "correctness",
  "focus": "AI advantage through knowledge asymmetry",
  "parent": null,
  "priority": "high",
  "depth": 0,
  "source": "seed",
  "discovery_source": "coordinator_initial",
  "discovery_round": 0,
  "rationale": "Tests whether knowledge asymmetry between AI and human players breaks game balance",
  "status": "frontier|in_progress|explored|timed_out|saturated|spawn_failed",
  "spawn_time_iso": null,
  "critique_file": null,
  "sub_angles": [],
  "flaws_found": []
}
```

- `depth 0` = top-level from dimension discovery
- `depth N` = discovered by depth-(N-1) critic
- Max depth: 3. Prevents infinite recursion on tangential concerns.
- `spawn_failed`: Agent tool returned an error (not a timeout). Resume retries the spawn; does not wait.
- `discovery_source`: "coordinator_initial" | "critic_suggested" | "outside_frame" — immutable once written.
