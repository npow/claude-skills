"""Minimal state for the hello-world smoke skill."""

from __future__ import annotations

from dataclasses import dataclass

from sagaflow.durable.state import WorkflowState


@dataclass
class HelloWorldState(WorkflowState):
    greeting_name: str = ""
    greeting_text: str = ""
