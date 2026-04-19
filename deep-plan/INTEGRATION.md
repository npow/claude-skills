# Integration

How `/deep-plan` composes with other skills and how it falls back when optional tooling is unavailable.

## Upstream: Called by `/autopilot` Phase 1

`/autopilot` Phase 1 (Plan) delegates to `/deep-plan` instead of re-implementing the Planner/Architect/Critic loop inline. Invocation contract:

```
/autopilot spawns /deep-plan as a subprocess-equivalent with:
  - CWD containing autopilot-{run_id}/phase-1/
  - Task description written to phase-1/task.md (copied from Phase 0 output)
  - Flags: --max-iter N (default 5), --deliberate if Phase 0 flagged risk, --interactive never (autopilot is non-interactive by default)
```

`/deep-plan` writes its own subdirectory `phase-1/deep-plan-{run_id}/` and returns the final `plan.md` + `adr.md` + termination label via file path. `/autopilot` reads the termination label from the deep-plan `state.json` — does not re-run the consensus logic.

`/autopilot` Phase 2 (Exec) handoff:
- If `termination.label == consensus_reached_at_iter_N` → proceed to Phase 2 with the final `plan.md`.
- If `termination.label == max_iter_no_consensus` → Phase 1 returns `blocked_at_phase_1`; autopilot stops unless `--accept-no-consensus` flag is set by the caller (off by default).
- If `termination.label` is any `*_unparseable_*` or `*_spawn_failed_*` → Phase 1 returns `blocked_at_phase_1`; autopilot surfaces the failure and halts.

## Downstream: Hands off to `/team` or `/loop-until-done`

Only triggered in `--interactive` mode after user approval at Step 7. `/deep-plan` does NOT auto-execute.

```
User chooses "Approve and implement via team":
  → invoke Skill("/team") with plan_path=deep-plan-{run_id}/plan.md
User chooses "Approve and execute via loop":
  → invoke Skill("/loop-until-done") with plan_path=deep-plan-{run_id}/plan.md
```

Both downstream skills must accept:
- `plan_path` — absolute path to the final `plan.md` (carries acceptance criteria with `verification_command` per row).
- `adr_path` — absolute path to `adr.md` for handoff-doc quality.
- `consensus_metadata` — the comment-block header in plan.md (termination label, iteration count, degraded-mode flags).

## External Provider Support

`--architect codex`, `--critic codex`, `--critic gemini` replace the default Claude Agent spawn with an external CLI call.

### Codex invocation (architect or critic)

```bash
# Architect
codex --agent-prompt architect \
      --input-file deep-plan-{run_id}/iterations/iter-{N}/architect-input.md \
      --output-file deep-plan-{run_id}/iterations/iter-{N}/architect-verdict.md \
      --timeout 180

# Critic
codex --agent-prompt critic \
      --input-file deep-plan-{run_id}/iterations/iter-{N}/critic-input.md \
      --output-file deep-plan-{run_id}/iterations/iter-{N}/critic-verdict.md \
      --timeout 180
```

The input file contains ALL prompt content (the same prompt template used for Claude Agent, rendered with paths resolved). The CLI is expected to read-from-paths and write-to-paths per our file-I/O contract.

### Gemini invocation (critic only)

```bash
gemini chat --system-prompt-file critic-system.md \
            --input-file deep-plan-{run_id}/iterations/iter-{N}/critic-input.md \
            --output-file deep-plan-{run_id}/iterations/iter-{N}/critic-verdict.md \
            --timeout 180
```

The Critic system prompt is provided via a file the skill generates at run start (`critic-system.md`) rather than via CLI args, to preserve the full adversarial-mandate prompt.

### Detection order

1. Check `which codex` (or `which gemini`) in PATH.
2. Run the CLI with `--version` (timeout 5s). Non-zero exit → unavailable.
3. If unavailable, fall back to default Claude Agent spawn and tag the verdict with `architect_mode: "degraded"` or `critic_mode: "degraded"` in the structured output AND in `state.json`.
4. Surface the degraded-mode fallback in the final plan's metadata header and in the coordinator's final summary.

### Output format contract (all providers)

