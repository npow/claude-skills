"""build-temporal skill registration."""

from __future__ import annotations

from typing import Any

from sagaflow.durable.activities import emit_finding, spawn_subagent, write_artifact
from sagaflow.slack_progress import report_slack_progress
from sagaflow.registry import SkillRegistry, SkillSpec

from .workflow import BuildInput, BuildWorkflow


def _build_input(
    *, run_id: str, run_dir: str, inbox_path: str, cli_args: dict[str, Any]
) -> BuildInput:
    spec = str(cli_args.get("spec", "")).strip()
    if not spec:
        extra = cli_args.get("_extra")
        if isinstance(extra, list) and extra:
            spec = " ".join(str(x) for x in extra)
    if not spec:
        raise ValueError("build requires --arg spec='...' or positional spec text")
    try:
        max_iter = int(cli_args.get("max_iterations", 3))
    except (TypeError, ValueError):
        max_iter = 3
    return BuildInput(
        run_id=run_id,
        spec=spec,
        inbox_path=inbox_path,
        run_dir=run_dir,
        max_iterations=max_iter,
        notify=True,
    )


def register(registry: SkillRegistry) -> None:
    registry.register(
        SkillSpec(
            name="build",
            workflow_cls=BuildWorkflow,
            activities=[write_artifact, emit_finding, spawn_subagent, report_slack_progress],
            build_input=_build_input,
        )
    )
