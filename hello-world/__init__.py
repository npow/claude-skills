"""hello-world skill registration."""

from __future__ import annotations

from typing import Any

from sagaflow.durable.activities import emit_finding, spawn_subagent, write_artifact
from sagaflow.prompts import load_prompt
from sagaflow.registry import SkillRegistry, SkillSpec

from skills.hello_world.workflow import HelloWorldInput, HelloWorldWorkflow


def _build_input(
    *, run_id: str, run_dir: str, inbox_path: str, cli_args: dict[str, Any]
) -> HelloWorldInput:
    name = str(cli_args.get("name", "world"))
    return HelloWorldInput(
        run_id=run_id,
        name=name,
        inbox_path=inbox_path,
        run_dir=run_dir,
        greeter_system_prompt=load_prompt(__file__, "greeter.system"),
        greeter_user_prompt=load_prompt(__file__, "greeter.user", substitutions={"name": name}),
        notify=bool(cli_args.get("notify", True)),
    )


def register(registry: SkillRegistry) -> None:
    registry.register(
        SkillSpec(
            name="hello-world",
            workflow_cls=HelloWorldWorkflow,
            activities=[write_artifact, emit_finding, spawn_subagent],
            build_input=_build_input,
        )
    )
