# State Management

## State File: `deep-research-state.json`

```json
{
  "seed": "The original research question",
  "run_id": "20260314-153022",
  "generation": 0,
  "round": 0,
  "max_rounds": 5,
  "max_agents_per_round": 6,
  "max_depth": 3,
  "topic_velocity": "fast_moving",
  "recency_threshold_months": 12,
  "dimensions": {
    "dim_name": {
      "description": "What this dimension covers",
      "directions": ["dir_001", "dir_003"],
      "explored_count": 0,
      "status": "uncovered|partial|covered"
    }
  },
  "directions": {
    "dir_001": {
      "question": "Specific research question",
      "dimension": "dim_name",
      "angle": "specific angle within dimension",
      "parent": null,
      "priority": "critical|high|medium|low",
      "depth": 0,
      "source": "seed|agent|reexpansion",
      "status": "frontier|in_progress|explored|timed_out|saturated",
      "findings_file": "deep-research-findings/dir_001.md",
      "sub_directions": ["dir_005", "dir_008"],
      "exhaustion_score": null
    }
  },
  "frontier": ["dir_003", "dir_007", "dir_012"],
  "duplication": {
    "hash_abc123": 1,
    "hash_def456": 2
  },
  "coverage_gaps": [],
  "rounds_without_new_dimensions": 0,
  "coordinator_summary_path": "deep-research-coordinator-summary.md"
}
```

---

## Run-Init Config Fields

- `topic_velocity` — one of `fast_moving` (e.g. LLM research, current events, emerging tech) or `stable` (e.g. historical analysis, mathematical foundations, established science). Set at run init; immutable after. Drives the freshness threshold used to compute `recency_class` on each source.
- `recency_threshold_months` — derived from `topic_velocity`: 12 for `fast_moving`, 36 for `stable`. Stored for clarity so agents don't recompute the mapping inconsistently.

These fields are inherited by every research agent in the run via the agent prompt (`Topic velocity: {topic_velocity}`) and are echoed in each findings file header.

---

## Concurrency Control

### Generation Counter (optimistic concurrency)
- Before any write: read current generation from state file
- Increment generation in the write
- After writing, re-read and verify generation is N+1
- If generation is not N+1: a concurrent write occurred → log conflict, retry with fresh read
- This is conflict-detectable, not truly atomic — but sufficient for single-coordinator use

### Lock File
- On startup: write `deep-research-{run_id}.lock` with timestamp
- If lock file from a different run_id exists and is < 15min old:
  "Another deep-research session appears active. Continue anyway? [y/N]"
- On clean exit: delete lock file

**Do NOT claim atomic writes.** The Write tool has no rename primitive. Use the generation counter for conflict detection instead.

---

## Deduplication Algorithm

### Tier 1 — Structural hash (fast, catches exact/near-exact)

**Clause-based causal-preserving hash** (NOT global word sort):
1. Lowercase
2. Split into clauses at clause boundaries (commas, "and", "because", "causes", "leads to", "results in")
3. For each clause: remove stop words, sort words within the clause
4. Join clause hashes in original clause order
5. Hash the result

This preserves "A causes B" vs "B causes A" as different hashes, while still catching "What causes A due to B?" = "What leads to A because of B?"

**Stop words to remove (within-clause only):** the, a, an, is, are, was, were, of, for, in, on, to, with, by, at, from, do, does, did, what, how, why, where, when, who, which

### Tier 2 — Semantic similarity check (catches synonyms, paraphrases)

Applied after Tier 1 passes:
- Compare new direction against all existing directions in the same dimension
- **Growing threshold:** Round 1 = 0.80, Round 2 = 0.83, Round 3 = 0.85, Round 4+ = 0.88
- Higher threshold in later rounds = stricter dedup (prevents late-round starvation as frontier shrinks)

**For embeddings-unavailable path — structured 3-criterion checklist:**
1. Do the questions ask about the same entity/phenomenon?
2. Would researching one question produce findings that fully answer the other?
3. Are they phrased to elicit the same type of information?
If ≥ 2 criteria are YES → duplicate

**Cost optimization:** Batch ALL new directions from a round together and check them in one coordinator reasoning step, not one step per direction.

### Dedup Logic

```
# Called AFTER collecting all new directions from the round (batch approach)
# Sort batch by (priority DESC, hash DESC) before processing — determinism
all_new_directions.sort(key=lambda d: (-priority_rank(d), -hash(d.question)))

function should_add_to_frontier(new_direction, pre_round_snapshot):
    hash = tier1_hash(new_direction.question)

    if hash in duplication:
        if duplication[hash] >= 2:
            return false  # saturated
        # Tier 2 check: is the second question semantically the same?
        existing = get_direction_by_hash(hash)
        if tier2_semantic_check(new_direction, existing) == SAME:
            # Same question → cross-validation mode (second agent gets first's findings)
            duplication[hash] += 1
            return true
        else:
            # Hash collision, different question → explore independently
            return true  # add with new hash slot
    else:
        tier2_result = tier2_semantic_check(new_direction, pre_round_snapshot)
        if tier2_result == DUPLICATE:
            duplication[hash] = 2  # mark saturated immediately
            return false
        else:
            duplication[hash] = 1
            return true
```

**Dedup counter only increments on SUCCESSFUL completion**, not on timeout. Timed-out agents do not consume dedup slots.

### Controlled Duplication (second exploration)
When a direction gets its second exploration (duplication count → 2):
- Second agent receives first agent's findings as additional context
- Second agent instructed: "Focus on what the first exploration MISSED. Look for contradictions, alternative perspectives, and gaps."

---

## Direction ID Validation

After each round, before updating state:
1. Read each completed findings file
2. Check that the header direction ID (`dir_XXX`) matches the path-based ID
3. If mismatch: log "Direction ID header mismatch in {file}: expected {expected}, found {actual}. Using path-based ID as canonical."
4. All cross-references and coordinator summary use path-based ID — the header ID is informational only

---

## State Updates

### After spawning agents
```json
"directions.{id}.status": "in_progress"
```

### After agent completes
```json
"directions.{id}.status": "explored",
"directions.{id}.exhaustion_score": 4,
"directions.{id}.sub_directions": ["dir_015", "dir_016"],
"dimensions.{dim}.explored_count": += 1,
"generation": += 1
```

### After agent times out
```json
"directions.{id}.status": "timed_out"
// NOT re-queued. Dedup counter NOT incremented.
// Logged in coordinator summary as timed out.
```

### After dedup and frontier update
```json
"directions.{new_id}": { ... },
"frontier": [..., "new_id"],
"duplication.{hash}": 1,
"generation": += 1
```

### After coverage evaluation
```json
"coverage_gaps": ["No direction covers multi-agent debate approaches"],
"rounds_without_new_dimensions": 0  // or += 1 if no new dims this round
```

---

## State Invariants

After every round, verify:
1. No direction has `status: "in_progress"` — all must be resolved
2. `frontier` contains only direction IDs that exist in `directions` with `status: "frontier"`
3. `duplication` values are all ≤ 2
4. `dimensions.*.explored_count` matches actual count of explored directions in that dimension
5. State file is valid JSON
6. `generation` is strictly monotonically increasing

---

## Recovery (session restart)

1. Read state.json
2. For each direction with `status: "in_progress"`:
   - If findings file exists → mark `explored`, process normally
   - If findings file missing → mark `timed_out` (NOT re-queued, NOT re-tried)
3. Continue from current frontier
