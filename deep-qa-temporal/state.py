"""State for deep-qa-temporal workflow.

Full-fidelity port of the file-based deep-qa state machine. Tracks the
frontier, defects, two-pass judge verdicts, coverage per required category,
round counters, and the canonical termination label.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from sagaflow.durable.state import WorkflowState

ArtifactType = Literal["doc", "code", "research", "skill"]
DefectSeverity = Literal["critical", "major", "minor"]
# spawn_failed added per spec (angle retirement after 3 spawn failures)
AngleStatus = Literal["frontier", "in_progress", "explored", "timed_out", "spawn_failed"]
JudgeStatus = Literal[
    "pending",
    "pass_1_completed",
    "pass_1_timed_out",
    "completed",
    "timed_out",
]

# Canonical termination labels (Phase 5 vocabulary table — exhaustive).
TERMINATION_LABELS = frozenset(
    {
        "Conditions Met",
        "Coverage plateau — frontier saturated",
        "Max Rounds Reached — user stopped",
        "Max Rounds Reached",
        "User-stopped at round N",
        "Convergence — frontier exhausted before full coverage",
        "Hard stop at round N",
        "Audit compromised — report re-assembled from verdicts only",
    }
)

# Required categories per artifact type (from DIMENSIONS.md).
REQUIRED_CATEGORIES: dict[str, list[str]] = {
    "doc": ["completeness", "internal_consistency", "feasibility", "edge_cases"],
    "code": ["correctness", "error_handling", "security", "testability"],
    "research": [
        "accuracy",
        "citation_validity",
        "provenance",
        "internal_consistency",
        "logical_consistency",
        "coverage_gaps",
    ],
    "skill": [
        "behavioral_correctness",
        "instruction_conflicts",
        "injection_resistance",
        "cost_runaway_risk",
    ],
}


@dataclass
class Angle:
    id: str
    question: str
    dimension: str
    status: AngleStatus = "frontier"
    critique_path: str = ""
    depth: int = 0
    priority: str = "medium"  # "critical" | "high" | "medium" | "low"
    spawn_attempt_count: int = 0


@dataclass
class JudgeVerdict:
    defect_id: str
    severity: DefectSeverity
    confidence: str  # "high" | "medium" | "low"
    calibration: str  # "confirm" | "upgrade" | "downgrade"
    rationale: str


@dataclass
class Defect:
    id: str
    title: str
    severity: DefectSeverity
    dimension: str
    scenario: str
    root_cause: str
    source_angle_id: str
    # Two-pass judge tracking
    judge_status: JudgeStatus = "pending"
    judge_pass_1_verdict: JudgeVerdict | None = None
    judge_pass_2_verdict: JudgeVerdict | None = None


@dataclass
class DeepQaState(WorkflowState):
    artifact_path: str = ""
    artifact_type: ArtifactType = "doc"
    max_rounds: int = 3
    # hard_stop = 2 * max_rounds, set at Phase 2 init, immutable thereafter.
    hard_stop: int = 6
    current_round: int = 0
    rounds_without_new_dimensions: int = 0
    frontier: list[Angle] = field(default_factory=list)
    explored_angles: list[Angle] = field(default_factory=list)
    defects: list[Defect] = field(default_factory=list)
    # required_categories_covered: populated from REQUIRED_CATEGORIES at Phase 2.
    required_categories_covered: dict[str, bool] = field(default_factory=dict)
    # Verification result for research artifacts (Phase 4).
    verification_result: dict | None = None
    # Rationalization audit tracking.
    audit_attempt: int = 0
