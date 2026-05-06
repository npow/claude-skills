"""monitor-temporal skill registration."""

from __future__ import annotations

from typing import Any

from sagaflow.durable.activities import emit_finding, spawn_subagent, write_artifact
from sagaflow.slack_progress import report_slack_progress
from sagaflow.registry import SkillRegistry, SkillSpec

from .workflow import MonitorInput, MonitorWorkflow


def _build_input(
    *, run_id: str, run_dir: str, inbox_path: str, cli_args: dict[str, Any]
) -> MonitorInput:
    target = str(cli_args.get("target", "")).strip()
    if not target:
        extra = cli_args.get("_extra")
        if isinstance(extra, list) and extra:
            target = " ".join(str(x) for x in extra)
    if not target:
        raise ValueError("monitor requires --arg target='...' or positional target text")
    preset = str(cli_args.get("preset", "auto"))
    recurring_raw = cli_args.get("recurring", False)
    if isinstance(recurring_raw, str):
        recurring = recurring_raw.lower() in ("true", "1", "yes")
    else:
        recurring = bool(recurring_raw)
    try:
        interval = int(cli_args.get("interval", 300))
    except (TypeError, ValueError):
        interval = 300
    return MonitorInput(
        run_id=run_id,
        target=target,
        inbox_path=inbox_path,
        run_dir=run_dir,
        preset=preset,
        recurring=recurring,
        interval_seconds=interval,
        notify=True,
    )


def register(registry: SkillRegistry) -> None:
    registry.register(
        SkillSpec(
            name="monitor",
            workflow_cls=MonitorWorkflow,
            activities=[write_artifact, emit_finding, spawn_subagent, report_slack_progress],
            build_input=_build_input,
        )
    )
