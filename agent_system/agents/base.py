"""Declarative role configuration; execution lives in runtime.py."""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    prompt: str
    tool_names: Tuple[str, ...]
    include_request: bool = False
