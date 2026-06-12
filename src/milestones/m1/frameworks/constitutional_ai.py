# [M1-origin | src/frameworks/constitutional_ai.py]
"""
Constitutional AI layer — Verification dimension.

From: Bai et al., Anthropic, 2022 (arXiv:2212.08073)
Thesis: generate → critique against explicit principles → revise until criteria pass.
        The critique-revision loop as a self-correcting output gate.

Used by all agents as the final layer before output is accepted.

Fields:
  principles  — list of criteria the output must satisfy
  revise_note — instruction for what to do when a principle is violated
                (default: revise before outputting)
"""

from dataclasses import dataclass, field


@dataclass
class ConstitutionalAI:
    _dimension = "Verification"
    principles: list[str] = field(default_factory=list)
    revise_note: str = (
        "If any principle is violated, revise your output before producing the final result."
    )

    def build(self) -> str:
        if not self.principles:
            return self.revise_note
        numbered = "\n".join(f"  {i + 1}. {p}" for i, p in enumerate(self.principles))
        return f"Critique your output against these principles:\n{numbered}\n\n{self.revise_note}"
