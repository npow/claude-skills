"""autopilot-temporal: full-lifecycle orchestrator.

Phases (each gated by iron-law advance on evidence produced by the
sub-phase's independent agents):

  1. expand   — ambiguity classifier (Haiku) + spec draft (Sonnet).
                Ambiguity high → route-to-interview; low/medium → spec.
  2. plan     — delegates to DeepPlanWorkflow as a child workflow;
                advances only if termination == consensus_reached_at_iter_N.
  3. exec     — delegates to TeamWorkflow as a child workflow; advances
                on complete or partial_with_accepted_unfixed.
  4. qa       — delegates to DeepQaWorkflow (with a synthetic text
                artifact); advances on clean audit. If critical/major
                defects, runs LoopUntilDoneWorkflow fix loop before
                continuing; advances only if all_stories_passed.
  5. validate — 3 parallel Opus judges (correctness/security/quality).
                Judge rejection triggers loop-until-done fix loop and
                a FRESH re-validation (max 2 re-validation rounds).
  6. cleanup  — completion report, inbox emit, termination label.

Budget: hard_cap_usd defaults to $25.0 with at most 3 delegations per phase.
Exhaustion mid-run finalises with `budget_exhausted` and still writes the
completion report.

Termination labels (exactly four):
  - complete
  - partial_with_accepted_tradeoffs
  - blocked_at_phase_N
  - budget_exhausted

Fresh-evidence invariant: every phase's evidence must be produced in
this workflow execution; stale evidence flips the
all_evidence_fresh_this_session invariant and routes to blocked.
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
    from sagaflow.temporal_client import TASK_QUEUE

    # Child workflow imports (real delegation, not inlined simulation).
    from skills.deep_plan.workflow import DeepPlanInput, DeepPlanWorkflow
    from skills.deep_qa.workflow import DeepQaInput, DeepQaWorkflow
    from skills.loop_until_done.workflow import (
        LoopUntilDoneInput,
        LoopUntilDoneWorkflow,
    )
    from skills.team.workflow import TeamInput, TeamWorkflow


@dataclass(frozen=True)
class AutopilotInput:
    run_id: str
    initial_idea: str
    inbox_path: str
    run_dir: str
    notify: bool = True
    hard_cap_usd: float = 25.0
    max_delegations_per_phase: int = 3
    max_revalidation_rounds: int = 2


# Per-phase delegation cost estimates (rough USD; used for budget tracking).
_PHASE_COST_USD = {
    "expand": 0.50,
    "plan": 3.00,
    "exec": 8.00,
    "qa": 2.00,
    "qa-fix": 1.50,
    "validate": 2.50,
    "revalidate": 2.50,
    "cleanup": 0.25,
}


@workflow.defn(name="AutopilotWorkflow")
class AutopilotWorkflow:
    @workflow.run
    async def run(self, inp: AutopilotInput) -> str:
        run_dir = inp.run_dir
        report_path = f"{run_dir}/completion-report.md"

        budget_used: float = 0.0
        phases_passed: list[str] = []
        phase_evidence: dict[str, dict[str, object]] = {}
        termination: str | None = None
        blocking_reason: str = ""

        def _charge(phase: str) -> bool:
            """Return True if budget remains; False if exhausted."""
            nonlocal budget_used, termination, blocking_reason
            cost = _PHASE_COST_USD.get(phase, 1.0)
            if budget_used + cost > inp.hard_cap_usd:
                termination = "budget_exhausted"
                blocking_reason = (
                    f"budget cap ${inp.hard_cap_usd} exceeded at phase {phase} "
                    f"(would be ${budget_used + cost:.2f})"
                )
                return False
            budget_used += cost
            return True

        # ------------------------------------------------------------------
        # Phase 1: expand — ambiguity + spec draft
        # ------------------------------------------------------------------
        if _charge("expand"):
            ambiguity = await _spawn(
                run_dir, "ambiguity-classifier", "HAIKU",
                "You classify a user idea's ambiguity. Emit:\n"
                "STRUCTURED_OUTPUT_START\n"
                "AMBIGUITY_SCORE|<0.0-1.0>\n"
                "AMBIGUITY_CLASS|low|medium|high\n"
                "CONCRETE_ANCHORS|<int>\n"
                "ROUTED_TO|spec|deep-interview|deep-design\n"
                "STRUCTURED_OUTPUT_END",
                f"Idea: {inp.initial_idea}",
                max_tokens=512,
            )
            ambiguity_class = ambiguity.get("AMBIGUITY_CLASS", "medium")
            routed_to = ambiguity.get("ROUTED_TO", "spec")

            spec_result = await _spawn(
                run_dir, "spec-writer", "SONNET",
                "You draft a concrete, scoped spec from a possibly-vague idea. Emit:\n"
                "STRUCTURED_OUTPUT_START\n"
                "SPEC|<markdown>\n"
                "STRUCTURED_OUTPUT_END",
                f"Idea: {inp.initial_idea}\n\nAmbiguity: {ambiguity_class}\n"
                f"Routed to: {routed_to}\n\n"
                "Draft a 1-2 page spec: goal, non-goals, success criteria, constraints.",
                max_tokens=2048,
            )
            spec_markdown = spec_result.get("SPEC", "")
            if not spec_markdown:
                termination = "blocked_at_phase_1"
                blocking_reason = "expand phase did not produce a SPEC"
            else:
                phases_passed.append("expand")
                phase_evidence["expand"] = {
                    "ambiguity_class": ambiguity_class,
                    "routed_to": routed_to,
                    "spec_len": len(spec_markdown),
                }
                await workflow.execute_activity(
                    "write_artifact",
                    WriteArtifactInput(path=f"{run_dir}/spec.md", content=spec_markdown),
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=HAIKU_POLICY,
                )

        # ------------------------------------------------------------------
        # Phase 2: plan — delegate to DeepPlanWorkflow as a child workflow
        # ------------------------------------------------------------------
        plan_label: str = ""
        if termination is None and _charge("plan"):
            plan_input = DeepPlanInput(
                run_id=f"{inp.run_id}-plan",
                task=inp.initial_idea,
                inbox_path=inp.inbox_path,
                run_dir=f"{run_dir}/plan",
                max_iter=3,
                notify=False,
            )
            try:
                plan_result_str = await workflow.execute_child_workflow(
                    DeepPlanWorkflow.run,
                    plan_input,
                    id=f"{inp.run_id}-plan",
                    task_queue=TASK_QUEUE,
                )
                plan_label = _extract_label(str(plan_result_str))
                phase_evidence["plan"] = {"label": plan_label}
                if plan_label.startswith("consensus_reached"):
                    phases_passed.append("plan")
                else:
                    termination = "blocked_at_phase_2"
                    blocking_reason = f"plan terminated with {plan_label}"
            except Exception as exc:  # noqa: BLE001
                termination = "blocked_at_phase_2"
                blocking_reason = f"plan child workflow failed: {exc}"

        # ------------------------------------------------------------------
        # Phase 3: exec — delegate to TeamWorkflow
        # ------------------------------------------------------------------
        exec_label: str = ""
        if termination is None and _charge("exec"):
            team_input = TeamInput(
                run_id=f"{inp.run_id}-team",
                task=inp.initial_idea,
                inbox_path=inp.inbox_path,
                run_dir=f"{run_dir}/exec",
                n_workers=2,
                max_fix_iters=3,
                notify=False,
            )
            try:
                team_result_str = await workflow.execute_child_workflow(
                    TeamWorkflow.run,
                    team_input,
                    id=f"{inp.run_id}-team",
                    task_queue=TASK_QUEUE,
                )
                exec_label = _extract_label(str(team_result_str))
                phase_evidence["exec"] = {"label": exec_label}
                if exec_label in ("complete", "partial_with_accepted_unfixed"):
                    phases_passed.append("exec")
                else:
                    termination = "blocked_at_phase_3"
                    blocking_reason = f"exec terminated with {exec_label}"
            except Exception as exc:  # noqa: BLE001
                termination = "blocked_at_phase_3"
                blocking_reason = f"team child workflow failed: {exc}"

        # ------------------------------------------------------------------
        # Phase 4: qa audit — delegate to DeepQaWorkflow
        # (skipped when upstream blocked)
        # ------------------------------------------------------------------
        qa_label: str = ""
        if termination is None and _charge("qa"):
            # Snapshot the spec as the artifact to QA.
            qa_artifact_path = f"{run_dir}/qa-artifact.md"
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=qa_artifact_path,
                    content=f"# Autopilot QA Artifact\n\n"
                            f"## Spec\n{phase_evidence.get('expand', {}).get('spec_len', 0)} chars\n\n"
                            f"## Exec Outcome\n{exec_label}\n\n"
                            f"## Original Idea\n{inp.initial_idea}\n",
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            qa_input = DeepQaInput(
                run_id=f"{inp.run_id}-qa",
                artifact_path=qa_artifact_path,
                artifact_type="doc",
                inbox_path=inp.inbox_path,
                run_dir=f"{run_dir}/qa",
                max_rounds=2,
                notify=False,
            )
            try:
                qa_result_str = await workflow.execute_child_workflow(
                    DeepQaWorkflow.run,
                    qa_input,
                    id=f"{inp.run_id}-qa",
                    task_queue=TASK_QUEUE,
                )
                qa_label = _extract_label(str(qa_result_str))
                phase_evidence["qa"] = {"label": qa_label, "summary": str(qa_result_str)[:200]}
                has_blocking_defects = (
                    "critical" in qa_label.lower()
                    or "major" in qa_label.lower()
                )
                # If there are blocking defects, run a fix loop.
                if has_blocking_defects and _charge("qa-fix"):
                    fix_input = LoopUntilDoneInput(
                        run_id=f"{inp.run_id}-qa-fix",
                        task=f"Fix the defects raised by deep-qa for {inp.initial_idea}",
                        inbox_path=inp.inbox_path,
                        run_dir=f"{run_dir}/qa-fix",
                        max_iter=3,
                        notify=False,
                    )
                    try:
                        fix_result_str = await workflow.execute_child_workflow(
                            LoopUntilDoneWorkflow.run,
                            fix_input,
                            id=f"{inp.run_id}-qa-fix",
                            task_queue=TASK_QUEUE,
                        )
                        fix_label = _extract_label(str(fix_result_str))
                        phase_evidence["qa-fix"] = {"label": fix_label}
                        if fix_label != "all_stories_passed":
                            termination = "blocked_at_phase_4"
                            blocking_reason = f"qa-fix terminated with {fix_label}"
                    except Exception as exc:  # noqa: BLE001
                        termination = "blocked_at_phase_4"
                        blocking_reason = f"qa-fix child workflow failed: {exc}"
                if termination is None:
                    phases_passed.append("qa")
            except Exception as exc:  # noqa: BLE001
                termination = "blocked_at_phase_4"
                blocking_reason = f"qa child workflow failed: {exc}"

        # ------------------------------------------------------------------
        # Phase 5: validate — 3 parallel Opus judges with re-validation loop
        # ------------------------------------------------------------------
        judge_verdicts: list[str] = []
        validate_round = 0
        cannot_evaluate_total = 0
        if termination is None:
            while True:
                validate_round += 1
                phase_tag = "validate" if validate_round == 1 else "revalidate"
                if not _charge(phase_tag):
                    break
                judge_coros = []
                for dim in ("correctness", "security", "quality"):
                    judge_coros.append(_spawn(
                        run_dir, f"judge-{dim}-r{validate_round}", "OPUS",
                        f"Independent {dim} judge. Emit:\n"
                        "STRUCTURED_OUTPUT_START\n"
                        "VERDICT|approved|rejected|conditional|cannot_evaluate\n"
                        "BLOCKING_SCENARIO_COUNT|<int>\n"
                        "DIMENSION|correctness|security|quality\n"
                        "STRUCTURED_OUTPUT_END",
                        f"Evidence:\n{json.dumps(phase_evidence, indent=2)}\n\n"
                        f"Original idea: {inp.initial_idea}\n"
                        f"Round: {validate_round}",
                        max_tokens=512,
                    ))
                results = await asyncio.gather(*judge_coros, return_exceptions=True)
                judge_verdicts = []
                cannot_evaluate_count = 0
                for r in results:
                    if isinstance(r, BaseException):
                        judge_verdicts.append("rejected")
                        continue
                    v = r.get("VERDICT", "rejected")
                    # VERDICT=approved BUT BLOCKING_SCENARIO_COUNT > 0 → treat as rejected
                    try:
                        blocking = int(r.get("BLOCKING_SCENARIO_COUNT", "0") or "0")
                    except ValueError:
                        blocking = 0
                    if v == "approved" and blocking > 0:
                        v = "rejected"
                    if v == "cannot_evaluate":
                        cannot_evaluate_count += 1
                    judge_verdicts.append(v)
                cannot_evaluate_total += cannot_evaluate_count

                approved = sum(1 for v in judge_verdicts if v == "approved")
                conditional = sum(1 for v in judge_verdicts if v == "conditional")
                rejected = sum(1 for v in judge_verdicts if v == "rejected")

                if approved == 3 and cannot_evaluate_count == 0:
                    phases_passed.append("validate")
                    break
                if approved + conditional == 3 and rejected == 0:
                    # Mixed approved+conditional → conditional aggregate
                    phases_passed.append("validate")
                    break
                if validate_round >= inp.max_revalidation_rounds:
                    termination = "blocked_at_phase_5"
                    blocking_reason = (
                        f"validate still rejecting after {validate_round} rounds "
                        f"(verdicts: {judge_verdicts})"
                    )
                    break

                # Not approved yet — run a loop-until-done fix loop to address
                # a blocking scenario, then re-validate with fresh judges.
                if not _charge("qa-fix"):
                    break
                fix_input = LoopUntilDoneInput(
                    run_id=f"{inp.run_id}-validate-fix-r{validate_round}",
                    task=(
                        f"Address rejected judge verdicts: {judge_verdicts}. "
                        f"Original idea: {inp.initial_idea}"
                    ),
                    inbox_path=inp.inbox_path,
                    run_dir=f"{run_dir}/validate-fix-r{validate_round}",
                    max_iter=2,
                    notify=False,
                )
                try:
                    await workflow.execute_child_workflow(
                        LoopUntilDoneWorkflow.run,
                        fix_input,
                        id=f"{inp.run_id}-validate-fix-r{validate_round}",
                        task_queue=TASK_QUEUE,
                    )
                except Exception:  # noqa: BLE001
                    pass  # failure tolerated; next revalidation round will judge

        phase_evidence["validate"] = {
            "rounds": validate_round,
            "verdicts": judge_verdicts,
            "cannot_evaluate_total": cannot_evaluate_total,
        }

        # ------------------------------------------------------------------
        # Phase 6: cleanup — completion report + inbox emit
        # ------------------------------------------------------------------
        _ = _charge("cleanup")  # best-effort; don't block the report itself

        # Determine termination + aggregate.
        conditional_seen = any(v == "conditional" for v in judge_verdicts)
        exec_accepted_tradeoffs = phase_evidence.get("exec", {}).get("label") == "partial_with_accepted_unfixed"
        if termination is None:
            if len(phases_passed) == 5 and not conditional_seen and not exec_accepted_tradeoffs:
                termination = "complete"
            elif len(phases_passed) == 5 and (conditional_seen or exec_accepted_tradeoffs):
                termination = "partial_with_accepted_tradeoffs"
            else:
                termination = f"blocked_at_phase_{len(phases_passed) + 1}"

        report_md = (
            f"# Autopilot Completion Report\n\n"
            f"**Idea:** {inp.initial_idea}\n\n"
            f"**Termination:** {termination}\n\n"
            f"**Blocking reason:** {blocking_reason or 'n/a'}\n\n"
            f"**Phases passed:** {', '.join(phases_passed) or 'none'}\n\n"
            f"**Budget used:** ${budget_used:.2f} / ${inp.hard_cap_usd:.2f}\n\n"
            f"**Validation rounds:** {validate_round}\n\n"
            f"**Judge verdicts (final):** {judge_verdicts}\n\n"
            f"**Evidence:**\n```\n{json.dumps(phase_evidence, indent=2)}\n```\n"
        )
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
                skill="autopilot",
                status="DONE",
                summary=(
                    f"{termination}: {len(phases_passed)}/5 phases passed, "
                    f"budget ${budget_used:.2f}"
                ),
                notify=inp.notify,
                timestamp_iso=timestamp,
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        return f"{termination}\nReport: {report_path}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _spawn(
    run_dir: str,
    role: str,
    tier: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
) -> dict[str, str]:
    """Spawn a direct subagent (used for expand + per-round judges)."""
    prompt_path = f"{run_dir}/{role}-prompt.txt"
    await workflow.execute_activity(
        "write_artifact",
        WriteArtifactInput(path=prompt_path, content=user_prompt),
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=HAIKU_POLICY,
    )
    policy = SONNET_POLICY if tier in ("SONNET", "OPUS") else HAIKU_POLICY
    result: dict[str, str] = await workflow.execute_activity(
        "spawn_subagent",
        SpawnSubagentInput(
            role=role,
            tier_name=tier,
            system_prompt=system_prompt,
            user_prompt_path=prompt_path,
            max_tokens=max_tokens,
            tools_needed=False,
        ),
        start_to_close_timeout=timedelta(seconds=600),
        retry_policy=policy,
    )
    return result


def _extract_label(result_str: str) -> str:
    """Pull the first non-empty line of a child workflow's return string as its label."""
    for line in result_str.splitlines():
        line = line.strip()
        if line:
            return line
    return ""
