"""State for autopilot-temporal."""

from __future__ import annotations

from dataclasses import dataclass, field

from sagaflow.durable.state import WorkflowState


@dataclass
class BudgetState:
    hard_cap_usd: float = 25.0
    token_spent_estimate_usd: float = 0.0
    max_delegations_per_phase: int = 3
    delegations_this_phase: int = 0

    def charge(self, usd: float) -> None:
        self.token_spent_estimate_usd += usd
        self.delegations_this_phase += 1

    def exhausted(self) -> bool:
        return self.token_spent_estimate_usd >= self.hard_cap_usd

    def phase_limit_reached(self) -> bool:
        return self.delegations_this_phase >= self.max_delegations_per_phase

    def reset_phase(self) -> None:
        self.delegations_this_phase = 0


@dataclass
class InvariantsState:
    all_evidence_fresh_this_session: bool = True


@dataclass
class AutopilotState(WorkflowState):
    initial_idea: str = ""
    current_phase: str = "expand"
    phases_passed: list[str] = field(default_factory=list)
    termination: str | None = None
    budget: BudgetState = field(default_factory=BudgetState)
    invariants: InvariantsState = field(default_factory=InvariantsState)
    # tracks which child skills were unavailable (degraded mode)
    degraded_skills: list[str] = field(default_factory=list)
