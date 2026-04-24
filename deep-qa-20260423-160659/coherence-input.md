# Coherence Integrator Input — All Critic Outputs

## Critic 1 (behavioral_correctness — structured output format ambiguity)
- DEFECT-1: CRITICAL — Variable field count in DEFECT lines (cross-lane uses 7 pipe-delimited fields vs 5 for in-lane)
- DEFECT-2: CRITICAL — VERDICT has no contract with DEFECT presence (approved + defects is valid per format)
- DEFECT-3: MAJOR — Zero DEFECTs with rejected verdict is valid per format (no cardinality constraint)
- DEFECT-4: MAJOR — DEFECT {id} field has no format contract (incompatible ID schemes across reviewers)
- DEFECT-5: MAJOR — DEFECT_FINAL ID namespace undefined (meta-reviewer ID source unknown)
- DEFECT-6: MAJOR — SMOKE_TEST_BLOCKED absent from reviewer structured output format block
- DEFECT-7: MAJOR — Token mismatch: reviewer emits SMOKE_TEST_BLOCKED, meta-reviewer expects smoke_blocked
- DEFECT-8: MINOR — confirmed_cross_lane vs confirmed decision rule undefined
- DEFECT-9: MINOR — PANEL_VERDICT|approved condition references smoke-test but smoke-test may be in degraded mode

## Critic 2 (instruction_conflicts — cross-lane empowerment rule)
- D1: CRITICAL — "Blocking" is undefined, making cross-lane filing threshold an open invitation
- D2: MAJOR — No quantitative cap or ratio guard on cross-lane volume
- D3: MAJOR — Table-level claim ("not their scope") contradicts prompt-level instruction ("Focus your analysis there. However...")
- D4: MINOR — Smoke-test reviewer has no realistic cross-lane filing capability but rule applies equally
- D5: MAJOR — Cross-lane findings can manufacture false "confirmed" status via same-evidence-path re-traversal

## Critic 3 (injection_resistance — smoke-test injection)
- DEFECT-3-01: CRITICAL — Smoke-test prompt grants unconditional execution to untrusted repro file, no sandbox
- DEFECT-3-02: HIGH — Spec file is second injection surface: golden paths derived from attacker-controlled content
- DEFECT-3-03: HIGH — Build output log is third injection surface via log-embedded prompt injection
- DEFECT-3-04: HIGH — "EXECUTE, not ANALYZE" directive suppresses safety judgment, amplifies injection
- DEFECT-3-05: HIGH — Injection execution produces misleading PASS verdict with no detection mechanism
- DEFECT-3-06: MEDIUM — Zero content-isolation boundary mentioned anywhere in spec/pattern/checklist

## Critic 4 (cost_runaway_risk — rejection loop economics)
- D1: CRITICAL — team skill has no rejection cap (unlimited panel cycles)
- D2: CRITICAL — Stacked rejection loops (team + loop-until-done) double worst-case to 50 agents
- D3: MAJOR — ship-it has no rejection cap stated
- D4: MAJOR — "Fresh panel every time" burns full context every cycle with no incremental savings
- D5: MAJOR — Timeout retry path is unbounded (no retry cap)
- D6: MAJOR — No total-cost gate or wall-clock budget for pattern
- D7: MINOR — Degraded mode still spawns meta-reviewer (no cost reduction)

## Critic 5 (behavioral_correctness — failure mode exhaustiveness)
- D1: CRITICAL — Meta-reviewer output unparseable (no failure mode row)
- D2: HIGH — All reviewers approve but smoke-test blocked: conflated with clean pass
- D3: HIGH — Reviewer produces logically inconsistent output (VERDICT|approved + critical DEFECT lines)
- D4: MEDIUM — Exactly 2 reviewers time out (boundary condition, quorum gap)
- D5: MEDIUM — Meta-reviewer can dismiss unanimous 4-reviewer finding
- D6: MEDIUM — Panel produces verdict but meta-reviewer was never spawned (silent skip)
- D7: LOW — CROSS_LANE finding on dismissed defect has no defined resolution

## Critic 6 (instruction_conflicts — meta-reviewer independence)
- D1: CRITICAL — Independence is instructional not structural (meta-reviewer receives full diff, can re-analyze)
- D2: MAJOR — 2v2 reviewer splits have no tiebreaker rule, forcing meta-reviewer into original analysis
- D3: MAJOR — "Dismissed" status has no required citation format, allowing meta-reviewer override without reviewer backing
- D4: MAJOR — Independence framing creates false confidence in downstream skills
