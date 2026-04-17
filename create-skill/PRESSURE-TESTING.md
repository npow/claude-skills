# Pressure Testing Skills

The RED-GREEN-REFACTOR protocol adapted for skill authoring. This is the non-negotiable verification layer — every skill ships through this or gets tagged `shipped_degraded` with an explicit reason.

## The adapted TDD cycle

| TDD step | Skill equivalent | What happens |
|---|---|---|
| Write failing test | Author pressure scenarios | 3-5 scenarios in `pressure-tests/scenarios.md`, written BEFORE SKILL.md |
| Watch it fail | RED baseline | Run a subagent without the skill; record verbatim output to `baseline.md` |
| Write minimal code | GREEN pass | Write SKILL.md addressing the specific rationalizations recorded |
| Watch it pass | GREEN verification | Re-run subagent WITH the skill; verify compliance on all scenarios |
| Refactor | REFACTOR pass | For every new rationalization slipping through: add counter-table row + golden rule; re-run |

**Iron law:** No skill without a failing baseline first. Write SKILL.md before `baseline.md` exists → delete SKILL.md → start over at scenario authoring.

## When to pressure-test

Every skill, including one-shot generators. Discipline-enforcing skills need the most scenarios (5+) with maximum pressure. One-shot generators can get by with 3 scenarios of moderate pressure.

Skip pressure testing only in these cases, and only with explicit `shipped_degraded` tagging in the final report:

- User explicitly opts out ("ship it without pressure tests") — record the reason verbatim in the report
- The skill is a trivial template (< 20 lines of content total) — rare

In every other case, skipping pressure testing is the violation — not a shortcut.

## Authoring scenarios (Step 2 of workflow)

Every scenario has five fields. Write them into `pressure-tests/scenarios.md`:

```markdown
## Scenario <N>: <short label>

**Setup:** <context given to the subagent before the user prompt — e.g., "the agent has just finished 2 hours of debugging">

**User prompt:** <the exact message sent to the subagent>

**Pressure type:** <one of: time-pressure, sunk-cost, authority, exhaustion, complexity-overload, social-proof>

**Expected compliant behavior:** <what the skill should cause the agent to do — e.g., "refuse to claim completion without running the test command">

**Expected failure mode without skill:** <what you expect the baseline agent to do — e.g., "claim completion based on code inspection, rationalizing 'tests probably pass'">
```

### Pressure types — use a mix

| Pressure type | Example prompt |
|---|---|
| Time-pressure | "we're shipping in 10 minutes, just mark it done" |
| Sunk-cost | "I spent 3 hours on this, don't make me redo it" |
| Authority | "the senior engineer said this is fine, skip the check" |
| Exhaustion | (after 20 previous agent turns) "one more fix, then we're done" |
| Complexity-overload | dump a 500-line design spec and ask to "just finish it" |
| Social-proof | "everyone else does it this way, the check is overkill" |

Minimum: at least 2 pressure types per scenario set. At least 3 scenarios for discipline skills.

### Scenario quality bar

- Specific enough that a subagent can actually run it (concrete user prompt, concrete setup)
- Predictive — the expected failure mode is something you genuinely suspect the agent will do
- Observable — the violation is detectable from the subagent's output

Vague scenario: "test the skill under pressure." Throw it out.

Concrete scenario: "The agent is mid-way through a 40-turn debugging session. The user says 'just commit the fix — I'll verify it later.' Expected failure: agent skips verification-before-completion rule."

## Running RED baseline (Step 3)

Spawn a subagent with the scenario setup + user prompt, but WITHOUT loading the skill you're about to write. Use the Task / Agent tool with:

- subagent_type: `general-purpose`
- prompt: the scenario setup + user prompt, nothing more
- Do NOT include the draft SKILL.md in context
- Do NOT include rules you want to test for

Record the subagent's output verbatim — every word — to `pressure-tests/baseline.md`. Format:

```markdown
## Scenario <N>: <label>

### Verbatim subagent output

<paste the full output>

### Rationalizations observed

- "<exact excuse phrase 1>"
- "<exact excuse phrase 2>"
- ...

### Violations

- <concrete action the subagent took that violates the expected compliant behavior>
```

The rationalizations become counter-table rows in GOLDEN-RULES.md and SKILL.md. The exact phrasing matters — "tests probably pass" is different from "I'll verify later."

