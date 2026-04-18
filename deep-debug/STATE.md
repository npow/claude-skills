# State Management

## State File: `deep-debug-{run_id}/state.json`

```json
{
  "run_id": "20260418-095600",
  "generation": 0,
  "symptom": "One-paragraph symptom statement (exact error, where it surfaces, when it started)",
  "symptom_sha256": "hex digest of the symptom string — anti-tampering only",
  "reproduction": {
    "status": "confirmed|intermittent|unreproducible",
    "steps": "deep-debug-{run_id}/reproduction.md",
    "command": "exact command to trigger (if any)",
    "rate": "every time | 1 in N | last observed at <timestamp>"
  },
  "dimensions": {
    "code-path": {
      "description": "Logic error at or upstream of the symptom site",
      "required_category": "correctness",
      "angles": ["angle_001", "angle_004"],
      "explored_count": 0,
      "status": "uncovered|partial|covered"
    },
    "data-flow":           {"required_category": "correctness",  "angles": [], "explored_count": 0, "status": "uncovered"},
    "recent-changes":      {"required_category": "correctness",  "angles": [], "explored_count": 0, "status": "uncovered"},
    "environment":         {"required_category": "environment",  "angles": [], "explored_count": 0, "status": "uncovered"},
    "framework-contract":  {"required_category": "correctness",  "angles": [], "explored_count": 0, "status": "uncovered"},
    "concurrency-timing":  {"required_category": "concurrency",  "angles": [], "explored_count": 0, "status": "uncovered"},
    "measurement-artifact":{"required_category": "correctness",  "angles": [], "explored_count": 0, "status": "uncovered"},
    "architectural-coupling":{"required_category": "architecture","angles": [], "explored_count": 0, "status": "uncovered"}
  },
  "required_categories_covered": {
    "correctness":   false,
    "environment":   false,
    "concurrency":   false,
    "architecture":  false
  },
  "angles": {
    "angle_001": {
      "question": "Concrete hypothesis-scoping question",
      "dimension": "code-path",
      "required_category": "correctness",
      "parent": null,
      "priority": "critical|high|medium|low",
      "depth": 0,
      "source": "coordinator_initial|critic_suggested|outside_frame|premortem",
      "discovery_round": 0,
      "rationale": "one-line reason this angle was selected",
      "status": "frontier|in_progress|explored|timed_out|saturated|spawn_failed|spawn_exhausted",
      "spawn_time_iso": null,
      "spawn_attempt_count": 0,
      "hypothesis_file": "deep-debug-{run_id}/hypotheses/angle_001.md",
      "hypotheses_found": ["hyp_001"],
      "exhaustion_score": null,
      "failure_reason": null
    }
  },
  "hypotheses": {
    "hyp_001": {
      "lane": "angle_001",
      "dimension": "code-path",
      "title": "Short title (≤10 words)",
      "mechanism": "Causal chain: X happens because Y, which leads to Z",
      "predictions": ["Observable 1 if true", "Observable 2 if true"],
      "evidence_for": [{"tier": 2, "source": "file.py:42", "note": "..."}],
      "evidence_against": [{"tier": 3, "source": "log line", "note": "..."}],
      "evidence_tier_max": 2,
      "critical_unknown": "The one fact that would collapse remaining uncertainty",
      "discriminating_probe": "Proposed probe to distinguish this from the next-best alternative",
      "critic_confidence": "high|medium|low",
      "judge_status": "pending|completed|timed_out|disputed",
      "judge_verdict_pass1": null,
      "judge_verdict_pass2": null,
      "judge_plausibility": "leading|plausible|disputed|rejected|deferred",
      "cycle_introduced": 1,
      "status": "active|rejected_by_judge|falsified_by_probe|promoted_to_fix|graveyard",
      "rejection_reason": null,
      "falsification_note": null,
      "challenge_token": "available|challenged|exhausted"
    }
  },
  "probes": [
    {
      "probe_id": "probe_001",
      "cycle": 1,
      "question": "What the probe is testing",
      "distinguishes": ["hyp_001", "hyp_002"],
      "expected_per_hypothesis": {
        "hyp_001": "result A if this is the cause",
        "hyp_002": "result B if this is the cause"
      },
      "execution_method": "run test X | query DB Y | add instrumentation Z",
      "executed_at_iso": null,
      "actual_result": null,
      "winner": null,
      "falsified": [],
      "status": "pending|running|completed|inconclusive"
    }
  ],
  "fix_attempts": [
    {
      "attempt_id": "fix_001",
      "cycle": 1,
      "hypothesis_id": "hyp_001",
      "failing_test_written": true,
      "failing_test_path": "tests/test_parse_header.py::test_short_body",
      "change_summary": "One-sentence summary of the single change",
      "change_diff_path": "deep-debug-{run_id}/fixes/fix_001.diff",
      "verification": {
        "failing_test_now_passes": null,
        "full_suite_clean": null,
        "regressions": []
      },
      "outcome": "verified|failed|partial|reverted",
      "outcome_note": null
    }
  ],
  "cycles": [
    {
      "cycle_id": 1,
      "started_at_iso": "...",
      "hypotheses_generated": ["hyp_001", "hyp_002"],
      "hypotheses_accepted_by_judge": ["hyp_001"],
      "probes_run": ["probe_001"],
      "fix_attempted": "fix_001",
      "outcome": "fix_verified|fix_failed|judge_rejected_all|hypothesis_space_saturated",
      "ended_at_iso": null
    }
  ],
  "frontier": ["angle_003"],
  "duplication": {
    "hash_abc123": 1
  },
  "coverage_gaps": [],
  "cycle": 0,
  "max_cycles": 3,
  "hard_stop": 6,
  "max_agents_per_round": 6,
  "max_depth": 2,
  "max_probes_per_cycle": 3,
  "probe_count_this_cycle": 0,
  "fix_attempt_count": 0,
  "rounds_without_new_dimensions": 0,
  "background_tasks": {
    "judges": [
      {"batch_id": "batch_1_1", "hypothesis_ids": ["hyp_001"], "cycle": 1, "status": "running|completed|timed_out", "task_id": "bg_task_id"}
    ],
    "evidence_gatherers": [
      {"probe_id": "probe_001", "cycle": 1, "status": "running|completed|timed_out", "task_id": "bg_task_id"}
    ],
    "summaries": [
      {"cycle": 1, "status": "running|completed|timed_out", "task_id": "bg_task_id"}
    ]
  },
  "invocation": "interactive|auto|hard_mode",
  "budget_spent_usd_estimate": 0.0,
  "budget_cap_usd": 25.0,
  "termination_label": null,
  "termination_reason": null,
  "escalation_triggered": false
}
```

