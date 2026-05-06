"""State types for the flaky-test-diagnoser skill."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from sagaflow.durable.state import WorkflowState


HypothesisStatus = Literal["pending", "confirmed", "rejected", "inconclusive"]


@dataclass
class Hypothesis:
    id: str
    category: str  # ORDERING | TIMING | SHARED_STATE | EXTERNAL_DEPENDENCY | RESOURCE_LEAK | NON_DETERMINISM
    mechanism: str
    status: HypothesisStatus = "pending"


@dataclass
class FlakyTestState(WorkflowState):
    """State for the flaky-test-diagnoser workflow."""

    test_identifier: str = ""
    n_runs: int = 10
    fail_rate: float = 0.0
    hypotheses: list[Hypothesis] = field(default_factory=list)
