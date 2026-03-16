# State Management

## State File: `deep-design-{run_id}/state.json`

```json
{
  "run_id": "20260314-153022",
  "generation": 0,
  "concept": "The original design concept",
  "core_claim": "The specific 1-2 sentence claim extracted at Step 0",
  "core_claim_sha256": "sha256-hex-of-core_claim-string",
  "core_claim_calibrated": true,
  "current_spec_version": "v0-initial",
  "current_spec_path": "deep-design-{run_id}/specs/v0-initial.md",
  "dimensions": {
    "dim_name": {
      "description": "What this dimension critiques",
      "required_category": "correctness|usability_ux|economics_cost|operability|security_trust|null",
      "angles": ["angle_001", "angle_003"],
      "explored_count": 0,
      "status": "uncovered|partial|covered"
    }
  },
  "required_categories_covered": {
    "correctness": false,
    "usability_ux": false,
    "economics_cost": false,
    "operability": false,
    "security_trust": false
  },
  "angles": {
    "angle_001": {
      "question": "Specific critique question",
      "dimension": "dim_name",
      "required_category": "correctness",
      "focus": "specific focus within dimension",
      "parent": null,
      "priority": "critical|high|medium|low",
      "depth": 0,
      "source": "seed|critic|reexpansion|outside_frame",
      "discovery_source": "coordinator_initial|critic_suggested|outside_frame",
      "discovery_round": 0,
      "rationale": "Why this angle was selected/generated",
      "status": "frontier|in_progress|explored|timed_out|saturated|spawn_failed|quorum_attempted",
      "spawn_time_iso": null,
      "completion_time_iso": null,
      "quorum_met": null,
      "failed_critics": 0,
      "critique_file": "deep-design-{run_id}/critiques/{angle_id}-{critic_agent_id}.md",
      "sub_angles": ["angle_005", "angle_008"],
      "suppressed_sub_angles": [],
      "flaws_found": ["flaw_001", "flaw_003"],
      "failure_reason": null
    }
  },
  "flaws": {
    "flaw_001": {
      "title": "AI can ask trivia to instantly identify human",
      "severity": "critical|major|minor",
      "dimension": "balance",
      "source_angle": "angle_001",
      "round_classified": 1,
      "scenario": "AI asks 'What is the SHA-256 hash of...' — no human can answer instantly",
      "root_cause": "No constraints on question types during interrogation",
      "status": "open|fixed|accepted|disputed|wont_fix|accepted_with_tension|pending_user_acknowledgment",
      "fix_description": null,
      "fix_version": null,
      "acceptance_rationale": null,
      "dispute_rationale": null,
      "gap_note": null,
      "gap_report_count": 0,
      "severity_challenge_token": "available|challenged|exhausted",
      "challenge_executed_by": "challenger_agent|null",
      "cascading_risks": []
    }
  },
  "component_invariants": {
    "component_name": {
      "invariant": "Description of invariant that must hold",
      "established_round": 1,
      "constraint_direction": "tightened|relaxed|neutral",
      "tightened_rounds": [1, 3],
      "last_updated_round": 3
    }
  },
  "component_name_history": [
    {
      "old_name": "severity_classifier",
      "new_name": "classification_agent",
      "migration_round": 4,
      "detection_basis": "semantic_equivalence"
    }
  ],
  "component_name_aliases": {
    "alias_name": "canonical_name"
  },
  "ordering_graph": {
    "edges": [
      {
        "from": "component_a",
        "to": "component_b",
        "established_round": 3,
        "basis": "fix_b_must_precede_fix_c_to_avoid_null_reference"
      }
    ]
  },
  "accepted_fixes": [
    {
      "flaw_id": "flaw_001",
      "fix_description": "Redesigned interrogation to open-ended questions only",
      "fix_version": "v1-post-round-1",
      "components_affected": ["interrogation_phase"],
      "accepted_round": 1
    }
  ],
  "frontier": ["angle_003", "angle_007"],
  "duplication": {
    "hash_abc123": 1
  },
  "coverage_gaps": [],
  "unverified_dropped": [],
  "rounds_without_new_dimensions": 0,
  "rounds_without_new_dim_categories": 0,
  "round": 0,
  "max_rounds": 5,
  "max_agents_per_round": 6,
  "max_depth": 3,
  "autonomous_mode": false,
  "hard_budget_cap": null,
  "layer2_alternatives": {
    "original": ["<alt1 — must fail core claim>", "<alt2 — must fail core claim>"],
    "refreshed": [
      {"round": 2, "alternatives": ["<updated alt1>", "<updated alt2>"]}
    ]
  },
  "core_mechanism_delimiter_version": 0,
  "complexity_budget": {
    "rounds_1_2": 2,
    "rounds_3_plus": 1,
    "overflows": []
  },
  "invariant_validation_results": {
    "round_1": {
      "ran": false,
      "violations": [],
      "stale_annotations": [],
      "regressions": []
    }
  },
  "gap_report_global_counts": {},
  "coverage_gaps_log_path": "deep-design-{run_id}/logs/coverage_gaps.jsonl",
  "frontier_pop_log_path": "deep-design-{run_id}/logs/frontier_pop_log.jsonl"
}
```

