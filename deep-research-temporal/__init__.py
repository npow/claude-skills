"""deep-research-temporal skill registration."""

from __future__ import annotations

from typing import Any

from sagaflow.durable.activities import emit_finding, spawn_subagent, write_artifact
from sagaflow.slack_progress import report_slack_progress
from sagaflow.registry import SkillRegistry, SkillSpec

from .workflow import DeepResearchInput, DeepResearchWorkflow


def _build_input(
    *, run_id: str, run_dir: str, inbox_path: str, cli_args: dict[str, Any]
) -> DeepResearchInput:
    seed = str(cli_args.get("seed", "")).strip()
    if not seed:
        extra = cli_args.get("_extra")
        if isinstance(extra, list) and extra:
            seed = " ".join(str(x) for x in extra)
    if not seed:
        raise ValueError("deep-research requires --arg seed='...' or positional seed text")
    try:
        max_dirs = int(cli_args.get("max_directions", 50))
    except (TypeError, ValueError):
        max_dirs = 5
    try:
        max_rounds = int(cli_args.get("max_rounds", 1000))
    except (TypeError, ValueError):
        max_rounds = 1000
    try:
        researcher_timeout = int(cli_args.get("researcher_timeout", 600))
    except (TypeError, ValueError):
        researcher_timeout = 600
    try:
        completion_threshold = float(cli_args.get("completion_threshold", 0.8))
    except (TypeError, ValueError):
        completion_threshold = 0.8
    return DeepResearchInput(
        run_id=run_id,
        seed=seed,
        inbox_path=inbox_path,
        run_dir=run_dir,
        max_directions=max_dirs,
        max_rounds=max_rounds,
        notify=True,
        researcher_timeout=researcher_timeout,
        completion_threshold=completion_threshold,
    )


def register(registry: SkillRegistry) -> None:
    registry.register(
        SkillSpec(
            name="deep-research",
            workflow_cls=DeepResearchWorkflow,
            activities=[write_artifact, emit_finding, spawn_subagent, report_slack_progress],
            build_input=_build_input,
        )
    )
