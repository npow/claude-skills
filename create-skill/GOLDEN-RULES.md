# Golden Rules for Skill Authoring

Fourteen hard rules. Each is stated with a concrete `create-skill` example so there is no ambiguity at the gate.

## 1. SKILL.md is a map, not a manual

**Rule:** SKILL.md names steps and points to files. It never contains the step details.

**Concrete example:**
- Allowed in SKILL.md: `1. **Design the file structure** — decide flat vs companion-split. See [FORMAT.md](FORMAT.md).`
- Forbidden in SKILL.md: any ````language` code block, any multi-paragraph explanation of a single step, any schema definition.

**Detection at review:** grep SKILL.md for ````` markers. Any match is a violation unless it's a schema illustration (< 10 lines) in the companion-file example section.

## 2. Description is discovery, not summary

**Rule:** The description contains trigger keywords and "Use when …" phrasing. It does NOT summarize the workflow — Claude follows description summaries as shortcuts and skips the body.

**Concrete example:**
- Good: `description: Creates well-structured Claude Code skills from scratch. Use when the user asks to build, design, or scaffold a new skill, slash command, or agent capability.`
- Bad: `description: Use when creating skills — runs RED baseline, writes SKILL.md, runs REFACTOR pass.` (summarizes workflow; Claude may skip the body entirely)

**Detection at review:** scan description for verbs that describe the skill's process (`runs`, `spawns`, `executes`, `produces`). If the description describes how the skill works (not when to invoke it), rewrite.

## 3. RED before GREEN — no skill ships without a baseline

**Rule:** `pressure-tests/baseline.md` MUST exist on disk before SKILL.md is written. The baseline file contains verbatim subagent output from the scenarios ran WITHOUT the skill loaded.

**Concrete example:**
- Before writing `SKILL.md`: run a subagent with the user request "build me a TDD discipline skill" + artificial time pressure, without loading the new skill. Record every word the subagent says to `pressure-tests/baseline.md`.
- After: examine the rationalizations. Those become counter-table rows.

**Detection at review:** `ls pressure-tests/` must show `scenarios.md`, `baseline.md`, `with-skill.md`. Any missing file with SKILL.md already written is a violation. Delete SKILL.md. Start over.

## 4. Golden rules prevent drift

**Rule:** Every produced skill has 3-8 domain-specific mechanical rules. Each uses imperative voice and prevents a specific failure mode observed in the baseline.

**Concrete example:**
- If baseline shows the agent saying "tests probably pass, I'll skip running them": add a rule like "Never claim completion without `test-output.txt` showing a green run timestamp from this session."
- Not: "Consider running tests."

**Detection at review:** scan golden rules for soft words (`consider`, `try to`, `prefer`, `should`). Any match is a violation. Rewrite as `Never` / `Always` / `Must`.

## 5. Anti-rationalization counter-table is not optional

**Rule:** Every skill ships with a counter-table with minimum 5 rows (discipline skills) or 3 rows (one-shot generators). Every row quotes an excuse observed in the baseline verbatim (no imagination).

**Concrete example:**
- Baseline logs the agent saying "the validation step is busywork when the code is obviously right."
- Counter-table row: `| "Validation is busywork when the code is obviously right." | Obvious ≠ evidence. Run the validation command and attach its exit code to the completion claim. |`

**Detection at review:** cross-reference every counter-table row against `pressure-tests/baseline.md`. Rows with no trace in baseline are fabricated; remove them and observe real baselines.

## 6. Termination labels are a finite enum

**Rule:** Every workflow skill defines an exhaustive finite set of 3-6 terminal labels. Labels are observable — each has a concrete condition that must be met on disk. `done` / `complete as shorthand` / `no issues` are forbidden as labels.

**Concrete example:**
- `/team` uses: `complete | partial_with_accepted_unfixed | blocked_unresolved | budget_exhausted | cancelled`.
- Every label has a gate: `complete` requires every AC verified green AND zero unresolved critical/major defects — both checked against evidence files on disk.

**Detection at review:** SKILL.md contains a termination label table with explicit conditions. Scan for missing `cancelled` label. Scan for vague labels like `done` / `success`. Replace.

## 7. Iron-law gates beat gentle reminders

**Rule:** A rule that says "verify tests pass" is weaker than a gate that refuses advancement unless a named file exists on disk and matches a pattern. Every completion claim is file-gated.

**Concrete example:**
- Weak: "The agent runs the tests before claiming completion."
- Strong: "Exit gate: `test-output.txt` exists on disk and contains a line matching `Tests: \d+ passed, 0 failed`. If not, do not advance."

**Detection at review:** search the skill body for "verify" / "check" / "ensure" as standalone directives (no concrete file or exit code). Any such occurrence must either get upgraded to a gate, or be rewritten as guidance with a concrete follow-on gate nearby.

## 8. Feedback loops are the product

**Rule:** Every skill encodes at least one do → check → diagnose → fix → re-check cycle. The `check` step is a concrete command or file inspection. The `diagnose` step is a symptom → cause → fix table, not "investigate further."

**Concrete example:**
- Allowed: "Run `npm test`. If failures: read the failing assertion, look up the symptom in FAILURES.md, apply the fix column. Re-run `npm test`."
- Not allowed: "Run tests. Fix any issues. Try again."

**Detection at review:** if failure handling contains the phrase "try again" or "retry," it's hope, not diagnosis. Replace with a symptom → cause → fix table.

## 9. Diagnose, don't retry

**Rule:** Never include "try again" or "retry" as a failure response. Every failure response includes a concrete diagnosis step.

**Concrete example:**
- Template: `| Symptom (observable) | Likely cause | Fix (concrete action) |`
- Catch-all row: `| None of the above | Unknown — log state before and after failing operation, inspect diff |`

