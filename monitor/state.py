"""State for monitor-temporal workflow."""

from __future__ import annotations

from dataclasses import dataclass, field

from sagaflow.durable.state import WorkflowState


@dataclass
class Metric:
    name: str
    value: str = ""
    threshold: str = ""
    status: str = "unknown"  # healthy | degraded | critical | unknown


@dataclass
class MonitorState(WorkflowState):
    target: str = ""
    preset: str = "auto"
    metrics: list[Metric] = field(default_factory=list)
    health_rating: str = "unknown"
    report_path: str = ""
    recurring: bool = False
    interval_seconds: int = 300
    termination_label: str = ""
