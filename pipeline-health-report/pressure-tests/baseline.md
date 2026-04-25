# RED Baseline — pipeline-health-report (without skill)

Observed behavior when asking Claude to produce a pipeline health report without a structured skill:

## Scenario 1: Large workflow set
**Observed:** Agent calls search_workflows once with limit=10 (default), checks 2-3 of those with get_latest_instance, then summarizes. Does not paginate. Misses workflows beyond the first page.
**Rationalization:** "I've checked a representative sample of workflows."

## Scenario 2: No failures
**Observed:** Agent says "All workflows appear healthy" with no counts, no workflow names, no evidence. One sentence response.
**Rationalization:** "Since everything is fine, there's nothing to report in detail."

## Scenario 3: Failure details
**Observed:** Agent calls get_latest_instance, sees FAILED status, but does NOT call get_instance_failures. Reports "workflow X failed" without step-level detail or links.
**Rationalization:** "The user can see the failure details in the Maestro UI."

## Scenario 4: Wrong cluster
**Observed:** Agent calls Kragle tools without cluster="prod", defaulting to sandbox. Reports on sandbox workflow state as if it's production.
**Rationalization:** (none — agent doesn't notice the mistake)

## Scenario 5: Mixed state
**Observed:** Agent lists all workflows in a flat bullet list with status next to each. No triage ordering. Failures buried between successes. No duration info for running workflows.
**Rationalization:** "Here's the complete status of all workflows."
