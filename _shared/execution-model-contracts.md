# Execution-Model Contracts (Shared)

Five contracts that every parallel-critic / independent-judge skill in this repo enforces. Written once here; each skill's SKILL.md references this file rather than re-stating the contracts verbatim.

**Used by:** deep-qa, deep-design, deep-debug, deep-research, proposal-reviewer, deep-plan, team, autopilot, loop-until-done.

---

## 1. Files Not Inline

**Contract:** all data passed to spawned agents via file paths — never inline strings. Inline content is silently truncated by the Task/Agent harness above some threshold (~50-100 KB varies by tool), so handing a large artifact inline produces undetectable partial reads.

**What must be a file:**
- Artifact under analysis (spec, code, proposal, research report)
- Known-defects list / known-claims list
- Per-angle or per-claim input definitions
- Judge input bundles (one per claim or batched)
- Any JSON/YAML that is more than ~20 lines

**What may be inline:**
- The agent's task instructions themselves (system + user prompts)
- File paths (obviously)
- Structured constants under ~20 lines (a dimension enum, a severity vocabulary)

**Verification:** before every Agent tool call, assert (a) the input file exists, (b) it is non-empty. Halt with error if either fails. Do not spawn an agent against a missing or empty input.

**Common failure mode:** "the artifact is small, I'll just paste it into the prompt." Today it's small. Tomorrow the user hands a 200-line spec. The harness silently truncates, the agent analyzes half, the coordinator synthesizes from incomplete critique. File-always avoids this class of bug entirely.

---

## 2. State Written Before Agent Spawn

**Contract:** write `spawn_time_iso` (and any associated state fields) to `state.json` BEFORE calling the Agent tool. Record `spawn_failed` status if the call errors. Resume logic re-reads `state.json` and replays from the last successfully-spawned step — never from in-memory state.

**Why before, not after:**
- If the coordinator crashes mid-spawn, post-spawn state is lost. Pre-spawn state allows resume to know "we intended to spawn X; we don't know if it ran; re-check its output file."
- Post-spawn writes also risk a race: the spawned agent may finish and mutate state before the coordinator records its spawn.

**Required fields per spawn:**
- `status`: one of `pending | in_progress | completed | timed_out | spawn_failed`
- `spawn_time_iso`: ISO-8601 UTC timestamp at the moment of the Agent call
- `spawn_attempt_count`: retry counter; after 3 failures, retire the angle/defect/task
- `output_path`: expected output file the agent will write to

**Generation counter invariant:** every state mutation (spawn, completion, timeout, coverage update) increments `state.generation` by 1. The counter is monotonic; resume verifies that replay produces a matching or higher generation value. Never decrement, never skip.

**Verification pattern:**
```python
state.agents[id].status = "in_progress"
state.agents[id].spawn_time_iso = now()
state.generation += 1
write_state(state)                                  # BEFORE spawn
reloaded = read_state()
assert reloaded.generation == state.generation      # verify write landed
Agent(...)                                          # now spawn
```

**Common failure mode:** "I'll record the spawn after it returns." When the coordinator crashes, the resume protocol cannot distinguish "never spawned" from "spawned and completed but coordinator died before recording." Pre-spawn write eliminates the ambiguity.

---

## 3. Structured Output Contract

**Contract:** agent outputs that the coordinator consumes for decisions (severity verdicts, credibility verdicts, critique defects, audit reports) are machine-parseable lines between `STRUCTURED_OUTPUT_START` and `STRUCTURED_OUTPUT_END` markers. The coordinator reads ONLY the structured fields. Free-text summaries are ignored.

**Format (pipe-separated key|value, one per line):**
```
STRUCTURED_OUTPUT_START
DEFECT_ID|defect-001
SEVERITY|major
CONFIDENCE|high
RATIONALE|Missing error path for network timeout in retry loop
STRUCTURED_OUTPUT_END
```

**Coordinator parser rules:**
- Each line is `KEY|VALUE`; multiple values joined with `;` or `,` as documented per key.
- Unknown keys ignored (forward-compatible).
- Missing required keys → fail-safe: treat the verdict as the WORST legal value for that check (e.g., `SEVERITY|critical`, `VERDICT|FALSE`, `REPORT_FIDELITY|compromised`).
- Entire missing or malformed block → same fail-safe.
- Multiple `START/END` blocks in one file → read only the LAST one (allows agents to revise).

**Why fail-safe to worst, not best:**
An unparseable output means the agent might have failed to understand the task. Defaulting to "looks good" hides failures. Defaulting to worst surfaces them — the coordinator either retries, escalates, or terminates honestly.

