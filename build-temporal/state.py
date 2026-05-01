"""State for build-temporal workflow."""

from __future__ import annotations

from dataclasses import dataclass, field

from sagaflow.durable.state import WorkflowState


@dataclass
class Task:
    id: str
    description: str
    acceptance_criteria: str
    status: str = "pending"  # pending | in_progress | completed | failed
    output_path: str = ""


@dataclass
class BuildState(WorkflowState):
    spec: str = ""
    plan_path: str = ""
    tasks: list[Task] = field(default_factory=list)
    current_phase: str = "assess"  # assess | plan | execute | verify | review
    review_findings: list[dict] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 3
    termination_label: str = ""
