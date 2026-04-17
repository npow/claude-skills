# Integration Guide

How `/loop-until-done` composes with other skills and what happens when they are not installed.

## Composition Map

| Where | Calls | Why |
|---|---|---|
| Step 5 (per-criterion verification) — optional upgrade | `deep-qa --diff` on the story's file delta | Adds structured defect registry per story instead of trusting the single `verification_command` exit status. Activated when `--critic=deep-qa` is set. |
| Step 7a (spec compliance review) | Selected by `--critic=` | Independent reviewer reads PRD + verification evidence + diff and renders verdict |
| Step 7b (code quality review) | Selected by `--critic=`, separate spawn | Independent reviewer reads diff and renders structural verdict |
| Step 8 (deslop pass) | `oh-my-claudecode:ai-slop-cleaner` (standard mode) | Removes AI-slop patterns (verbose comments, dead branches, over-engineered abstractions) on session file delta |
| Step 8 (post-deslop regression) | Re-runs every story's `verification_command` | Iron-law gate that deslop did not break verified criteria |

## `deep-qa` Integration

### Primary integration: `--critic=deep-qa`

When the run is launched with `--critic=deep-qa`, both reviewer passes in Step 7 run `deep-qa --diff` against the session file delta. Two separate invocations:

- **Step 7a (spec compliance):** invoke `deep-qa --diff --type code` with a metadata hint identifying the PRD path. Deep-qa's critics assess: correctness, error_handling, edge_cases — dimensions that map to "does this satisfy the PRD?"
- **Step 7b (code quality):** invoke `deep-qa --diff --type code` with the code-quality prompt variant. Deep-qa's critics assess: security, testability, maintainability — structural concerns.

Both invocations produce structured defect registries. The coordinator converts the defect registry to the reviewer verdict format:

- If the registry contains ANY `severity: critical` defect: `VERDICT|rejected|<defect count> critical defects`
- If the registry contains only `severity: major` or `minor` defects: `VERDICT|approved|<summary>` (majors/minors are logged as advisory, not blocking)
- If deep-qa itself errored: `VERDICT|rejected|deep-qa-error`, requires manual intervention

The coordinator writes the verdict file to `loop-{run_id}/reviews/spec-compliance-{iter}.md` (and `code-quality-{iter}.md`) with the same structured marker format other reviewers use (see FORMAT.md).

### Secondary integration: per-criterion audit (opt-in)

For very high-stakes runs, the coordinator MAY invoke `deep-qa` inside Step 5 for a specific criterion. This is an opt-in addition, not the default. Triggered by setting `state.json.verification_mode: "deep-qa"` via a config flag (not wired in v1; design hook).

### Falsifiability judge integration

The Step 2b falsifiability judge is a general-purpose agent, not `deep-qa`. Rationale: falsifiability is a schema check on the PRD, not a QA pass on an artifact. Using deep-qa for Step 2b would be overkill and would conflict with deep-qa's artifact-type system (deep-qa expects a real artifact, not a JSON schema).

## `ai-slop-cleaner` Integration (Preserved from OMC)

`/loop-until-done` preserves OMC ralph's deslop pass wholesale — it is a good idea that catches a specific class of defect (verbose AI-generated boilerplate) that neither the spec-compliance reviewer nor the code-quality reviewer targets directly.

### Invocation

Step 8 invokes `oh-my-claudecode:ai-slop-cleaner` with:
- Standard mode (not `--review`) — actually clean, not just report
- Scope bounded to session file delta: the union of all `files_modified` across all `story_passed` events in `progress.jsonl`
- Max files: hard cap at 100 files; beyond that, log a warning and scope to the 100 most-recently-modified
- Output captured to `loop-{run_id}/deslop/cleaner-output-{iter}.md`

### Post-Deslop Regression Gate (Iron-Law)

After deslop runs, re-run EVERY acceptance criterion's `verification_command` (not just the criteria in files the cleaner touched — cleaner changes can have non-local effects). Capture output to `loop-{run_id}/verify/{criterion_id}-{iter}-postdeslop.txt`.

If any criterion that was `passes: true` before deslop now fails:
1. Read the cleaner's diff to isolate which edit introduced the regression
2. Option A: roll back that specific edit (preferred)
3. Option B: fix the regression in place (if the cleaner identified a genuine issue)
4. Re-run the regression gate until post-deslop verification matches pre-deslop
5. Log each cycle in `progress.jsonl` as `post_deslop_regression` events

The coordinator MUST NOT mark the run `all_stories_passed` with a failing post-deslop regression. This is an iron-law gate.

### Opt-out: `--no-deslop`

If the user passes `--no-deslop`:
- Step 8 is skipped entirely
- `state.json.deslop_mode: "skipped_no_deslop"`
- Final summary tags the run as "deslop skipped by user request"
- Post-deslop regression is not required (no deslop = no deslop regression)

Use `--no-deslop` only when the cleanup pass is intentionally out of scope (e.g., for rapid prototyping runs where boilerplate is expected).

## Degraded Mode Matrix

Each integration has a documented fallback when the dependency is not installed.

### `deep-qa` missing

