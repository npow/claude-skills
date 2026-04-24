# ADR-001: Single Durable Substrate — Finish Absorbing swarmd into sagaflow

**Status:** in progress (most phases already executed)
**Date:** 2026-04-23 (original); revised 2026-04-23 after verification
**Deciders:** npow
**Supersedes:** none

---

## Context

Two Temporal-backed durable execution systems ran in parallel historically:

| | Sagaflow | Swarmd |
|---|---|---|
| Code root | `/Users/npow/code/skillflow/sagaflow` | `/Users/npow/code/research/swarm/swarmd` |
| Worker binary | `sagaflow worker` | `swarm worker` |
| State dir | `~/.sagaflow/` | `~/.swarm/` |
| Architecture | Workflow registry | Single-mission interpreter |

An absorption effort has been partially completed:

- `sagaflow.missions` package exists and contains ~all of `swarmd.durable.*` + `swarmd.schemas.*` + parts of `swarmd.classifier.*` + `swarmd.lib.llm_client`. See `sagaflow/missions/__init__.py` docstring: *"Absorbed from swarmd (the standalone swarm orchestrator) into sagaflow."*
- `sagaflow.worker.build_extra_workflows()` imports `MissionWorkflow, PatternDetectorWorkflow, LLMCriticWorkflow, ResourceMonitorWorkflow` from `sagaflow.missions` and registers them.
- `sagaflow.worker.build_mission_activities()` imports 18 mission activities (anticheat, criterion check, completion judge, invariant enforcement, subagent spawn, etc.) and registers them.
- `sagaflow.cli` has `sagaflow mission launch|status|abort` subcommands (cli.py:388-486).

What remains prevents full consolidation.

## Decision

**Finish the absorption: cut `/swarm` over to `sagaflow mission launch`, fill in the lib/hooks/mcp gaps that were left behind, then decommission the standalone swarmd worker + CLI.**

## Current state — what's done

| Claim | Evidence |
|---|---|
| `sagaflow.missions` package exists | `/Users/npow/code/skillflow/sagaflow/missions/` present with `__init__.py`, `activities/`, `classifier/`, `lib/`, `schemas/`, `specialists/`, `state.py`, `workflow.py`, `errors.py`, `retry_policies.py` |
| Sagaflow worker registers mission workflows | `worker.py:215-230` imports + extends `extras` with 4 workflow classes |
| Sagaflow worker registers mission activities | `worker.py:235-281` builds list of 18 activities |
| Sagaflow CLI has mission subcommands | `cli.py:388` `# mission subcommands — absorbed from swarmd CLI`; three commands wired |
| `sagaflow.missions` imports are used | `worker.py` + `cli.py` both import from `sagaflow.missions.{workflow, specialists, activities, schemas, retry_policies}` |

## Current state — what's NOT done

