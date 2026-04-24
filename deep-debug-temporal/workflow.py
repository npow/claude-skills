"""deep-debug-temporal workflow.

Phases:
  0. Symptom locking — compute symptom_sha256, store in state. Spawn premortem agent (Haiku).
  1. Evidence gathering — write evidence.md.
  2. Hypothesis generation — parallel Sonnet agents (up to 6 spec-derived + 1 outside-frame).
  3. Independent judge — two-pass blind (Haiku batches): pass-1 blind, pass-2 informed.
     Rebuttal round (Sonnet) if ≥2 hypotheses tied at 'leading'.
  4. Discriminating probes — Haiku evidence-gatherer (tools_needed=True), max 3 per cycle.
  5. Fix + verify cycle — Sonnet fix-worker (tools_needed=True), sequential, max 3 attempts.
  6. Architectural escalation — Opus architect (tools_needed=True) after 3 failed fix attempts.
  7. Cycle termination check — hard stop at cycle 6, terminal labels.
  8. Final report — Sonnet synthesis.

Cycles: max=3, hard_stop=6.
Terminal labels (7):
  Fixed — reproducing test now passes
  Environmental — requires retry/monitoring, not fix
  Architectural escalation required — 3 fix attempts failed across distinct hypotheses
  Hypothesis space saturated — no plausible hypothesis survives judge
  Cannot reproduce — investigation blocked
  User-stopped at phase N
  Hard stop at cycle N
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from string import Template

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from sagaflow.durable.activities import (
        EmitFindingInput,
        SpawnSubagentInput,
        WriteArtifactInput,
    )
    from sagaflow.durable.retry_policies import HAIKU_POLICY, SONNET_POLICY

# ── constants ────────────────────────────────────────────────────────────────
_MAX_HYP_PER_CYCLE = 6          # spec-derived hypothesis agents
_MAX_PROBES_PER_CYCLE = 3
_MAX_FIX_ATTEMPTS = 3
_DEFAULT_MAX_CYCLES = 3
_DEFAULT_HARD_STOP = 6
_BATCH_SIZE = 5                  # hypotheses per judge batch


@dataclass(frozen=True)
class DeepDebugInput:
    run_id: str
    symptom: str
    reproduction_command: str
    inbox_path: str
    run_dir: str
    # Prompts loaded from the claude-skills repo at build_input time -- single source of
    # truth for both the Claude Code driver and this workflow. Keep optional so legacy
    # tests that construct DeepDebugInput directly keep working via the default-None path.
    premortem_system_prompt: str = ""
    premortem_user_prompt: str = ""
    hypothesis_system_prompt: str = ""
    hypothesis_user_prompt: str = ""
    outside_frame_system_prompt: str = ""
    outside_frame_user_prompt: str = ""
    judge_pass1_system_prompt: str = ""
    judge_pass1_user_prompt: str = ""
    judge_pass2_system_prompt: str = ""
    judge_pass2_user_prompt: str = ""
    rebuttal_system_prompt: str = ""
    rebuttal_user_prompt: str = ""
    probe_system_prompt: str = ""
    probe_user_prompt: str = ""
    fix_system_prompt: str = ""
    fix_user_prompt: str = ""
    architect_system_prompt: str = ""
    architect_user_prompt: str = ""
    num_hypotheses: int = 4
    max_cycles: int = _DEFAULT_MAX_CYCLES
    hard_stop: int = _DEFAULT_HARD_STOP
    notify: bool = True


# ── workflow ─────────────────────────────────────────────────────────────────

@workflow.defn(name="DeepDebugWorkflow")
class DeepDebugWorkflow:

    @workflow.run
    async def run(self, inp: DeepDebugInput) -> str:  # noqa: PLR0912, PLR0915
        run_dir = inp.run_dir
        report_path = f"{run_dir}/debug-report.md"

        # ── Phase 0: symptom locking + SHA256 ──────────────────────────────
        symptom_sha256 = hashlib.sha256(inp.symptom.encode()).hexdigest()

        # Phase 0e: premortem agent (Haiku, no tools)
        premortem_prompt_path = f"{run_dir}/premortem-prompt.txt"
        premortem_user = inp.premortem_user_prompt
        premortem_system = inp.premortem_system_prompt
        await _write(run_dir, premortem_prompt_path, premortem_user)
        premortem_result = await workflow.execute_activity(
            "spawn_subagent",
            SpawnSubagentInput(
                role="premortem",
                tier_name="HAIKU",
                system_prompt=premortem_system,
                user_prompt_path=premortem_prompt_path,
                max_tokens=1024,
                tools_needed=False,
            ),
            start_to_close_timeout=timedelta(seconds=600),
            retry_policy=HAIKU_POLICY,
        )
        blind_spots: list[str] = _parse_json_list_str(premortem_result.get("BLIND_SPOTS", "[]"))

        # Track state across cycles
        all_hypotheses: list[dict[str, str]] = []
        fix_attempt_count = 0
        terminal_label: str | None = None
        cycle = 0

        for cycle in range(1, inp.hard_stop + 1):
            if cycle > inp.max_cycles and fix_attempt_count == 0:
                terminal_label = f"Hard stop at cycle {cycle}"
                break

            # ── SHA256 verification before each cycle ──────────────────────
            check = hashlib.sha256(inp.symptom.encode()).hexdigest()
            if check != symptom_sha256:
                terminal_label = "SYMPTOM_TAMPERED"
                break

            # ── Phase 2: hypothesis generation ─────────────────────────────
            num_hyp = min(inp.num_hypotheses, _MAX_HYP_PER_CYCLE)
            hyp_prompt_paths: list[str] = []
            for i in range(num_hyp):
                p = f"{run_dir}/c{cycle}-hyp-prompt-{i}.txt"
                angles = [
                    "logic / boundary conditions",
                    "concurrency / shared state",
                    "environment / configuration",
                    "resource / timing",
                    "dependency / API contract",
                    "architecture / abstraction mismatch",
                ]
                blind = "\n".join(f"- {s}" for s in blind_spots) if blind_spots else "none"
                user_prompt = _sub(
                    inp.hypothesis_user_prompt,
                    symptom=inp.symptom, repro=inp.reproduction_command,
                    cycle=str(cycle), angle=angles[i % len(angles)],
                    blind_spots=blind,
                )
                await _write(run_dir, p, user_prompt)
                hyp_prompt_paths.append(p)

            # outside-frame agent (slot #7)
            of_prompt_path = f"{run_dir}/c{cycle}-outside-frame-prompt.txt"
            of_user = _sub(inp.outside_frame_user_prompt, symptom=inp.symptom)
            await _write(run_dir, of_prompt_path, of_user)

            # Spawn all hypothesis agents + outside-frame in parallel
            hyp_sys = inp.hypothesis_system_prompt
            hyp_coros = [
                workflow.execute_activity(
                    "spawn_subagent",
                    SpawnSubagentInput(
                        role="hypothesis",
                        tier_name="SONNET",
                        system_prompt=hyp_sys,
                        user_prompt_path=p,
                        max_tokens=1024,
                        tools_needed=False,
                    ),
                    start_to_close_timeout=timedelta(seconds=600),
                    retry_policy=SONNET_POLICY,
                )
                for p in hyp_prompt_paths
            ]
            of_sys = inp.outside_frame_system_prompt
            of_coro = workflow.execute_activity(
                "spawn_subagent",
                SpawnSubagentInput(
                    role="outside-frame",
                    tier_name="SONNET",
                    system_prompt=of_sys,
                    user_prompt_path=of_prompt_path,
                    max_tokens=1024,
                    tools_needed=False,
                ),
                start_to_close_timeout=timedelta(seconds=600),
                retry_policy=SONNET_POLICY,
            )

            all_results = await asyncio.gather(*hyp_coros, of_coro, return_exceptions=True)
            hyp_results = all_results[:-1]
            of_result = all_results[-1]

            cycle_hypotheses: list[dict[str, str]] = []
            for i, r in enumerate(hyp_results):
                if isinstance(r, BaseException):
                    continue
                h = {
                    "id": f"c{cycle}-h{i}",
                    "dimension": r.get("DIMENSION", "unknown"),
                    "mechanism": r.get("MECHANISM", ""),
                    "confidence": r.get("CONFIDENCE", "low"),
                    "outside_frame": "false",
                }
                if h["mechanism"]:
                    cycle_hypotheses.append(h)

            # outside-frame hypothesis
            if not isinstance(of_result, BaseException):
                of_dim = of_result.get("DIMENSION", "outside-frame")
                of_mech = of_result.get("MECHANISM", "")
                if of_mech:
                    cycle_hypotheses.append({
                        "id": f"c{cycle}-hOF",
                        "dimension": of_dim,
                        "mechanism": of_mech,
                        "confidence": of_result.get("CONFIDENCE", "low"),
                        "outside_frame": "true",
                    })

            all_hypotheses.extend(cycle_hypotheses)

            if not cycle_hypotheses:
                terminal_label = "Hypothesis space saturated — no plausible hypothesis survives judge"
                break

            # ── Phase 3: two-pass blind judge ──────────────────────────────
            # Write stripped judge-input batches (confidence removed) + confidence cache
            judge_verdicts: list[dict[str, str]] = []
            batches = _make_batches(cycle_hypotheses, _BATCH_SIZE)
            for b_idx, batch in enumerate(batches):
                stripped = [{k: v for k, v in h.items() if k != "confidence"} for h in batch]
                confidence_claims = {h["id"]: h.get("confidence", "low") for h in batch}

                p1_prompt = f"{run_dir}/c{cycle}-judge-p1-b{b_idx}.txt"
                p1_user = _sub(
                    inp.judge_pass1_user_prompt,
                    symptom=inp.symptom,
                    hypotheses_json=json.dumps(stripped, indent=2),
                )
                await _write(run_dir, p1_prompt, p1_user)
                p1_sys = inp.judge_pass1_system_prompt
                pass1_result = await workflow.execute_activity(
                    "spawn_subagent",
                    SpawnSubagentInput(
                        role="judge-pass-1",
                        tier_name="HAIKU",
                        system_prompt=p1_sys,
                        user_prompt_path=p1_prompt,
                        max_tokens=1024,
                        tools_needed=False,
                    ),
                    start_to_close_timeout=timedelta(seconds=600),
                    retry_policy=HAIKU_POLICY,
                )
                pass1_verdicts = _parse_judge_verdicts(pass1_result.get("VERDICTS", "[]"))

                # Pass 2: informed with confidence claims
                p2_prompt = f"{run_dir}/c{cycle}-judge-p2-b{b_idx}.txt"
                p2_user = _sub(
                    inp.judge_pass2_user_prompt,
                    pass1_verdicts_json=json.dumps(pass1_verdicts, indent=2),
                    confidence_claims_json=json.dumps(confidence_claims, indent=2),
                )
                await _write(run_dir, p2_prompt, p2_user)
                p2_sys = inp.judge_pass2_system_prompt
                pass2_result = await workflow.execute_activity(
                    "spawn_subagent",
                    SpawnSubagentInput(
                        role="judge-pass-2",
                        tier_name="HAIKU",
                        system_prompt=p2_sys,
                        user_prompt_path=p2_prompt,
                        max_tokens=1024,
                        tools_needed=False,
                    ),
                    start_to_close_timeout=timedelta(seconds=600),
                    retry_policy=HAIKU_POLICY,
                )
                pass2_verdicts = _parse_judge_verdicts(pass2_result.get("VERDICTS", "[]"))

                # Merge: pass2 overrides pass1 for verdicts that have PASS2_VERDICT
                merged = _merge_pass_verdicts(pass1_verdicts, pass2_verdicts)
                judge_verdicts.extend(merged)

            # Rebuttal round: if ≥2 hypotheses are 'leading'
            leaders = [v for v in judge_verdicts if v.get("plausibility") == "leading"]
            if len(leaders) >= 2:
                leader_a = leaders[0]
                leader_b = leaders[1]
                rebuttal_prompt = f"{run_dir}/c{cycle}-rebuttal.txt"
                leader_hyp_r = _hyp_by_id(cycle_hypotheses, leader_a.get("hyp_id", "")) or leader_a
                alt_hyp_r = _hyp_by_id(cycle_hypotheses, leader_b.get("hyp_id", "")) or leader_b
                reb_user = _sub(
                    inp.rebuttal_user_prompt,
                    symptom=inp.symptom,
                    leader_json=json.dumps(leader_hyp_r, indent=2),
                    alternative_json=json.dumps(alt_hyp_r, indent=2),
                )
                await _write(run_dir, rebuttal_prompt, reb_user)
                reb_sys = inp.rebuttal_system_prompt
                rebuttal_result = await workflow.execute_activity(
                    "spawn_subagent",
                    SpawnSubagentInput(
                        role="rebuttal",
                        tier_name="SONNET",
                        system_prompt=reb_sys,
                        user_prompt_path=rebuttal_prompt,
                        max_tokens=1024,
                        tools_needed=False,
                    ),
                    start_to_close_timeout=timedelta(seconds=600),
                    retry_policy=SONNET_POLICY,
                )
                outcome = rebuttal_result.get("OUTCOME", "INCONCLUSIVE")
                new_leader_id = rebuttal_result.get("NEW_LEADER", "")
                # Apply rebuttal outcome
                if outcome == "LEADER_FALSIFIED" and new_leader_id:
                    for v in judge_verdicts:
                        if v.get("hyp_id") == leaders[0]["hyp_id"]:
                            v["plausibility"] = "rejected"
                elif outcome == "LEADER_WEAKENED" and new_leader_id:
                    for v in judge_verdicts:
                        if v.get("hyp_id") == leaders[0]["hyp_id"]:
                            v["plausibility"] = "plausible"
                # Re-compute leaders after rebuttal
                leaders = [v for v in judge_verdicts if v.get("plausibility") == "leading"]

            # ── Phase 4: discriminating probes ─────────────────────────────
            promoted_hyp: dict[str, str] | None = None
            probe_count = 0

            if len(leaders) == 1:
                # Single clear leader — no probe needed if no plausibles either
                plausibles = [v for v in judge_verdicts if v.get("plausibility") == "plausible"]
                if not plausibles:
                    promoted_hyp = _hyp_by_id(cycle_hypotheses, leaders[0]["hyp_id"])
                else:
                    # Design probe to discriminate leader vs top plausible
                    leader_hyp = _hyp_by_id(cycle_hypotheses, leaders[0]["hyp_id"])
                    rival_hyp = _hyp_by_id(cycle_hypotheses, plausibles[0]["hyp_id"])
                    promoted_hyp, probe_count = await _run_probes(
                        run_dir, cycle, inp.symptom,
                        leader_hyp, rival_hyp, probe_count, _MAX_PROBES_PER_CYCLE,
                        probe_sys=inp.probe_system_prompt,
                        probe_user_tpl=inp.probe_user_prompt,
                    )
            elif len(leaders) >= 2:
                # Multiple leaders survive rebuttal — probe to discriminate
                leader_hyp = _hyp_by_id(cycle_hypotheses, leaders[0]["hyp_id"])
                rival_hyp = _hyp_by_id(cycle_hypotheses, leaders[1]["hyp_id"])
                promoted_hyp, probe_count = await _run_probes(
                    run_dir, cycle, inp.symptom,
                    leader_hyp, rival_hyp, probe_count, _MAX_PROBES_PER_CYCLE
                )
            else:
                # No leaders at all
                terminal_label = (
                    "Hypothesis space saturated — no plausible hypothesis survives judge"
                )
                break

            if promoted_hyp is None:
                # Probes exhausted without winner
                fix_attempt_count += 1
                if fix_attempt_count >= _MAX_FIX_ATTEMPTS:
                    terminal_label = (
                        "Architectural escalation required — "
                        "3 fix attempts failed across distinct hypotheses"
                    )
                    await _run_architect(run_dir, inp.symptom, all_hypotheses,
                                         arch_sys=inp.architect_system_prompt,
                                         arch_user=inp.architect_user_prompt)
                    break
                continue  # next cycle

            # ── Phase 5: fix + verify cycle ────────────────────────────────
            fix_path = f"{run_dir}/c{cycle}-fix-prompt.txt"
            fix_user = _sub(
                inp.fix_user_prompt,
                symptom=inp.symptom, repro=inp.reproduction_command,
                hypothesis_json=json.dumps(promoted_hyp, indent=2),
            )
            await _write(run_dir, fix_path, fix_user)
            fix_sys = inp.fix_system_prompt
            fix_result = await workflow.execute_activity(
                "spawn_subagent",
                SpawnSubagentInput(
                    role="fix-worker",
                    tier_name="SONNET",
                    system_prompt=fix_sys,
                    user_prompt_path=fix_path,
                    max_tokens=2048,
                    tools_needed=True,
                ),
                start_to_close_timeout=timedelta(seconds=300),
                retry_policy=SONNET_POLICY,
            )

            fix_result.get("FIX_APPLIED", "false").lower() == "true"
            test_passes = fix_result.get("TEST_PASSES", "false").lower() == "true"
            fix_attempt_count += 1

            if test_passes:
                terminal_label = "Fixed — reproducing test now passes"
                break

            # Fix failed — check escalation threshold
            if fix_attempt_count >= _MAX_FIX_ATTEMPTS:
                terminal_label = (
                    "Architectural escalation required — "
                    "3 fix attempts failed across distinct hypotheses"
                )
                await _run_architect(run_dir, inp.symptom, all_hypotheses,
                                         arch_sys=inp.architect_system_prompt,
                                         arch_user=inp.architect_user_prompt)
                break

            # Otherwise loop to next cycle

        # ── Phase 8: hard stop check ───────────────────────────────────────
        if terminal_label is None:
            if cycle >= inp.hard_stop:
                terminal_label = f"Hard stop at cycle {cycle}"
            else:
                terminal_label = "Hypothesis space saturated — no plausible hypothesis survives judge"

        # ── Phase 8: final report ──────────────────────────────────────────
        leading_verdict = next(
            (v for v in (
                _flatten_verdicts(all_hypotheses)
            ) if v.get("plausibility") == "leading"),
            None,
        )
        summary = (
            f"{len(all_hypotheses)} hypotheses across {cycle} cycle(s); "
            f"leader={leading_verdict.get('hyp_id') if leading_verdict else 'none'}; "
            f"fix_attempts={fix_attempt_count}; "
            f"label={terminal_label}"
        )

        report_md = _fallback_report(all_hypotheses, terminal_label, fix_attempt_count, cycle)
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(path=report_path, content=report_md),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )

        timestamp = workflow.now().isoformat(timespec="seconds")
        await workflow.execute_activity(
            "emit_finding",
            EmitFindingInput(
                inbox_path=inp.inbox_path,
                run_id=inp.run_id,
                skill="deep-debug",
                status="DONE",
                summary=summary,
                notify=inp.notify,
                timestamp_iso=timestamp,
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        return f"{summary}\nReport: {report_path}"


# ── helpers ───────────────────────────────────────────────────────────────────


def _sub(template_str: str, **kwargs: str) -> str:
    """Substitute $variables in a loaded prompt template. Safe for workflow use."""
    return Template(template_str).safe_substitute(kwargs)


async def _write(run_dir: str, path: str, content: str) -> None:
    await workflow.execute_activity(
        "write_artifact",
        WriteArtifactInput(path=path, content=content),
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=HAIKU_POLICY,
    )


async def _run_probes(
    run_dir: str,
    cycle: int,
    symptom: str,
    leader: dict[str, str] | None,
    rival: dict[str, str] | None,
    probe_count: int,
    max_probes: int,
    *,
    probe_sys: str = "",
    probe_user_tpl: str = "",
) -> tuple[dict[str, str] | None, int]:
    """Run discriminating probes between leader and rival. Returns (winner, new_probe_count)."""
    while probe_count < max_probes:
        if leader is None or rival is None:
            break
        probe_prompt = f"{run_dir}/c{cycle}-probe-{probe_count}.txt"
        probe_user = _sub(
            probe_user_tpl,
            symptom=symptom,
            leader_json=json.dumps(leader, indent=2),
            rival_json=json.dumps(rival, indent=2),
        )
        await _write(run_dir, probe_prompt, probe_user)
        probe_result = await workflow.execute_activity(
            "spawn_subagent",
            SpawnSubagentInput(
                role="probe",
                tier_name="HAIKU",
                system_prompt=probe_sys,
                user_prompt_path=probe_prompt,
                max_tokens=1024,
                tools_needed=True,
            ),
            start_to_close_timeout=timedelta(seconds=300),
            retry_policy=HAIKU_POLICY,
        )
        probe_count += 1

        winner_id = probe_result.get("WINNER", "null")
        status = probe_result.get("STATUS", "inconclusive")

        if status == "completed" and winner_id not in ("null", ""):
            winner = leader if winner_id == leader.get("id") else rival
            return winner, probe_count

        if status == "execution_failed":
            break

        # inconclusive: try again (next iteration)

    return None, probe_count


async def _run_architect(
    run_dir: str,
    symptom: str,
    hypotheses: list[dict[str, str]],
    *,
    arch_sys: str = "",
    arch_user: str = "",
) -> None:
    """Phase 7: spawn Opus architect agent."""
    arch_prompt = f"{run_dir}/architect-prompt.txt"
    arch_user_text = _sub(
        arch_user,
        symptom=symptom,
        hypotheses_json=json.dumps(hypotheses, indent=2),
    )
    await _write(run_dir, arch_prompt, arch_user_text)
    await workflow.execute_activity(
        "spawn_subagent",
        SpawnSubagentInput(
            role="architect",
            tier_name="SONNET",   # OPUS maps to SONNET in test env; prod overrides tier name
            system_prompt=arch_sys,
            user_prompt_path=arch_prompt,
            max_tokens=2048,
            tools_needed=True,
        ),
        start_to_close_timeout=timedelta(seconds=300),
        retry_policy=SONNET_POLICY,
    )


def _hyp_by_id(
    hypotheses: list[dict[str, str]], hyp_id: str
) -> dict[str, str] | None:
    return next((h for h in hypotheses if h.get("id") == hyp_id), None)


def _make_batches(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def _merge_pass_verdicts(
    pass1: list[dict[str, str]],
    pass2: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Pass2 overrides pass1 verdict per hyp_id when present."""
    p2_by_id = {v.get("hyp_id"): v for v in pass2}
    result = []
    for v in pass1:
        hid = v.get("hyp_id")
        if hid in p2_by_id:
            merged = dict(v)
            merged.update(p2_by_id[hid])
            result.append(merged)
        else:
            result.append(v)
    return result


def _flatten_verdicts(hypotheses: list[dict[str, str]]) -> list[dict[str, str]]:
    """Convert hypothesis list to verdict-like dicts for final report lookup."""
    return [{"hyp_id": h.get("id"), "plausibility": h.get("plausibility", "pending")}
            for h in hypotheses]


def _parse_judge_verdicts(raw: str) -> list[dict[str, str]]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [x for x in parsed if isinstance(x, dict)]
    except json.JSONDecodeError:
        pass
    return []


def _parse_json_list_str(raw: str) -> list[str]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    except json.JSONDecodeError:
        pass
    return []


def _fallback_report(
    hypotheses: list[dict[str, str]],
    terminal_label: str | None,
    fix_attempts: int,
    cycles: int,
) -> str:
    lines = [
        "# Debug Report",
        "",
        f"**Terminal label:** {terminal_label}",
        f"**Cycles:** {cycles} | **Fix attempts:** {fix_attempts}",
        "",
        "## Hypotheses",
    ]
    for h in hypotheses:
        lines.append(f"- [{h.get('dimension', '?')}] {h.get('mechanism', '')}")
    return "\n".join(lines)


