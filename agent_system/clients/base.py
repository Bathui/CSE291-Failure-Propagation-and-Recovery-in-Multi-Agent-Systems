"""Interfaces consumed by agents and experiment setup."""
from typing import Protocol


class ChatModel(Protocol):
    def chat(self, messages: list, tools: list, seed: int) -> dict:
        """Return a chat completion without interpreting workflow state."""
        ...


class ModelClient(ChatModel, Protocol):
    def preflight(self) -> dict:
        """Check connectivity and return provider metadata."""
        ...
