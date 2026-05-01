# Cross-Run Evidence Aggregation

Shared pattern for distilling signals across multiple skill runs into actionable harness evolution proposals. Based on AHE (Agentic Harness Engineering) "Agent Debugger" concept — but built from structured telemetry already emitted by autopilot, deep-qa, and deep-research, not raw trajectories.

## When to use

Any skill that produces structured telemetry (termination labels, routing decisions, phase verdicts, defect registries) should feed into cross-run evidence when invoked by an evolution-oriented workflow.

## Evidence sources

| Skill | Signal | Location |
|---|---|---|
| autopilot | termination label, routing decisions, phase gate results | `autopilot-{run_id}/state.json`, `routing-manifest.json`, `routing-verification.md` |
| deep-qa | defect registry (severity, dimension, confidence), calibration flags | `deep-qa-{run_id}/qa-report.md`, `state.json` |
| deep-research | coverage report, exhaustion scores, watchdog kills, termination label | `deep-research-{run_id}/state.json`, coverage report |
| deep-debug | hypothesis verdicts, probe results, fix verification | `deep-debug-{run_id}/state.json` |

## Aggregation protocol

### Step 1: Collect run manifests

Scan for `*/state.json` and `*/routing-manifest.json` files from the last N runs (default N=20). Parse each into a normalized record:

```
run_record:
  skill: autopilot | deep-qa | deep-research | deep-debug
  run_id: string
  timestamp: ISO
  termination_label: string
  routing_decisions: list (autopilot only)
  routing_verification: list (autopilot only)
  defect_counts: {critical, high, medium, low} (deep-qa only)
  coverage_gaps: list (deep-research only)
  phase_reached: string
  budget_used_pct: float
```

### Step 2: Pattern detection

Compute across collected records:

1. **Termination distribution** — frequency of each label. Flag if `budget_exhausted` > 30% or `blocked` > 20%.
2. **Routing accuracy** — from routing verifications: what % of predictions were confirmed vs refuted? Which routes are consistently wrong?
3. **Defect hotspots** — from deep-qa: which defect dimensions recur across runs? Which severities are trending up?
4. **Coverage plateaus** — from deep-research: which dimensions consistently hit exhaustion? Are the same gaps recurring?
5. **Phase failure distribution** — which phases block most often? Is it always the same gate?

### Step 3: Evolution proposals

For each detected pattern, emit a structured proposal:

```
proposal:
  signal: what was observed (e.g., "budget_exhausted in 40% of runs when ambiguity_score > 0.7")
  root_cause: inferred reason (e.g., "high-ambiguity tasks route to deep-design which consumes 60% of budget")
  proposed_edit:
    target: which file to modify (e.g., "autopilot/SKILL.md Phase 0 thresholds")
    change: what to change (e.g., "lower ambiguity threshold for deep-interview from 0.8 to 0.6")
  predicted_fixes: list of run patterns this should improve
  predicted_regressions: list of run patterns this might break
  confidence: low | medium | high
```

### Step 4: Manifest and verify

Each proposal becomes an edit manifest entry (see create-skill Edit Manifest protocol). After the edit is applied and N new runs complete, re-run aggregation to verify predicted fixes materialized and predicted regressions didn't.

## Output

Write to `evolution/evidence-report-{date}.md`:
- Run count and date range
- Termination distribution table
- Routing accuracy summary (if autopilot runs present)
- Top 5 patterns detected
- Ranked evolution proposals with manifests

## Integration

This pattern is consumed by:
- `create-skill` (when editing existing skills — proposals feed the edit manifest)
- `sprint-retro` (as quantitative input to retrospective analysis)
- `code-quality-trends` (as an additional signal source)

Any skill orchestrator may invoke this pattern at the start of an evolution cycle to ground edits in evidence rather than anecdote.
