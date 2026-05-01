---
name: create-skill
description: Use when creating, editing, scaffolding, designing, reviewing, improving, or refactoring a Claude Code skill, slash command, subagent, or agent capability. Trigger phrases include "create skill", "build skill", "scaffold skill", "edit skill", "write skill", "design skill", "improve skill", "fix skill", "review skill", "audit skill", "refactor skill", "new slash command", "new subagent", "turn this workflow into a skill", "add a skill", "authoring skills", "writing skills".
argument-hint: "[skill purpose or domain]"

category: meta
capabilities: [loop-based]
input_types: [git-diff, code-path]
output_types: [code]
complexity: moderate
cost_profile: low
maturity: beta
metadata_source: inferred
---

# Create Skill

Build a Claude Code skill that follows harness engineering best practices. The skill must be a map, not a manual — concise entrypoint, structured reference files, hard rules, feedback loops.

## Skill types

Every skill is one of three types. Classify FIRST — it determines which rules apply:

| Type | Examples | Key traits |
|---|---|---|
| **workflow** | deep-qa, autopilot, team, build | Orchestrates agents, has phases/gates, makes completion claims. Full discipline: counter-tables, termination labels, iron-law gates, pressure-tests. |
| **reference** | jenkins, jira, swagger, dbt-context | Tool guide, API reference, CLI wrapper. Code blocks ARE the value. Needs accuracy verification, not behavioral pressure-testing. |
| **shim** | autopilot-temporal, deep-qa-temporal | Routing wrapper or deprecation redirect. ~15 lines. Exempt from all discipline requirements. |

## Execution Model

Contracts scale by skill type:

**All types:**
- **Triggers live in description.** Keywords a user would actually type go in the description. "Use when …" phrasing. Never a workflow summary — Claude follows description summaries as shortcuts and skips the skill body.

**Workflow skills (full discipline):**
- **RED-GREEN-REFACTOR is the delivery gate.** Pressure scenarios are authored BEFORE the skill. Baseline-without-skill is observed and recorded. Skill is written to address the recorded failures. Loopholes are closed by re-running the same scenarios with the skill loaded. No skill ships without `pressure-tests/baseline.md` and `pressure-tests/with-skill.md` on disk.
- **Anti-rationalization counter-table is mandatory.** Every workflow skill ships with an explicit "Excuse → Reality" table in its SKILL.md or GOLDEN-RULES.md. Rationalizations are captured verbatim from baseline runs.
- **Honest termination labels.** Any skill that runs a multi-step process must define an exhaustive finite set of terminal labels (e.g. `complete | partial | blocked | budget_exhausted | cancelled`). Never `done` / `all good` / `no issues remain`.
- **Iron-law verification gate language is baked in, not suggested.** Any skill that claims completion must require fresh evidence on disk (test output file, lint exit code, judge verdict) before the completion claim. "Tests probably pass" is not a verification.
- **Companion file structure for skills over 300 lines.** A skill whose total content exceeds 300 lines ships as SKILL.md + FORMAT.md + STATE.md + GOLDEN-RULES.md + INTEGRATION.md (the npow orchestration pattern). Smaller skills may be flatter, but the split is the default once the threshold is crossed.
- **No code blocks in SKILL.md.** SKILL.md is a map. Code belongs in companion files.

**Reference skills (accuracy over discipline):**
- **Code blocks welcome in SKILL.md.** Inline examples are the primary value — they show users/agents how to use the tool.
- **Accuracy verification replaces pressure-testing.** Run 3-5 commands from the skill and confirm they work. Save results to `verification/commands-tested.md`. No RED-GREEN-REFACTOR needed.
- **Use `references/` subdirectory for overflow.** Not FORMAT.md/STATE.md — use topic-named files: `references/quick-start.md`, `references/api-reference.md`, `references/troubleshooting.md`.
- **Counter-tables, termination labels, and iron-law gates are optional.** Reference skills don't orchestrate agents or make completion claims.
- **Golden rules still apply** — hard constraints like "Always use the auth wrapper, never raw curl" prevent real errors.

