"""State for deep-research-temporal."""

from __future__ import annotations

from dataclasses import dataclass, field

from sagaflow.durable.state import WorkflowState

# Cross-cutting dimensions required on every run (in addition to WHO/WHAT/HOW/etc.)
CROSS_CUT_DIMS = [
    "PRIOR-FAILURE",
    "BASELINE",
    "ADJACENT-EFFORTS",
    "STRATEGIC-TIMING",
    "ACTUAL-USAGE",
]

STANDARD_DIMS = ["WHO", "WHAT", "HOW", "WHERE", "WHEN", "WHY", "LIMITS"]

ALL_DIMS = STANDARD_DIMS + CROSS_CUT_DIMS


@dataclass
class Direction:
    id: str
    question: str
    dimension: str
    status: str = "frontier"
    findings_path: str = ""
    priority: str = "medium"
    depth: int = 0


@dataclass
class SourceVerification:
    title: str
    authors_or_org: str
    year: int
    confidence: str
    verified: bool = False


@dataclass
class DeepResearchState(WorkflowState):
    seed: str = ""
    max_rounds: int = 2
    current_round: int = 0
    frontier: list[Direction] = field(default_factory=list)

    # Novelty / vocabulary-bootstrap state (Phase 0g + Phase 2.5)
    topic_novelty: str = ""          # familiar | emerging | novel | cold_start
    self_report_novelty: str = ""    # raw LLM self-report before override
    vocab_bootstrap_path: str = ""   # path to vocabulary_bootstrap.json if written
    source_verification_log: list[SourceVerification] = field(default_factory=list)
    authoritative_languages: list[str] = field(default_factory=list)
    coverage_expectation: str = "en_dominant"   # from Phase 0f

    # Cross-cut dimension coverage: dim → list of explored direction IDs
    cross_cut_coverage: dict[str, list[str]] = field(default_factory=dict)

    # Fact-verification results (Phase 4)
    verified_claims: list[dict] = field(default_factory=list)
    mismatched_claims: list[dict] = field(default_factory=list)
    unverifiable_claims: list[dict] = field(default_factory=list)

    # Per-round coordinator summaries
    coordinator_summaries: list[str] = field(default_factory=list)

    # Termination tracking
    termination_label: str = ""
