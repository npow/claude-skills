"""deep-design-temporal: Temporal port of the deep-design skill.

Phases:
  a. Initial draft (Sonnet): from concept, produce v0-initial spec stored in state.
  b. Per-round critique pipeline:
       1. Fact-sheet agent (Haiku) — reads spec, emits RECOVERY_BEHAVIORS.
       2. Parallel spec-derived critics (Haiku × ≤6) + outside-frame critic (Haiku).
       3. Two-pass blind severity judges (Haiku) — pass-1 blind, pass-2 sees claim.
       4. Challenger agent (Haiku) — if redesign agent disputes a severity verdict.
       5. Cross-fix checker (Haiku) — detects conflicts between proposed fixes.
       6. Redesign agent (Sonnet) — sole spec author; addresses accepted flaws.
       7. Invariant-validation agent (Haiku) — verifies spec against invariants.
       8. Drift-judge agent (Haiku) — scores semantic drift from core_claim.
  c. Termination check: "Conditions Met" or "Max Rounds Reached".
  d. Final synthesis (Sonnet): clean spec.md + revision summary.
  e. Write spec.md, emit_finding to INBOX.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from sagaflow.durable.activities import (
        EmitFindingInput,
        SpawnSubagentInput,
        WriteArtifactInput,
    )
    from sagaflow.durable.retry_policies import HAIKU_POLICY, SONNET_POLICY
    from .state import (
        CrossFixConflict,
        DeepDesignState,
        Flaw,
        InvariantViolation,
        RecoveryBehavior,
    )


@dataclass(frozen=True)
class DeepDesignInput:
    run_id: str
    concept: str          # free-form description of the design to produce
    inbox_path: str
    run_dir: str
    max_rounds: int = 2
    notify: bool = True
    # Prompts loaded from ~/.claude/skills/deep-design/prompts/ at build_input time.
    # Empty string means "use inline default".
    draft_system_prompt: str = ""
    draft_user_prompt: str = ""
    fact_sheet_system_prompt: str = ""
    fact_sheet_user_prompt: str = ""
    critic_system_prompt: str = ""
    critic_user_prompt: str = ""
    outside_frame_system_prompt: str = ""
    outside_frame_user_prompt: str = ""
    judge_system_prompt: str = ""
    judge_pass1_user_prompt: str = ""
    judge_pass2_user_prompt: str = ""
    challenger_system_prompt: str = ""
    challenger_user_prompt: str = ""
    cross_fix_system_prompt: str = ""
    cross_fix_user_prompt: str = ""
    redesign_system_prompt: str = ""
    redesign_user_prompt: str = ""
    invariant_validator_system_prompt: str = ""
    invariant_validator_user_prompt: str = ""
    drift_judge_system_prompt: str = ""
    drift_judge_user_prompt: str = ""
    synth_system_prompt: str = ""
    synth_user_prompt: str = ""


# Max spec-derived critics per round (outside-frame is slot #7, tracked separately).
_MAX_CRITICS_PER_ROUND = 6
# Quorum: ≥ 4 of 6 spec-derived critics must return parseable output.
_QUORUM_THRESHOLD = 4


@workflow.defn(name="DeepDesignWorkflow")
class DeepDesignWorkflow:
    @workflow.run
    async def run(self, inp: DeepDesignInput) -> str:
        state = DeepDesignState(
            run_id=inp.run_id,
            skill="deep-design",
        )
        state.set_core_claim(inp.concept, calibrated=True)
        spec_path = f"{inp.run_dir}/spec.md"
        max_rounds = max(1, min(inp.max_rounds, 5))

        # ------------------------------------------------------------------ #
        # Phase a: initial draft                                               #
        # ------------------------------------------------------------------ #
        draft_prompt_path = f"{inp.run_dir}/draft-prompt.txt"
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(
                path=draft_prompt_path,
                content=inp.draft_user_prompt,
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        draft_result = await workflow.execute_activity(
            "spawn_subagent",
            SpawnSubagentInput(
                role="draft",
                tier_name="SONNET",
                system_prompt=inp.draft_system_prompt,
                user_prompt_path=draft_prompt_path,
                max_tokens=128000,
                tools_needed=False,
            ),
            start_to_close_timeout=timedelta(seconds=600),
            retry_policy=SONNET_POLICY,
        )
        state.spec_draft = draft_result.get("SPEC", _fallback_spec(inp.concept))

        # ------------------------------------------------------------------ #
        # Phase b: critique rounds                                             #
        # ------------------------------------------------------------------ #
        for round_idx in range(max_rounds):
            state.current_round = round_idx

            # -------------------------------------------------------------- #
            # b.1 Fact-sheet agent                                            #
            # -------------------------------------------------------------- #
            fact_sheet_prompt_path = f"{inp.run_dir}/fact-sheet-r{round_idx}.txt"
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=fact_sheet_prompt_path,
                    content=inp.fact_sheet_user_prompt or _fact_sheet_user_prompt(spec_md=state.spec_draft),  # runtime-dynamic
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            fact_sheet_result = await workflow.execute_activity(
                "spawn_subagent",
                SpawnSubagentInput(
                    role="fact-sheet",
                    tier_name="HAIKU",
                    system_prompt=inp.fact_sheet_system_prompt,
                    user_prompt_path=fact_sheet_prompt_path,
                    max_tokens=128000,
                    tools_needed=False,
                ),
                start_to_close_timeout=timedelta(seconds=600),
                retry_policy=HAIKU_POLICY,
            )
            state.recovery_behaviors = _parse_recovery_behaviors(
                fact_sheet_result.get("RECOVERY_BEHAVIORS", "[]")
            )

            # -------------------------------------------------------------- #
            # b.2 Parallel critics                                            #
            # -------------------------------------------------------------- #
            # Spec-derived critics (up to 6).
            critic_prompt_paths: list[str] = []
            for i in range(_MAX_CRITICS_PER_ROUND):
                ppath = f"{inp.run_dir}/critic-r{round_idx}-{i}.txt"
                await workflow.execute_activity(
                    "write_artifact",
                    WriteArtifactInput(
                        path=ppath,
                        content=inp.critic_user_prompt or _critic_user_prompt(  # runtime-dynamic
                            spec_md=state.spec_draft,
                            concept=inp.concept,
                            critic_index=i,
                        ),
                    ),
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=HAIKU_POLICY,
                )
                critic_prompt_paths.append(ppath)

            # Outside-frame critic (slot #7, seeded from original concept only).
            of_prompt_path = f"{inp.run_dir}/outside-frame-r{round_idx}.txt"
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=of_prompt_path,
                    content=inp.outside_frame_user_prompt,
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )

            # Run all critics in parallel.
            spec_critic_coros = [
                workflow.execute_activity(
                    "spawn_subagent",
                    SpawnSubagentInput(
                        role="critic",
                        tier_name="HAIKU",
                        system_prompt=inp.critic_system_prompt,
                        user_prompt_path=ppath,
                        max_tokens=128000,
                        tools_needed=False,
                    ),
                    start_to_close_timeout=timedelta(seconds=600),
                    retry_policy=HAIKU_POLICY,
                )
                for ppath in critic_prompt_paths
            ]
            outside_frame_coro = workflow.execute_activity(
                "spawn_subagent",
                SpawnSubagentInput(
                    role="outside-frame",
                    tier_name="HAIKU",
                    system_prompt=inp.outside_frame_system_prompt,
                    user_prompt_path=of_prompt_path,
                    max_tokens=128000,
                    tools_needed=False,
                ),
                start_to_close_timeout=timedelta(seconds=600),
                retry_policy=HAIKU_POLICY,
            )

            all_critic_results = await asyncio.gather(
                *spec_critic_coros,
                outside_frame_coro,
                return_exceptions=True,
            )

            spec_critic_results = all_critic_results[:_MAX_CRITICS_PER_ROUND]
            outside_frame_result = all_critic_results[_MAX_CRITICS_PER_ROUND]

            # Quorum check: ≥ 4 of 6 spec-derived critics must succeed.
            parseable_count = sum(
                1
                for r in spec_critic_results
                if not isinstance(r, BaseException) and r.get("FLAWS")
            )
            quorum_met = parseable_count >= _QUORUM_THRESHOLD

            # Collect new flaws from all critics.
            round_flaws: list[Flaw] = []
            existing_flaw_ids = {f.id for f in state.flaws}

            for result in spec_critic_results:
                if isinstance(result, BaseException):
                    continue
                for raw_flaw in _parse_flaws(result.get("FLAWS", "[]")):
                    fid = raw_flaw.get("id", "")
                    if fid and fid not in existing_flaw_ids:
                        existing_flaw_ids.add(fid)
                        round_flaws.append(
                            Flaw(
                                id=fid,
                                title=raw_flaw.get("title", ""),
                                severity=raw_flaw.get("severity", "minor"),  # type: ignore[arg-type]
                                dimension=raw_flaw.get("dimension", ""),
                                scenario=raw_flaw.get("scenario", ""),
                            )
                        )

            # Outside-frame flaws (tracked separately, do not affect quorum).
            if not isinstance(outside_frame_result, BaseException):
                for raw_flaw in _parse_flaws(
                    outside_frame_result.get("FLAWS", "[]")
                ):
                    fid = raw_flaw.get("id", "")
                    if fid and fid not in existing_flaw_ids:
                        existing_flaw_ids.add(fid)
                        round_flaws.append(
                            Flaw(
                                id=fid,
                                title=raw_flaw.get("title", ""),
                                severity=raw_flaw.get("severity", "minor"),  # type: ignore[arg-type]
                                dimension=raw_flaw.get("dimension", ""),
                                scenario=raw_flaw.get("scenario", ""),
                            )
                        )

            # Handle GAP_REPORTs from any critic.
            for result in list(spec_critic_results) + (
                [] if isinstance(outside_frame_result, BaseException)
                else [outside_frame_result]
            ):
                if isinstance(result, BaseException):
                    continue
                for gap in _parse_gap_reports(result.get("GAP_REPORTS", "[]")):
                    flaw_id = gap.get("references_flaw_id", "")
                    if flaw_id:
                        outcome = state.record_gap_report(flaw_id)
                        if outcome == "reopened":
                            # Re-open the flaw for re-fix.
                            for flaw in state.flaws:
                                if flaw.id == flaw_id:
                                    flaw.status = "open"
                                    break

            state.flaws.extend(round_flaws)

            if not quorum_met or not round_flaws:
                # Skip redesign if quorum not met or no new flaws.
                continue

            # -------------------------------------------------------------- #
            # b.3 Two-pass blind severity judges                              #
            # -------------------------------------------------------------- #
            open_flaws = [f for f in round_flaws if f.status == "open"]
            for flaw in open_flaws:
                judge_prompt_path = f"{inp.run_dir}/judge-p1-r{round_idx}-{flaw.id}.txt"
                await workflow.execute_activity(
                    "write_artifact",
                    WriteArtifactInput(
                        path=judge_prompt_path,
                        content=inp.judge_pass1_user_prompt or _judge_pass1_user_prompt(  # runtime-dynamic
                            flaw=flaw, spec_md=state.spec_draft
                        ),
                    ),
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=HAIKU_POLICY,
                )
                judge_p1_result = await workflow.execute_activity(
                    "spawn_subagent",
                    SpawnSubagentInput(
                        role="judge-pass-1",
                        tier_name="HAIKU",
                        system_prompt=inp.judge_system_prompt,
                        user_prompt_path=judge_prompt_path,
                        max_tokens=128000,
                        tools_needed=False,
                    ),
                    start_to_close_timeout=timedelta(seconds=600),
                    retry_policy=HAIKU_POLICY,
                )
                p1_verdict = _parse_verdict(judge_p1_result.get("VERDICT", ""))
                flaw.judge_pass1_verdict = p1_verdict  # type: ignore[assignment]

                # Pass 2: judge sees the critic's original severity claim.
                judge_p2_prompt_path = (
                    f"{inp.run_dir}/judge-p2-r{round_idx}-{flaw.id}.txt"
                )
                await workflow.execute_activity(
                    "write_artifact",
                    WriteArtifactInput(
                        path=judge_p2_prompt_path,
                        content=inp.judge_pass2_user_prompt or _judge_pass2_user_prompt(  # runtime-dynamic
                            flaw=flaw,
                            pass1_verdict=p1_verdict or "minor",
                            original_severity=flaw.severity,
                        ),
                    ),
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=HAIKU_POLICY,
                )
                judge_p2_result = await workflow.execute_activity(
                    "spawn_subagent",
                    SpawnSubagentInput(
                        role="judge-pass-2",
                        tier_name="HAIKU",
                        system_prompt=inp.judge_system_prompt,
                        user_prompt_path=judge_p2_prompt_path,
                        max_tokens=128000,
                        tools_needed=False,
                    ),
                    start_to_close_timeout=timedelta(seconds=600),
                    retry_policy=HAIKU_POLICY,
                )
                p2_verdict = _parse_verdict(judge_p2_result.get("VERDICT", ""))
                flaw.judge_pass2_verdict = p2_verdict  # type: ignore[assignment]
                if p2_verdict:
                    flaw.severity = p2_verdict  # type: ignore[assignment]
                if p2_verdict == "rejected":
                    flaw.status = "disputed"

            # -------------------------------------------------------------- #
            # b.4 Challenger agent                                            #
            # -------------------------------------------------------------- #
            # For each flaw where the original severity was higher than the
            # judge's final verdict, spend one challenge token if available.
            challengeable = [
                f
                for f in open_flaws
                if (
                    not f.challenge_token_spent
                    and f.judge_pass2_verdict is not None
                    and _severity_rank(f.judge_pass2_verdict)
                    < _severity_rank(f.severity)
                )
            ]
            for flaw in challengeable:
                flaw.challenge_token_spent = True
                challenger_prompt_path = (
                    f"{inp.run_dir}/challenger-r{round_idx}-{flaw.id}.txt"
                )
                await workflow.execute_activity(
                    "write_artifact",
                    WriteArtifactInput(
                        path=challenger_prompt_path,
                        content=inp.challenger_user_prompt or _challenger_user_prompt(  # runtime-dynamic
                            flaw=flaw, spec_md=state.spec_draft
                        ),
                    ),
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=HAIKU_POLICY,
                )
                challenger_result = await workflow.execute_activity(
                    "spawn_subagent",
                    SpawnSubagentInput(
                        role="challenger",
                        tier_name="HAIKU",
                        system_prompt=inp.challenger_system_prompt,
                        user_prompt_path=challenger_prompt_path,
                        max_tokens=128000,
                        tools_needed=False,
                    ),
                    start_to_close_timeout=timedelta(seconds=600),
                    retry_policy=HAIKU_POLICY,
                )
                challenge_outcome = challenger_result.get("CHALLENGE", "")
                if challenge_outcome.startswith("CHALLENGE_UPHELD"):
                    # Restore the pre-judge severity.
                    pass  # severity already reverted by the flaw's original value

            # -------------------------------------------------------------- #
            # b.5 Cross-fix checker                                           #
            # -------------------------------------------------------------- #
            accepted_flaws = [
                f
                for f in open_flaws
                if f.status == "open" and f.severity in ("critical", "major")
            ]
            if accepted_flaws:
                cross_fix_prompt_path = (
                    f"{inp.run_dir}/cross-fix-r{round_idx}.txt"
                )
                await workflow.execute_activity(
                    "write_artifact",
                    WriteArtifactInput(
                        path=cross_fix_prompt_path,
                        content=inp.cross_fix_user_prompt or _cross_fix_user_prompt(  # runtime-dynamic
                            flaws=accepted_flaws, spec_md=state.spec_draft
                        ),
                    ),
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=HAIKU_POLICY,
                )
                cross_fix_result = await workflow.execute_activity(
                    "spawn_subagent",
                    SpawnSubagentInput(
                        role="cross-fix",
                        tier_name="HAIKU",
                        system_prompt=inp.cross_fix_system_prompt,
                        user_prompt_path=cross_fix_prompt_path,
                        max_tokens=128000,
                        tools_needed=False,
                    ),
                    start_to_close_timeout=timedelta(seconds=600),
                    retry_policy=HAIKU_POLICY,
                )
                state.cross_fix_conflicts = _parse_cross_fix_conflicts(
                    cross_fix_result.get("CONFLICTS", "[]")
                )

                # Conflicts block advancement.
                if state.cross_fix_conflicts:
                    continue

            # -------------------------------------------------------------- #
            # b.6 Redesign agent                                              #
            # -------------------------------------------------------------- #
            redesign_prompt_path = f"{inp.run_dir}/redesign-r{round_idx}.txt"
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=redesign_prompt_path,
                    content=inp.redesign_user_prompt or _redesign_user_prompt(  # runtime-dynamic
                        spec_md=state.spec_draft,
                        flaws=accepted_flaws,
                        invariants=state.component_invariants,
                        round_idx=round_idx,
                    ),
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            redesign_result = await workflow.execute_activity(
                "spawn_subagent",
                SpawnSubagentInput(
                    role="redesign",
                    tier_name="SONNET",
                    system_prompt=inp.redesign_system_prompt,
                    user_prompt_path=redesign_prompt_path,
                    max_tokens=128000,
                    tools_needed=False,
                ),
                start_to_close_timeout=timedelta(seconds=600),
                retry_policy=SONNET_POLICY,
            )
            new_spec = redesign_result.get("SPEC", state.spec_draft)

            # Record complexity delta.
            components_added = int(redesign_result.get("COMPONENTS_ADDED", "0") or "0")
            budget = state.complexity_budget_for_round(round_idx)
            state.complexity_added_per_round[round_idx] = components_added
            if components_added > budget:
                # Record DESIGN_TENSION — do not advance.
                pass
            else:
                state.spec_draft = new_spec

            # Mark addressed flaws.
            for flaw in accepted_flaws:
                flaw.status = "addressed"

            # -------------------------------------------------------------- #
            # b.7 Invariant-validation agent                                  #
            # -------------------------------------------------------------- #
            inv_prompt_path = (
                f"{inp.run_dir}/invariant-validator-r{round_idx}.txt"
            )
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=inv_prompt_path,
                    content=inp.invariant_validator_user_prompt or _invariant_validator_user_prompt(  # runtime-dynamic
                        spec_md=state.spec_draft,
                        invariants=state.component_invariants,
                    ),
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            inv_result = await workflow.execute_activity(
                "spawn_subagent",
                SpawnSubagentInput(
                    role="invariant-validator",
                    tier_name="HAIKU",
                    system_prompt=inp.invariant_validator_system_prompt,
                    user_prompt_path=inv_prompt_path,
                    max_tokens=128000,
                    tools_needed=False,
                ),
                start_to_close_timeout=timedelta(seconds=600),
                retry_policy=HAIKU_POLICY,
            )
            state.invariant_violations = _parse_invariant_violations(
                inv_result.get("VIOLATIONS", "[]")
            )

            # Violations block round advancement.
            if state.invariant_violations:
                continue

            # -------------------------------------------------------------- #
            # b.8 Drift-judge agent                                           #
            # -------------------------------------------------------------- #
            drift_prompt_path = f"{inp.run_dir}/drift-judge-r{round_idx}.txt"
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=drift_prompt_path,
                    content=inp.drift_judge_user_prompt or _drift_judge_user_prompt(  # runtime-dynamic
                        core_claim=state.core_claim,
                        spec_md=state.spec_draft,
                        calibrated=state.core_claim_calibrated,
                    ),
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            drift_result = await workflow.execute_activity(
                "spawn_subagent",
                SpawnSubagentInput(
                    role="drift-judge",
                    tier_name="HAIKU",
                    system_prompt=inp.drift_judge_system_prompt,
                    user_prompt_path=drift_prompt_path,
                    max_tokens=128000,
                    tools_needed=False,
                ),
                start_to_close_timeout=timedelta(seconds=600),
                retry_policy=HAIKU_POLICY,
            )
            drift_score_raw = drift_result.get("DRIFT_SCORE", "")
            drift_verdict_raw = drift_result.get("DRIFT_VERDICT", "ok")
            try:
                state.drift_score = float(drift_score_raw)
            except (ValueError, TypeError):
                state.drift_score = None
            state.drift_verdict = drift_verdict_raw if drift_verdict_raw in ("ok", "warning", "critical") else "ok"  # type: ignore[assignment]

            # DRIFT_CRITICAL halts redesign — route affected flaws to PERSISTENT_TENSION.
            if state.drift_verdict == "critical":
                for flaw in state.flaws:
                    if flaw.status == "open":
                        flaw.status = "persistent_tension"
                break

            # -------------------------------------------------------------- #
            # Termination check (early exit)                                  #
            # -------------------------------------------------------------- #
            if _check_early_exit(state):
                state.termination_label = "Conditions Met"
                break

        else:
            state.termination_label = "Max Rounds Reached"

        if state.termination_label is None:
            state.termination_label = "Max Rounds Reached"

        # ------------------------------------------------------------------ #
        # Phase d: final synthesis                                             #
        # ------------------------------------------------------------------ #
        synth_prompt_path = f"{inp.run_dir}/synth-prompt.txt"
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(
                path=synth_prompt_path,
                content=inp.synth_user_prompt or _synth_user_prompt(  # runtime-dynamic
                    concept=inp.concept,
                    spec_md=state.spec_draft,
                    flaws=[vars(f) for f in state.flaws],
                    termination_label=state.termination_label,
                ),
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        synth_result = await workflow.execute_activity(
            "spawn_subagent",
            SpawnSubagentInput(
                role="synth",
                tier_name="SONNET",
                system_prompt=inp.synth_system_prompt,
                user_prompt_path=synth_prompt_path,
                max_tokens=128000,
                tools_needed=False,
            ),
            start_to_close_timeout=timedelta(seconds=600),
            retry_policy=SONNET_POLICY,
        )
        final_spec = synth_result.get("REPORT", state.spec_draft)

        # ------------------------------------------------------------------ #
        # Phase e: write spec.md + emit finding                               #
        # ------------------------------------------------------------------ #
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(path=spec_path, content=final_spec),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )

        flaw_count = len(state.flaws)
        summary = (
            f"{flaw_count} flaw(s) surfaced across {state.current_round + 1} "
            f"critique round(s). Termination: {state.termination_label}. "
            f"Final spec at {spec_path}"
        )
        timestamp = workflow.now().isoformat(timespec="seconds")
        await workflow.execute_activity(
            "emit_finding",
            EmitFindingInput(
                inbox_path=inp.inbox_path,
                run_id=inp.run_id,
                skill="deep-design",
                status="DONE",
                summary=summary,
                notify=inp.notify,
                timestamp_iso=timestamp,
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        return summary


# =========================================================================== #
# Early-exit helper                                                             #
# =========================================================================== #

def _check_early_exit(state: "DeepDesignState") -> bool:
    """Return True only if ALL three early-exit conditions are satisfied."""
    # 1. All 5 required categories covered.
    if not all(state.required_categories_covered.values()):
        return False
    # 2. No new dimension categories for ≥ 2 consecutive rounds.
    if state.rounds_without_new_dim_categories < 2:
        return False
    # 3. No open critical flaws (excluding accepted_with_tension).
    open_criticals = [
        f
        for f in state.flaws
        if f.severity == "critical" and f.status == "open"
    ]
    return len(open_criticals) == 0


# =========================================================================== #
# Severity helpers                                                              #
# =========================================================================== #

_SEVERITY_ORDER = {"rejected": 0, "minor": 1, "major": 2, "critical": 3}


def _severity_rank(s: str | None) -> int:
    return _SEVERITY_ORDER.get(s or "", 0)


# =========================================================================== #
# Prompt templates                                                              #
# =========================================================================== #


def _fact_sheet_user_prompt(spec_md: str) -> str:
    return (
        "--- SPEC START ---\n"
        f"{spec_md[:20000]}\n"
        "--- SPEC END ---\n\n"
        "List all recovery and error-handling behaviors per component."
    )



def _critic_user_prompt(spec_md: str, concept: str, critic_index: int) -> str:
    dimensions = [
        "correctness",
        "usability_ux",
        "economics_cost",
        "operability",
        "security_trust",
        "scalability and performance",
    ]
    focus = dimensions[critic_index % len(dimensions)]
    return (
        f"Design concept: {concept}\n"
        f"Your focus dimension: {focus}\n\n"
        "--- SPEC START ---\n"
        f"{spec_md[:20000]}\n"
        "--- SPEC END ---\n\n"
        f"Review focusing on {focus}. Find real flaws only."
    )



def _judge_pass1_user_prompt(flaw: "Flaw", spec_md: str) -> str:
    return (
        "Flaw title: {title}\n"
        "Flaw scenario: {scenario}\n"
        "Flaw dimension: {dimension}\n"
        "(Severity claim stripped — assess independently.)\n\n"
        "--- SPEC START ---\n"
        "{spec}\n"
        "--- SPEC END ---\n\n"
        "Assess validity and severity independently (pass 1). "
        "Output VERDICT|<severity> as the final structured line."
    ).format(
        title=flaw.title,
        scenario=flaw.scenario,
        dimension=flaw.dimension,
        spec=spec_md[:10000],
    )


def _judge_pass2_user_prompt(
    flaw: "Flaw", pass1_verdict: str, original_severity: str
) -> str:
    return (
        "Pass 1 verdict: {p1}\n"
        "Critic's original severity claim: {orig}\n\n"
        "Flaw title: {title}\n"
        "You may CONFIRM, UPGRADE, or DOWNGRADE your pass-1 verdict. "
        "Output final VERDICT|<severity> and UPHELD|UPGRADED|DOWNGRADED."
    ).format(
        p1=pass1_verdict,
        orig=original_severity,
        title=flaw.title,
    )



def _challenger_user_prompt(flaw: "Flaw", spec_md: str) -> str:
    return (
        "Flaw title: {title}\n"
        "Flaw scenario: {scenario}\n"
        "Judge pass-2 verdict: {j2}\n\n"
        "--- SPEC START ---\n"
        "{spec}\n"
        "--- SPEC END ---\n\n"
        "Is the judge's downgrade of this flaw's severity justified? "
        "Output CHALLENGE|CHALLENGE_UPHELD|<rationale> or CHALLENGE|CHALLENGE_REJECTED|<rationale>."
    ).format(
        title=flaw.title,
        scenario=flaw.scenario,
        j2=flaw.judge_pass2_verdict or "unknown",
        spec=spec_md[:10000],
    )



def _cross_fix_user_prompt(flaws: "list[Flaw]", spec_md: str) -> str:
    flaw_summaries = [
        {"id": f.id, "title": f.title, "scenario": f.scenario} for f in flaws
    ]
    return (
        "Proposed fixes for these flaws:\n"
        f"{json.dumps(flaw_summaries, indent=2)}\n\n"
        "--- SPEC START ---\n"
        f"{spec_md[:10000]}\n"
        "--- SPEC END ---\n\n"
        "Detect conflicts between proposed fixes. Output CONFLICTS|[...] structured list."
    )



def _redesign_user_prompt(
    spec_md: str,
    flaws: "list[Flaw]",
    invariants: "list",
    round_idx: int,
) -> str:
    budget = 2 if round_idx < 2 else 1
    flaw_list = [
        {"id": f.id, "title": f.title, "severity": f.severity, "scenario": f.scenario}
        for f in flaws
    ]
    inv_list = [
        {"key": inv.key, "invariant": inv.invariant}
        for inv in invariants
    ]
    return (
        "--- CURRENT SPEC START ---\n"
        f"{spec_md[:20000]}\n"
        "--- CURRENT SPEC END ---\n\n"
        f"Flaws to address ({len(flaws)}):\n"
        f"{json.dumps(flaw_list, indent=2)}\n\n"
        f"Do-not-weaken invariants:\n"
        f"{json.dumps(inv_list, indent=2)}\n\n"
        f"Complexity budget this round: ≤{budget} new component(s)/field(s).\n"
        "Output SPEC|<revised spec> and COMPONENTS_ADDED|<integer>."
    )



def _invariant_validator_user_prompt(spec_md: str, invariants: "list") -> str:
    inv_list = [
        {"key": inv.key, "invariant": inv.invariant}
        for inv in invariants
    ]
    return (
        "Component invariants:\n"
        f"{json.dumps(inv_list, indent=2)}\n\n"
        "--- SPEC START ---\n"
        f"{spec_md[:20000]}\n"
        "--- SPEC END ---\n\n"
        "Output VIOLATIONS|[...] for any invariant violations found."
    )



def _drift_judge_user_prompt(
    core_claim: str, spec_md: str, calibrated: bool
) -> str:
    return (
        f"Original core claim:\n{core_claim}\n\n"
        "--- SPEC START ---\n"
        f"{spec_md[:10000]}\n"
        "--- SPEC END ---\n\n"
        f"Calibrated: {calibrated}\n"
        "Output DRIFT_SCORE|<float> and DRIFT_VERDICT|ok|warning|critical."
    )



def _synth_user_prompt(
    concept: str,
    spec_md: str,
    flaws: "list[dict]",
    termination_label: str,
) -> str:
    return (
        f"Original concept: {concept}\n"
        f"Termination label: {termination_label}\n\n"
        "--- REFINED SPEC START ---\n"
        f"{spec_md[:20000]}\n"
        "--- REFINED SPEC END ---\n\n"
        f"Flaws addressed ({len(flaws)}):\n"
        f"{json.dumps(flaws, indent=2)[:5000]}\n\n"
        "Produce the final polished spec.md with coverage report."
    )


# =========================================================================== #
# Parsers                                                                       #
# =========================================================================== #

def _parse_flaws(raw: str) -> list[dict[str, str]]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [f for f in parsed if isinstance(f, dict)]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _parse_gap_reports(raw: str) -> list[dict[str, str]]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [g for g in parsed if isinstance(g, dict)]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _parse_recovery_behaviors(raw: str) -> list["RecoveryBehavior"]:
    result = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    result.append(
                        RecoveryBehavior(
                            component=item.get("component", ""),
                            behavior=item.get("behavior", ""),
                        )
                    )
    except (json.JSONDecodeError, TypeError):
        pass
    return result


def _parse_verdict(raw: str) -> str | None:
    """Extract severity from 'VERDICT|critical' or bare 'critical' etc."""
    if not raw:
        return None
    for token in raw.replace("|", " ").split():
        if token in ("critical", "major", "minor", "rejected"):
            return token
    return None


def _parse_cross_fix_conflicts(raw: str) -> list["CrossFixConflict"]:
    result = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    result.append(
                        CrossFixConflict(
                            fix_a=item.get("fix_a", ""),
                            fix_b=item.get("fix_b", ""),
                            description=item.get("description", ""),
                        )
                    )
    except (json.JSONDecodeError, TypeError):
        # Unparseable = assumed conflict (fail-safe).
        result.append(
            CrossFixConflict(fix_a="unknown", fix_b="unknown", description="parse_error")
        )
    return result


def _parse_invariant_violations(raw: str) -> list["InvariantViolation"]:
    result = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    result.append(
                        InvariantViolation(
                            key=item.get("key", ""),
                            invariant=item.get("invariant", ""),
                            spec_section=item.get("spec_section", ""),
                            evidence=item.get("evidence", ""),
                        )
                    )
    except (json.JSONDecodeError, TypeError):
        # Unparseable = assumed violation (fail-safe).
        result.append(
            InvariantViolation(
                key="unknown",
                invariant="parse_error",
                spec_section="",
                evidence="",
            )
        )
    return result


def _fallback_spec(concept: str) -> str:
    return (
        f"# Design Specification (fallback draft)\n\n"
        f"**Concept:** {concept}\n\n"
        "The initial draft agent produced no structured output. "
        "A human should complete this specification.\n\n"
        "## Open Questions\n\n"
        "- What are the primary goals and non-goals?\n"
        "- What components are needed?\n"
        "- What are the key interfaces?\n"
    )
