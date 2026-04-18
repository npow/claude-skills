# Parallel Critic Quorum

Shared pattern for skills that fire N critics concurrently on orthogonal dimensions and need a deterministic way to (a) decide when the round succeeded, (b) deduplicate findings before synthesis, and (c) fail loudly when too many critics silently break.

**Used by:** deep-design (parallel-critic round), deep-qa (Phase 3 per-round critics), deep-research (per-round research directions), proposal-reviewer (4-dimension critic round).

**Not used by:** team (pipeline), autopilot (pipeline), loop-until-done (sequential stories).

---

## Why this pattern exists

Parallel critics are fast and diverse, but they introduce three failure modes the single-critic version doesn't have:

1. **Silent breakage:** one of N critics returns unparseable output; synthesis from the other N-1 looks fine; the missing dimension is undetected.
2. **Over-eager duplication:** two critics on adjacent dimensions report "the same" defect with slightly different wording; synthesis lists both as independent findings.
3. **Coverage theatre:** coordinator counts N successful critics as "full coverage" without checking that the required dimensions were all represented.

The quorum pattern fixes all three with structural rules:
- **Quorum** → at least M of N critics return parseable output, or the round fails
- **Dedup against a stable pre-round snapshot** → never dedup against a moving target
- **Coverage check against required categories** → parseable output ≠ dimension covered

---

## The pattern

### 1. Spawn phase

Coordinator spawns N critics concurrently:
- Each critic receives a specific dimension (or angle within a dimension) via its input file
- Each critic's output path is known in advance and written to state BEFORE the Agent call
- Coordinator does NOT wait for spawn ordering — all N go out in one Agent-tool batch
- Timeout: typically 120s-180s per critic

### 2. Collect phase

Coordinator waits for all N or until a global deadline. For each critic:

| Outcome | Action |
|---|---|
| Returned, parseable output | Accept → feed into dedup |
| Returned, unparseable output | Reject → count as failed critic |
| Timed out | Reject → count as timed-out critic |
| Spawn failed | Reject → count as spawn_failed critic |

### 3. Quorum check

Compute `parseable_count = N - (unparseable + timed_out + spawn_failed)`.

**Quorum rule:** `parseable_count >= M` where M is skill-specific:
- Typical: `M = ceil(N * 0.75)` for 4+ critic pools (3 of 4, 5 of 6, etc.)
- Strict: `M = N - 1` for small pools where each dimension is load-bearing (deep-design's 4-critic round)
- Lenient: `M = ceil(N / 2)` for exploratory rounds where partial signal is useful

**If quorum fails:** the round did NOT produce actionable output. Do NOT synthesize from the M-1 critics that succeeded — their selection is biased by which critics happened to work. Instead:
- Log `QUORUM_FAILED: {parseable_count}/{N}, required {M}`
- For exploration skills (deep-research): mark the round as incomplete, allow re-spawn with increased timeout
- For adversarial skills (deep-design, deep-qa, proposal-reviewer): terminate with `insufficient_evidence` label; do not issue a final report based on partial output

### 4. Dedup phase

Dedup operates on the **stable pre-round snapshot** — the set of findings that existed BEFORE this round started. Not the live frontier.

**Why pre-round snapshot and not live:** if critic A's output is processed before critic B's, dedup would compare B against (pre-round + A). That creates order-dependent behavior — run the same critics in a different processing order and you get a different deduped set. Freezing the snapshot makes dedup order-independent.

**Algorithm:**
```
snapshot = known_findings_at_round_start  # frozen before any critic output is touched
new_findings = []
for critic_output in parseable_outputs:
    for finding in critic_output.findings:
        if not is_duplicate(finding, snapshot) and not is_duplicate(finding, new_findings):
            new_findings.append(finding)
        else:
            log_duplicate(finding, reason)
return new_findings
```

`is_duplicate` can be a text-similarity check, a structured-field match, or a named-entity overlap check — skill-specific. The contract is that the comparison target is stable.

### 5. Coverage check

Parseable output ≠ required dimension covered. After dedup:
- For each `required_category` in the skill's dimension taxonomy, verify that at least one finding OR one explored angle has `dimension = {category}` in state.json
- If a required category has zero parseable exploration: the coverage is incomplete even though the quorum succeeded
- Generate a CRITICAL-priority direction for each uncovered required category in the next round

Coverage is read from `state.json` — not from coordinator memory. If critics reported findings for a dimension but the state update failed silently, the coverage check catches it.

---

## Integration checklist

Each skill importing this pattern must:

- [ ] Define N (critics per round) and M (quorum threshold) in its SKILL.md
- [ ] Define the dimension taxonomy and which dimensions are `required_category`
- [ ] Define `is_duplicate` — the similarity function used in dedup (can be text-similarity, structured-field match, named-entity match)
- [ ] State whether quorum failure is fatal (adversarial skills) or re-tryable (exploration skills)
- [ ] Ensure `state.json` tracks `required_categories_covered` with entries set to `true` only after coverage verification, not after parseable output
- [ ] Pre-round snapshot is captured and frozen before ANY critic output is read — no race conditions with live frontier mutation

---

## Common failure modes

**Dedup against live frontier.** Different processing orders produce different deduped sets. Use a pre-round snapshot.

**Quorum met but required dimension uncovered.** Parseable ≠ covered. Run the coverage check as a separate step after quorum.

**Silent unparseable treated as success.** A critic that returned no parseable output is a failure, not a "nothing to report" success. Count it against quorum.

**Synthesis from M-1 critics when quorum fails.** Tempting, because there's output on disk. But the selection is biased by which critics happened to work — synthesis produces confident-looking output that hides the gap. Terminate with `insufficient_evidence` instead.

**N set too low.** 2 critics don't give orthogonal coverage; 3 is the minimum for the pattern to mean anything. If a skill only needs 2 critics, it's really a 2-judge pattern, not a parallel-critic quorum.

---

## Divergence allowed

Each skill sets its own N, M, dimension taxonomy, and `is_duplicate` implementation. The shared pattern is the contract: parallel spawn + quorum + dedup-against-snapshot + coverage check. The specific numbers and similarity functions are domain-specific.
