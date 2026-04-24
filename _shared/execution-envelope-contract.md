# Execution-Envelope Contract (Shared)

A **skill** describes an algorithm (the *what*). An **envelope** is the runtime that executes the algorithm (the *where*). Direction-C architecture says: one SKILL.md per algorithm; envelope is a switch, not a separate skill.

**Used by:** loop-until-done, team, autopilot, deep-plan, deep-design, deep-qa, deep-research, deep-debug, proposal-reviewer, flaky-test-diagnoser, hello-world.

---

## The two envelopes

### In-session envelope

The coordinator is Claude in the current CC conversation. It spawns subagents via the `Agent` tool. It writes state to `~/.claude/runs/<skill>/<run_id>/` (or skill-specific paths). Session death = workflow death. Resume-on-reload is best-effort (read last state file, decide whether to resume).

**Correct when:**
- Algorithm fits in a single CC session (≲ 2 hours real-time, ≲ 500k tokens context budget)
- User wants to watch progress and intervene
- Output fidelity is the critical quality signal (user is in the loop)

**Primitives it uses:**
- `Agent` tool for subagent spawns
- `TaskCreate` / `TaskUpdate` for progress
- `Monitor` for long-lived tails
- Files under the user's CWD or `~/.claude/`

### Durable envelope

The coordinator is a Temporal workflow running on the sagaflow worker daemon. Activities call out to Claude (either in-process via Anthropic API, or spawn `claude -p --bare` subprocesses). State persists in `~/.sagaflow/state/<run_id>/`. Session death ≠ workflow death — the workflow keeps running on the worker.

**Correct when:**
- Algorithm runs for > 2 hours OR may exceed a single session's context budget
- User wants fire-and-forget (no intervention required)
- The mission is long enough that observing the outcome matters more than watching progress
- Multiple workflows must run in parallel without competing for one Claude session

**Primitives it uses:**
- Temporal activities for spawns (registered by sagaflow)
- `sagaflow launch <workflow-name>` as the submit API
- `~/.sagaflow/INBOX.md` for completion notifications
- `~/.sagaflow/runs/<run_id>/` for artifacts (equivalent to per-run state dir)

---

## The contract — a skill with both envelopes MUST

1. **Own one `SKILL.md`** describing the algorithm in envelope-agnostic language.
2. **Include a `## In-session execution` section** explaining how to invoke when the coordinator is Claude in-session. For many algorithms this is the body of the skill's existing SKILL.md.
3. **Include a `## Durable execution` section** explaining how to invoke via sagaflow: the `sagaflow launch <name>` command, the inputs, the output location, how to monitor, how to cancel.
4. **Route envelope choice by flag or auto-heuristic** — e.g. `/loop-until-done` runs in-session; `/loop-until-done --durable` runs on sagaflow. The skill documents which is default; the documentation must not present the envelope choice as "two different skills."
5. **Share prompts** — both envelopes read the same prompt files (e.g. `<skill>/prompts/prd-system.txt`). The in-session coordinator inlines prompts into `Agent` calls; the durable workflow passes prompts as activity inputs. Prompt drift between envelopes is a bug.
6. **Share termination-label vocabulary** — the set of honest termination labels is a property of the algorithm, not the envelope. Both envelopes emit labels from the same enum.

---

## The contract — a skill with only one envelope

Some algorithms only make sense in one envelope:

- **parallel-exec** — in-session only. Its value is watching many subagents finish in a single session. A durable variant adds nothing.
- **loop** (scheduler) — in-session only. It schedules within a session; durable scheduling is what cron is for.
- **slack-reply, debug-pr, google-*, ccr-***  — in-session only. Short tasks, tool-heavy, no need for durability.
- **ship-it** — currently in-session; a durable variant is viable future work.

Single-envelope skills OMIT the `## Durable execution` section entirely. They do not get a phantom `-temporal` doppelganger.

---

## Migration from current state (pre-Direction-C)

**Current state:** each skill that has both envelopes is split into two directories: `<name>/` (in-session SKILL.md + prompts) and `<name>-temporal/` (launcher SKILL.md + Python workflow module).

**Target state:**
- `<name>/SKILL.md` — algorithm + both envelope sections
- `<name>/prompts/` — shared prompt files
- `<name>/durable/` — Python workflow module (moved from `<name>-temporal/`), registered by sagaflow
- `<name>-temporal/` directory deleted

**Transitional compatibility:** the `<name>-temporal` entry in Claude's skill catalog is retired, but existing `sagaflow launch <name>` invocations continue to work (registry points at the new `<name>/durable/workflow.py`). See `ADR-001-single-substrate.md` for the cutover plan.

---

## Common failure modes

- **Envelope drift** — updates to the algorithm land in `<name>/SKILL.md` but the `<name>-temporal/` workflow.py silently diverges. Direction-C fixes this by unifying the home directory.
- **Prompt drift** — in-session coordinator inlines a prompt; durable workflow reads an older copy from `prompts/`. Both envelopes MUST read from `prompts/` at run time.
- **Label drift** — in-session termination uses the label "complete"; durable uses "all_stories_passed". Same algorithm → same labels. Document the enum in the algorithm section.
- **Hidden envelope coupling** — a step in the algorithm that only works in-session (e.g. "open a browser to verify the UI"). Flag these explicitly as "in-session only" and have the durable envelope emit `envelope_incompatible_step` rather than silently skipping.

---

## Integration checklist for a skill adopting this contract

- [ ] SKILL.md has a one-line cross-reference near the top: `See [_shared/execution-envelope-contract.md](../_shared/execution-envelope-contract.md) for envelope semantics.`
- [ ] Algorithm is described in envelope-agnostic language — nothing like "the coordinator uses the Agent tool" in the main body; envelope-specific verbs go in the envelope sections.
- [ ] `## In-session execution` section exists or the skill declares itself single-envelope with reason.
- [ ] `## Durable execution` section exists or the skill declares itself single-envelope with reason.
- [ ] Prompts live in `prompts/` and are read by both envelopes at run time (not inlined differently).
- [ ] Termination labels are declared once; both envelopes emit from that enum.
- [ ] In-session-only steps are explicitly flagged.
