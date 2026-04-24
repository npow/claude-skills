"""State types for the proposal-reviewer skill."""

from __future__ import annotations

from dataclasses import dataclass, field

from sagaflow.durable.state import WorkflowState


@dataclass
class Claim:
    id: str
    text: str
    tier: str  # "core" | "supporting" | "peripheral"


@dataclass
class Weakness:
    id: str
    title: str
    severity: str        # critic's raw claim (stripped before judge sees it)
    dimension: str       # "viability" | "competition" | "structural" | "evidence"
    scenario: str
    root_cause: str = ""
    fix_direction: str = ""
    counter_response: str = ""  # author counter-response (falsifiability contract)


@dataclass
class CredibilityVerdict:
    claim_id: str
    verdict: str          # VERIFIED | PARTIALLY_TRUE | UNVERIFIABLE | FALSE
    confidence: str       # high | medium | low
    rationale: str = ""


@dataclass
class SeverityVerdict:
    weakness_id: str
    falsifiable: bool
    severity: str         # fatal | major | minor | rejected
    fixability: str       # fixable | inherent_risk | fatal
    confidence: str       # high | medium | low
    rationale: str = ""


@dataclass
class LandscapeVerdict:
    market_window: str      # open | closing | closed
    platform_risk: str      # low | medium | high
    most_likely_threat: str = ""


@dataclass
class AuditResult:
    fidelity: str           # clean | compromised
    acceptance_rates: dict[str, float] = field(default_factory=dict)
    suspicious_patterns: list[str] = field(default_factory=list)


@dataclass
class ProposalReviewState(WorkflowState):
    proposal_text: str = ""
    proposal_text_sha256: str = ""
    core_claim: str = ""
    claims: list[Claim] = field(default_factory=list)
    weaknesses: list[Weakness] = field(default_factory=list)
    credibility_verdicts: list[CredibilityVerdict] = field(default_factory=list)
    severity_verdicts: list[SeverityVerdict] = field(default_factory=list)
    landscape_verdict: LandscapeVerdict | None = None
    audit_result: AuditResult | None = None
    termination: str = ""
