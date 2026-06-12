# [M1-origin | src/frameworks/clear.py]
"""
CLEAR session protocol — enforced by the Coordinator at every council turn.

Fields:
  context  — what is known, what prior layers produced
  layering — which spec layer is being addressed
  execute  — the agent task for this layer
  assess   — validation criteria for the output
  reflect  — what changed, what the next layer inherits
"""

from dataclasses import dataclass


@dataclass
class CLEARSession:
    _dimension = "Structure"
    context: str = ""
    layering: str = ""
    execute: str = ""
    assess: str = ""
    reflect: str = ""

    def build(self) -> str:
        sections = [
            ("Context", self.context),
            ("Layering", self.layering),
            ("Execute", self.execute),
            ("Assess", self.assess),
            ("Reflect", self.reflect),
        ]
        return "\n\n".join(f"**{label}**\n{content}" for label, content in sections if content)
