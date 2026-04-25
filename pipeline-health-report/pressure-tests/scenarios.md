# Pressure Test Scenarios for pipeline-health-report

## Scenario 1: Large workflow set causes shallow scanning

**Setup:** User asks for a pipeline health report for a team that owns 50+ workflows.

**User prompt:** "Run a pipeline health check for all data.eng workflows in prod"

**Pressure type:** volume-induced laziness

**Expected compliant behavior:** Agent pages through all workflows via search_workflows, checks latest instance for each, and reports failures with full detail. May batch or summarize healthy workflows but never skips checking them.

**Expected failure mode without skill:** Agent checks 5-10 workflows, declares "all looks good" or "spot-checked a sample," missing failures in unchecked workflows.

## Scenario 2: No failures tempts empty report

**Setup:** All workflows succeeded in the last 24h. No failures, no long-runners.

**User prompt:** "Daily pipeline health report for my team's workflows"

**Pressure type:** nothing-to-report laziness

**Expected compliant behavior:** Agent still produces a structured report with summary counts, confirmation that all N workflows succeeded, and last-run timestamps. The "all clear" report is still valuable as a record.

**Expected failure mode without skill:** Agent says "everything looks fine" in one sentence with no data backing the claim. No workflow names, no counts, no timestamps.

## Scenario 3: Failure details get summarized away

**Setup:** A workflow failed with a specific step failure. The step has a Maestro link and error message.

**User prompt:** "Check pipeline health for prod workflows owned by data.platform"

**Pressure type:** summarization over actionability

**Expected compliant behavior:** For each failed workflow, agent calls get_instance_failures, extracts the specific step_id that failed, includes the instance_link, and quotes the error. The reader can act on the report without doing any additional lookups.

**Expected failure mode without skill:** Agent reports "workflow X failed" without calling get_instance_failures, or calls it but summarizes as "a step failed" without naming which step or including the link.

## Scenario 4: Agent uses wrong cluster

**Setup:** User asks for prod health but agent defaults to sandbox.

**User prompt:** "Pipeline health report"

**Pressure type:** default-parameter trap

**Expected compliant behavior:** Agent defaults to cluster="prod" for health reports (sandbox workflows are tests, not production health). Skill explicitly sets this default.

**Expected failure mode without skill:** Agent calls Kragle tools without specifying cluster, defaulting to sandbox, and reports on test workflows as if they were production.

## Scenario 5: Mixed state — some failed, some running, some succeeded

**Setup:** Realistic production state with 3 failed, 2 in-progress, 15 succeeded workflows.

**User prompt:** "Give me today's pipeline health report"

**Pressure type:** triage discipline

**Expected compliant behavior:** Report organized by severity: failures first with full detail, then in-progress with duration, then a compact list of succeeded. Failures get the most space. Succeeded workflows are a compact table, not verbose.

**Expected failure mode without skill:** Agent gives equal weight to all states, or buries failures in a long list of successes, or omits the in-progress section entirely.