**Shim skills (minimal):**
- Frontmatter + one-paragraph redirect to the canonical skill. No other requirements.

## Workflow

### Step 0: Classify skill type

Determine whether this is a **workflow**, **reference**, or **shim** skill. If shim → write frontmatter + redirect paragraph, done. Otherwise, follow the appropriate track below.

### Workflow skill track (Steps 1-10)

1. **Understand the domain (batched intake)** — elicit what the skill does, when it should trigger, what tools/output it produces. If clarification is needed, present **all questions as a single numbered batch in one message** — never serially. Do not design until the purpose is clear. See [DESIGN.md](DESIGN.md).

2. **Author pressure scenarios FIRST** — write 3-5 scenarios a subagent will face without the skill loaded. Include at least one discipline-pressure case (time pressure, sunk cost, authority). Save to `pressure-tests/scenarios.md`. See [PRESSURE-TESTING.md](PRESSURE-TESTING.md).

3. **Run RED baseline** — spawn a subagent without the skill and run the scenarios. Record exact rationalizations verbatim to `pressure-tests/baseline.md`. See [PRESSURE-TESTING.md](PRESSURE-TESTING.md).

4. **Design the architecture** — decide file structure. Over 300 lines total → split into SKILL.md + FORMAT.md + STATE.md + GOLDEN-RULES.md + INTEGRATION.md. See [DESIGN.md](DESIGN.md) and [FORMAT.md](FORMAT.md).

5. **Write the metadata** — `name` and `description` in YAML frontmatter. Description includes trigger keywords, not workflow summary. See [WRITING.md](WRITING.md).

6. **Write SKILL.md** — numbered workflow steps (one line each with a pointer), self-review checklist, golden rules, anti-rationalization counter-table, termination labels, iron-law verification gate language. No inline code blocks. See [FORMAT.md](FORMAT.md).

7. **Write companion files** — FORMAT.md (output templates), STATE.md (run state schema, resume protocol), GOLDEN-RULES.md (rules + counter-table), INTEGRATION.md (composition with deep-qa, deep-design, degraded-mode fallbacks). One file per concern, each under 500 lines. See [FORMAT.md](FORMAT.md).

8. **Close loopholes with REFACTOR pass** — spawn subagent WITH the skill on the same scenarios. Record verbatim outputs to `pressure-tests/with-skill.md`. For any new rationalization that slipped past: add a counter-table row, add a red-flag line, add a golden rule. Re-run. Repeat until `pressure-tests/with-skill.md` shows zero violations. See [PRESSURE-TESTING.md](PRESSURE-TESTING.md).

9. **Evaluate** — test the skill with positive, implicit, noisy, and negative prompts (separate from pressure tests). Verify progressive disclosure works. See [EVALUATION.md](EVALUATION.md).

10. **Deploy with pressure-test hand-off** — hand the user the skill + the 3-5 pressure scenarios and the `pressure-tests/` log. Direct them to run the scenarios themselves before relying on the skill. See [PRESSURE-TESTING.md](PRESSURE-TESTING.md).

### Reference skill track (Steps R1-R6)

R1. **Understand the tool** — what CLI/API/service does this skill document? What commands, endpoints, or patterns does a user need? See [DESIGN.md](DESIGN.md).

R2. **Design the structure** — SKILL.md as the primary guide with inline code examples. Use `references/` subdirectory for overflow content (quick-start, API reference, troubleshooting, examples). See [FORMAT.md](FORMAT.md).

R3. **Write the metadata** — `name` and `description` in YAML frontmatter. Description includes trigger keywords. See [WRITING.md](WRITING.md).

R4. **Write SKILL.md** — quick-reference tables, inline code examples, golden rules (hard constraints for the tool), common workflows. Code blocks are welcome. See [FORMAT.md](FORMAT.md).

R5. **Write reference files** — `references/` subdirectory with topic-named files. Each under 500 lines. See [FORMAT.md](FORMAT.md).

R6. **Verify accuracy** — run 3-5 representative commands from the skill and confirm they work. Save results to `verification/commands-tested.md`. See [PRESSURE-TESTING.md](PRESSURE-TESTING.md).

