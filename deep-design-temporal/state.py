"""State for deep-design-temporal workflow.

Tracks the current spec draft, flaw findings from critics, round progress,
and all intermediate agent outputs (fact sheets, judge verdicts, invariants,
ordering graph, drift scores, gap report counts, and complexity budget).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Literal

from sagaflow.durable.state import WorkflowState

FlawSeverity = Literal["critical", "major", "minor", "rejected"]
FlawStatus = Literal["open", "addressed", "wont_fix", "disputed", "persistent_tension"]


@dataclass
class Flaw:
    id: str
    title: str
    severity: FlawSeverity
    dimension: str
    scenario: str
    status: FlawStatus = "open"
    gap_report_count: int = 0
    challenge_token_spent: bool = False
    judge_pass1_verdict: FlawSeverity | None = None
    judge_pass2_verdict: FlawSeverity | None = None


@dataclass
class ComponentInvariant:
    key: str
    invariant: str
    constraint_direction: Literal["tightened", "relaxed", "neutral"] = "neutral"
    tightened_rounds: list[int] = field(default_factory=list)


@dataclass
class OrderingEdge:
    from_component: str
    to_component: str
    established_round: int
    basis: str


@dataclass
class CrossFixConflict:
    fix_a: str
    fix_b: str
    description: str


@dataclass
class InvariantViolation:
    key: str
    invariant: str
    spec_section: str
    evidence: str


@dataclass
class RecoveryBehavior:
    component: str
    behavior: str


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@dataclass
class DeepDesignState(WorkflowState):
    # Core concept
    core_claim: str = ""
    core_claim_sha256: str = ""
    core_claim_calibrated: bool = False

    # Round tracking
    max_rounds: int = 3
    current_round: int = 0
    rounds_without_new_dim_categories: int = 0

    # Required category coverage
    required_categories_covered: dict[str, bool] = field(
        default_factory=lambda: {
            "correctness": False,
            "usability_ux": False,
            "economics_cost": False,
            "operability": False,
            "security_trust": False,
        }
    )

    # Spec state
    spec_draft: str = ""

    # Flaw tracking
    flaws: list[Flaw] = field(default_factory=list)

    # GAP_REPORT global counts (flaw_id -> count)
    gap_report_global_counts: dict[str, int] = field(default_factory=dict)

    # Complexity budget: components/fields added this run
    complexity_added_per_round: dict[int, int] = field(default_factory=dict)

    # Component invariants (append-only; coordinator-write-prohibited)
    component_invariants: list[ComponentInvariant] = field(default_factory=list)
    component_name_history: dict[str, str] = field(default_factory=dict)

    # Ordering graph
    ordering_graph_edges: list[OrderingEdge] = field(default_factory=list)

    # Fact sheet for current round
    recovery_behaviors: list[RecoveryBehavior] = field(default_factory=list)

    # Cross-fix conflicts blocking advancement
    cross_fix_conflicts: list[CrossFixConflict] = field(default_factory=list)

    # Invariant violations blocking advancement
    invariant_violations: list[InvariantViolation] = field(default_factory=list)

    # Drift tracking
    drift_score: float | None = None
    drift_verdict: Literal["ok", "warning", "critical"] | None = None

    # Termination label (overrides base WorkflowState.terminal_label with typed choices)
    # Values: "Conditions Met" | "Max Rounds Reached"
    termination_label: str | None = None

    # Frontier pop audit log path (relative to run_dir)
    frontier_pop_log: list[dict] = field(default_factory=list)

    def set_core_claim(self, claim: str, *, calibrated: bool) -> None:
        self.core_claim = claim
        self.core_claim_sha256 = _sha256(claim)
        self.core_claim_calibrated = calibrated

    def verify_core_claim_integrity(self) -> bool:
        """Return True if stored sha256 matches current core_claim text."""
        return _sha256(self.core_claim) == self.core_claim_sha256

    def complexity_budget_for_round(self, round_idx: int) -> int:
        """Return max new components allowed this round (2 for rounds 0-1, 1 for 2+)."""
        return 2 if round_idx < 2 else 1

    def record_gap_report(self, flaw_id: str) -> Literal["reopened", "persistent_tension"]:
        """Increment GAP_REPORT count. Return 'persistent_tension' on the 3rd hit."""
        self.gap_report_global_counts[flaw_id] = (
            self.gap_report_global_counts.get(flaw_id, 0) + 1
        )
        count = self.gap_report_global_counts[flaw_id]
        for flaw in self.flaws:
            if flaw.id == flaw_id:
                flaw.gap_report_count = count
                if count >= 3:
                    flaw.status = "persistent_tension"
                    return "persistent_tension"
                break
        return "reopened"
