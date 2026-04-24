"""autopilot-temporal skill registration."""

from __future__ import annotations

from typing import Any

from sagaflow.durable.activities import emit_finding, spawn_subagent, write_artifact
from sagaflow.registry import SkillRegistry, SkillSpec

from .workflow import AutopilotInput, AutopilotWorkflow


def _build_input(
    *, run_id: str, run_dir: str, inbox_path: str, cli_args: dict[str, Any]
) -> AutopilotInput:
    idea = str(cli_args.get("idea", "")).strip()
    if not idea:
        extra = cli_args.get("_extra")
        if isinstance(extra, list) and extra:
            idea = " ".join(str(x) for x in extra)
    if not idea:
        raise ValueError("autopilot requires --arg idea='...' or positional idea text")
    return AutopilotInput(
        run_id=run_id,
        initial_idea=idea,
        inbox_path=inbox_path,
        run_dir=run_dir,
        notify=True,
    )


def register(registry: SkillRegistry) -> None:
    registry.register(
        SkillSpec(
            name="autopilot",
            workflow_cls=AutopilotWorkflow,
            activities=[write_artifact, emit_finding, spawn_subagent],
            build_input=_build_input,
        )
    )