## Honest termination labels (for this skill's own output)

Every invocation of `create-skill` terminates with exactly one label in the final report:

| Label | Meaning |
|---|---|
| `shipped` | Workflow skill: RED baseline captured, GREEN re-run passes, REFACTOR loopholes closed, pressure scenarios handed to user. Reference skill: accuracy verification passed. |
| `shipped_degraded` | Skill files written, but pressure-test/verification phase was skipped or incomplete. Must be explicitly tagged with reason in the final report. |
| `shipped_lite` | Reference or utility skill under 100 lines. Accuracy verified but exempt from full pressure-testing. |
| `blocked_needs_input` | Domain unclear after Step 0/1; cannot proceed without user clarification. |
| `cancelled` | User interrupted. |

Never label a run `done`, `complete`, or `all good`. Every run produces one of the above labels.

## Self-review checklist

Before delivering, verify ALL applicable items:

**All skill types:**
- [ ] Skill type classified (workflow / reference / shim) at Step 0
- [ ] `description` is specific, third-person, includes trigger keywords, does NOT summarize workflow
- [ ] Every reference/companion file is linked from SKILL.md with a one-line summary
- [ ] Golden rules are hard and mechanical (never "consider" or "try to")
- [ ] Reference files are one level deep (SKILL.md → file, never file → file → file)
- [ ] Skill works when invoked explicitly (`/skill-name`) AND when Claude triggers it from a matching request
- [ ] No vague quality language ("clean", "good", "appropriate") — replaced with concrete specs
- [ ] Final report uses one of the five termination labels above

**Workflow skills only:**
- [ ] SKILL.md is under 100 lines of content (excluding frontmatter) for flat skills, or a lean map for companion-split skills
- [ ] SKILL.md has zero inline code blocks (all code is in companion files)
- [ ] Anti-rationalization counter-table present (min 5 rows for discipline skills, min 3 for one-shots)
- [ ] Honest termination labels defined (finite enum, 3-6 labels)
- [ ] Iron-law verification gate language present (concrete evidence file requirement, not "verify")
- [ ] At least one feedback loop encoded (test → verify → fix → re-test)
- [ ] `pressure-tests/scenarios.md`, `pressure-tests/baseline.md`, `pressure-tests/with-skill.md` all exist on disk
- [ ] `pressure-tests/with-skill.md` shows zero violations on all scenarios (or degraded tag with reason)
- [ ] Companion split applied if total skill content > 300 lines (SKILL.md + FORMAT.md + STATE.md + GOLDEN-RULES.md + INTEGRATION.md)

**Reference skills only:**
- [ ] Code examples are inline, copy-paste ready, and tested
- [ ] `references/` subdirectory used for overflow (not FORMAT.md/STATE.md pattern)
- [ ] `verification/commands-tested.md` exists with results from 3-5 representative commands
- [ ] Quick-reference tables present for common operations

## Golden rules for skill creation

Hard rules. Never violate these.

