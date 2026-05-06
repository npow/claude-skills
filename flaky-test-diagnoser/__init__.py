"""flaky-test-diagnoser skill registration."""

from __future__ import annotations

from typing import Any

from sagaflow.durable.activities import emit_finding, spawn_subagent, write_artifact
from sagaflow.prompts import load_claude_skill_prompt
from sagaflow.registry import SkillRegistry, SkillSpec

from .activities import run_test_subprocess
from .workflow import FlakyTestInput, FlakyTestWorkflow


def _build_input(
    *, run_id: str, run_dir: str, inbox_path: str, cli_args: dict[str, Any]
) -> FlakyTestInput:
    test = cli_args.get("test") or ""
    if not test:
        raise ValueError("flaky-test-diagnoser requires --arg test='<test identifier>'")
    command = cli_args.get("command") or ""
    if not command:
        raise ValueError("flaky-test-diagnoser requires --arg command='<run command>'")
    try:
        n_runs = int(cli_args.get("n_runs", 10))
    except (TypeError, ValueError):
        n_runs = 10
    return FlakyTestInput(
        run_id=run_id,
        test_identifier=str(test),
        run_dir=run_dir,
        inbox_path=inbox_path,
        run_command=str(command),
        n_runs=n_runs,
        notify=True,
        hyp_system_prompt=load_claude_skill_prompt("flaky-test-diagnoser", "hyp.system"),
        hyp_user_prompt=load_claude_skill_prompt("flaky-test-diagnoser", "hyp.user"),
        judge_system_prompt=load_claude_skill_prompt("flaky-test-diagnoser", "judge.system"),
        judge_user_prompt=load_claude_skill_prompt("flaky-test-diagnoser", "judge.user"),
        synth_system_prompt=load_claude_skill_prompt("flaky-test-diagnoser", "synth.system"),
        synth_user_prompt=load_claude_skill_prompt("flaky-test-diagnoser", "synth.user"),
    )


def register(registry: SkillRegistry) -> None:
    registry.register(
        SkillSpec(
            name="flaky-test-diagnoser",
            workflow_cls=FlakyTestWorkflow,
            activities=[
                write_artifact,
                emit_finding,
                spawn_subagent,
                run_test_subprocess,
            ],
            build_input=_build_input,
        )
    )
