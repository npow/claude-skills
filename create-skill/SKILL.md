---
name: create-skill
description: Use when creating, editing, scaffolding, designing, reviewing, improving, or refactoring a Claude Code skill, slash command, subagent, or agent capability. Trigger phrases include "create skill", "build skill", "scaffold skill", "edit skill", "write skill", "design skill", "improve skill", "fix skill", "review skill", "audit skill", "refactor skill", "new slash command", "new subagent", "turn this workflow into a skill", "add a skill", "authoring skills", "writing skills".
argument-hint: "[skill purpose or domain]"
---

# Create Skill

Build a Claude Code skill that follows harness engineering best practices. The skill must be a map, not a manual — concise entrypoint, structured reference files, hard rules, feedback loops. Every skill this skill produces is RED-GREEN-REFACTOR tested before it ships.

## Execution Model

Non-negotiable contracts for every skill produced by this skill:

- **RED-GREEN-REFACTOR is the delivery gate.** Pressure scenarios are authored BEFORE the skill. Baseline-without-skill is observed and recorded. Skill is written to address the recorded failures. Loopholes are closed by re-running the same scenarios with the skill loaded. No skill ships without `pressure-tests/baseline.md` and `pressure-tests/with-skill.md` on disk.
- **Anti-rationalization counter-table is mandatory.** Every skill (discipline or workflow) ships with an explicit "Excuse → Reality" table in its SKILL.md or GOLDEN-RULES.md. Rationalizations are captured verbatim from baseline runs.
- **Honest termination labels for workflow skills.** Any skill that runs a multi-step process must define an exhaustive finite set of terminal labels (e.g. `complete | partial | blocked | budget_exhausted | cancelled`). Never `done` / `all good` / `no issues remain`.
- **Iron-law verification gate language is baked in, not suggested.** Any skill that claims completion must require fresh evidence on disk (test output file, lint exit code, judge verdict) before the completion claim. "Tests probably pass" is not a verification.
- **Companion file structure for skills over 300 lines.** A skill whose total content exceeds 300 lines ships as SKILL.md + FORMAT.md + STATE.md + GOLDEN-RULES.md + INTEGRATION.md (the npow orchestration pattern). Smaller skills may be flatter, but the split is the default once the threshold is crossed.
- **Triggers live in description.** Keywords a user would actually type go in the description. "Use when …" phrasing. Never a workflow summary — Claude follows description summaries as shortcuts and skips the skill body.

## Workflow

1. **Understand the domain (batched intake)** — elicit what the skill does, when it should trigger, what tools/output it produces. If clarification is needed, present **all questions as a single numbered batch in one message** — never serially. Do not design until the purpose is clear. See [DESIGN.md](DESIGN.md).

2. **Author pressure scenarios FIRST** — write 3-5 scenarios a subagent will face without the skill loaded. Include at least one discipline-pressure case (time pressure, sunk cost, authority). Save to `pressure-tests/scenarios.md`. See [PRESSURE-TESTING.md](PRESSURE-TESTING.md).

3. **Run RED baseline** — spawn a subagent without the skill and run the scenarios. Record exact rationalizations verbatim to `pressure-tests/baseline.md`. See [PRESSURE-TESTING.md](PRESSURE-TESTING.md).

4. **Design the architecture** — decide file structure. Over 300 lines total → split into SKILL.md + FORMAT.md + STATE.md + GOLDEN-RULES.md + INTEGRATION.md. See [DESIGN.md](DESIGN.md) and [FORMAT.md](FORMAT.md).

5. **Write the metadata** — `name` and `description` in YAML frontmatter. Description includes trigger keywords, not workflow summary. See [WRITING.md](WRITING.md).

6. **Write SKILL.md** — numbered workflow steps (one line each with a pointer), self-review checklist, golden rules, anti-rationalization counter-table, termination labels (if workflow), iron-law verification gate language. No inline code blocks. See [FORMAT.md](FORMAT.md).

7. **Write companion files** — FORMAT.md (output templates), STATE.md (run state schema, resume protocol), GOLDEN-RULES.md (rules + counter-table), INTEGRATION.md (composition with deep-qa, deep-design, degraded-mode fallbacks). One file per concern, each under 500 lines. See [FORMAT.md](FORMAT.md).

8. **Close loopholes with REFACTOR pass** — spawn subagent WITH the skill on the same scenarios. Record verbatim outputs to `pressure-tests/with-skill.md`. For any new rationalization that slipped past: add a counter-table row, add a red-flag line, add a golden rule. Re-run. Repeat until `pressure-tests/with-skill.md` shows zero violations. See [PRESSURE-TESTING.md](PRESSURE-TESTING.md).

9. **Evaluate** — test the skill with positive, implicit, noisy, and negative prompts (separate from pressure tests). Verify progressive disclosure works. See [EVALUATION.md](EVALUATION.md).

10. **Deploy with pressure-test hand-off** — hand the user the skill + the 3-5 pressure scenarios and the `pressure-tests/` log. Direct them to run the scenarios themselves before relying on the skill. See [PRESSURE-TESTING.md](PRESSURE-TESTING.md).

## Honest termination labels (for this skill's own output)

Every invocation of `create-skill` terminates with exactly one label in the final report:

| Label | Meaning |
|---|---|
| `shipped` | Skill files written, RED baseline captured, GREEN re-run passes, REFACTOR loopholes closed, pressure scenarios handed to user. |
| `shipped_degraded` | Skill files written, but pressure-test phase was skipped or incomplete. Must be explicitly tagged with reason in the final report. |
| `blocked_needs_input` | Domain unclear after Step 1; cannot proceed without user clarification. |
| `cancelled` | User interrupted. |

