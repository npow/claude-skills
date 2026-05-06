"""build-temporal: spec-driven build with plan/execute/verify/review loop.

Phases:
  1. Assess + Plan — Opus reads spec, produces task list as STRUCTURED_OUTPUT.
  2. Execute — parallel Sonnet agents, one per task, via asyncio.gather.
  3. Verify — Sonnet agent runs tests/lint against acceptance criteria.
  4. Review — Opus critic evaluates output quality.
  5. Fix loop — if review finds issues, re-execute failed tasks (max N iterations).
  6. Ship — emit finding to inbox.
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
    from sagaflow.slack_progress import ReportSlackProgressInput
    from .state import BuildState, Task

_PROGRESS_TITLE = "build"
_PROGRESS_PHASES = [
    "Assess + plan",
    "Execute tasks",
    "Verify output",
    "Review quality",
    "Ship",
]


async def _report_progress(
    run_dir: str, phase_idx: int, status: str = "in_progress",
    detail: str = "", final: bool = False, *, _steps: list[dict] | None = None,
) -> list[dict]:
    if _steps is None:
        _steps = [{"name": n, "status": "pending", "detail": "", "elapsed_s": 0.0}
                  for n in _PROGRESS_PHASES]
    _steps[phase_idx]["status"] = status
    if detail:
        _steps[phase_idx]["detail"] = detail
    try:
        await workflow.execute_activity(
            "report_slack_progress",
            ReportSlackProgressInput(run_dir=run_dir, title=_PROGRESS_TITLE,
                steps=tuple(_steps), final=final),
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=HAIKU_POLICY,
        )
    except Exception:
        pass
    return _steps


async def _write(path: str, content: str) -> None:
    await workflow.execute_activity(
        "write_artifact",
        WriteArtifactInput(path=path, content=content),
        start_to_close_timeout=timedelta(seconds=30),
        retry_policy=HAIKU_POLICY,
    )


async def _spawn(
    *, role: str, tier: str, system_prompt: str, prompt_path: str,
    max_tokens: int = 128000, tools_needed: bool = False,
) -> dict[str, str]:
    result = await workflow.execute_activity(
        "spawn_subagent",
        SpawnSubagentInput(
            role=role,
            tier_name=tier,
            system_prompt=system_prompt,
            user_prompt_path=prompt_path,
            max_tokens=max_tokens,
            tools_needed=tools_needed,
        ),
        start_to_close_timeout=timedelta(minutes=15),
        retry_policy=SONNET_POLICY,
    )
    if isinstance(result, dict):
        return result
    return {}


async def _emit(
    *, inbox_path: str, run_id: str, skill: str, status: str, summary: str,
    notify: bool = True,
) -> None:
    await workflow.execute_activity(
        "emit_finding",
        EmitFindingInput(
            inbox_path=inbox_path,
            run_id=run_id,
            skill=skill,
            status=status,
            summary=summary,
            notify=notify,
            timestamp_iso=workflow.now().isoformat(timespec="seconds"),
        ),
        start_to_close_timeout=timedelta(seconds=30),
        retry_policy=HAIKU_POLICY,
    )


@dataclass(frozen=True)
class BuildInput:
    run_id: str
    spec: str
    inbox_path: str
    run_dir: str
    max_iterations: int = 3
    notify: bool = True


@workflow.defn(name="BuildWorkflow")
class BuildWorkflow:

    @workflow.run
    async def run(self, inp: BuildInput) -> str:
        run_dir = inp.run_dir
        state = BuildState(
            run_id=inp.run_id,
            skill="build",
            spec=inp.spec,
            max_iterations=inp.max_iterations,
        )
        spec_path = f"{run_dir}/spec.md"
        plan_path = f"{run_dir}/plan.md"
        verify_path = f"{run_dir}/verify.md"
        state.plan_path = plan_path

        await _write(spec_path, inp.spec)

        steps = await _report_progress(run_dir, 0, "in_progress")

        # ------------------------------------------------------------------ #
        # Phase 1 — Assess + Plan                                             #
        # ------------------------------------------------------------------ #
        plan_prompt_path = f"{run_dir}/plan-prompt.txt"
        await _write(plan_prompt_path,
            f"Spec file: {spec_path}\n"
            "Read the spec file above carefully.\n\n"
            "Produce a build plan: decompose the spec into atomic, independently "
            "executable tasks. Each task must have clear acceptance criteria.\n\n"
            "Also write a human-readable plan summary to: " + plan_path + "\n\n"
            "STRUCTURED_OUTPUT_START\n"
            "TASKS|<json array of {id, description, acceptance_criteria}>\n"
            "STRUCTURED_OUTPUT_END\n"
        )
        plan_result = await _spawn(
            role="planner",
            tier="OPUS",
            system_prompt=(
                "You are a build planner. Decompose specs into atomic executable tasks. "
                "STRUCTURED_OUTPUT_START\n"
                "TASKS|<json array of {id, description, acceptance_criteria}>\n"
                "STRUCTURED_OUTPUT_END"
            ),
            prompt_path=plan_prompt_path,
            tools_needed=True,
        )
        raw_tasks = plan_result.get("TASKS", "[]")
        try:
            tasks_list = json.loads(raw_tasks)
        except json.JSONDecodeError:
            tasks_list = []

        for t in tasks_list:
            state.tasks.append(Task(
                id=str(t.get("id", f"task_{len(state.tasks)}")),
                description=str(t.get("description", "")),
                acceptance_criteria=str(t.get("acceptance_criteria", "")),
            ))

        steps = await _report_progress(run_dir, 0, "completed",
            detail=f"{len(state.tasks)} tasks planned")

        # ------------------------------------------------------------------ #
        # Phase 2-4 — Execute / Verify / Review loop                          #
        # ------------------------------------------------------------------ #
        while state.iteration < state.max_iterations:
            state.iteration += 1
            state.current_phase = "execute"

            # Phase 2 — Execute tasks in parallel
            steps = await _report_progress(run_dir, 1, "in_progress",
                detail=f"iteration {state.iteration}", _steps=steps)

            pending = [t for t in state.tasks if t.status in ("pending", "failed")]
            if not pending:
                break

            async def _execute_task(task: Task) -> None:
                task.status = "in_progress"
                output_path = f"{run_dir}/task-{task.id}-output.md"
                task.output_path = output_path
                prompt_path = f"{run_dir}/task-{task.id}-prompt.txt"
                await _write(prompt_path,
                    f"Spec file: {spec_path}\n"
                    f"Plan file: {plan_path}\n"
                    "Read both files above for context.\n\n"
                    f"Task ID: {task.id}\n"
                    f"Task description: {task.description}\n"
                    f"Acceptance criteria: {task.acceptance_criteria}\n\n"
                    "Implement this task completely. Use all tools needed.\n"
                    f"Write your implementation output/summary to: {output_path}\n"
                )
                try:
                    await _spawn(
                        role=f"executor-{task.id}",
                        tier="SONNET",
                        system_prompt=(
                            "You are a build executor. Implement the assigned task completely "
                            "using all available tools. Write output to the specified file."
                        ),
                        prompt_path=prompt_path,
                        tools_needed=True,
                    )
                    task.status = "completed"
                except Exception:
                    task.status = "failed"

            await asyncio.gather(*[_execute_task(t) for t in pending])

            completed = [t for t in state.tasks if t.status == "completed"]
            steps = await _report_progress(run_dir, 1, "completed",
                detail=f"{len(completed)}/{len(state.tasks)} completed", _steps=steps)

            # Phase 3 — Verify
            state.current_phase = "verify"
            steps = await _report_progress(run_dir, 2, "in_progress",
                detail=f"iteration {state.iteration}", _steps=steps)

            outputs_list = "\n".join(
                f"- Task {t.id}: {t.output_path}"
                for t in state.tasks if t.status == "completed" and t.output_path
            )
            verify_prompt_path = f"{run_dir}/verify-prompt.txt"
            await _write(verify_prompt_path,
                f"Spec file: {spec_path}\n"
                f"Plan file: {plan_path}\n"
                "Read both files above for context.\n\n"
                "Verify that task outputs meet their acceptance criteria.\n\n"
                f"Task output files:\n{outputs_list}\n\n"
                "Run tests, linting, or checks as appropriate.\n"
                f"Write verification results to: {verify_path}\n\n"
                "STRUCTURED_OUTPUT_START\n"
                "VERIFY_VERDICT|PASSED or FAILED\n"
                "FAILED_TASKS|<json array of task ids that failed verification>\n"
                "STRUCTURED_OUTPUT_END\n"
            )
            verify_result = await _spawn(
                role="verifier",
                tier="SONNET",
                system_prompt=(
                    "You verify build outputs against acceptance criteria. Run tests and checks. "
                    "STRUCTURED_OUTPUT_START\n"
                    "VERIFY_VERDICT|PASSED or FAILED\n"
                    "FAILED_TASKS|<json array of task ids that failed verification>\n"
                    "STRUCTURED_OUTPUT_END"
                ),
                prompt_path=verify_prompt_path,
                tools_needed=True,
            )

            verify_verdict = verify_result.get("VERIFY_VERDICT", "PASSED").strip()
            steps = await _report_progress(run_dir, 2, "completed",
                detail=verify_verdict, _steps=steps)

            # Phase 4 — Review
            state.current_phase = "review"
            steps = await _report_progress(run_dir, 3, "in_progress",
                detail=f"iteration {state.iteration}", _steps=steps)

            review_prompt_path = f"{run_dir}/review-prompt.txt"
            await _write(review_prompt_path,
                f"Spec file: {spec_path}\n"
                f"Plan file: {plan_path}\n"
                f"Verification results: {verify_path}\n"
                "Read all files above.\n\n"
                f"Task output files:\n{outputs_list}\n\n"
                "Review the overall build quality:\n"
                "- Does the output fully satisfy the spec?\n"
                "- Are there correctness issues?\n"
                "- Are there missing edge cases?\n"
                "- Is the code/output clean and maintainable?\n\n"
                "STRUCTURED_OUTPUT_START\n"
                "REVIEW_VERDICT|APPROVED or ISSUES_FOUND\n"
                "ISSUES|<json array of {task_id, description, severity}>\n"
                "STRUCTURED_OUTPUT_END\n"
            )
            review_result = await _spawn(
                role="reviewer",
                tier="OPUS",
                system_prompt=(
                    "You are a build quality reviewer. Critically assess outputs against spec. "
                    "STRUCTURED_OUTPUT_START\n"
                    "REVIEW_VERDICT|APPROVED or ISSUES_FOUND\n"
                    "ISSUES|<json array of {task_id, description, severity}>\n"
                    "STRUCTURED_OUTPUT_END"
                ),
                prompt_path=review_prompt_path,
                tools_needed=True,
            )

            review_verdict = review_result.get("REVIEW_VERDICT", "APPROVED").strip()
            raw_issues = review_result.get("ISSUES", "[]")
            try:
                issues_list = json.loads(raw_issues)
            except json.JSONDecodeError:
                issues_list = []

            state.review_findings = issues_list

            steps = await _report_progress(run_dir, 3, "completed",
                detail=review_verdict, _steps=steps)

            if review_verdict == "APPROVED" and verify_verdict == "PASSED":
                state.termination_label = "Review approved"
                break

            # Mark failed tasks for re-execution
            failed_ids_raw = verify_result.get("FAILED_TASKS", "[]")
            try:
                failed_ids = set(json.loads(failed_ids_raw))
            except json.JSONDecodeError:
                failed_ids = set()
            for issue in issues_list:
                tid = str(issue.get("task_id", ""))
                if tid:
                    failed_ids.add(tid)

            for task in state.tasks:
                if task.id in failed_ids:
                    task.status = "failed"

        if not state.termination_label:
            state.termination_label = (
                f"Max iterations ({state.max_iterations}) reached"
                if state.iteration >= state.max_iterations
                else "All tasks completed"
            )

        # ------------------------------------------------------------------ #
        # Phase 5 — Ship                                                      #
        # ------------------------------------------------------------------ #
        steps = await _report_progress(run_dir, 4, "in_progress", _steps=steps)

        completed_count = sum(1 for t in state.tasks if t.status == "completed")
        summary = (
            f"build: {state.termination_label}\n"
            f"Tasks: {completed_count}/{len(state.tasks)} completed, "
            f"Iterations: {state.iteration}, "
            f"Issues: {len(state.review_findings)}"
        )
        await _emit(
            inbox_path=inp.inbox_path,
            run_id=inp.run_id,
            skill="build",
            status=state.termination_label,
            summary=summary,
            notify=inp.notify,
        )

        steps = await _report_progress(run_dir, 4, "completed",
            detail=state.termination_label, final=True, _steps=steps)

        return summary