**Common failure mode:** "the prose summary is richer, I'll parse that." Free-text is non-deterministic — the same agent on the same input produces different phrasings. Parsing prose breaks silently; structured-markers break loudly. Always structured.

---

## 4. Independence Invariant

**Contract:** the coordinator orchestrates; it does NOT evaluate. Every load-bearing verdict — severity classification, credibility verdict, approval gate, report-fidelity check — is delegated to a separate agent with fresh context. The coordinator's job is to write input files, spawn agents, read structured output, and assemble. The coordinator never "decides" anything with impact.

**What coordinator MAY do:**
- Select which angles/claims/dimensions to evaluate next
- Route work to judges (dispatcher, not evaluator)
- Detect convergence (coverage, frontier exhaustion) from structured state
- Assemble the final report from judge verdicts

**What coordinator MUST delegate:**
- Severity classification (delegate to severity judges)
- Credibility / VERIFIED / FALSE verdicts (delegate to credibility judges)
- Falsifiability of a weakness (delegate to falsifiability judges)
- Go / no-go / approval / sign-off (delegate to gate agents)
- "Is this defect real?" (delegate to critics + judges, not coordinator-reasoned)

**Why:** the coordinator has context pollution — it has seen the critique, the defect counts, the time budget, the user's apparent preferences. Any of those can drift its judgment. A fresh agent reading only the structured input has no such pressure.

**Calibration signal:** if the coordinator is ever tempted to say "this defect doesn't seem important — I'll drop it from the report," stop. That's an evaluation. Write it to a judge input file, spawn a judge, read the verdict.

**Common failure mode:** "the judge is slow — I'll just classify this one." The coordinator's throughput gain is small; the independence invariant violation cascades into trust failures everywhere downstream.

---

## 5. Coverage Completeness Invariant

**Contract:** when a skill defines required coverage categories (e.g., deep-design's 5 required dimension categories, deep-qa's defect categories), ALL required categories MUST have `explored_count >= 1` before the coordinator may proceed to final synthesis. This is a hard gate — not a quality judgment, not a "nice to have," not something the coordinator can waive.

**What the coordinator MUST do when categories are uncovered:**
- Run coverage extension rounds targeting uncovered categories (up to the skill's defined extension limit)
- If extensions are exhausted and gaps remain: label the output `INCOMPLETE — uncovered: {list}`
- If the execution environment has context constraints: use sagaflow durable execution instead of skipping coverage

**What the coordinator MUST NOT do:**
- Proceed to synthesis with uncovered categories and a "Conditions Met" or equivalent label
- Note uncovered categories in a coverage report while presenting the output as complete work
- Cite context constraints, tooling limitations, or time pressure as reasons to skip required coverage
- Unilaterally decide that an uncovered category "isn't relevant to this concept"

**Why this is a shared contract:** every parallel-critic skill has the same failure mode — the coordinator runs out of context or patience, declares the work done, and lists the gaps as if noting them is equivalent to closing them. This contract makes the gate explicit: coverage categories are structural requirements, not aspirational targets.

**Verification pattern:**
```python
for category in required_categories:
    assert state.categories[category].explored_count >= 1, \
        f"INCOMPLETE: {category} has zero explored angles"
# Only after ALL pass: proceed to synthesis
```

**Common failure mode:** "I covered the 3 most important categories and noted the other 2 as gaps." The user asked for all 5. Noting gaps while declaring completion is the bug, not the mitigation.

---

## Integration checklist for a skill importing this reference

- [ ] SKILL.md has a one-line cross-reference near the Execution Model section: `See [_shared/execution-model-contracts.md](../_shared/execution-model-contracts.md) for the shared contracts.`
- [ ] If the skill restates any of the 5 contracts inline, either delete the duplicate OR mark it as "elaborated for this skill's domain" with explicit divergence noted.
- [ ] If the skill defines required coverage categories, verify they are enforced by Contract 5 (coverage completeness invariant) — the coordinator MUST NOT proceed to synthesis with uncovered categories.
- [ ] Skill-specific extensions (e.g., "files must use the `{run_id}/angles/` directory") go in the skill's own SKILL.md, not in this shared reference.
- [ ] The skill's self-review checklist references these contracts by name so it's clear which items are inherited from the shared spec vs. skill-specific.

---

## Divergence policy

If a skill legitimately needs to override one of these contracts (example: a skill that processes sub-100-byte configs can safely go inline and skip `files not inline`), document the override explicitly in the skill's SKILL.md with reasoning. Silent divergence is the failure mode — explicit divergence is fine.