---

## Concurrency Control

### Generation Counter (optimistic concurrency)
- Before any write: read current generation from state file
- Increment generation in the write
- After writing, re-read and verify generation is N+1
- If generation is not N+1: a concurrent write occurred → log conflict, retry with fresh read
- This is conflict-detectable, not truly atomic — but sufficient for single-coordinator use

### Lock File
- On startup: write `deep-design-{run_id}.lock` with timestamp
- If lock file from a different run_id exists and is < 15min old:
  "Another deep-design session appears active. Continue anyway? [y/N]"
- On clean exit: delete lock file

**Do NOT claim atomic writes.** The Write tool has no rename primitive. Use the generation counter for conflict detection instead.

---

## Deduplication Algorithm

### Tier 1 — Structural hash (fast, catches exact/near-exact)

**Clause-based causal-preserving hash** (NOT global word sort — global sort destroys "A causes B" ≠ "B causes A"):
1. Lowercase
2. Split into clauses at clause boundaries (commas, "and", "because", "causes", "leads to", "results in")
3. For each clause: remove stop words, sort words WITHIN the clause
4. Join clause hashes in original clause order
5. Hash the result

**Stop words to remove (within-clause only):** the, a, an, is, are, was, were, of, for, in, on, to, with, by, at, from, do, does, did, what, how, why, where, when, who, which

This preserves "A causes B" vs "B causes A" as different hashes, while still catching "What causes A due to B?" = "What leads to A because of B?"

### Tier 2 — Semantic similarity check (catches synonyms, paraphrases)

Applied after Tier 1 passes:
- Compare new angle against all existing angles in the same dimension
- **Growing threshold:** Round 1 = 0.80, Round 2 = 0.83, Round 3 = 0.85, Round 4+ = 0.88
- Higher threshold in later rounds = stricter dedup (prevents late-round starvation as frontier shrinks)

**For embeddings-unavailable path — structured 3-criterion checklist:**
1. Do the questions examine the same failure mode or design concern?
2. Would critiquing one angle produce findings that fully answer the other?
3. Are they phrased to elicit the same type of problem?
If ≥ 2 criteria are YES → duplicate

**Cost optimization:** Batch ALL new angles from a round together and check them in one coordinator reasoning step, not one step per angle.

### Dedup Logic

```
# Called AFTER collecting all new angles from the round (batch approach)
# Sort batch by (priority DESC, hash DESC) before processing — determinism
all_new_angles.sort(key=lambda a: (-priority_rank(a), -hash(a.question)))

function should_add_to_frontier(new_angle, pre_round_snapshot):
    hash = tier1_hash(new_angle.question)

    if hash in duplication:
        if duplication[hash] >= 2:
            return false  # saturated
        # Tier 2 check: is the second question semantically the same?
        existing = get_angle_by_hash(hash)
        if tier2_semantic_check(new_angle, existing) == SAME:
            # Same angle → second critic gets first's findings for cross-validation
            duplication[hash] += 1
            return true
        else:
            # Hash collision, different angle → explore independently
            return true  # add with new hash slot
    else:
        tier2_result = tier2_semantic_check(new_angle, pre_round_snapshot)
        if tier2_result == DUPLICATE:
            duplication[hash] = 2  # mark saturated immediately
            return false
        else:
            duplication[hash] = 1
            return true
```

**Dedup counter only increments on SUCCESSFUL completion**, not on timeout. Timed-out critics do not consume dedup slots. `spawn_failed` angles also do not consume dedup slots.

