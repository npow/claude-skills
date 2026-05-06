"""State for team-temporal."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from sagaflow.durable.state import WorkflowState

WorkerStatus = Literal[
    "not_spawned",
    "spawned",
    "working",
    "task_complete_pending_review",
    "task_complete_approved",
    "task_complete_rejected",
    "shutdown_confirmed",
    "blocked",
    "failed",
]

TerminationLabel = Literal[
    "complete",
    "partial_with_accepted_unfixed",
    "blocked_unresolved",
    "budget_exhausted",
    "cancelled",
]


@dataclass
class WorkerRecord:
    worker_id: str
    subtask_id: str
    status: WorkerStatus = "not_spawned"
    spawn_time_iso: str | None = None
    consecutive_rejections: int = 0
    agent_type: str = "executor"


@dataclass
class DefectRecord:
    defect_id: str
    severity: str
    description: str
    fix_attempts: int = 0
    fix_verdict: str | None = None  # fixed | not_fixed | partial


@dataclass
class StageRecord:
    name: str
    status: str = "pending"  # pending | in_progress | gate_checking | complete | blocked
    evidence_files: list[str] = field(default_factory=list)


@dataclass
class HandoffRegistry:
    plan: str | None = None
    prd: str | None = None
    exec: str | None = None
    verify: str | None = None
    fix: str | None = None


@dataclass
class TeamState(WorkflowState):
    task: str = ""
    task_text_sha256: str = ""
    n_workers: int = 2
    max_fix_iters: int = 3
    agent_type: str = "executor"
    current_stage: str = "plan"
    stages_completed: list[str] = field(default_factory=list)
    stages: list[StageRecord] = field(default_factory=list)
    workers: list[WorkerRecord] = field(default_factory=list)
    defects: list[DefectRecord] = field(default_factory=list)
    handoffs: HandoffRegistry = field(default_factory=HandoffRegistry)
    fix_iter: int = 0
    prd_revision_count: int = 0
    plan_rework_count: int = 0
