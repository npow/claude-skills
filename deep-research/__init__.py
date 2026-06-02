"""deep-research-temporal skill registration."""

from __future__ import annotations

import os
from typing import Any

from sagaflow.durable.activities import (
    emit_finding,
    finalize_manifest_activity,
    run_shell_activity,
    spawn_subagent,
    write_artifact,
)
from sagaflow.slack_progress import report_slack_progress
from sagaflow.registry import SkillRegistry, SkillSpec

from .workflow_rlm import (
    DeepResearchInput as DeepResearchRLMInput,
    DeepResearchWorkflow as DeepResearchRLMWorkflow,
)

# Default backend is the RLM-based workflow (cheaper + denser specifics
# than the DFS pipeline preserved in workflow.py). Set
# DEEP_RESEARCH_BACKEND=dfs to fall back to the legacy DFS workflow.
if os.environ.get("DEEP_RESEARCH_BACKEND", "rlm").lower() == "dfs":
    from .workflow import DeepResearchInput, DeepResearchWorkflow
else:
    DeepResearchInput = DeepResearchRLMInput
    DeepResearchWorkflow = DeepResearchRLMWorkflow


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
        min_rounds = int(cli_args.get("min_rounds", 3))
    except (TypeError, ValueError):
        min_rounds = 3
    return DeepResearchInput(
        run_id=run_id,
        seed=seed,
        inbox_path=inbox_path,
        run_dir=run_dir,
        max_directions=max_dirs,
        max_rounds=max_rounds,
        min_rounds=min_rounds,
        notify=True,
        mcp_categories_json=os.environ.get("RESEARCH_MCP_CATEGORIES", "{}"),
    )


def _build_rlm_input(
    *, run_id: str, run_dir: str, inbox_path: str, cli_args: dict[str, Any]
) -> DeepResearchRLMInput:
    seed = str(cli_args.get("query") or cli_args.get("seed") or "").strip()
    if not seed:
        extra = cli_args.get("_extra")
        if isinstance(extra, list) and extra:
            seed = " ".join(str(x) for x in extra)
    if not seed:
        raise ValueError("rlm-research requires --arg query='...' or positional query text")

    def _int_arg(name: str, default: int) -> int:
        try:
            return int(cli_args.get(name, default))
        except (TypeError, ValueError):
            return default

    return DeepResearchRLMInput(
        run_id=run_id,
        seed=seed,
        inbox_path=inbox_path,
        run_dir=run_dir,
        max_directions=_int_arg("max_dimensions", _int_arg("max_directions", 8)),
        max_rounds=_int_arg("max_rounds", 100),
        min_rounds=_int_arg("min_rounds", 3),
        iters_per_dimension=_int_arg("iters_per_dimension", 25),
        llm_calls_per_dimension=_int_arg("llm_calls_per_dimension", 60),
        max_gap_rounds=_int_arg("max_gap_rounds", 2),
        max_workers=_int_arg("max_workers", 8),
        verbose=bool(cli_args.get("verbose", False)),
        notify=True,
        mcp_categories_json=os.environ.get("RESEARCH_MCP_CATEGORIES", "{}"),
    )


def register(registry: SkillRegistry) -> None:
    common_activities = [
        write_artifact,
        emit_finding,
        spawn_subagent,
        report_slack_progress,
        finalize_manifest_activity,
        run_shell_activity,
    ]
    registry.register(
        SkillSpec(
            name="deep-research",
            workflow_cls=DeepResearchWorkflow,
            activities=common_activities,
            build_input=_build_input,
        )
    )
    registry.register(
        SkillSpec(
            name="rlm-research",
            workflow_cls=DeepResearchRLMWorkflow,
            activities=common_activities,
            build_input=_build_rlm_input,
        )
    )
