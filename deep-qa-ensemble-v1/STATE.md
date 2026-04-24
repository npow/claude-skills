# State Management

## State File: `deep-qa-{run_id}/state.json`

```json
{
  "run_id": "20260314-153022",
  "generation": 0,
  "artifact_name": "Name or filename of the artifact being QA'd",
  "artifact_path": "deep-qa-{run_id}/artifact.md",
  "artifact_type": "doc|code|research|skill",
  "dimensions": {
    "dim_name": {
      "description": "What this QA dimension checks",
      "required_category": "completeness|internal_consistency|feasibility|edge_cases|correctness|error_handling|security|testability|accuracy|citation_validity|logical_consistency|coverage_gaps|behavioral_correctness|instruction_conflicts|injection_resistance|cost_runaway_risk|null",
      "angles": ["angle_001", "angle_003"],
      "explored_count": 0,
      "status": "uncovered|partial|covered"
    }
  },
  "required_categories_covered": {
    "completeness": false,
    "internal_consistency": false,
    "feasibility": false,
    "edge_cases": false
  },
  "angles": {
    "angle_001": {
      "question": "Specific QA question",
      "dimension": "dim_name",
      "required_category": "completeness",
      "focus": "specific focus within dimension",
      "parent": null,
      "priority": "critical|high|medium|low",
      "depth": 0,
      "source": "seed|critic",
      "status": "frontier|in_progress|explored|timed_out|saturated|spawn_failed|spawn_exhausted",
      "spawn_time_iso": null,
      "spawn_attempt_count": 0,
      "exhaustion_score": null,
      "critique_file": "deep-qa-{run_id}/critiques/angle_001.md",
      "sub_angles": [],
      "defects_found": [],
      "failure_reason": null
    }
  },
  "defects": {
    "defect_001": {
      "title": "Missing error path for authentication failure",
      "severity": "critical|major|minor",
      "judge_status": "pending|pass_1_completed|pass_1_timed_out|completed|timed_out",
      "judge_batch_id": "batch_1_1",
      "judge_pass_1_verdict": {
        "severity": "critical|major|minor",
        "confidence": "high|medium|low",
        "rationale": "one-line basis for pass-1 blind verdict"
      },
      "judge_pass_2_verdict": {
        "severity": "critical|major|minor",
        "confidence": "high|medium|low",
        "calibration": "confirm|upgrade|downgrade",
        "rationale": "one-line basis for pass-2 informed verdict"
      },
      "dimension": "dim_name",
      "source_angle": "angle_001",
      "round_classified": 1,
      "scenario": "A developer implementing the spec encounters a token expiry — section 4.2 specifies no error response, so they return a generic 500",
      "root_cause": "Auth error path not specified in the token lifecycle section",
      "author_counter_response": "what the artifact author could plausibly say to defend this — from the critic; required for the defect to be falsifiable",
      "status": "open|accepted|disputed|wont_fix",
      "acceptance_rationale": null,
      "dispute_rationale": null,
      "severity_challenge_token": "available|challenged|exhausted"
    }
  },
  "frontier": ["angle_003", "angle_007"],
  "duplication": {
    "hash_abc123": 1
  },
  "coverage_gaps": [],
  "rounds_without_new_dimensions": 0,
  "round": 0,
  "max_rounds": 4,
  "hard_stop": 8,
  "max_agents_per_round": 6,
  "max_depth": 3,
  "background_tasks": {
    "judges": [
      {"batch_id": "batch_1_1", "defect_ids": ["defect_001", "defect_002"], "round": 1, "pass": 1, "status": "running|completed|timed_out", "task_id": "bg_task_id"},
      {"batch_id": "batch_pass2_1", "defect_ids": ["defect_001", "defect_002"], "round": 1, "pass": 2, "status": "running|completed|timed_out", "task_id": "bg_task_id"}
    ],
    "summaries": [
      {"round": 1, "status": "running|completed|timed_out", "task_id": "bg_task_id"}
    ],
    "rationalization_audit": {
      "status": "not_started|running|clean|compromised|compromised_twice|timed_out",
      "attempt_count": 0,
      "task_id": "bg_task_id",
      "verdict_path": "deep-qa-{run_id}/judges/rationalization-audit.md"
    }
  },
  "auto": false,
  "files_examined": ["artifact.md"]
}
```

