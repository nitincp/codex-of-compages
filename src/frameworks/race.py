"""
RACE prompt builder — for lightweight generation tasks (code stubs, test scaffolds, config).

Fields:
  role     — brief agent identity
  action   — specific generation task
  context  — minimal necessary context
  execute  — output format and constraints
"""

from dataclasses import dataclass


@dataclass
class RACEPrompt:
    role: str = ""
    action: str = ""
    context: str = ""
    execute: str = ""

    def build(self) -> str:
        sections = [
            ("Role", self.role),
            ("Action", self.action),
            ("Context", self.context),
            ("Execute", self.execute),
        ]
        return "\n\n".join(f"**{label}**\n{content}" for label, content in sections if content)
