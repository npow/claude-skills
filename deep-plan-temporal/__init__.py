"""deep-plan-temporal skill registration."""

from __future__ import annotations

from typing import Any

from sagaflow.durable.activities import emit_finding, spawn_subagent, write_artifact
from sagaflow.prompts import load_claude_skill_prompt
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
        planner_system_prompt=load_claude_skill_prompt("deep-plan", "planner.system"),
        planner_user_prompt=load_claude_skill_prompt("deep-plan", "planner.user"),
        architect_system_prompt=load_claude_skill_prompt("deep-plan", "architect.system"),
        architect_user_prompt=load_claude_skill_prompt("deep-plan", "architect.user"),
        critic_system_prompt=load_claude_skill_prompt("deep-plan", "critic.system"),
        critic_user_prompt=load_claude_skill_prompt("deep-plan", "critic.user"),
        adr_system_prompt=load_claude_skill_prompt("deep-plan", "adr.system"),
        adr_user_prompt=load_claude_skill_prompt("deep-plan", "adr.user"),
    )


def register(registry: SkillRegistry) -> None:
    registry.register(
        SkillSpec(
            name="deep-plan",
            workflow_cls=DeepPlanWorkflow,
            activities=[write_artifact, emit_finding, spawn_subagent],
            build_input=_build_input,
        )
    )