**Detection at review:** grep the skill for `retry` / `try again`. Every match is a violation. Rewrite with a diagnosis table row.

## 10. Concrete beats abstract

**Rule:** Replace every subjective adjective with a concrete specification.

**Concrete example:**
- Slop: "Write clean code."
- Concrete: "Functions under 30 lines. No callbacks nested deeper than 2. Variables use `snake_case` in Python, `camelCase` in JavaScript."

**Detection at review:** grep for `clean`, `good`, `appropriate`, `reasonable`, `nice`, `proper`. For each match: either specify the concrete standard or delete the sentence.

## 11. Progressive disclosure saves context

**Rule:** Only SKILL.md loads on trigger. Companion files load when Claude reads them. Put expensive content (long examples, full APIs, code templates) in companion files.

**Concrete example:**
- Allowed in SKILL.md: a 5-row termination label table.
- Forbidden in SKILL.md: a full 200-line state.json schema. That goes in STATE.md.

**Detection at review:** count SKILL.md content lines (excluding frontmatter). Over 150 for a flat skill, or over 200 for a companion-split skill's map — extract content to companion files.

## 12. Boring technology is better technology

**Rule:** Prefer composable, stable, well-known tools. Reimplement over wrapping opaque dependencies.

**Concrete example:**
- Prefer: file-based state (`state.json`), bash for checks, `jq` for JSON queries, `grep` for pattern checks.
- Avoid: exotic state stores, obscure npm packages that drift, MCP-only state tools that make the skill non-portable.

**Detection at review:** for each dependency, ask: is it well-represented in the training corpus? Is the surface area stable? If no: replace with a boring alternative.

## 13. Promote rules from docs to code

**Rule:** When a documented instruction keeps being violated under pressure, encode it as a validation function or a structural test, not a stronger-worded paragraph.

**Concrete example:**
- If REFACTOR pass shows the agent still skipping the counter-table: add a structural test — "Before returning SKILL.md as final, grep for an H2 section containing `Excuse | Reality`. If missing, do not return; rewrite with the counter-table."
- Executable rule > reworded paragraph.

**Detection at review:** if the same rationalization slips through REFACTOR twice, escalate the rule from prose to a concrete gate.

## 14. If it's not in the skill files, it doesn't exist

**Rule:** The agent can only see what's in the skill directory. Slack conversations, external docs, team norms — all invisible. Every constraint must be in a skill file.

**Concrete example:**
- Allowed: "The counter-table format is defined in FORMAT.md section 8."
- Forbidden: "Follow team convention for counter-table format." (invisible to the agent)

**Detection at review:** scan the skill for references to external context ("team convention", "as we discussed", "standard practice"). Replace each with an inline spec or a file pointer.

## Anti-rationalization counter-table (full set for skill authoring)

The SKILL.md carries a tight 7-row version of this table. The full set lives here.

| Excuse | Reality |
|---|---|
| "Pressure-testing is overkill for this skill." | No skill ships without a RED baseline. Step 2 is non-negotiable. Delete SKILL.md and start over. |
| "I already wrote the skill; I'll test after." | Skill body written before baseline is unverified documentation. Delete it. Run Step 2 first. |
| "The agent obviously understands this rule." | Obvious to you ≠ obvious under pressure. Run the scenarios anyway. |
| "I'll add a counter-table row I imagined the agent might say." | Counter-table rows come from observed baseline output, not imagination. |
| "Companion-split is bureaucracy for a short skill." | Under 300 lines total: keep it flat. Over 300: split. Not optional above the threshold. |
| "Termination label `done` is fine, I mean `complete`." | `done` is ambiguous. Enum must be honest. `complete` requires observable conditions on disk. |
| "Iron-law gate language is too strict; I'll say `verify and confirm`." | `Verify` is a reminder. A gate refuses advancement unless a named file exists with a matching pattern. Use the gate. |
| "I don't have time for RED baseline right now." | Tag the final report `shipped_degraded` with `reason: skipped pressure testing`. The user will see it. |
| "The counter-table is getting long; I'll skip some." | Length is a feature. Skipped rows become real rationalizations in production. Keep all observed rows. |
| "Two companion files feel redundant; I'll merge them." | Each companion file has a distinct job. Merging them causes partial reads. Keep the split. |
| "The description is clear enough; I don't need every keyword." | Claude searches description for match. Missing keywords = missing invocations. Add every synonym a user might type. |
| "I know what failure modes the agent will hit." | You know after baseline, not before. Run RED. |
| "This skill is an exception because it's so simple." | Simple skills break too. 15 min of baseline beats hours of debugging an un-pressure-tested skill. |
| "`deep-qa` isn't installed so I'll skip the skill review." | INTEGRATION.md documents the degraded-mode fallback. Use it. Tag output with `SKILL_REVIEW: degraded`. |
| "I'll re-use OMC's skill structure because it's fine." | OMC and npow have different philosophies. Audit which parts apply to a npow-style skill before copy-paste. |

## Red flags — STOP and start over

If any of these are true, stop the current skill and restart from Step 2 of the workflow:

- No `pressure-tests/` directory exists.
- `pressure-tests/baseline.md` is missing or empty.
- SKILL.md was written before `baseline.md` existed.
- The counter-table was filled in with imagined rationalizations, not observed ones.
- Termination labels include `done` / `no issues remain` / `all good`.
- Any completion claim in the skill body uses "verify" / "ensure" / "check" as the actual gate (not backed by a concrete file/exit-code check).
- Description summarizes the workflow instead of naming trigger conditions.
- Reference files reference each other (forbidden — one level deep only).

Red flag present → delete the offending files → return to the workflow step that produces them.
