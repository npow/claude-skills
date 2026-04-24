"""State for deep-plan-temporal workflow."""

from __future__ import annotations

from dataclasses import dataclass, field

from sagaflow.durable.state import WorkflowState


@dataclass
class AgentRoleStats:
    """Per-role accounting tracked in the verdict registry."""

    spawns: int = 0
    unparseable: int = 0
    verdicts: dict[str, int] = field(default_factory=dict)

    def record_spawn(self) -> None:
        self.spawns += 1

    def record_unparseable(self) -> None:
        self.unparseable += 1

    def record_verdict(self, verdict: str) -> None:
        self.verdicts[verdict] = self.verdicts.get(verdict, 0) + 1


@dataclass
class DeepPlanState(WorkflowState):
    task: str = ""
    max_iter: int = 5
    current_iter: int = 0
    mode: str = "short"  # "short" | "deliberate"
    task_text_sha256: str = ""
    verdict_history: list[str] = field(default_factory=list)
    dropped_rejections_total: int = 0

    # agent_verdict_registry: role -> AgentRoleStats (serialised as nested dict)
    agent_verdict_registry: dict[str, AgentRoleStats] = field(default_factory=dict)

    def registry_for(self, role: str) -> AgentRoleStats:
        if role not in self.agent_verdict_registry:
            self.agent_verdict_registry[role] = AgentRoleStats()
        return self.agent_verdict_registry[role]
