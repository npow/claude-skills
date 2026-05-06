"""deep-qa-temporal skill registration."""

from __future__ import annotations

from typing import Any

from sagaflow.durable.activities import emit_finding, spawn_subagent, write_artifact
from sagaflow.prompts import load_claude_skill_prompt
from sagaflow.registry import SkillRegistry, SkillSpec
from sagaflow.slack_progress import report_slack_progress

from .activities import read_text_file
from .workflow import DeepQaInput, DeepQaWorkflow


def _build_input(
    *, run_id: str, run_dir: str, inbox_path: str, cli_args: dict[str, Any]
) -> DeepQaInput:
    path = cli_args.get("path") or ""
    if not path:
        raise ValueError("deep-qa requires --path <artifact>")
    artifact_type = str(cli_args.get("type", "doc"))
    try:
        max_rounds = int(cli_args.get("max_rounds", 3))
    except (TypeError, ValueError):
        max_rounds = 3
    return DeepQaInput(
        run_id=run_id,
        artifact_path=str(path),
        artifact_type=artifact_type,
        inbox_path=inbox_path,
        run_dir=run_dir,
        max_rounds=max_rounds,
        notify=True,
        dim_discovery_system_prompt=load_claude_skill_prompt("deep-qa", "dim_discovery.system"),
        dim_discovery_user_prompt=load_claude_skill_prompt("deep-qa", "dim_discovery.user"),
        critic_system_prompt=load_claude_skill_prompt("deep-qa", "critic.system"),
        critic_user_prompt=load_claude_skill_prompt("deep-qa", "critic.user"),
        judge_pass1_system_prompt=load_claude_skill_prompt("deep-qa", "judge_pass1.system"),
        judge_pass1_user_prompt=load_claude_skill_prompt("deep-qa", "judge_pass1.user"),
        judge_pass2_system_prompt=load_claude_skill_prompt("deep-qa", "judge_pass2.system"),
        judge_pass2_user_prompt=load_claude_skill_prompt("deep-qa", "judge_pass2.user"),
        auditor_system_prompt=load_claude_skill_prompt("deep-qa", "auditor.system"),
        auditor_user_prompt=load_claude_skill_prompt("deep-qa", "auditor.user"),
        verifier_system_prompt=load_claude_skill_prompt("deep-qa", "verifier.system"),
        verifier_user_prompt=load_claude_skill_prompt("deep-qa", "verifier.user"),
        synth_system_prompt=load_claude_skill_prompt("deep-qa", "synth.system"),
        synth_user_prompt=load_claude_skill_prompt("deep-qa", "synth.user"),
    )


def register(registry: SkillRegistry) -> None:
    registry.register(
        SkillSpec(
            name="deep-qa",
            workflow_cls=DeepQaWorkflow,
            activities=[write_artifact, emit_finding, spawn_subagent, read_text_file, report_slack_progress],
            build_input=_build_input,
        )
    )
