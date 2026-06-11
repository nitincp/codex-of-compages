"""
Persona Prompting layer — Technique dimension.

Industry-standard technique: prefix the prompt with a rich identity declaration.
Grounds the model in a specific role, background, and communication style.
Used by: SME Agent (who speaks), Spec Specialist (what specialist am I).

Fields:
  role              — job title and seniority
  background        — years of experience, domain expertise
  priorities        — what this persona cares most about
  communication_style — how they express themselves
"""

from dataclasses import dataclass


@dataclass
class PersonaLayer:
    role: str = ""
    background: str = ""
    priorities: str = ""
    communication_style: str = ""

    def build(self) -> str:
        parts = []
        if self.role:
            parts.append(f"You are a {self.role}.")
        if self.background:
            parts.append(self.background)
        if self.priorities:
            parts.append(f"Your priorities: {self.priorities}")
        if self.communication_style:
            parts.append(f"Communication style: {self.communication_style}")
        return " ".join(parts)
