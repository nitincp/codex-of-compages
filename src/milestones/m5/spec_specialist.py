# [M5-origin]
"""
SpecSpecialistAgent — M5 stub.

Receives a CRISPE string as its system prompt at call time (the meta-prompting moment).
No ComposedPrompt chain — the system prompt IS the injected CRISPE prompt from SpecAdvisorAgent.
Forced tool-use returns SpecialistOutput.

Scoped to m5/ only — promoted to src/agents/ at M7 with FewShot + full CAI.
"""

from __future__ import annotations

from typing import cast

from anthropic.types import ToolParam

from src.agents.base import BaseAgent
from src.milestones.m5.schema import SpecialistOutput

_TOOL_NAME = "report_formal_spec"

_TOOL_SCHEMA: ToolParam = cast(
    ToolParam,
    {
        "name": _TOOL_NAME,
        "description": "Report the formal specification generated for the given project brief.",
        "input_schema": {
            "type": "object",
            "properties": {
                "spec_content": {
                    "type": "string",
                    "description": "The full formal specification text in the selected language.",
                },
                "spec_lang": {
                    "type": "string",
                    "description": (
                        "The formal specification language used "
                        "(e.g. 'JSON Schema', 'TLA+', 'OpenAPI')."
                    ),
                },
                "well_formedness_notes": {
                    "type": "string",
                    "description": (
                        "Notes from the self-check for syntactic well-formedness "
                        "and coverage of the stated objective."
                    ),
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence in the specification, 0.0 to 1.0.",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
            },
            "required": ["spec_content", "spec_lang", "well_formedness_notes", "confidence"],
        },
    },
)


class SpecSpecialistAgent(BaseAgent[SpecialistOutput]):
    """Generates a formal specification using an injected CRISPE prompt as its system prompt."""

    def run(self, project_brief: str, system_prompt: str) -> SpecialistOutput:
        """
        Generate a formal specification.

        system_prompt — the CRISPE string produced by SpecAdvisorAgent.build_crispe_prompt().
        project_brief — the raw project brief from the user (user message).
        """
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Project brief: {project_brief}",
                }
            ],
            tools=[_TOOL_SCHEMA],
            tool_choice={"type": "any"},
        )
        self._log_usage(response.usage)

        tool_block = next(b for b in response.content if b.type == "tool_use")
        return SpecialistOutput.model_validate(tool_block.input)
