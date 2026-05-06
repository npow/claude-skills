"""loop-until-done skill registration."""

from __future__ import annotations

import json
from typing import Any

from sagaflow.durable.activities import emit_finding, spawn_subagent, write_artifact
from sagaflow.prompts import load_claude_skill_prompt
from sagaflow.registry import SkillRegistry, SkillSpec

from .workflow import LoopUntilDoneInput, LoopUntilDoneWorkflow


def _build_input(
    *, run_id: str, run_dir: str, inbox_path: str, cli_args: dict[str, Any]
) -> LoopUntilDoneInput:
    # --arg task="..." or positional text via _extra
    task = cli_args.get("task") or ""
    if not task:
        extra = cli_args.get("_extra", [])
        if isinstance(extra, list) and extra:
            task = " ".join(str(x) for x in extra)
    if not task:
        raise ValueError("loop-until-done requires --arg task='<description>' or positional text")
    try:
        max_iter = int(cli_args.get("max_iter", 5))
    except (TypeError, ValueError):
        max_iter = 5

    task_str = str(task)

    return LoopUntilDoneInput(
        run_id=run_id,
        task=task_str,
        inbox_path=inbox_path,
        run_dir=run_dir,
        max_iter=max_iter,
        notify=True,
        prd_system_prompt=load_claude_skill_prompt("loop-until-done", "prd.system"),
        prd_user_prompt=load_claude_skill_prompt(
            "loop-until-done", "prd.user", substitutions={"task": task_str},
        ),
        falsifiability_system_prompt=load_claude_skill_prompt("loop-until-done", "falsifiability.system"),
        falsifiability_user_prompt="",  # dynamic: depends on generated criteria
        executor_system_prompt=load_claude_skill_prompt("loop-until-done", "executor.system"),
        executor_user_prompt="",  # dynamic: depends on per-story data
        verifier_system_prompt=load_claude_skill_prompt("loop-until-done", "verifier.system"),
        verifier_user_prompt="",  # dynamic: depends on per-criterion data
        reviewer_system_prompt=load_claude_skill_prompt("loop-until-done", "reviewer.system"),
        reviewer_user_prompt="",  # dynamic: depends on full run results
    )


def register(registry: SkillRegistry) -> None:
    registry.register(
        SkillSpec(
            name="loop-until-done",
            workflow_cls=LoopUntilDoneWorkflow,
            activities=[write_artifact, emit_finding, spawn_subagent],
            build_input=_build_input,
        )
    )
