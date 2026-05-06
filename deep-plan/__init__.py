"""deep-plan-temporal skill registration."""

from __future__ import annotations

from typing import Any

from sagaflow.durable.activities import emit_finding, spawn_subagent, write_artifact
from sagaflow.slack_progress import report_slack_progress
from sagaflow.registry import SkillRegistry, SkillSpec

from .workflow import DeepPlanInput, DeepPlanWorkflow


def _build_input(
    *, run_id: str, run_dir: str, inbox_path: str, cli_args: dict[str, Any]
) -> DeepPlanInput:
    # Accept --arg task="..." or a positional via _extra list.
    task = cli_args.get("task") or ""
    if not task:
        extra = cli_args.get("_extra", [])
        if extra:
            task = " ".join(str(e) for e in extra)
    if not task:
        raise ValueError("deep-plan requires --arg task=\"<description>\" or a positional task argument")
    try:
        max_iter = int(cli_args.get("max_iter", 5))
    except (TypeError, ValueError):
        max_iter = 5
    return DeepPlanInput(
        task=task,
        run_id=run_id,
        run_dir=run_dir,
        inbox_path=inbox_path,
        max_iter=max_iter,
        notify=True,
    )


def register(registry: SkillRegistry) -> None:
    registry.register(
        SkillSpec(
            name="deep-plan",
            workflow_cls=DeepPlanWorkflow,
            activities=[write_artifact, emit_finding, spawn_subagent, report_slack_progress],
            build_input=_build_input,
        )
    )