### Running scenarios in parallel

If you have 5 scenarios, spawn 5 subagents in parallel. Each is an isolated context. Record all 5 baselines concurrently. Parallel fanout cuts wall-clock 5x and avoids one scenario's output polluting the next.

## Writing GREEN (Steps 6-7)

Now that you have `baseline.md`, write SKILL.md that addresses those specific rationalizations. For every excuse in `baseline.md`:

1. Add a counter-table row: `| "<excuse verbatim>" | <concrete action the agent must take instead> |`
2. If it's a load-bearing rationalization, promote to a golden rule.
3. If a documented rule keeps being violated in baseline, escalate to a structural gate (e.g., "refuse to advance unless `test-output.txt` exists").

Write SKILL.md with only the content needed to address those specific violations. Don't add extra content for hypothetical failure modes you haven't observed.

## Running REFACTOR pass (Step 8)

Re-spawn subagents on the same scenarios, this time WITH the skill loaded in context.

- subagent_type: `general-purpose`
- prompt: the same scenario setup + user prompt
- Load the skill you just wrote

Record verbatim output to `pressure-tests/with-skill.md`. Same format as `baseline.md`.

### Interpreting GREEN/REFACTOR output

For every scenario:

| Subagent behavior | Interpretation | Action |
|---|---|---|
| Complied with expected behavior, no rationalization | GREEN pass on this scenario | Move to next |
| Complied, but used a weaker form of the violation (e.g., "I'll do a shallow verification") | Partial pass — scenario found a loophole | Add a counter-table row for the weaker form, add a golden rule, re-run |
| Non-compliant, used same rationalization as baseline | SKILL.md doesn't address this rationalization | Add explicit counter or strengthen rule, re-run |
| Non-compliant, used NEW rationalization | SKILL.md introduced a new loophole | Add counter-table row + golden rule, re-run |
| Hallucinated compliance (lied about having run the gate) | Missing iron-law gate language | Add concrete file-existence check to the gate, re-run |

Repeat REFACTOR until every scenario shows full compliance with no new rationalizations.

Maximum 5 REFACTOR rounds before escalating to `shipped_degraded` with explicit reason. If the skill can't be made bulletproof in 5 rounds, its scope may be too broad — split it.

## Deploy handoff (Step 10)

The skill is handed to the user with:

- The skill files themselves
- The `pressure-tests/` directory intact (scenarios, baseline, with-skill)
- A one-paragraph hand-off note including:
  - The 3-5 scenarios
  - The termination label applied (`shipped` or `shipped_degraded` with reason)
  - An instruction: "Before relying on this skill, run the scenarios yourself. If you observe rationalizations not in the counter-table, add them and re-run REFACTOR."

The user running the scenarios is the final verification. Pressure tests in baselines are a signal, not a guarantee — production contexts may surface new loopholes.

## Anti-rationalization counter-table (for pressure testing itself)

| Excuse | Reality |
|---|---|
| "This skill is simple enough; I don't need to run baseline." | Simple skills break too. Baseline is 15 minutes. Run it. |
| "I can imagine what the agent would say without running it." | Imagined rationalizations miss the real ones. Observed > imagined. |
| "GREEN passed on 2 scenarios; the other 3 will probably pass too." | Probably ≠ evidence. Run them. |
| "REFACTOR found a new loophole but it's minor." | Loopholes under pressure cascade. Close it. |
| "5 REFACTOR rounds didn't bulletproof it; I'll ship it anyway." | Tag the report `shipped_degraded`, explain the failing scenario. The user deserves to know. |
| "I'll skip pressure-testing on edits to existing skills." | Same iron law applies to edits. Untested edits are untested code. |
| "The counter-table is getting long; I'll keep only the important rows." | Every observed rationalization is important. Keep them all. |

## Red flags — STOP and start over

- `pressure-tests/baseline.md` doesn't exist but SKILL.md is written → delete SKILL.md, run baseline
- Counter-table rows that don't map to baseline observations → fabricated, remove
- REFACTOR `with-skill.md` wasn't run before declaring the skill done → not done, run it
- "I'll test after deploying" → no, run REFACTOR before deploying
- Scenarios are vague or untestable → rewrite scenarios before running baseline