**Key differences from deep-design state:**
- No `core_claim`, `core_claim_sha256`, `core_claim_calibrated` — QA doesn't draft a spec
- No `component_invariants`, `ordering_graph` — no redesign loop
- No `accepted_fixes` — defects are reported, not fixed
- `flaws` → `defects`; flaw statuses `fixed` and `wont_fix` → only `open`, `accepted`, `disputed`, `wont_fix`
- Adds `artifact_name`, `artifact_path`, `artifact_type`
- Adds `judge_status` and `judge_batch_id` on defects for pipelined severity classification
- Adds `background_tasks` registry for tracking pipelined judge batches and coordinator summaries

---

## Angle ID Generation
Use incrementing IDs: `angle_001`, `angle_002`, etc.

## Defect ID Generation
Use incrementing IDs: `defect_001`, `defect_002`, etc.

---

## Concurrency Control

### Generation Counter (optimistic concurrency)
- Before any write: read current generation from state file
- Increment generation in the write
- After writing, re-read and verify generation is N+1
- If generation is not N+1: a concurrent write occurred → log conflict, retry with fresh read
- This is conflict-detectable, not truly atomic — sufficient for single-coordinator use

### Lock File
- On startup: write `deep-qa-{run_id}.lock` with timestamp
- If lock file from a different run_id exists and is < 15min old:
  "Another deep-qa session appears active. Continue anyway? [y/N]"
- On clean exit: delete lock file

**Do NOT claim atomic writes.** Use the generation counter for conflict detection.

---

## Deduplication Algorithm

### Tier 1 — Structural hash (catches exact/near-exact)

**Clause-based causal-preserving hash** (NOT global word sort):
1. Lowercase
2. Split into clauses at clause boundaries (commas, "and", "because", "causes", "leads to", "results in")
3. For each clause: remove stop words, sort words within the clause
4. Join clause hashes in original clause order
5. Hash the result

**Stop words to remove (within-clause only):** the, a, an, is, are, was, were, of, for, in, on, to, with, by, at, from, do, does, did, what, how, why, where, when, who, which

### Tier 2 — Semantic similarity check (catches synonyms, paraphrases)

Applied after Tier 1 passes:
- Compare new angle against all existing angles in the same dimension
- **Growing threshold:** Round 1 = 0.80, Round 2 = 0.83, Round 3 = 0.85, Round 4+ = 0.88

**For embeddings-unavailable path — structured 3-criterion checklist:**
1. Do the questions examine the same defect pattern or quality concern?
2. Would critiquing one angle produce findings that fully answer the other?
3. Are they phrased to elicit the same type of problem?
If ≥ 2 criteria are YES → duplicate

**Cost optimization:** Batch ALL new angles from a round and check them in one coordinator reasoning step.

### Dedup Logic

```
function should_add_to_frontier(new_angle, pre_round_snapshot):
    # Depth check — enforce max_depth before any other check
    if new_angle.depth > max_depth:
        return false  # silently drop; depth exceeded

    # Depth must be set by the caller before calling this function:
    #   new_angle.depth = parent_angle.depth + 1
    # New angles reported by critics MUST have depth assigned before dedup.

    hash = tier1_hash(new_angle.question)

    if hash in duplication:
        if duplication[hash] >= 2:
            return false  # saturated
        existing = get_angle_by_hash(hash)
        if tier2_semantic_check(new_angle, existing) == SAME:
            duplication[hash] += 1
            # before adding, check frontier cap (see below)
            return frontier_cap_check(new_angle)
        else:
            return frontier_cap_check(new_angle)  # hash collision, different question
    else:
        tier2_result = tier2_semantic_check(new_angle, pre_round_snapshot)
        if tier2_result == DUPLICATE:
            duplication[hash] = 2  # mark saturated immediately
            return false
        else:
            duplication[hash] = 1
            return frontier_cap_check(new_angle)

function frontier_cap_check(new_angle):
    # Use LIVE frontier count (not pre-round snapshot) for cap enforcement
    if len(live_frontier) < 30:
        return true
    # Cap reached — displacement required
    # Find the lowest-priority angle in the live frontier that is NOT:
    #   - The only remaining angle for a required_category
    #   - A depth-0 angle for any dimension with no other depth-0 angles
    evict_candidate = find_lowest_priority_displaceable_angle(live_frontier, new_angle)
    if evict_candidate is None:
        return false  # cannot displace safely; log FRONTIER_FULL_DISPLACEMENT_BLOCKED
    # Only displace if new_angle.priority >= evict_candidate.priority
    if priority_rank(new_angle) >= priority_rank(evict_candidate):
        remove_from_frontier(evict_candidate)
        return true
    else:
        return false  # new angle is lower priority than everything displaceable
```