### Controlled Duplication (second critique)
When an angle gets its second critique (duplication count → 2):
- Second critic receives first critic's findings as additional context
- Second critic instructed: "The first critic found these issues. Look for what they MISSED. Challenge their assumptions. Are their suggested fixes actually viable?"
- This provides cross-validation of both flaws and fixes

---

## Angle ID Generation
Use incrementing IDs: `angle_001`, `angle_002`, etc.

## Flaw ID Generation
Use incrementing IDs: `flaw_001`, `flaw_002`, etc.

---

## State Updates

### Before spawning each critic (CRITICAL: state written BEFORE Agent tool call)
```json
"angles.{id}.status": "in_progress",
"angles.{id}.spawn_time_iso": "<ISO timestamp>",
"generation": += 1
```

### If Agent tool returns spawn error
```json
"angles.{id}.status": "spawn_failed",
"angles.{id}.spawn_time_iso": null,
"angles.{id}.failure_reason": "<error message>",
"generation": += 1
```
Resume behavior: retry spawn (different from `timed_out` → wait loop).

### After critic completes
```json
"angles.{id}.status": "explored",
"angles.{id}.sub_angles": ["angle_015", "angle_016"],
"angles.{id}.flaws_found": ["flaw_005", "flaw_006"],
"dimensions.{dim}.explored_count": += 1,
"required_categories_covered.{category}": true,
"generation": += 1
```

### After critic times out
```json
"angles.{id}.status": "timed_out"
// NOT re-queued. Dedup counter NOT incremented.
// Logged in coordinator summary as timed out.
```

### After dedup and frontier update
```json
"angles.{new_id}": { ... },
"frontier": [..., "new_id"],
"duplication.{hash}": 1,
"generation": += 1
```

### After flaw validation
```json
"flaws.{id}.status": "disputed",
"flaws.{id}.dispute_rationale": "Contradicts flaw_003 finding — if detection rate is 94%+, this strategy isn't viable"
```

### After redesign phase
```json
"flaws.{id}.status": "fixed",
"flaws.{id}.fix_description": "Redesigned interrogation to use open-ended questions only",
"flaws.{id}.fix_version": "v1-post-round-1",
"component_invariants.{component}": {
  "invariant": "...",
  "constraint_direction": "tightened",
  "tightened_rounds": [1],
  "last_updated_round": 1
},
"accepted_fixes": [{ ... }],
"current_spec_version": "v1-post-round-1",
"current_spec_path": "deep-design-{run_id}/specs/v1-post-round-1.md",
"generation": += 1
```

### After component rename detected (inventory-rebuild time)
```json
// Atomic rename of component_invariants key
"component_invariants.{new_name}": { ...copy of old entry... },
// Delete old key
"component_name_history": [..., {
  "old_name": "severity_classifier",
  "new_name": "classification_agent",
  "migration_round": 4,
  "detection_basis": "semantic_equivalence"
}],
"generation": += 1
```

### After coverage evaluation
```json
"coverage_gaps": ["No critic has examined accessibility for colorblind users"],
"rounds_without_new_dimensions": 0  // or += 1 if no new dims this round
```

---

## State Invariants

After every round, verify:
1. No angle has `status: "in_progress"` — all must be resolved (explored, timed_out, or spawn_failed)
2. `frontier` contains only angle IDs with `status: "frontier"`
3. `duplication` values are all <= 2
4. `dimensions.*.explored_count` matches actual count of explored angles in that dimension
5. All flaws referenced by angles exist in the `flaws` registry
6. State file is valid JSON
7. `current_spec_path` points to an existing file
8. `generation` is strictly monotonically increasing
9. `core_claim_sha256` matches SHA256 of `core_claim` string — if mismatch, log CORE_CLAIM_TAMPERED and halt
10. No `component_invariants` key matches an old name in `component_name_history` — stale keys indicate failed migration

---

## Recovery (session restart)

1. Read state.json
2. Verify `core_claim_sha256` matches SHA256 of `core_claim` — halt if tampered
3. For each angle with `status: "in_progress"`:
   - If critique file exists → mark `explored`, process normally
   - If critique file missing → mark `timed_out` (NOT re-queued, NOT re-tried)
4. For each angle with `status: "spawn_failed"`:
   - Re-add to frontier for retry (spawn_failed = spawn was refused, not attempted)
5. Continue from current frontier
