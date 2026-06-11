"""
VOICE — RETIRED. Do not use.

Replaced by: COSTARPrompt (Structure) + PersonaLayer (Technique) + ConstitutionalAI (Verification).
Each dimension is now a separate composable layer. See docs/composition_framework.md.

Original rationale for VOICE preserved below for historical reference only.
---
VOICE prompt builder — for persona simulation (SME Agent).

Grounds the concept of embodying a domain expert across a multi-turn conversation.
Each field name states exactly what it carries.

Fields:
  voice       — persona identity: role, background, domain expertise, communication style
  ownership   — domain scope: responsibilities, priorities, concerns, non-negotiables
  interaction — conversation history: requirements already stated + council responses received
  context     — situational context: system being built, current scenario hint
  examine     — authenticity gate: would a real [persona] say this?
"""

from dataclasses import dataclass


@dataclass
class VOICEPrompt:
    voice: str = ""
    ownership: str = ""
    interaction: str = ""
    context: str = ""
    examine: str = (
        "Before outputting: would a real person matching this persona actually say this? "
        "Is it consistent with prior requirements stated in this session and the council's "
        "last response? Does it sound like a stakeholder need, not a technical specification? "
        "If not, revise before outputting."
    )

    def build(self) -> str:
        sections = [
            ("Voice", self.voice),
            ("Ownership", self.ownership),
            ("Interaction", self.interaction),
            ("Context", self.context),
            ("Examine", self.examine),
        ]
        return "\n\n".join(f"**{label}**\n{content}" for label, content in sections if content)