**Depth assignment rule (REQUIRED before calling should_add_to_frontier):**
When a critic reports new angles, the coordinator MUST assign depth before adding to the frontier:
```
for new_angle in critic_reported_angles:
    new_angle.depth = parent_angle.depth + 1
    # parent_angle is the angle the critic was analyzing
```
Angles without an assigned depth are treated as depth = parent.depth + 1 of the popped angle.

**Tier 2 scope constraint (applies to BOTH embeddings path and checklist path):**
Compare new angle against all existing angles **in the same dimension only** — not across all dimensions. This constraint applies equally to both the embeddings similarity path and the 3-criterion checklist fallback path.

**Dedup counter only increments on SUCCESSFUL completion.** Timed-out and spawn_failed angles do not consume dedup slots.

**Controlled second exploration:**
When an angle gets its second critique (duplication count → 2):
- Second critic receives first critic's findings as additional context
- Second critic instructed: "Focus on what the first QA pass MISSED. Challenge their severity assessments."

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
"angles.{id}.spawn_attempt_count": += 1,
"angles.{id}.failure_reason": "<error message>",
"generation": += 1
```
Resume behavior: retry spawn if `spawn_attempt_count < 3`. After 3 failed attempts: set `status: "spawn_exhausted"` — no further retries, no re-queue. Log in coordinator summary.

### After critic completes
```json
"angles.{id}.status": "explored",
"angles.{id}.sub_angles": ["angle_015"],
"angles.{id}.defects_found": ["defect_003"],
"angles.{id}.exhaustion_score": 3,
"dimensions.{dim}.explored_count": += 1,
"required_categories_covered.{category}": true,
"generation": += 1
```
Note: `required_categories_covered.{category}` is only set to true if the critique file's declared `**QA Dimension:**` header matches the angle's assigned dimension in state.json. Dimension mismatch → do NOT update coverage; flag in coordinator summary.

### After critic times out
```json
"angles.{id}.status": "timed_out",
"generation": += 1
// NOT re-queued. Dedup counter NOT incremented.
// Logged in coordinator summary as timed out.
```

### After critic creates defect (before judge runs)
```json
"defects.{id}.severity": "critical|major|minor",  // critic-proposed (preliminary)
"defects.{id}.judge_status": "pending",
"defects.{id}.judge_batch_id": "batch_{round}_{batch_num}",
"defects.{id}.status": "open",
"generation": += 1
```

### After spawning background judge batch
```json
"background_tasks.judges[].batch_id": "batch_{round}_{batch_num}",
"background_tasks.judges[].defect_ids": ["defect_001", "defect_002"],
"background_tasks.judges[].round": {round},
"background_tasks.judges[].status": "running",
"background_tasks.judges[].task_id": "{background_task_id}",
"generation": += 1
```

### After spawning background coordinator summary
```json
"background_tasks.summaries[].round": {round},
"background_tasks.summaries[].status": "running",
"background_tasks.summaries[].task_id": "{background_task_id}",
"generation": += 1
```

### After pass-1 blind severity judge batch completes (Phase 5.5.a)
For each defect in the batch:
```json
"defects.{id}.judge_pass_1_verdict": {
  "severity": "critical|major|minor",   // pass-1 BLIND judgment (no critic severity visible)
  "confidence": "high|medium|low",
  "rationale": "..."
},
"defects.{id}.judge_status": "pass_1_completed",
"background_tasks.judges[batch_idx].status": "completed",
"generation": += 1
// NOTE: defects.{id}.severity is NOT yet overwritten — pass-2 is authoritative.
```

### After pass-2 informed severity judge batch completes (Phase 5.5.b)
For each defect in the batch:
```json
"defects.{id}.judge_pass_2_verdict": {
  "severity": "critical|major|minor",        // pass-2 INFORMED judgment
  "confidence": "high|medium|low",
  "calibration": "confirm|upgrade|downgrade", // did pass-2 agree with pass-1 or change it?
  "rationale": "..."
},
"defects.{id}.severity": "critical|major|minor",  // authoritative; set from pass_2_verdict.severity
"defects.{id}.judge_status": "completed",
"background_tasks.judges[batch_idx].status": "completed",
"generation": += 1
```

**Authoritative-severity invariant:** after Phase 5.5.b drain, for every defect where `judge_status == "completed"`, `defects.{id}.severity` MUST equal `defects.{id}.judge_pass_2_verdict.severity`. Pass-1 verdict is kept only as a calibration record; it is never the authoritative value.

### After rationalization audit completes (Phase 5.6)
```json
"background_tasks.rationalization_audit.status": "clean|compromised|compromised_twice|timed_out",
"background_tasks.rationalization_audit.attempt_count": += 1,
"generation": += 1
```
Termination impact: `compromised_twice` or `timed_out` triggers the `"Audit compromised — report re-assembled from verdicts only"` label.

### After defect validation (dispute)
```json
"defects.{id}.status": "disputed",
"defects.{id}.dispute_rationale": "<which validation check failed and why>",
"generation": += 1
```

### After coverage evaluation
```json
"coverage_gaps": ["No angle has examined the token refresh error path"],
"rounds_without_new_dimensions": 0,  // or += 1 if no new dims this round
"generation": += 1
```

---

## State Invariants

After every round, verify:
1. No angle has `status: "in_progress"` — all must be resolved (explored, timed_out, spawn_failed, or spawn_exhausted)
2. `frontier` contains only angle IDs with `status: "frontier"`
3. `duplication` values are all ≤ 2
4. `len(frontier) <= 30`
5. `dimensions.*.explored_count` matches actual count of explored angles in that dimension
6. All defects referenced by angles exist in the `defects` registry
7. State file is valid JSON
8. `generation` is strictly monotonically increasing
9. `hard_stop` value in state.json equals the value set at initialization — never changed
10. All `critique_file` paths across angles are unique (no two angles share a path)
11. All new defects this round have `judge_status: "pending"` and a valid `judge_batch_id`
12. All background judge batches from this round are registered in `background_tasks.judges` with `status: "running"`

After Phase 5.5 drain (additional invariants):
13. No defect has `judge_status: "pending"` or `"pass_1_completed"` — all must be `completed` (both passes done) or `timed_out` (one or both passes timed out)
14. All entries in `background_tasks.judges` have `status: "completed"` or `status: "timed_out"`
15. All entries in `background_tasks.summaries` have `status: "completed"` or `status: "timed_out"`
16. For every defect with `judge_status: "completed"`: `defects.{id}.severity == defects.{id}.judge_pass_2_verdict.severity` (authoritative-severity invariant)

After Phase 5.6 rationalization audit (additional invariants):
17. `background_tasks.rationalization_audit.status` is one of: `clean`, `compromised_twice`, `timed_out` (terminal states — never `running` or `not_started` once Phase 5.6 completes)
18. If `status == "compromised_twice"`: coordinator terminates with label `"Audit compromised — report re-assembled from verdicts only"` — no further Phase 6 coordinator synthesis; report is written directly from judge verdicts

---

## Recovery (session restart)

1. Read state.json
2. For each angle with `status: "in_progress"`:
   - If critique file exists → mark `explored`, process normally
   - If critique file missing → mark `timed_out` (NOT re-queued, NOT re-tried)
3. For each angle with `status: "spawn_failed"`:
   - Re-add to frontier for retry (spawn was refused, not attempted)
4. Continue from current frontier
