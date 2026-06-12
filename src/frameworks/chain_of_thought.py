"""
Chain of Thought layer — Reasoning dimension.

From: Wei et al., Google Brain, NeurIPS 2022 (arXiv:2201.11903)
Thesis: intermediate reasoning steps dramatically improve performance on complex tasks.

Makes reasoning steps explicit and auditable. Used by: Spec Advisor (candidate evaluation).

Fields:
  steps   — list of step prompts to reason through in sequence
  preamble — optional instruction before the steps (default: standard CoT preamble)
"""

from dataclasses import dataclass, field


@dataclass
class ChainOfThought:
    _dimension = "Reasoning"
    steps: list[str] = field(default_factory=list)
    preamble: str = "Think through this step by step before producing your final answer."

    def build(self) -> str:
        parts = [self.preamble] if self.preamble else []
        for i, step in enumerate(self.steps, 1):
            parts.append(f"Step {i}: {step}")
        return "\n".join(parts)
