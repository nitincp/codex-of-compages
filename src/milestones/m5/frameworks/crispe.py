# [M5-copy | src/frameworks/crispe.py]
"""
CRISPE prompt builder — for technical generation and complex reasoning.
Used by: Spec Specialist (receives this as a dynamically generated system prompt),
         Test Engineer (Gherkin generation from spec stack).

For persona simulation (SME Agent), use VOICEPrompt instead.

Fields:
  capacity    — act as a [spec language] specialist
  role        — this agent's role in the council
  insight     — context from parent-layer specs (injected)
  statement   — the specific generation task
  personality — precise, minimal, verifiable
  experiment  — generate + self-check for syntactic well-formedness
"""

from dataclasses import dataclass


@dataclass
class CRISPEPrompt:
    _dimension = "Structure"
    capacity: str = ""
    role: str = ""
    insight: str = ""
    statement: str = ""
    personality: str = "Precise, minimal, and verifiable"
    experiment: str = (
        "Generate the spec, then self-check for syntactic well-formedness"
        " and coverage of the stated objective."
    )

    def build(self) -> str:
        sections = [
            ("Capacity", self.capacity),
            ("Role", self.role),
            ("Insight", self.insight),
            ("Statement", self.statement),
            ("Personality", self.personality),
            ("Experiment", self.experiment),
        ]
        return "\n\n".join(f"**{label}**\n{content}" for label, content in sections if content)
