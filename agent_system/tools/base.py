"""Tool contracts and a per-agent session, with no model dependencies."""
from dataclasses import dataclass, field
from typing import Callable, Tuple


@dataclass
class ToolContext:
    task: dict
    stage_id: str
    evidence: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict
    handler: Callable[[dict, ToolContext], Tuple[dict, bool]]

    def as_api(self):
        return {"type": "function", "function": {
            "name": self.name, "description": self.description,
            "parameters": self.parameters}}
