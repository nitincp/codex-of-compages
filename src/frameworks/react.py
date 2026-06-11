"""
ReAct layer — Reasoning dimension.

From: Yao et al., Google + Princeton, ICLR 2023 (arXiv:2210.03629)
Thesis: interleaving Reasoning traces with Acting steps outperforms either alone.
        Produces auditable, human-readable decisions.

Used by: Coordinator (assess spec quality → decide proceed/retry/escalate).

Fields:
  thought_prompt   — what to reason about
  action_options   — the possible actions (e.g. ["proceed", "retry", "escalate"])
  observation_note — what the observation should capture after acting
"""

from dataclasses import dataclass, field


@dataclass
class ReActLoop:
    thought_prompt: str = ""
    action_options: list[str] = field(default_factory=list)
    observation_note: str = ""

    def build(self) -> str:
        parts = []
        if self.thought_prompt:
            parts.append(f"**Thought**\n{self.thought_prompt}")
        if self.action_options:
            options = " | ".join(self.action_options)
            parts.append(f"**Action**\nChoose one: {options}\nState your chosen action and the explicit rationale.")
        if self.observation_note:
            parts.append(f"**Observation**\n{self.observation_note}")
        return "\n\n".join(parts)