External CLIs MUST produce output matching the structured format in FORMAT.md. If an external CLI produces text without `STRUCTURED_OUTPUT_START/END` markers:
- First failure → re-spawn once using the default Claude Agent (not the external CLI — the CLI is now known-broken for this call).
- Second failure → mark `unparseable` and terminate iteration with the appropriate `*_unparseable_at_iter_N` label.

## Degraded Modes

`/deep-plan` core logic requires only the Claude Agent tool and file I/O. It has no hard dependency on `deep-design`, `deep-qa`, Codex, Gemini, or any MCP state tools. The following degraded modes are documented:

| Condition | Behavior | Tag in output |
|---|---|---|
| `codex` requested but not installed/broken | Fall back to Claude Agent with same prompt template | `architect_mode: "degraded"` or `critic_mode: "degraded"` |
| `gemini` requested but not installed/broken | Fall back to Claude Agent | `critic_mode: "degraded"` |
| No `state_write` MCP tool | Use plain `Write` tool for `state.json` | No tag — file-based state is the default contract |
| `/team` not installed at user approval (interactive) | Offer only "execute via loop" option; if `/loop-until-done` also missing, offer only "output plan and stop" | Surfaced at the interactive gate |
| `/loop-until-done` not installed at user approval (interactive) | Same symmetrical fallback | Surfaced at interactive gate |
| Run invoked with no `/autopilot` context | Standalone mode; resume via on-disk `state.json` | Default path, no special handling |

### Degraded-mode final-summary example

```
# Consensus Plan Complete
Run: 20260416-153022
Termination: consensus_reached_at_iter_3
Iterations: 3

Warnings:
- Architect mode: degraded (codex CLI not available in PATH; fell back to Claude Agent for iterations 1-3)
- 2 Critic rejections were dropped by the falsifiability gate (rubber-stamp phrases)

Final plan: deep-plan-20260416-153022/plan.md
ADR: deep-plan-20260416-153022/adr.md
```

## Optional Integration: `deep-design`

`/deep-plan`'s Architect pass is architectural review. If `deep-design` is installed, callers can optionally run `deep-design` on the Planner's output BEFORE invoking `/deep-plan` — this is a pre-step, not an internal dependency. `/deep-plan` does NOT auto-invoke `deep-design`. The distinction:

- `deep-design` adversarially stress-tests a *design concept* over many rounds with dozens of critics.
- `/deep-plan` runs a *fixed* 3-role loop on a *plan* to reach consensus.

They are orthogonal. A caller doing architecture-heavy work should run `deep-design` first to harden the design, then `/deep-plan` to produce the ADR-backed implementation plan.

## Optional Integration: `deep-qa`

Not invoked by `/deep-plan`. The output plan's `verification_command[]` fields are consumed by `/team`'s verify stage or `/loop-until-done`'s per-story verification, where `deep-qa` may be the chosen verifier. `/deep-plan` is responsible only for producing the plan with verification commands; it does not run them.

## Tool Expectations

`/deep-plan` uses only these primitives:

- **Write** — state.json, plan inputs, feedback bundles, final plan copy, ADR copy, logs
- **Read** — reading prior iteration files for feedback assembly
- **Task** (subagent_type="general-purpose") — Planner, Architect (default), Critic (default), ADR Scribe
- **Bash** — optional, only for launching external CLIs (`codex`, `gemini`) and for checking CLI availability

No hard dependency on MCP state tools, TeamCreate/TaskList, or OMC-specific infrastructure. The skill runs in plain Claude Code.

## Invocation Examples

### Autonomous (non-interactive)
```
/deep-plan "Migrate user auth from passport.js to JWT with rotation"
```

### Interactive gates enabled
```
/deep-plan --interactive "Migrate user auth from passport.js to JWT with rotation"
```

### Deliberate mode forced (high-risk)
```
/deep-plan --deliberate "Design data-migration for users table with 500M rows"
```

### External providers
```
/deep-plan --architect codex --critic gemini "Refactor the order-processing pipeline for idempotency"
```

### Max-iteration override
```
/deep-plan --max-iter 3 "Add rate limiting to the public API"
```

### Downstream handoff (via `/autopilot`)
```
/autopilot "Implement two-factor auth"
  → Phase 0: spec / deep-design
  → Phase 1: /deep-plan (called internally)
  → Phase 2: /team
  → Phase 3: deep-qa --diff
  → Phase 4: 3 independent judges
```
