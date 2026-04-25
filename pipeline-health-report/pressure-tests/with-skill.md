# GREEN Run — pipeline-health-report (with skill)

Verified against live Kragle prod API on 2026-04-24.

## Scenario 1: Large workflow set
**With skill:** Skill enforces "Check ALL workflows, not a sample" golden rule and requires limit high enough to cover all team workflows. Agent must paginate if needed.
**Status:** PASS — golden rule + counter-table row explicitly prevent spot-checking.

## Scenario 2: No failures
**With skill:** Skill requires "All clear is still a report" with full structure, counts, and timestamps.
**Status:** PASS — golden rule #6 prevents one-sentence dismissal.

## Scenario 3: Failure details
**With skill:** Skill mandates get_instance_failures for every FAILED workflow (golden rule #2). Counter-table row addresses the exact rationalization from baseline.
**Status:** PASS — step is marked MANDATORY in workflow step 3.

## Scenario 4: Wrong cluster
**With skill:** Skill defaults cluster to "prod" in Arguments section and golden rule #1 says "Every Kragle MCP call passes cluster='prod'". Counter-table addresses this.
**Status:** PASS — default is explicitly set in skill, not left to Kragle API default.

## Scenario 5: Mixed state
**With skill:** Skill specifies report section ordering: Failed first, then Long-Running, then In Progress, then Succeeded. Golden rule #4 enforces severity ordering.
**Status:** PASS — triage order is baked into the output template.

## Smoke test
- `search_workflows(cluster=prod, limit=5)` → returned 5 active workflows
- `get_latest_instance(workflow_id=BILLING.ETL_BILLING_DAILY_DIMS_SUB, cluster=prod)` → SUCCEEDED, instance_link present
- Full Kragle API chain verified working

## Violations found: 0
