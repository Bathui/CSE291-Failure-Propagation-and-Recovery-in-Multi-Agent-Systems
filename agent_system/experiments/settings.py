"""Runtime settings for a live-model experiment."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExperimentSettings:
    base_url: str = "http://127.0.0.1:8000/v1"
    model: str = "cse291-qwen3-8b"
    timeout: float = 180
    max_tokens: int = 512
    max_turns: int = 6
    repeats: int = 1
    seed: int = 42
    output: Path = Path("results_llm")

    def __post_init__(self):
        if min(self.repeats, self.max_tokens, self.max_turns) < 1 or self.timeout <= 0:
            raise ValueError("Repeat count, token limit, turn limit and timeout must be positive")
