"""State for deep-debug-temporal."""

from __future__ import annotations

from dataclasses import dataclass, field

from sagaflow.durable.state import WorkflowState


@dataclass
class Hypothesis:
    id: str
    dimension: str
    mechanism: str
    plausibility: str = "pending"  # leading | plausible | disputed | rejected | deferred
    evidence_tier: str = "unknown"
    pass2_verdict: str = ""  # CONFIRM | UPGRADE | DOWNGRADE
    is_outside_frame: bool = False


@dataclass
class FixAttempt:
    cycle: int
    hyp_id: str
    fix_applied: bool = False
    test_passes: bool = False
    outcome: str = ""  # verified | failed | reverted


@dataclass
class DeepDebugState(WorkflowState):
    symptom: str = ""
    symptom_sha256: str = ""
    reproduction_command: str = ""
    max_cycles: int = 3
    hard_stop: int = 6
    current_cycle: int = 0
    fix_attempt_count: int = 0
    escalation_triggered: bool = False
    hypotheses: list[Hypothesis] = field(default_factory=list)
    fix_attempts: list[FixAttempt] = field(default_factory=list)
