"""
SpecAdvisorAgent — M2 baseline: COSTAR structure layer only.

Selects the optimal formal specification language for a given project brief.
Later milestones add ChainOfThought (M3) and ConstitutionalAI (M4).

Composition chain (M2): COSTARPrompt only
"""

from __future__ import annotations

from typing import cast

from anthropic.types import ToolParam

from src.agents.base import BaseAgent
from src.agents.schemas import SpecAdvisorOutput
from src.frameworks import ComposedPrompt, COSTARPrompt

_TOOL_NAME = "report_spec_selection"

_TOOL_SCHEMA: ToolParam = cast(
    ToolParam,
    {
        "name": _TOOL_NAME,
        "description": "Report the selected formal specification language and justification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selected_lang": {
                    "type": "string",
                    "description": "The formal specification language selected for this layer "
                    "(e.g. 'JSON Schema', 'OpenAPI', 'TLA+', 'CML', 'Alloy', 'Event-B').",
                },
                "layer": {
                    "type": "string",
                    "description": "Which spec layer this targets: "
                    "'system', 'domain', 'component', or 'api'.",
                },
                "justification": {
                    "type": "string",
                    "description": "Why this language best fits the project. "
                    "Reference specific project characteristics.",
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence in the selection, 0.0 to 1.0.",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
            },
            "required": ["selected_lang", "layer", "justification", "confidence"],
        },
    },
)

_SPEC_LANGUAGES = """
Available formal specification languages and their ideal use cases:
- JSON Schema: data shapes, simple REST payloads, configuration schemas
- OpenAPI: REST API contracts, request/response schemas, multi-endpoint services
- Pydantic: Python data models with validation, internal API contracts
- TLA+: distributed systems, concurrency, consistency properties, safety/liveness proofs
- CML: communicating concurrent processes, session protocols, message-passing systems
- Alloy: relational/structural properties, access control, data invariants, bounded verification
- Event-B: safety-critical systems, refinement-based development, certified software
"""


class SpecAdvisorAgent(BaseAgent[SpecAdvisorOutput]):
    """
    Selects the optimal formal specification language for a project brief.

    M2: COSTAR structure layer only — baseline for comparison in later milestones.
    """

    def _build_system_prompt(self) -> str:
        costar = COSTARPrompt(
            context=(
                "You are the Spec Advisor in the Faber prompt engineering council. "
                "Your role is to analyse a project brief and select the most appropriate "
                "formal specification language for the current layer of the spec stack. "
                "The project brief may range from a simple CRUD app to a complex "
                "distributed system; your selection must reflect that complexity.\n\n"
                + _SPEC_LANGUAGES
            ),
            objective=(
                "Select the single best formal specification language for the given project "
                "brief and identify which spec layer it addresses (system, domain, component, "
                "or api). Provide a concise but specific justification referencing concrete "
                "characteristics of the project (e.g. concurrency requirements, data model "
                "complexity, API surface, consistency constraints)."
            ),
            style="Formal and analytical. Reference specific technical properties of the project.",
            tone="Rigorous and precise",
            audience=(
                "The Spec Specialist agent, which will use your selection to generate a "
                "formal specification. Your justification informs which properties to emphasise."
            ),
            response_format=(
                "Call the report_spec_selection tool with: selected_lang (exact language name "
                "from the list above), layer (system/domain/component/api), justification "
                "(why this language fits — must cite specific project characteristics), "
                "confidence (0.0–1.0)."
            ),
        )
        return ComposedPrompt(layers=[costar]).build()

    def run(self, project_brief: str) -> SpecAdvisorOutput:
        """Select a spec language for the given project brief."""
        system_prompt = self._build_system_prompt()

        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
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
        return SpecAdvisorOutput.model_validate(tool_block.input)
