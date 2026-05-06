"""State for loop-until-done workflow.

Drives a PRD-generation → falsifiability-judge → execute → verify →
two-stage-review → deslop → complete loop with full termination tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from sagaflow.durable.state import WorkflowState

# ── story / criterion status ───────────────────────────────────────────────────

StoryStatus = Literal["pending", "in_progress", "passed", "blocked"]

CurrentPhase = Literal[
    "story_implement",
    "story_verify",
    "reviewer_gate",
    "deslop_regression",
    "complete",
    "blocked",
]

DeslopMode = Literal["standard", "skipped_no_deslop", "skipped_unavailable"]

VerificationMode = Literal["basic", "deep-qa"]


# ── per-criterion ──────────────────────────────────────────────────────────────

@dataclass
class AcceptanceCriterion:
    id: str
    story_id: str
    criterion: str
    verification_command: str
    expected_pattern: str
    passes: bool = False
    last_verified_at: str | None = None  # ISO timestamp


# ── per-story ──────────────────────────────────────────────────────────────────

@dataclass
class Story:
    id: str
    title: str
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    status: StoryStatus = "pending"


# ── reviewer approval rate tracking ───────────────────────────────────────────

@dataclass
class ReviewerApprovalRate:
    total_reviews: int = 0
    approved: int = 0
    rejected: int = 0
    warning_threshold_approaching_rubber_stamp: bool = False

    def record(self, *, approved: bool) -> None:
        self.total_reviews += 1
        if approved:
            self.approved += 1
        else:
            self.rejected += 1
        # Flag if approval rate >= 95% over >= 10 reviews.
        if self.total_reviews >= 10:
            rate = self.approved / self.total_reviews
            self.warning_threshold_approaching_rubber_stamp = rate >= 0.95

    @property
    def possibly_rubber_stamp(self) -> bool:
        return self.warning_threshold_approaching_rubber_stamp


# ── top-level run config (parsed CLI flags) ────────────────────────────────────

@dataclass
class RunConfig:
    no_prd: bool = False
    no_deslop: bool = False
    critic: str = "architect"          # architect | critic | deep-qa | codex
    budget: int = 25
    resume: str | None = None
    executor_tier: str | None = None   # haiku | sonnet | opus


# ── full workflow state ────────────────────────────────────────────────────────

@dataclass
class LoopUntilDoneState(WorkflowState):
    # ── task identity ──────────────────────────────────────────────────────────
    task: str = ""

    # ── PRD ───────────────────────────────────────────────────────────────────
    prd_sha256: str | None = None       # immutable after Phase 2
    prd_locked: bool = False

    # ── iteration budget ──────────────────────────────────────────────────────
    max_iter: int = 25
    current_iter: int = 0
    iteration_started_at: str | None = None  # ISO; used by iron-law gate

    # ── stories ───────────────────────────────────────────────────────────────
    stories: list[Story] = field(default_factory=list)

    # ── per-story fail counts (for infeasibility cap) ─────────────────────────
    iterations_per_story: dict[str, int] = field(default_factory=dict)
    # criterion_fail_counts[story_id][criterion_id] = consecutive fails
    criterion_fail_counts: dict[str, dict[str, int]] = field(default_factory=dict)

    # ── PRD falsifiability revision tracking ──────────────────────────────────
    prd_revision_attempts: int = 0

    # ── reviewer caps ─────────────────────────────────────────────────────────
    reviewer_rejection_count: int = 0
    reviewer_approval_rate: ReviewerApprovalRate = field(
        default_factory=ReviewerApprovalRate
    )

    # ── phase / mode ──────────────────────────────────────────────────────────
    current_phase: CurrentPhase = "story_implement"
    deslop_mode: DeslopMode = "standard"
    verification_mode: VerificationMode = "basic"

    # ── run config ────────────────────────────────────────────────────────────
    config: RunConfig = field(default_factory=RunConfig)
