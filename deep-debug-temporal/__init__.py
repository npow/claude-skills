"""deep-debug-temporal skill registration."""

from __future__ import annotations

from typing import Any

from sagaflow.durable.activities import emit_finding, spawn_subagent, write_artifact
from sagaflow.slack_progress import report_slack_progress
from sagaflow.prompts import load_claude_skill_prompt
from sagaflow.registry import SkillRegistry, SkillSpec

from .workflow import DeepDebugInput, DeepDebugWorkflow


def _build_input(
    *, run_id: str, run_dir: str, inbox_path: str, cli_args: dict[str, Any]
) -> DeepDebugInput:
    symptom = str(cli_args.get("symptom", "")).strip()
    if not symptom:
        extra = cli_args.get("_extra")
        if isinstance(extra, list) and extra:
            symptom = " ".join(str(x) for x in extra)
    if not symptom:
        raise ValueError("deep-debug requires --arg symptom='...' or positional symptom text")
    repro = str(cli_args.get("reproduction", "")).strip()
    try:
        num = int(cli_args.get("num_hypotheses", 4))
    except (TypeError, ValueError):
        num = 4
    return DeepDebugInput(
        run_id=run_id,
        symptom=symptom,
        reproduction_command=repro,
        inbox_path=inbox_path,
        run_dir=run_dir,
        premortem_system_prompt=load_claude_skill_prompt("deep-debug", "premortem.system"),
        premortem_user_prompt=load_claude_skill_prompt(
            "deep-debug", "premortem.user", substitutions={"symptom": symptom}
        ),
        hypothesis_system_prompt=load_claude_skill_prompt("deep-debug", "hypothesis.system"),
        hypothesis_user_prompt=load_claude_skill_prompt("deep-debug", "hypothesis.user"),
        outside_frame_system_prompt=load_claude_skill_prompt("deep-debug", "outside-frame.system"),
        outside_frame_user_prompt=load_claude_skill_prompt("deep-debug", "outside-frame.user"),
        judge_pass1_system_prompt=load_claude_skill_prompt("deep-debug", "judge-pass1.system"),
        judge_pass1_user_prompt=load_claude_skill_prompt("deep-debug", "judge-pass1.user"),
        judge_pass2_system_prompt=load_claude_skill_prompt("deep-debug", "judge-pass2.system"),
        judge_pass2_user_prompt=load_claude_skill_prompt("deep-debug", "judge-pass2.user"),
        rebuttal_system_prompt=load_claude_skill_prompt("deep-debug", "rebuttal.system"),
        rebuttal_user_prompt=load_claude_skill_prompt("deep-debug", "rebuttal.user"),
        probe_system_prompt=load_claude_skill_prompt("deep-debug", "probe.system"),
        probe_user_prompt=load_claude_skill_prompt("deep-debug", "probe.user"),
        fix_system_prompt=load_claude_skill_prompt("deep-debug", "fix.system"),
        fix_user_prompt=load_claude_skill_prompt("deep-debug", "fix.user"),
        architect_system_prompt=load_claude_skill_prompt("deep-debug", "architect.system"),
        architect_user_prompt=load_claude_skill_prompt("deep-debug", "architect.user"),
        num_hypotheses=num,
        notify=True,
    )


def register(registry: SkillRegistry) -> None:
    registry.register(
        SkillSpec(
            name="deep-debug",
            workflow_cls=DeepDebugWorkflow,
            activities=[write_artifact, emit_finding, spawn_subagent, report_slack_progress],
            build_input=_build_input,
        )
    )