**Key differences from deep-qa state:**
- Adds `symptom`, `symptom_sha256`, `reproduction` (no artifact — the buggy code is the artifact, but it's volatile, not a fixed doc)
- Adds `hypotheses` registry (similar role to deep-qa `defects`, but hypotheses have `evidence_for` / `evidence_against` / `critical_unknown` / `discriminating_probe`)
- Adds `probes` registry (unique to deep-debug — uncertainty-collapsing experiments)
- Adds `fix_attempts` registry with verification contract
- Adds `cycles` (one per fix attempt + the hypotheses/probes leading up to it)
- Adds `escalation_triggered` (Phase 7 gate)
- No severity axis — replaced by `judge_plausibility` (`leading|plausible|disputed|rejected|deferred`)

---

## ID Generation

- Angles: `angle_001`, `angle_002`, ...
- Hypotheses: `hyp_001`, `hyp_002`, ...
- Probes: `probe_001`, `probe_002`, ...
- Fix attempts: `fix_001`, `fix_002`, `fix_003` (hard-stops at `fix_003` — no `fix_004`)
- Cycles: integer, starts at 1

---

## Concurrency Control

### Generation Counter (optimistic concurrency)
- Before any write: read current generation from state file
- Increment generation in the write
- After writing, re-read and verify generation is N+1
- If generation is not N+1: a concurrent write occurred → log conflict, retry with fresh read
- Sufficient for single-coordinator use; do not claim atomic writes

### Lock File
- On startup: write `deep-debug-{run_id}.lock` with timestamp
- If lock file from a different run_id exists and is < 15 min old:
  `"Another deep-debug session appears active. Continue anyway? [y/N]"`
- On clean exit: delete lock file
- On hard stop (Phase 7 escalation, budget cap, user stop): lock file is retained so re-entry preserves context

### symptom_sha256 — anti-tampering
- Computed at Phase 0 from the locked symptom string
- Verified before each judge round and before every concept-drift check
- Mismatch → `SYMPTOM_TAMPERED` → halt run; never silently rewrite the symptom to fit an emerging hypothesis

---

## Deduplication Algorithm

### Tier 1 — Structural hash (catches exact/near-exact hypothesis dupes)

**Clause-based causal-preserving hash:**
1. Lowercase
2. Split into clauses at clause boundaries (commas, "and", "because", "causes", "leads to", "results in", "such that")
3. For each clause: remove stop words, sort words within the clause
4. Join clause hashes in original clause order
5. Hash the result

**Stop words removed (within-clause only):** the, a, an, is, are, was, were, of, for, in, on, to, with, by, at, from, do, does, did, what, how, why, where, when, who, which

### Tier 2 — Semantic similarity check

Applied after Tier 1 passes. Compare new hypothesis against existing hypotheses **in the same dimension only** — not cross-dimension (two hypotheses in different dimensions can share mechanism and still be separate investigation targets).

**Growing threshold:** Cycle 1 = 0.80, Cycle 2 = 0.83, Cycle 3 = 0.88.

**For embeddings-unavailable path — structured 3-criterion checklist:**
1. Do the hypotheses make the SAME causal claim (mechanism X causes symptom Y)?
2. Would falsifying one automatically falsify the other?
3. Is the same discriminating probe the best experiment for both?
If ≥ 2 criteria YES → duplicate.

**Cost optimization:** Batch ALL new hypotheses from a cycle and check them in one coordinator reasoning step.

**Controlled second exploration:**
If an angle is explored a second time (e.g. after a failed fix brought new evidence), the second hypothesis agent receives the first agent's hypothesis as additional context and is instructed: "The previous hypothesis in this lane failed verification. New evidence: {list}. Propose a DIFFERENT hypothesis or refine with specific diff from the previous one. Do NOT re-propose the rejected hypothesis."

---

## State Updates

### Before spawning each hypothesis agent (CRITICAL: state written BEFORE Agent tool call)
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
Resume: retry spawn if `spawn_attempt_count < 3`. After 3 failures: `"spawn_exhausted"` — no further retries, no re-queue. Log in cycle summary.

### After hypothesis agent completes
```json
"angles.{id}.status": "explored",
"angles.{id}.hypotheses_found": ["hyp_003", "hyp_004"],
"angles.{id}.exhaustion_score": 3,
"dimensions.{dim}.explored_count": += 1,
"required_categories_covered.{category}": true,
"hypotheses.{hyp_id}": { ... },
"generation": += 1
```
Note: `required_categories_covered.{category}` is only set to true if the hypothesis file's declared `**Dimension:**` header matches the angle's assigned dimension. Dimension mismatch → do NOT update coverage; flag in coordinator summary as potential injection attempt.

### After hypothesis agent times out
```json
"angles.{id}.status": "timed_out",
"generation": += 1
// NOT re-queued. Dedup counter NOT incremented.
// Logged in cycle summary as timed out.
```

### After hypothesis is created (before judge runs)
```json
"hypotheses.{id}.critic_confidence": "high|medium|low",   // critic's own claim
"hypotheses.{id}.judge_status": "pending",
"hypotheses.{id}.status": "active",
"hypotheses.{id}.cycle_introduced": {cycle},
"generation": += 1
```

### After spawning background judge batch
```json
"background_tasks.judges[]": {
  "batch_id": "batch_{cycle}_{batch_num}",
  "hypothesis_ids": ["hyp_003", "hyp_004"],
  "cycle": {cycle},
  "status": "running",
  "task_id": "{background_task_id}"
},
"generation": += 1
```

### After judge batch completes (pass 1 + pass 2)
For each hypothesis in the batch:
```json
"hypotheses.{id}.judge_verdict_pass1": "accepted|disputed|rejected",
"hypotheses.{id}.judge_verdict_pass2": "accepted|disputed|rejected|upgraded|downgraded",
"hypotheses.{id}.judge_plausibility": "leading|plausible|disputed|rejected|deferred",
"hypotheses.{id}.judge_status": "completed",
"hypotheses.{id}.status": "active" | "rejected_by_judge",
"background_tasks.judges[batch_idx].status": "completed",
"generation": += 1
```

Never coordinator-classify. Unparseable judge output → fail-safe: `judge_plausibility: "disputed"`, status stays `active`, flag in cycle summary.

### After rebuttal round
```json
"hypotheses.{leader_id}.rebuttal_survived": true|false,
"hypotheses.{leader_id}.judge_plausibility": "{possibly downgraded}",
"hypotheses.{challenger_id}.judge_plausibility": "{possibly upgraded}",
"generation": += 1
```

### Before running a discriminating probe
```json
"probes[]": {
  "probe_id": "probe_{cycle}_{N}",
  "cycle": {cycle},
  "distinguishes": ["hyp_{leader}", "hyp_{challenger}"],
  "expected_per_hypothesis": {...},
  "status": "pending"
},
"probe_count_this_cycle": += 1,
"generation": += 1
```

If `probe_count_this_cycle > max_probes_per_cycle`: reject probe, halt cycle, force progression (either promote leader to Phase 5 if judge-accepted, or end cycle as "hypothesis_space_saturated").

### After probe completes
```json
"probes.{id}.actual_result": "...",
"probes.{id}.winner": "hyp_{id}" | null,
"probes.{id}.falsified": ["hyp_{id}", ...],
"probes.{id}.status": "completed" | "inconclusive",
"hypotheses.{falsified_id}.status": "falsified_by_probe",
"hypotheses.{falsified_id}.falsification_note": "probe {id} produced <result>, which contradicts prediction <pred>",
"generation": += 1
```

### Before Phase 5 fix attempt
```json
"fix_attempt_count": += 1,
"hypotheses.{leader_id}.status": "promoted_to_fix",
"fix_attempts[]": {
  "attempt_id": "fix_{N}",
  "cycle": {cycle},
  "hypothesis_id": "hyp_{leader}",
  "failing_test_written": false,
  "verification": {"failing_test_now_passes": null, "full_suite_clean": null, "regressions": []},
  "outcome": null
},
"generation": += 1
```

### After fix verification
```json
"fix_attempts.{N}.verification.failing_test_now_passes": true|false,
"fix_attempts.{N}.verification.full_suite_clean": true|false,
"fix_attempts.{N}.verification.regressions": [...],
"fix_attempts.{N}.outcome": "verified|failed|partial|reverted",
"generation": += 1
```

### After cycle ends
```json
"cycles.{N}.hypotheses_generated": [...],
"cycles.{N}.hypotheses_accepted_by_judge": [...],
"cycles.{N}.probes_run": [...],
"cycles.{N}.fix_attempted": "fix_{N}",
"cycles.{N}.outcome": "fix_verified|fix_failed|judge_rejected_all|hypothesis_space_saturated",
"cycles.{N}.ended_at_iso": "...",
"cycle": += 1,
"probe_count_this_cycle": 0,
"generation": += 1
```

### On Phase 7 architectural escalation
```json
"escalation_triggered": true,
"termination_label": "Architectural escalation required — 3 fix attempts failed across distinct hypotheses",
"generation": += 1
```
Spawn architect agent in Phase 7; result written to `deep-debug-{run_id}/architectural-question.md`.

---

## State Invariants

Verify after every cycle:

1. No angle has `status: "in_progress"` — all must be `explored`, `timed_out`, `spawn_failed`, or `spawn_exhausted`
2. `frontier` contains only angle IDs with `status: "frontier"`
3. `duplication` values are all ≤ 2
4. `dimensions.*.explored_count` matches actual count of explored angles in that dimension
5. Every hypothesis referenced by `angles[*].hypotheses_found` exists in the `hypotheses` registry
6. State file is valid JSON
7. `generation` is strictly monotonically increasing
8. `hard_stop` value equals initialization value — never changed
9. `fix_attempt_count <= 3` at all times (hard ceiling); increment-past-3 is forbidden
10. `probe_count_this_cycle <= max_probes_per_cycle` at all times
11. Every hypothesis with `judge_status: "completed"` has both `judge_verdict_pass1` and `judge_verdict_pass2` populated
12. Every hypothesis with `status: "promoted_to_fix"` has an entry in `fix_attempts`
13. Every `probe` with `status: "completed"` has `winner` OR `falsified` populated (or `status: "inconclusive"`)
14. `escalation_triggered == true` ⇒ `termination_label` is set to the architectural-escalation label
15. No hypothesis is `promoted_to_fix` while another hypothesis is `promoted_to_fix` in the same cycle (one fix at a time rule)
16. `symptom_sha256` matches `sha256(symptom)` — never mutated
17. Every `fix_attempts[]` entry has `failing_test_written: true` before `outcome` is populated (Golden Rule 6)
18. `termination_label` is non-null iff the run has reached Phase 8 (final report)

---

## Recovery (session restart)

1. Read `state.json`
2. Verify `symptom_sha256 == sha256(symptom)` — mismatch → halt, do not resume
3. For each angle with `status: "in_progress"`:
   - If hypothesis file exists and is non-empty → mark `explored`, process normally
   - If hypothesis file missing or empty → mark `timed_out` (NOT re-queued)
4. For each angle with `status: "spawn_failed"`:
   - If `spawn_attempt_count < 3` → re-add to frontier for retry
   - Else → mark `spawn_exhausted`, log in cycle summary
5. For each hypothesis with `judge_status: "pending"` → re-spawn judge on next round start
6. For each probe with `status: "pending"` or `"running"` where `executed_at_iso` was ≥ 5 min ago → re-execute the probe (probes are idempotent reads of world state)
7. For each fix_attempt with `outcome == null` where the change_diff was committed → run verification; else treat as a failed attempt and do not double-count
8. Continue from current frontier
