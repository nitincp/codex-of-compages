"""
Few-shot layer — Technique dimension.

Industry-standard technique: provide 1-3 examples to ground the model's output format
and syntax. Used by: Spec Specialist (spec syntax examples from Kuzu graph),
Test Engineer (Gherkin examples derived from spec artifacts).

Fields:
  examples     — list of (label, content) tuples
  preamble     — optional instruction before examples
"""

from dataclasses import dataclass, field


@dataclass
class FewShot:
    examples: list[tuple[str, str]] = field(default_factory=list)
    preamble: str = "Here are examples to guide the format and style of your output:"

    def build(self) -> str:
        if not self.examples:
            return ""
        parts = [self.preamble] if self.preamble else []
        for label, content in self.examples:
            parts.append(f"--- Example: {label} ---\n{content}")
        return "\n\n".join(parts)