| `--critic` setting | Behavior | Output tag |
|---|---|---|
| `deep-qa` requested but deep-qa missing | Abort with a clear error: "deep-qa is required for `--critic=deep-qa` but not installed. Install deep-qa or re-run with `--critic=architect`." Do NOT silently degrade — the user explicitly asked for deep-qa rigor. | N/A (abort) |
| `architect`, `critic`, or `codex` | No impact — those reviewers don't depend on deep-qa | `verification_mode: "basic"` |

### `oh-my-claudecode:ai-slop-cleaner` missing

| Situation | Behavior | Output tag |
|---|---|---|
| `--no-deslop` NOT set and cleaner missing | Step 8 logs "ai-slop-cleaner not available; skipping deslop pass" and proceeds to Step 9. | `deslop_mode: "skipped_unavailable"` in state.json; final summary flags "deslop pass skipped due to unavailable dependency — run with `oh-my-claudecode:ai-slop-cleaner` installed for cleaner output" |
| `--no-deslop` set | Step 8 skipped regardless | `deslop_mode: "skipped_no_deslop"` |

### `oh-my-claudecode:architect` / `critic` missing

| `--critic` setting | Fallback | Output tag |
|---|---|---|
| `architect` (default) and architect agent missing | Spawn a generic `subagent_type: general-purpose` Sonnet agent with the spec-compliance / code-quality prompt templates from SKILL.md. Separate spawns for 7a and 7b remain mandatory. | `reviewer_mode: "degraded_general_purpose"` |
| `critic` and critic agent missing | Same as above — fall back to general-purpose Sonnet | `reviewer_mode: "degraded_general_purpose"` |
| `codex` and `omc ask codex` unavailable | Abort with a clear error (user explicitly asked for a cross-model opinion) | N/A (abort) |

### `omc ask codex` missing (for `--critic=codex`)

Same as above: user explicitly asked for codex, so aborting is more honest than silently substituting a different reviewer.

## How `/loop-until-done` Is Called By Other Skills

### By `/autopilot` (Phase 3 — QA fix loop)

After deep-qa surfaces defects in Phase 3, autopilot invokes `/loop-until-done` with a synthetic PRD:
- One story per deep-qa defect (priority = defect severity)
- Acceptance criteria derived from deep-qa's `reproduction_steps` field
- `--critic=deep-qa` to re-audit the same dimensions after fixing

This is documented in `/autopilot`'s INTEGRATION.md. From `/loop-until-done`'s side, the behavior is identical — synthetic PRDs still pass through Step 2b falsifiability.

### By `/team` (team-fix stage)

`/team` may invoke `/loop-until-done` for the fix stage when `fix_budget` is exhausted and the remaining defects require sustained iteration. The handoff writes the defect list to a PRD file that `/loop-until-done` reads at Step 2a instead of drafting from scratch.

In this mode, `state.json.config.resume_of` is set to the team run id for auditability.

## Call-Order Diagram

```
User invokes /loop-until-done "task" --critic=deep-qa
          │
          ▼
    Step 0-1: init, read config
          │
          ▼
    Step 2a: planner drafts prd.json                        (Sonnet general-purpose)
          │
          ▼
    Step 2b: falsifiability judge                            (Sonnet general-purpose)
          │ fail? → Step 2c: revise + loop 2a-2c (≤ 3x)
          │
          ▼
    Step 2d: lock PRD (prd_sha256 written)
          │
          ▼
 ┌─ Step 3: pick next story                                  (coordinator, mechanical)
 │        │
 │        ▼
 │    Step 4: executor implements                            (Haiku/Sonnet/Opus)
 │        │
 │        ▼
 │    Step 5: verify each criterion                          (coordinator runs commands,
 │        │                                                    reads captured output)
 │        │  any fail? → Step 4
 │        ▼
 │    Step 6: mark story passed                              (iron-law gate)
 │        │
 └────────┘  loop until all stories passed
          │
          ▼
 ┌─ Step 7a: spec-compliance reviewer                         (deep-qa --diff --type code,
 │                                                              spec-compliance variant)
 │  Step 7b: code-quality reviewer                            (deep-qa --diff --type code,
 │                                                              code-quality variant)
 │        │    (run in parallel, separate spawns)
 │        ▼
 │    Step 7c: gate — both must return VERDICT|approved|
 │        │  either rejected? → increment reviewer_rejection_count, re-queue, Step 3
 └────────┘
          │
          ▼
    Step 8: ai-slop-cleaner on session file delta             (oh-my-claudecode:ai-slop-cleaner)
          │
          ▼
    Step 8b: post-deslop regression (re-run every criterion)  (iron-law)
          │  any regressed? → fix & re-run; loop until green
          │
          ▼
    Step 9: write summary.md, set termination label
```

## Compatibility and Version Pinning

- `deep-qa` — tested with the version in `/Users/npow/.claude/skills/deep-qa/`; requires `--diff` support
- `oh-my-claudecode:ai-slop-cleaner` — tested with OMC plugin `4.10.2`; standard mode behavior
- `subagent_type: oh-my-claudecode:architect` — optional; fallback to general-purpose Sonnet is documented above
- `subagent_type: general-purpose` — always available (built into Claude Code)

When a dependency's format or interface changes, update the relevant section above and bump the fallback behavior. Do NOT silently adapt — a format change that would silently degrade review rigor should abort with an explicit error message pointing at this file.