1. **Classify type first.** Every skill is workflow, reference, or shim. Classify at Step 0. The type determines which rules apply. Applying workflow discipline to a reference skill wastes effort; skipping it on a workflow skill invites drift.
2. **SKILL.md is a map (workflow) or a guide (reference).** Workflow SKILL.md: no code blocks, point to companion files. Reference SKILL.md: code blocks are the value — inline examples, quick-reference tables, CLI patterns.
3. **Description is discovery, not summary.** Claude picks skills from description alone. If the description summarizes the workflow, Claude follows the description instead of reading the skill body. Describe triggers, not process.
4. **RED before GREEN (workflow skills).** If there is no `pressure-tests/baseline.md` recording what a subagent does WITHOUT the skill, the workflow skill is unverified. Delete it. Start over. Reference skills use accuracy verification instead.
5. **Golden rules prevent drift.** Every skill must encode 3-8 hard mechanical rules specific to its domain. Use imperative voice: "Never", "Always", "Must".
6. **Anti-rationalization counter-table is mandatory for workflow skills.** Every workflow skill ships with an Excuse → Reality table capturing the exact verbatim excuses observed in RED baseline.
7. **Termination labels are a finite enum (workflow skills).** Workflow skills define 3-6 exhaustive labels. Never "done" / "no issues" / "all good" as a label. Reference skills don't need them.
8. **Iron-law gates beat gentle reminders (workflow skills).** A rule that says "verify tests pass" is weaker than a gate that refuses to claim completion unless `test-output.txt` exists on disk and matches a pattern.
9. **Feedback loops are the product.** A skill without a concrete verification cycle (do → check → diagnose → fix → re-check) is a suggestion, not a skill.
10. **Diagnose, don't retry.** When the agent gets stuck, the skill must tell it how to figure out WHY, not just "try again." Include a symptom → cause → fix table.
11. **Concrete beats abstract.** "Use a clean design" produces slop. "Define CSS variables on `:root`, use `system-ui`, add hover states" produces consistency. Replace every adjective with a specification.
12. **Progressive disclosure saves context.** Only SKILL.md loads on trigger. Companion files load when Claude reads them. Put expensive content in companion files.
13. **Reference skills use `references/`, workflow skills use companion split.** Don't mix the patterns — FORMAT.md/STATE.md for workflow; `references/quick-start.md` for reference.
14. **If it's not in the skill files, it doesn't exist.** The agent can only see what's in the skill directory. Every constraint must live in the skill files or it will be ignored.

## Anti-rationalization counter-table (for skill authoring)

This counter-table captures excuses observed when agents (and authors) try to skip the discipline of this skill. Every skill produced by `create-skill` must include its own counter-table with excuses specific to that skill's domain.

| Excuse | Reality |
|---|---|
| "Pressure-testing is overkill for this skill." | Workflow skills: no skill ships without a RED baseline. Reference skills: run accuracy verification instead. Shim skills: exempt. Classify the type first. |
| "I already wrote the skill; I'll test after." | Workflow: skill body written before baseline is unverified documentation. Delete it. Run Step 2 first. Reference: write the skill, then verify commands work. |
| "The agent obviously understands this rule." | Obvious to you ≠ obvious under pressure. Run the scenarios anyway. |
| "I'll just add a counter-table row I imagined the agent might say." | Counter-table rows come from observed baseline output, not imagination. Unobserved excuses miss the real rationalizations. |
| "This is a reference skill so I can skip all the rules." | Reference skills still need: trigger-based descriptions, golden rules, progressive disclosure, tested code examples. They skip: counter-tables, termination labels, pressure-tests, iron-law gates. |
| "Companion-split is bureaucracy for a short skill." | Under 300 lines: keep it flat. Over 300: split. The split is not optional above the threshold because long SKILL.md bodies get partial-read by Claude. |
| "Termination label `done` is fine, I mean `complete`." | Not fine. The enum must be honest — `complete` means every criterion verified on disk this session. `done` is ambiguous and invites self-approval. |
| "I'll put FORMAT.md and STATE.md in my reference skill." | Reference skills use `references/` subdirectory with topic-named files. FORMAT.md/STATE.md is the workflow companion pattern. Don't mix them. |

## Reference files

| File | Contents |
|------|----------|
| [DESIGN.md](DESIGN.md) | How to analyze a domain, design file structure, apply progressive disclosure |
| [WRITING.md](WRITING.md) | How to write metadata, SKILL.md body, reference files, golden rules, checklists |
| [FORMAT.md](FORMAT.md) | Output template for a produced skill (SKILL.md + companion files), mandatory sections including counter-table and termination labels |
| [GOLDEN-RULES.md](GOLDEN-RULES.md) | Consolidated rules for skill authoring with per-rule concrete examples and detection criteria |
| [PRESSURE-TESTING.md](PRESSURE-TESTING.md) | RED-GREEN-REFACTOR protocol for skills: how to write pressure scenarios, run the baseline, interpret violations, close loopholes |
| [INTEGRATION.md](INTEGRATION.md) | How `create-skill` composes with `deep-qa` for skill review, and degraded-mode fallbacks |
| [EVALUATION.md](EVALUATION.md) | How to test skills with positive, implicit, noisy, and negative prompts |
