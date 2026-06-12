# [M1-origin | src/frameworks/costar.py]
"""
COSTAR prompt builder — for high-stakes structured outputs (spec selection, architecture docs).

Fields:
  context    — what is known, parent-layer specs
  objective  — what this layer needs to produce
  style      — formal notation with plain-English rationale
  tone       — rigorous, collaborative
  audience   — which agent(s) consume this output
  response   — expected format and constraints
"""

from dataclasses import dataclass


@dataclass
class COSTARPrompt:
    _dimension = "Structure"
    context: str = ""
    objective: str = ""
    style: str = "Formal notation with plain-English rationale"
    tone: str = "Rigorous and collaborative"
    audience: str = ""
    response_format: str = ""

    def build(self) -> str:
        sections = [
            ("Context", self.context),
            ("Objective", self.objective),
            ("Style", self.style),
            ("Tone", self.tone),
            ("Audience", self.audience),
            ("Response Format", self.response_format),
        ]
        return "\n\n".join(f"**{label}**\n{content}" for label, content in sections if content)
