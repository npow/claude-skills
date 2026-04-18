# Pre-Mortem Blind-Spot Seeding

Shared pattern used by skills that run DFS-style frontier expansion and want to avoid the "optimize-for-the-obvious" failure mode. Before the first round of expansion, spawn one cheap agent whose only job is to imagine the ways the run could miss the important thing.

**Used by:** deep-design (Step 0 pre-mortem), deep-qa (Phase 0e), deep-research (Phase 0e), deep-debug (Phase 0e).

**Not used by:** proposal-reviewer (single-round, not DFS), team (pipeline, not frontier), autopilot (pipeline), loop-until-done (story-by-story).

---

## Why this pattern exists

Frontier-expansion skills anchor on the seed and generate directions that sit "near" it. If the seed itself is miscast, every generated direction inherits the miscast — you get a high-coverage run that missed the real insight. The pre-mortem is an anti-anchoring step: one agent spends ~$0.05 to enumerate how this could all go wrong, and the coordinator auto-seeds the resulting blind spots as `priority=critical` directions in round 1.

The pattern is cheap (1 Haiku agent), catches the biggest failure class (wrong framing), and composes with the rest of the DFS without extra machinery.

---

## The pattern

**Location:** runs immediately after the seed is validated and immediately before round-1 dimension expansion.

**Agent:** 1 Haiku agent, `run_in_background=false` (coordinator blocks until output available; the output feeds directly into round-1 angle generation).

**Cost:** ~$0.05 per run. Runs exactly once, never re-invoked.

**Output:** written to `{run_id}/premortem.md` as a numbered list, one concrete claim per blind-spot angle.

**Coordinator action:** read the file, convert each listed blind spot into a round-1 direction with `priority=critical`. These directions compete with dimension-derived directions in the frontier but get priority scheduling.

---

## Canonical prompt template

```
Given the {seed_type} "{seed}", list {N} concrete ways this {skill_purpose}
could miss the important {outcome_term}.

Cover these angles:
 1. {angle_1_name} — {angle_1_description}
 2. {angle_2_name} — {angle_2_description}
 3. {angle_3_name} — {angle_3_description}
 4. {angle_4_name} — {angle_4_description}
 5. {angle_5_name} — {angle_5_description}

Output to {premortem_path} with one concrete claim per angle.
Each claim must be specific enough that the coordinator can convert it to a research/QA/design direction with a crisp question. "The seed might be wrong" is too vague — "The seed assumes that X is the bottleneck; if the bottleneck is actually Y, every direction in this run is irrelevant" is usable.
```

**Template variables each skill supplies:**
- `{seed_type}`: seed / artifact / bug-report / spec (the skill's unit of input)
- `{seed}`: the verbatim seed/artifact text
- `{skill_purpose}`: research / QA / design / root-cause investigation
- `{outcome_term}`: insight / defect / flaw / root cause
- `{N}`: number of angles, typically 5
- `{angle_1_name}` through `{angle_5_name}`: domain-specific blind-spot categories (see per-skill lists below)
- `{premortem_path}`: `{run_id}/premortem.md`

---

## Per-skill angle lists (domain-specific — stay in each skill's SKILL.md)

The *structure* of the pre-mortem is shared; the *angles* are skill-specific. Each skill keeps its own angle list inline because the angles encode the skill's theory of how runs go wrong.

**deep-research** — 5 research-specific blind spots:
1. Wrong framing — the seed presupposes a conclusion that may be wrong
2. Adjacent-effort blindness — parallel work that would duplicate or invalidate
3. Stale assumption — something assumed true that has changed
4. Baseline blindness — no measurement of what's being "improved"
5. Strategic-timing blindness — planning window / roadmap / executive memo coincidence

**deep-qa** — QA-specific blind spots (suggested; if not already present in deep-qa's Phase 0e, port this list):
1. Silent omission — a critical component mentioned but never specified
2. Unstated invariant — behavior assumed by implementers but not documented
3. Boundary ambiguity — spec wording that two readers could interpret incompatibly
4. Error-path gap — happy path documented; failure response undefined
5. Adversarial surface — security/injection paths not covered by the artifact's stated dimensions

**deep-design** — design-specific blind spots (suggested):
1. Wrong abstraction — the design's primary abstraction obscures rather than clarifies
2. Unstated coupling — two components treated as independent that aren't
3. Upgrade path — the design cannot evolve without rewriting foundational pieces
4. Failure mode — design works when everything works; fails badly under partial failure
5. Operational blindness — no metric / trace / debug story

**deep-debug** — bug-investigation blind spots (suggested):
1. Wrong layer — investigating at the layer where the symptom surfaces, not where the cause lives
2. Reproduction drift — the reproduction differs subtly from the production failure
3. Recent change blindness — a fix in an unrelated area introduced this
4. State history — the bug requires a state transition, not a single state
5. Environmental difference — prod has a condition dev doesn't

Each skill's SKILL.md lists its own 5 angles. The shared file provides the pattern structure; per-skill angles are the skill's theory.

---

## Integration checklist

Before a skill references this pattern, verify:

- [ ] The skill has a DFS / frontier-expansion architecture (if not, this pattern probably doesn't apply)
- [ ] Phase 0 (or equivalent) runs AFTER seed validation but BEFORE round-1 direction generation
- [ ] The skill supplies its own 5 angle names + descriptions
- [ ] `{run_id}/premortem.md` path is written into the skill's directory-structure section
- [ ] Round-1 logic converts each pre-mortem claim to a direction with `priority=critical`
- [ ] State schema has a place to mark pre-mortem-seeded directions (e.g., `directions.{id}.source = "premortem"`) so the coordinator can report coverage of them
- [ ] Pre-mortem runs exactly once per run (not per round); resume does NOT re-run it if `{run_id}/premortem.md` already exists

---

## Common failure modes

**Pre-mortem output too vague.** Claims like "this could be wrong" produce directions that can't be executed. The prompt MUST force concreteness; reject output that doesn't name what specifically is wrong.

**Pre-mortem seeded directions dropped on budget constraint.** If round 1 runs out of agent slots and pre-mortem directions are at the back of the queue, the point is lost. Pre-mortem directions get `priority=critical` so they displace lower-priority dimension angles when the frontier is full.

**Pre-mortem replaces dimension expansion.** The pre-mortem is supplementary — it adds 5 directions before the normal dimension-driven expansion runs. Don't let it become the only seeding mechanism; dimension expansion catches the vast majority of known-unknowns, while pre-mortem targets unknown-unknowns.

**Skipping on resume.** Once `premortem.md` exists, resume uses it as-is. Re-running the pre-mortem on resume wastes budget and produces different angles from the original run, creating churn.
