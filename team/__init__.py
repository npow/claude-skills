"""team-temporal skill registration."""

from __future__ import annotations

from typing import Any

from sagaflow.durable.activities import emit_finding, spawn_subagent, write_artifact
from sagaflow.registry import SkillRegistry, SkillSpec

from .workflow import TeamInput, TeamWorkflow


def _build_input(
    *, run_id: str, run_dir: str, inbox_path: str, cli_args: dict[str, Any]
) -> TeamInput:
    task = str(cli_args.get("task", "")).strip()
    if not task:
        extra = cli_args.get("_extra")
        if isinstance(extra, list) and extra:
            task = " ".join(str(x) for x in extra)
    if not task:
        raise ValueError("team requires --arg task='...' or positional task text")
    try:
        n = int(cli_args.get("n_workers", 2))
    except (TypeError, ValueError):
        n = 2
    try:
        max_fix = int(cli_args.get("max_fix_iters", 3))
    except (TypeError, ValueError):
        max_fix = 3
    return TeamInput(
        run_id=run_id,
        task=task,
        inbox_path=inbox_path,
        run_dir=run_dir,
        n_workers=max(1, min(n, 8)),
        max_fix_iters=max_fix,
        notify=True,
    )


def register(registry: SkillRegistry) -> None:
    registry.register(
        SkillSpec(
            name="team",
            workflow_cls=TeamWorkflow,
            activities=[write_artifact, emit_finding, spawn_subagent],
            build_input=_build_input,
        )
    )