Never label a run `done`, `complete`, or `all good`. Every run produces one of the above labels.

## Self-review checklist

Before delivering, verify ALL:

- [ ] SKILL.md is under 100 lines of content (excluding frontmatter) for flat skills, or a lean map for companion-split skills
- [ ] SKILL.md has zero inline code blocks (all code is in reference files)
- [ ] `description` is specific, third-person, includes trigger keywords, does NOT summarize workflow
- [ ] Every reference/companion file is linked from SKILL.md with a one-line summary
- [ ] Golden rules are hard and mechanical (never "consider" or "try to")
- [ ] Anti-rationalization counter-table present (min 5 rows for discipline skills, min 3 for one-shots)
- [ ] Honest termination labels defined (if skill is a workflow with completion claims)
- [ ] Iron-law verification gate language present (concrete evidence file requirement, not "verify")
- [ ] Self-review checklist exists and every item is objectively verifiable
- [ ] At least one feedback loop encoded (test → verify → fix → re-test)
- [ ] No vague quality language ("clean", "good", "appropriate") — replaced with concrete specs
- [ ] `pressure-tests/scenarios.md`, `pressure-tests/baseline.md`, `pressure-tests/with-skill.md` all exist on disk
- [ ] `pressure-tests/with-skill.md` shows zero violations on all scenarios (or degraded tag with reason)
- [ ] Reference files are one level deep (SKILL.md → file, never file → file → file)
- [ ] Skill works when invoked explicitly (`/skill-name`) AND when Claude triggers it from a matching request
- [ ] Companion split applied if total skill content > 300 lines (SKILL.md + FORMAT.md + STATE.md + GOLDEN-RULES.md + INTEGRATION.md)
- [ ] Validation errors include remediation instructions (what's wrong AND how to fix)
- [ ] Final report uses one of the four termination labels above

## Golden rules for skill creation

Hard rules. Never violate these.

1. **SKILL.md is a map.** It tells Claude what to do and where to find details. It does not contain the details itself. If you're writing a code block in SKILL.md, it belongs in a companion file.
2. **Description is discovery, not summary.** Claude picks skills from description alone. If the description summarizes the workflow, Claude follows the description instead of reading the skill body. Describe triggers, not process.
3. **RED before GREEN. No skill ships without a baseline.** If there is no `pressure-tests/baseline.md` recording what a subagent does WITHOUT the skill, the skill is unverified. Delete it. Start over.
4. **Golden rules prevent drift.** Every skill must encode 3-8 hard mechanical rules specific to its domain. Use imperative voice: "Never", "Always", "Must".
5. **Anti-rationalization counter-table is not optional.** Every skill ships with an Excuse → Reality table capturing the exact verbatim excuses observed in RED baseline. Soft rationalizations always resurface under pressure.
6. **Termination labels are a finite enum.** Workflow skills define 3-6 exhaustive labels. Never "done" / "no issues" / "all good" as a label.
7. **Iron-law gates beat gentle reminders.** A rule that says "verify tests pass" is weaker than a gate that refuses to claim completion unless `test-output.txt` exists on disk and matches a pattern. Encode gates, not reminders.
8. **Feedback loops are the product.** A skill without a concrete verification cycle (do → check → diagnose → fix → re-check) is a suggestion, not a skill.
9. **Diagnose, don't retry.** When the agent gets stuck, the skill must tell it how to figure out WHY, not just "try again." Include a symptom → cause → fix table.
10. **Concrete beats abstract.** "Use a clean design" produces slop. "Define CSS variables on `:root`, use `system-ui`, add hover states" produces consistency. Replace every adjective with a specification.
11. **Progressive disclosure saves context.** Only SKILL.md loads on trigger. Companion files load when Claude reads them. Put expensive content in companion files.
12. **Boring technology is better technology.** Prefer composable, stable, well-known tools. Reimplement before wrapping opaque dependencies.
13. **Promote rules from docs to code.** When a documented instruction keeps being violated, encode it as a validation function or structural test, not a stronger-worded paragraph.
14. **If it's not in the skill files, it doesn't exist.** The agent can only see what's in the skill directory. Every constraint must live in the skill files or it will be ignored.

## Anti-rationalization counter-table (for skill authoring)

This counter-table captures excuses observed when agents (and authors) try to skip the discipline of this skill. Every skill produced by `create-skill` must include its own counter-table with excuses specific to that skill's domain.

| Excuse | Reality |
|---|---|
| "Pressure-testing is overkill for this skill." | No skill ships without a RED baseline. 15 min of testing beats hours of agent-rationalized failure in production. Delete the skill and start from Step 2. |
| "I already wrote the skill; I'll test after." | Skill body written before baseline is unverified documentation. Delete it. Run Step 2 first. Start over. |
| "The agent obviously understands this rule." | Obvious to you ≠ obvious under pressure. Run the scenarios anyway. |
| "I'll just add a counter-table row I imagined the agent might say." | Counter-table rows come from observed baseline output, not imagination. Unobserved excuses miss the real rationalizations. |
| "Companion-split is bureaucracy for a short skill." | Under 300 lines: keep it flat. Over 300: split. The split is not optional above the threshold because long SKILL.md bodies get partial-read by Claude. |
| "Termination label `done` is fine, I mean `complete`." | Not fine. The enum must be honest — `complete` means every criterion verified on disk this session. `done` is ambiguous and invites self-approval. |
| "Iron-law gate language is too strict; I'll say `verify and confirm`." | `Verify and confirm` is a reminder. A gate says: "do not advance until `state.stages[i].evidence_files` is non-empty and every listed file exists on disk." Use the gate. |

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
