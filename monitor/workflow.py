"""monitor-temporal: health monitoring with optional recurring loop.

Phases:
  1. Gather — Sonnet agent collects health data using all available tools.
  2. Assess — Haiku agent evaluates metrics against thresholds.
  3. Report — Haiku agent writes formatted health report.
  4. Emit finding to inbox.
  If recurring=True, sleep interval_seconds and repeat from Phase 1.
"""

from __future__ import annotations

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
    from .state import MonitorState

_PROGRESS_TITLE = "monitor"
_PROGRESS_PHASES = [
    "Gather health data",
    "Assess thresholds",
    "Write report",
    "Emit finding",
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
        start_to_close_timeout=timedelta(minutes=10),
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
class MonitorInput:
    run_id: str
    target: str
    inbox_path: str
    run_dir: str
    preset: str = "auto"
    recurring: bool = False
    interval_seconds: int = 300
    notify: bool = True


@workflow.defn(name="MonitorWorkflow")
class MonitorWorkflow:

    @workflow.run
    async def run(self, inp: MonitorInput) -> str:
        run_dir = inp.run_dir
        state = MonitorState(
            run_id=inp.run_id,
            skill="monitor",
            target=inp.target,
            preset=inp.preset,
            recurring=inp.recurring,
            interval_seconds=inp.interval_seconds,
        )

        cycle = 0
        last_summary = ""

        while True:
            cycle += 1
            timestamp = workflow.now().strftime("%Y%m%d-%H%M%S")
            report_path = f"{run_dir}/report-{timestamp}.md"
            state.report_path = report_path

            steps = await _report_progress(run_dir, 0, "in_progress",
                detail=f"cycle {cycle}")

            # ---------------------------------------------------------------- #
            # Phase 1 — Gather health data                                     #
            # ---------------------------------------------------------------- #
            target_path = f"{run_dir}/target.md"
            await _write(target_path,
                f"Monitor target: {inp.target}\n"
                f"Preset: {inp.preset}\n"
                f"Cycle: {cycle}\n"
            )
            gather_prompt_path = f"{run_dir}/gather-{cycle}-prompt.txt"
            await _write(gather_prompt_path,
                f"Target file: {target_path}\n"
                "Read the target file above.\n\n"
                f"Gather comprehensive health data for: {inp.target}\n"
                f"Monitoring preset: {inp.preset}\n\n"
                "Collect all relevant metrics, logs, error rates, latency, "
                "resource usage, and any anomalies using all available tools.\n\n"
                "STRUCTURED_OUTPUT_START\n"
                "METRICS|<json array of {name, value, threshold, status}>\n"
                "HEALTH_RATING|healthy or degraded or critical\n"
                "STRUCTURED_OUTPUT_END\n\n"
                f"Also write raw gathered data to: {run_dir}/raw-data-{cycle}.md\n"
            )
            gather_result = await _spawn(
                role=f"gatherer-{cycle}",
                tier="SONNET",
                system_prompt=(
                    "You gather health metrics and system data using all available tools. "
                    "STRUCTURED_OUTPUT_START\n"
                    "METRICS|<json array of {name, value, threshold, status}>\n"
                    "HEALTH_RATING|healthy or degraded or critical\n"
                    "STRUCTURED_OUTPUT_END"
                ),
                prompt_path=gather_prompt_path,
                tools_needed=True,
            )

            raw_metrics = gather_result.get("METRICS", "[]")
            state.health_rating = gather_result.get("HEALTH_RATING", "unknown").strip()

            steps = await _report_progress(run_dir, 0, "completed",
                detail=f"health={state.health_rating}", _steps=steps)

            # ---------------------------------------------------------------- #
            # Phase 2 — Assess thresholds                                      #
            # ---------------------------------------------------------------- #
            steps = await _report_progress(run_dir, 1, "in_progress", _steps=steps)

            assess_prompt_path = f"{run_dir}/assess-{cycle}-prompt.txt"
            await _write(assess_prompt_path,
                f"Target: {inp.target}\n"
                f"Preset: {inp.preset}\n"
                f"Raw metrics JSON: {raw_metrics}\n\n"
                "Evaluate each metric against its threshold. "
                "Identify which are healthy, degraded, or critical.\n"
                "Note any trends or concerning patterns.\n\n"
                "STRUCTURED_OUTPUT_START\n"
                "ASSESSMENT|<json object with overall_status, critical_count, "
                "degraded_count, healthy_count, key_findings>\n"
                "STRUCTURED_OUTPUT_END\n"
            )
            assess_result = await _spawn(
                role=f"assessor-{cycle}",
                tier="HAIKU",
                system_prompt=(
                    "You assess health metrics against thresholds and identify issues. "
                    "STRUCTURED_OUTPUT_START\n"
                    "ASSESSMENT|<json object with overall_status, critical_count, "
                    "degraded_count, healthy_count, key_findings>\n"
                    "STRUCTURED_OUTPUT_END"
                ),
                prompt_path=assess_prompt_path,
                tools_needed=False,
            )

            assessment_raw = assess_result.get("ASSESSMENT", "{}")
            steps = await _report_progress(run_dir, 1, "completed",
                detail="assessment complete", _steps=steps)

            # ---------------------------------------------------------------- #
            # Phase 3 — Write report                                           #
            # ---------------------------------------------------------------- #
            steps = await _report_progress(run_dir, 2, "in_progress", _steps=steps)

            report_prompt_path = f"{run_dir}/report-{cycle}-prompt.txt"
            await _write(report_prompt_path,
                f"Target: {inp.target}\n"
                f"Preset: {inp.preset}\n"
                f"Cycle: {cycle}\n"
                f"Timestamp: {timestamp}\n"
                f"Health rating: {state.health_rating}\n"
                f"Metrics: {raw_metrics}\n"
                f"Assessment: {assessment_raw}\n\n"
                "Write a clear health report with:\n"
                "- Executive summary (one sentence)\n"
                "- Overall health status\n"
                "- Critical issues (if any) with recommended actions\n"
                "- Degraded metrics with context\n"
                "- Healthy metrics summary\n"
                "- Recommendations\n\n"
                f"Write the report to: {report_path}\n"
            )
            await _spawn(
                role=f"reporter-{cycle}",
                tier="HAIKU",
                system_prompt="You write concise health monitoring reports.",
                prompt_path=report_prompt_path,
                tools_needed=True,
            )

            steps = await _report_progress(run_dir, 2, "completed",
                detail=f"report at {report_path}", _steps=steps)

            # ---------------------------------------------------------------- #
            # Phase 4 — Emit finding                                           #
            # ---------------------------------------------------------------- #
            steps = await _report_progress(run_dir, 3, "in_progress", _steps=steps)

            state.termination_label = (
                f"cycle {cycle}: {state.health_rating}"
                if inp.recurring else state.health_rating
            )
            last_summary = (
                f"monitor: {inp.target} — {state.health_rating}\n"
                f"Cycle: {cycle}, Preset: {inp.preset}, "
                f"Report: {report_path}"
            )
            await _emit(
                inbox_path=inp.inbox_path,
                run_id=inp.run_id,
                skill="monitor",
                status=state.termination_label,
                summary=last_summary,
                notify=inp.notify,
            )

            is_final = not inp.recurring
            steps = await _report_progress(run_dir, 3, "completed",
                detail=state.termination_label, final=is_final, _steps=steps)

            if not inp.recurring:
                break

            # Reset steps for next cycle and sleep
            steps = None
            await workflow.sleep(timedelta(seconds=inp.interval_seconds))

        return last_summary
