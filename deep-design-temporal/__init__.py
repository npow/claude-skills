"""deep-design-temporal skill registration."""

from __future__ import annotations

from typing import Any

from sagaflow.durable.activities import emit_finding, spawn_subagent, write_artifact
from sagaflow.prompts import load_claude_skill_prompt
from sagaflow.registry import SkillRegistry, SkillSpec

from .workflow import DeepDesignInput, DeepDesignWorkflow

_SKILL = "deep-design"


def _build_input(
    *, run_id: str, run_dir: str, inbox_path: str, cli_args: dict[str, Any]
) -> DeepDesignInput:
    concept = cli_args.get("concept") or ""
    if not concept:
        # Fall back to positional extras joined as a single string.
        extras = cli_args.get("_extra", [])
        if isinstance(extras, list):
            concept = " ".join(str(e) for e in extras)
    if not concept:
        raise ValueError("deep-design requires --arg concept='<description>'")
    try:
        max_rounds = int(cli_args.get("max_rounds", 2))
    except (TypeError, ValueError):
        max_rounds = 2
    return DeepDesignInput(
        run_id=run_id,
        concept=str(concept),
        inbox_path=inbox_path,
        run_dir=run_dir,
        max_rounds=max_rounds,
        notify=True,
        # System prompts (no runtime variables — safe to load as-is).
        draft_system_prompt=load_claude_skill_prompt(_SKILL, "draft.system"),
        fact_sheet_system_prompt=load_claude_skill_prompt(_SKILL, "fact_sheet.system"),
        critic_system_prompt=load_claude_skill_prompt(_SKILL, "critic.system"),
        outside_frame_system_prompt=load_claude_skill_prompt(_SKILL, "outside_frame.system"),
        judge_system_prompt=load_claude_skill_prompt(_SKILL, "judge.system"),
        challenger_system_prompt=load_claude_skill_prompt(_SKILL, "challenger.system"),
        cross_fix_system_prompt=load_claude_skill_prompt(_SKILL, "cross_fix.system"),
        redesign_system_prompt=load_claude_skill_prompt(_SKILL, "redesign.system"),
        invariant_validator_system_prompt=load_claude_skill_prompt(_SKILL, "invariant_validator.system"),
        drift_judge_system_prompt=load_claude_skill_prompt(_SKILL, "drift_judge.system"),
        synth_system_prompt=load_claude_skill_prompt(_SKILL, "synth.system"),
        # User prompts where ALL variables are available at build_input time.
        draft_user_prompt=load_claude_skill_prompt(_SKILL, "draft.user", substitutions={"concept": concept}),
        outside_frame_user_prompt=load_claude_skill_prompt(_SKILL, "outside_frame.user", substitutions={"concept": concept}),
        # User prompts with runtime-only variables — left empty so workflow
        # uses inline defaults that can format with runtime state.
        fact_sheet_user_prompt="",
        critic_user_prompt="",
        judge_pass1_user_prompt="",
        judge_pass2_user_prompt="",
        challenger_user_prompt="",
        cross_fix_user_prompt="",
        redesign_user_prompt="",
        invariant_validator_user_prompt="",
        drift_judge_user_prompt="",
        synth_user_prompt="",
    )


def register(registry: SkillRegistry) -> None:
    registry.register(
        SkillSpec(
            name="deep-design",
            workflow_cls=DeepDesignWorkflow,
            activities=[write_artifact, emit_finding, spawn_subagent],
            build_input=_build_input,
        )
    )
