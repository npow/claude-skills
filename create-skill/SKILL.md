---
name: create-skill
description: Creates well-structured Claude Code skills from scratch. Use when the user asks to build, design, or scaffold a new skill, slash command, or agent capability. Applies harness engineering best practices — table-of-contents architecture, golden rules, self-review loops, progressive disclosure, and evaluation.
argument-hint: "[skill purpose or domain]"
---

# Create Skill

Build a Claude Code skill that follows harness engineering best practices. The skill must be a map, not a manual — concise entrypoint, structured reference files, hard rules, feedback loops.

## Workflow

1. **Understand the domain** — ask what the skill does, when it should trigger, what tools/output it produces. Do not design until the purpose is clear. See [DESIGN.md](DESIGN.md).

2. **Design the architecture** — decide file structure, what goes in SKILL.md vs reference files. SKILL.md is the table of contents (~50-100 lines of content). Everything else is a reference file. See [DESIGN.md](DESIGN.md).

3. **Write the metadata** — `name` and `description` in YAML frontmatter. The description is the single most important line — it determines when Claude loads the skill. See [WRITING.md](WRITING.md).

4. **Write SKILL.md** — numbered workflow steps (one line each with a pointer to the relevant reference file), self-review checklist, golden rules. No inline code blocks. No long explanations. See [WRITING.md](WRITING.md).

5. **Write reference files** — detailed guidance, code patterns, templates, examples. One file per concern. Keep each under 500 lines. See [WRITING.md](WRITING.md).

6. **Evaluate** — test the skill with real prompts (explicit, implicit, negative). Verify progressive disclosure works. See [EVALUATION.md](EVALUATION.md).

7. **Iterate** — use the skill on a real task. Observe where Claude struggles. Fix the scaffolding, not the symptoms. Re-evaluate.

## Self-review checklist

Before delivering, verify ALL:

- [ ] SKILL.md is under 100 lines of content (excluding frontmatter)
- [ ] SKILL.md has zero inline code blocks (all code is in reference files)
- [ ] `description` is specific, third-person, includes trigger keywords
- [ ] Every reference file is linked from SKILL.md with a one-line summary
- [ ] Golden rules are hard and mechanical (never "consider" or "try to")
- [ ] Self-review checklist exists and is actionable
- [ ] At least one feedback loop encoded (test → verify → fix → re-test)
- [ ] No vague quality language ("clean", "good", "appropriate") — replaced with concrete standards
- [ ] Reference files are one level deep (SKILL.md → file, never file → file → file)
- [ ] Skill works when invoked explicitly (`/skill-name`) AND when Claude triggers it from a matching request
- [ ] Technology choices are boring and well-known (no exotic deps the agent will struggle with)
- [ ] Validation errors include remediation instructions (not just "invalid" — say what's wrong and how to fix)
- [ ] All domain knowledge lives in the skill files (nothing assumed from external context)

## Golden rules for skill creation

Hard rules. Never violate these.

1. **SKILL.md is a map.** It tells Claude what to do and where to find details. It does not contain the details itself. If you're writing a code block in SKILL.md, it belongs in a reference file.
2. **Description is discovery.** Claude picks skills from description alone. If the description doesn't contain the keywords a user would say, the skill won't trigger. Write it as if you're writing a search index entry.
3. **Golden rules prevent drift.** Every skill must encode 3-8 hard mechanical rules specific to its domain. These are the guardrails that keep output consistent across runs. Use imperative language: "Never", "Always", "Must".
4. **Feedback loops are the product.** A skill without a verification step is a suggestion, not a skill. Every skill must have at least one cycle of: do → check → fix. The check must be concrete (run a command, verify a file, inspect output).
5. **Diagnose, don't retry.** When the agent gets stuck, the skill must tell it how to figure out WHY, not just to "try again." Include a failure diagnosis table or triage protocol.
6. **Concrete beats abstract.** "Use a clean design" produces slop. "Define CSS variables on `:root`, use `system-ui` font stack, add hover states to interactive elements" produces consistent output. Replace every adjective with a specification.
7. **Progressive disclosure saves context.** Only SKILL.md loads on trigger. Reference files load when Claude reads them. Put expensive content (long examples, full APIs, code templates) in reference files.
8. **Boring technology is better technology.** Skills must prefer composable, stable, well-known tools and APIs that are well-represented in training data. When a dependency is opaque or brittle, reimplement the needed subset rather than fighting upstream behavior.
9. **Promote rules from docs to code.** When a documented instruction keeps being violated, encode it as a validation function, a structural test, or a linter — not a stronger-worded paragraph. Executable rules enforce themselves. Write error messages that explain what's wrong AND how to fix it so the agent can self-correct.
10. **If it's not in the skill files, it doesn't exist.** The agent can only see what's in the skill directory. Knowledge in external docs, chat threads, or your head is invisible to the system. Every constraint, convention, and pattern must live in the skill files or it will be ignored.

## Reference files

| File | Contents |
|------|----------|
| [DESIGN.md](DESIGN.md) | How to analyze a domain, design file structure, apply progressive disclosure |
| [WRITING.md](WRITING.md) | How to write metadata, SKILL.md body, reference files, golden rules, checklists |
| [EVALUATION.md](EVALUATION.md) | How to test skills with real prompts, positive/negative/implicit cases |