1. **`/swarm` command still routes to swarmd, not sagaflow.** `commands/swarm.md:100` has `from swarmd.schemas.mission import Mission` for YAML validation. `commands/swarm.md:139` launches via `/Users/npow/code/research/swarm/.venv/bin/swarm launch`. Status/abort/findings calls all use the `swarm` CLI. **A cutover attempt on 2026-04-23 was reverted** after smoke-testing exposed [blocker B1](#blockers-from-cutover-attempt).

2. **`swarmd.lib` partially ported.** `swarmd/lib/` has 12 files; `sagaflow/missions/lib/` has 1 (`llm_client.py`). Missing: `criteria_templates.py, hashing.py, heartbeat.py, ids.py, interventions.py, launcher_liveness.py, locking.py, notify_os.py, paths.py, status.py, transcript.py`. Status of each unknown — some may be dead code on swarmd already; others may be load-bearing for mission workflows on sagaflow.

3. **`swarmd.hooks` not ported.** Contains `user_prompt_submit.py` (UserPromptSubmit Claude-Code hook) plus two shell hooks (`post_tool_use_track_files.sh`, `stop_regression_check.sh`). These may be swarm-CLI-adjacent user hooks unrelated to the Temporal workflow itself — verify before porting.

4. **`swarmd.mcp` not ported.** An MCP server directory. Unknown whether it's load-bearing for missions or a separate swarm-facing MCP surface.

5. **Two Temporal workers still running.** swarmd worker polls task queue `"swarm"`; sagaflow worker polls a different queue (`TASK_QUEUE` in `sagaflow.temporal_client`). Even though sagaflow CAN run missions, submissions made via `swarm launch` land on the swarmd worker.

6. **sagaflow environment missing `pyyaml`.** `sagaflow mission launch` immediately errors with `ModuleNotFoundError: No module named 'yaml'` on a vanilla install. Fixed in this session by `/opt/nflx/python3.11 -m pip install --user --break-system-packages pyyaml` but should be a proper install dependency in `sagaflow/pyproject.toml`. See [blocker B2](#blockers-from-cutover-attempt).

7. **`-temporal` skill directories still present.** `hello-world-temporal`, `deep-qa-temporal`, …, `autopilot-temporal` — 11 dirs that sagaflow's `build_registry()` loads via the `_DIR_TO_LEGACY` map in `worker.py:64-76`. These contain the Python workflow modules; the non-temporal `<name>/` dirs are SKILL.md only. Collapse into `<name>/durable/` is independent of swarmd decommission and orthogonally useful.

## Consequences

### After finish-absorption

- One worker polling one queue. `swarm worker` binary no longer needed.
- `/swarm` continues to be the user-facing entry point for criteria-poll-hold-window missions, but routes via `sagaflow mission launch`.
- `~/.swarm/` no longer written to (historical only).
- Skill catalog still has 11 `-temporal` dirs unless the orthogonal Phase 4 is also done; that's the user-facing cleanup.

### Retained tradeoffs

- `/swarm`'s preflight chain (brainstorming → deep-design → writing-plans → criteria rigor linter) stays.
- `swarmd.lib` gaps: porting adds maintenance surface; NOT porting risks sagaflow missions being quietly incomplete. Each missing module needs a triage pass.

## Alternatives considered

### A. Leave it partially-absorbed
Rejected. Two workers, two state dirs, user invokes `/swarm` → swarmd path. The duplicate code exists on both sides and drifts. The whole point of the absorption was to consolidate; finishing it is cheap relative to continuing to maintain both.

### B. Revert the absorption (remove `sagaflow.missions`)
Rejected. The absorbed code is the current target; reverting would throw away committed migration work.

### C. Fold sagaflow INTO swarmd instead (other direction)
Rejected. Sagaflow has a skill registry + 11 skills; swarmd has a single generic workflow. Inverting the absorption requires either (a) rebuilding the registry inside swarmd, or (b) reimplementing every skill as a mission template. Both are strictly more work than finishing the current direction.

---

## Cutover plan — remaining phases

### Phase 1: triage `swarmd.lib` gaps

For each missing module in `swarmd/lib/` (criteria_templates, hashing, heartbeat, ids, interventions, launcher_liveness, locking, notify_os, paths, status, transcript):
- `grep -rn "from swarmd.lib.<mod>" /Users/npow/code/research/swarm/` → is it used inside swarmd?
- `grep -rn "from swarmd" /Users/npow/code/skillflow/sagaflow/` → is sagaflow.missions already importing it?
- If used in swarmd AND not in sagaflow.missions → port into `sagaflow.missions.lib.<mod>`
- If unused in swarmd → leave as-is; swarmd is going away anyway

**Verification:** any mission activity sagaflow doesn't already import from `swarmd.lib.*` is either unused or ported. No swarmd-import left in sagaflow runtime code paths.

### Phase 2: verify `swarmd.hooks` and `swarmd.mcp` scopes

- `hooks/user_prompt_submit.py`: is this installed into the user's `~/.claude/settings.json`? If so, it runs in Claude-Code (not in the worker) — likely unrelated to mission execution. If it runs inside the worker, port.
- `hooks/*.sh`: same question — inspect how they get invoked.
- `swarmd/mcp/`: read `__init__.py` to see what it exports. If it's a dev-time MCP server offering mission inspection, port only if useful in sagaflow; otherwise leave.

**Verification:** every swarm component either has a known sagaflow home OR is documented as "not needed post-decommission."

### Phase 3: rewrite `/swarm` to route via sagaflow

Edit `/Users/npow/.claude/commands/swarm.md`:
- Line 8: `Launcher: Temporal-backed swarm CLI at /Users/npow/code/research/swarm/.venv/bin/swarm` → `Launcher: sagaflow mission subcommand`
- Line 15: `/Users/npow/code/research/swarm/.venv/bin/swarm worker` → `sagaflow worker run`
- Line 100: `from swarmd.schemas.mission import Mission` → `from sagaflow.missions.schemas.mission import Mission`
- Line 111: linter path `/Users/npow/code/research/swarm/lint_criteria.py` → verify equivalent exists in sagaflow or port it
- Line 131: `swarm health` → `sagaflow health`
- Line 139: `swarm launch <yaml>` → `sagaflow mission launch <yaml>`
- Steps 5 (report + monitor): `swarm status|findings|abort` → `sagaflow mission status|abort` (plus sagaflow equivalent of `findings --tail`)

**Verification:** `/swarm <prose>` submits a `MissionWorkflow` to sagaflow's task queue, runs on sagaflow worker, writes state into `~/.sagaflow/` (or equivalent). Old swarmd worker sits idle.

### Phase 4: collapse `-temporal` skill dirs (independent of Phase 1-3)

For each pair `<name>/` and `<name>-temporal/`:
- Move `<name>-temporal/*.py` to `<name>/durable/`
- Update `<name>/SKILL.md` with a `## Durable execution` section (see [`execution-envelope-contract.md`](execution-envelope-contract.md))
- Update `sagaflow/worker.py:_DIR_TO_LEGACY` to point at `<name>/durable/` instead of `<name>-temporal/`
- Delete `<name>-temporal/` directory

Can be done per-skill as smaller chunks; doesn't need to be a single batch.

**Verification:** `sagaflow launch <name>` works for every migrated skill. Claude's skill catalog shows exactly one entry per algorithm.

### Phase 5: decommission swarmd

After Phase 3 has been stable for a grace period (suggested: 1 week of real use):
- Check `lsof -i :7233` and `ps aux | grep "swarm worker"` — if anything still polling queue `"swarm"`, stop it
- Remove any `launchd`/`brew services` entries for swarmd worker
- Archive `/Users/npow/code/research/swarm/` (move to `~/archive/` or tag + delete)
- Decide: migrate `~/.swarm/*` state to `~/.sagaflow/*`, or leave in place as historical

**Verification:** `sagaflow health` reports one worker with the expected workflow registry including mission workflows. No process still polling `swarm` task queue.

### Phase 6: remove the gap between sagaflow.missions and ITS original source

Over time, sagaflow.missions has drifted. Confirm the absorbed copy is authoritative, then delete swarmd.* from the filesystem to prevent accidental imports.

---

## Rollback

- **Phase 1:** deletions only add files; safe.
- **Phase 2:** documentation; safe.
- **Phase 3:** revert `commands/swarm.md` via git; swarmd worker still running means `/swarm` works as before.
- **Phase 4:** revert skill dir moves via git; sagaflow loader may need its `_DIR_TO_LEGACY` reverted too.
- **Phase 5:** once swarmd is archived, restoring it means un-archiving + restarting the worker. Before Phase 5, snapshot `~/.swarm/` with `tar -cf ~/.swarm.backup.tar ~/.swarm/`.

---

## Blockers from cutover attempt (2026-04-23)

### B1. `sagaflow mission launch` workflow runs but writes no state dir

**Observed:** a smoke mission submitted via `sagaflow mission launch /tmp/swarm-mission-smoke.yaml` returned `workflow_id=mission-20260423-221743` immediately. `sagaflow mission status <id>` returned a valid Temporal state with `findings_count: 1` and `phase: running`. However `ls ~/.swarm/state/mission-20260423-221743/` returned "No such file or directory" — no on-disk state directory was created.

**Root cause hypothesis:** `sagaflow.missions.lib.paths.ensure_session_dirs(session_id)` is supposed to create `~/.swarm/state/<id>/`, `~/.swarm/state/<id>/health/`, `~/.swarm/missions/<id>/`, etc. This function is defined but not being invoked from `MissionWorkflow` on startup (the equivalent call in swarmd likely happened in its CLI or worker init path that wasn't ported).

**Impact:** without the state directory, `emit_finding_activity` has no dir to write `findings.jsonl` into. The "findings_count: 1" visible via Temporal query reflects workflow internal state, not a disk mirror. `swarm findings --tail` (if it were called against sagaflow) would show nothing. Tailing `~/.swarm/state/<id>/findings.jsonl` (as `/swarm`'s reporting step instructs) would fail.

**Fix path:** either (a) add `ensure_session_dirs(session_id)` as the first activity in `MissionWorkflow.run` before any emit_finding call, or (b) call it from `sagaflow.cli.mission_launch` before submitting the workflow. The latter is safer — it's deterministic, runs outside the Temporal sandbox, and doesn't require changing workflow history.

**Blocks:** `/swarm` cutover to sagaflow.

### B2. `pyyaml` not in sagaflow's install deps

**Observed:** `sagaflow mission launch` errors at `import yaml` in `sagaflow/cli.py:408`.

**Fix path:** add `pyyaml` to `sagaflow/pyproject.toml` dependencies. (Worked around in-session via `--user --break-system-packages` install but that's fragile.)

**Blocks:** anyone on a fresh sagaflow install using `sagaflow mission launch` at all.

### B3. `lint_criteria.py` was never ported

**Observed:** `commands/swarm.md:111` references `/Users/npow/code/research/swarm/lint_criteria.py` which doesn't exist at that path. It may have existed historically but isn't in the current swarm repo or in sagaflow.

**Fix path:** either port it to sagaflow (or the skills repo), or replace with the inline in-session criteria rigor check (which the reverted `/swarm` version also has as a fallback).

**Blocks:** nothing critical — the inline check is a viable substitute.

---

## Open questions

1. **What in `swarmd.lib/*` is actually load-bearing for runtime?** Grep showed only `swarmd.lib.paths` is imported by swarmd.durable code (one site: `read_recent_events.py`). Sagaflow.missions already has `lib/paths.py`. So `swarmd.lib/*` is likely dead in the absorbed code path. Confirm via a dry run of every mission activity once B1 is fixed.
2. **Are there swarmd consumers OTHER than `/swarm`?** Any script, service, or user habit that invokes `swarm launch` directly? Check `~/.zshrc`, `~/bin/`, launchd plists.

---

## References

- [`execution-envelope-contract.md`](execution-envelope-contract.md) — algorithm vs envelope factoring; powers Phase 4
- [`criteria-poll-hold-window.md`](criteria-poll-hold-window.md) — observational termination primitive (lives in both swarmd and sagaflow.missions)
- [`anticheat-critic-panel.md`](anticheat-critic-panel.md) — pass-transition validator (lives in both swarmd and sagaflow.missions)
- [`SHARED-PATTERNS-SURVEY.md`](SHARED-PATTERNS-SURVEY.md) — catalog of primitives already extracted across skills

---

## Revision notes

The first draft of this ADR (2026-04-23 AM) described absorption as a future plan — that was wrong. Most of it already happened. This revision (2026-04-23 PM) was written after reading `sagaflow/worker.py`, `sagaflow/cli.py`, `sagaflow/missions/` contents, and the `diff -rq` between swarmd/ and sagaflow/missions/. The earlier draft should not be trusted; this one is grounded in source.
