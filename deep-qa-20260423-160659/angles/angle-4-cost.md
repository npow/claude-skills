# Angle 4: Cost Runaway Risk — 4 Sonnet Reviewers + Meta-Reviewer

QA Dimension: cost_runaway_risk
Priority: high
Depth: 0

Question: The pattern spawns 4 Sonnet reviewers in parallel plus a Sonnet meta-reviewer (5 Sonnet agents total per review cycle). If a skill has a rejection loop (e.g., loop-until-done caps at 5 rejections), the worst case is 5 × 5 = 25 Sonnet agents for review alone. Is there any mechanism to prevent cost runaway from repeated panel rejections? Are the timeouts (180s per reviewer, 300s for smoke-test) sufficient constraints?
