# Output Format

The canonical template for every skill produced by `create-skill`. This document defines the MANDATORY sections of a produced skill's SKILL.md and its companion files. Every section here is required — not suggested.

## Decision: flat skill or companion-split skill

| Total skill content | Shape |
|---|---|
| Under 300 lines (all files combined) | Flat: SKILL.md + 1-3 topic files (e.g. DESIGN.md, WORKFLOW.md) |
| 300+ lines total | Companion-split: SKILL.md + FORMAT.md + STATE.md + GOLDEN-RULES.md + INTEGRATION.md |

The companion split is the npow orchestration pattern. Use it whenever a skill does multi-stage work, state persistence, or external-skill composition.

## Flat skill template

```
<skill-name>/
├── SKILL.md                 # ≤100 lines content, see "SKILL.md sections" below
├── <TOPIC-A>.md             # reference file, ≤500 lines
├── <TOPIC-B>.md             # reference file, ≤500 lines (optional)
└── pressure-tests/
    ├── scenarios.md         # 3-5 pressure scenarios (authored BEFORE SKILL.md)
    ├── baseline.md          # RED: verbatim subagent output without the skill
    └── with-skill.md        # GREEN/REFACTOR: verbatim subagent output with the skill
```

## Companion-split skill template

```
<skill-name>/
├── SKILL.md                 # lean map — workflow, golden rules, counter-table, labels, file index
├── FORMAT.md                # output formats for every artifact the skill produces
├── STATE.md                 # state.json schema, resume protocol, pre-transition gate checks
├── GOLDEN-RULES.md          # consolidated rules with per-rule concrete examples + counter-table
├── INTEGRATION.md           # composition with deep-qa, deep-design, degraded-mode fallbacks
└── pressure-tests/
    ├── scenarios.md
    ├── baseline.md
    └── with-skill.md
```

## SKILL.md sections (mandatory in every skill)

Every produced SKILL.md has these sections in this order. No section may be omitted.

### 1. YAML frontmatter

- `name`: lowercase letters, numbers, hyphens. Max 64 chars.
- `description`: third-person, "Use when …" phrasing, includes trigger keywords, does NOT summarize workflow.
- `argument-hint` (optional): one-line hint for what to type after the skill name.

Keyword coverage: list the exact words a user would say. If the skill is for "creating an API client," include "create", "scaffold", "generate", "build" — all the synonyms.

### 2. Title + one-line purpose statement

```markdown
# <Skill Name>

One sentence: what this skill does and its core mechanism.
```

### 3. Execution Model (workflow skills only)

A bulleted list of non-negotiable contracts. Each bullet is a hard rule that applies to every invocation. Typical entries:

- All data passed to agents via files, never inline.
- State written before agent spawn.
- Structured output is the contract; free-text is ignored.
- No coordinator self-approval of load-bearing claims.
- Iron-law pre-transition gate.
- Honest termination labels (enumerated).

Flat one-shot skills may skip this section.

### 4. Workflow

Numbered steps, one line each. Each step: bold verb phrase → em-dash → one-line description → link to the reference file with the detail.

```markdown
## Workflow

1. **Verb phrase** — brief description. See [FILE.md](FILE.md).
2. **Verb phrase** — brief description. See [OTHER.md](OTHER.md).
```

5-12 steps. Fewer means the skill is trivial. More means it needs splitting.

### 5. Honest termination labels (workflow skills only)

A finite enum table. Every invocation of the skill terminates with exactly one label.

```markdown
## Honest termination labels

| Label | Meaning |
|---|---|
| `<label_1>` | <concrete condition that must be met> |
| `<label_2>` | <concrete condition that must be met> |
| ... |
```

Minimum 3 labels. Maximum 6. One must be `cancelled`. Every label has a concrete, observable condition. Never `done`, `all good`, `no issues remain` as a label.

Flat one-shot skills may omit this section if they don't make completion claims. Otherwise, required.

### 6. Self-review checklist

Checkbox list. Every item is objectively verifiable (yes/no without judgment).

```markdown
## Self-review checklist

Before delivering, verify ALL:

- [ ] <concrete, observable condition>
- [ ] <concrete, observable condition>
```

6-15 items. Items like "code is clean" are forbidden. Items like "No console errors during a full run" are required shape.

### 7. Golden rules

3-8 hard mechanical rules specific to this skill. Imperative voice ("Never", "Always", "Must"). Each rule prevents a specific failure mode observed in the RED baseline.

```markdown
## Golden rules

Hard rules. Never violate these.

1. **<Rule name>.** <Imperative explanation.>
2. **<Rule name>.** <Imperative explanation.>
```

### 8. Anti-rationalization counter-table

MANDATORY. Excuses captured verbatim from the RED baseline, paired with concrete realities.

```markdown
## Anti-rationalization counter-table

| Excuse | Reality |
|---|---|
| "<verbatim excuse from baseline>" | <specific action the agent must take instead> |
| "<verbatim excuse from baseline>" | <specific action the agent must take instead> |
```

Minimum 5 rows for discipline-enforcing skills. Minimum 3 rows for one-shot generators. Every row references a real excuse, not invented.

### 9. Reference/companion file index

A table listing every other file in the skill directory.

```markdown
## Reference files

| File | Contents |
|------|----------|
| [FILE.md](FILE.md) | One-line summary |
```

## Companion file templates

### FORMAT.md

For every output artifact the skill produces: the exact schema. Example from `/team`:

- Handoff schema
- Acceptance criterion schema
- Verdict file schema (`STRUCTURED_OUTPUT_START` / `END` markers, required fields)
- State file schema

Each section shows a copy-paste template with required fields marked.

### STATE.md

The runtime state of a skill invocation:

- `state.json` schema with every field typed
- `generation` counter semantics
- Pre-transition gate checks (the iron-law gate — concrete file-existence checks)
- Resume protocol (how to replay from the last completed stage by reading `state.json`)
- Invariant checks run on every gate transition

### GOLDEN-RULES.md

Expanded golden rules. Each rule gets:

- Rule statement
- Concrete examples specific to this skill
- Detection criteria at review (how to spot a violation in the state file or artifacts)

Plus the full anti-rationalization counter-table with more rows than SKILL.md carries (SKILL.md has a tight 5-7 row version; GOLDEN-RULES.md carries the full set).

### INTEGRATION.md

How this skill composes with other skills:

- Which skills it can invoke (`deep-qa`, `deep-design`, `/spec`, `/loop-until-done`, etc.)
- The invocation contract for each (input files, output directory, expected structured output)
- Degraded-mode fallback for when the external skill isn't installed — what the skill does instead, and what quality tag the output carries (`VERIFICATION_MODE: degraded`)

## Iron-law verification gate language (mandatory wording)

Any produced skill that makes completion claims must use this exact pattern of language, adapted to the skill's domain. Do NOT use soft words like "verify" or "check" — use "gate" and "evidence on disk."

Example wording template:

```markdown
**Exit gate (all must pass):**

- `<path-to-evidence-file-1>` exists and parses against the FORMAT.md schema.
- `<path-to-evidence-file-2>` has `<structured marker>` with `VERDICT: approved` inside structured markers.
- `state.stages[<i>].evidence_files = [<list of paths>]`.

If exit fails: do not transition. <Concrete remediation: e.g., re-spawn X with rejection reasons as input>.
```

Every completion claim is gated by file-existence checks on disk. Never by the coordinator's own reading of events.

## Pressure-tests directory (mandatory for every produced skill)

Every produced skill has a `pressure-tests/` directory with three files:

- `scenarios.md` — 3-5 scenarios, each with (setup, user prompt, pressure type, expected compliant behavior, failure mode)
- `baseline.md` — RED verbatim output of a subagent running the scenarios WITHOUT the skill loaded
- `with-skill.md` — GREEN/REFACTOR verbatim output of a subagent running the same scenarios WITH the skill

See PRESSURE-TESTING.md for the protocol.
