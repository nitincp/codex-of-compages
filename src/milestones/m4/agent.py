# [M4-origin | src/agents/spec_advisor.py @ a966ce9]
"""
SpecAdvisorAgent — M4: COSTAR (Structure) + ChainOfThought (Reasoning)
+ ConstitutionalAI (Verification).

Selects the optimal formal specification language for a given project brief.
CAI critique-revision loop self-corrects weak outputs and passes strong ones through.

Composition chain (M4): COSTARPrompt → ChainOfThought → ConstitutionalAI

Frozen for the M4 milestone — do not import from src.agents.
"""

from __future__ import annotations

from typing import cast

from anthropic.types import ToolParam

from src.agents.base import BaseAgent
from src.milestones.m4.frameworks.chain_of_thought import ChainOfThought
from src.milestones.m4.frameworks.composed import ComposedPrompt
from src.milestones.m4.frameworks.constitutional_ai import ConstitutionalAI
from src.milestones.m4.frameworks.costar import COSTARPrompt
from src.milestones.m4.schema import SpecAdvisorOutput

_TOOL_NAME = "report_spec_selection"

_TOOL_SCHEMA: ToolParam = cast(
    ToolParam,
    {
        "name": _TOOL_NAME,
        "description": "Report the selected spec language, reasoning steps, and justification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reasoning_steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ordered reasoning steps taken to reach the selection. "
                    "Each step must reference a specific concern (e.g. concurrency, data shape, "
                    "API surface) or name a candidate language being evaluated.",
                },
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
                "revised": {
                    "type": "boolean",
                    "description": (
                        "Set to true if the Constitutional AI critique found a principle "
                        "violation and you revised your output. False if all principles "
                        "were satisfied on the first pass."
                    ),
                },
                "revision_notes": {
                    "type": "string",
                    "description": (
                        "Describe what was changed and why after the CAI critique. "
                        "Empty string if revised=false."
                    ),
                },
            },
            "required": [
                "reasoning_steps",
                "selected_lang",
                "layer",
                "justification",
                "confidence",
                "revised",
                "revision_notes",
            ],
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
    """Selects the optimal formal specification language for a project brief."""

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
                "Call the report_spec_selection tool with: reasoning_steps (ordered list of "
                "steps taken — each step names a concern or candidate language evaluated), "
                "selected_lang (exact language name from the list above), "
                "layer (system/domain/component/api), justification "
                "(why this language fits — must cite specific project characteristics), "
                "confidence (0.0–1.0), "
                "revised (true if the CAI critique caused you to change your output, "
                "false if all principles were satisfied on the first pass), "
                "revision_notes (what changed and why; empty string if revised=false)."
            ),
        )
        cot = ChainOfThought(
            steps=[
                "Identify the primary technical concerns of this project brief "
                "(e.g. concurrency, data shape, API surface, safety constraints, "
                "consistency model).",
                "For each concern, name one or two candidate specification languages "
                "that address it and briefly evaluate their fit.",
                "Weigh the candidates against each other: which language covers the most critical "
                "concerns with the least overhead for this project's complexity level?",
                "Select the best language and determine which spec layer it targets "
                "(system, domain, component, or api).",
                "State your confidence in the selection (0.0–1.0) based on how well the language "
                "covers the identified concerns.",
            ]
        )
        cai = ConstitutionalAI(
            principles=[
                "The justification must reference at least one specific technical characteristic "
                "of the project (e.g. concurrency model, consistency requirements, API surface, "
                "data shapes, safety constraints). Generic statements that could apply to any "
                "project are not acceptable.",
                "The reasoning_steps must include at least one step that names a candidate "
                "specification language by name and explicitly evaluates its fit against a "
                "specific characteristic of this project.",
                "If the project brief is vague or underspecified — providing fewer than two "
                "concrete technical signals — you must lower confidence below 0.75 AND set "
                "revised=true, with revision_notes explaining what assumptions were required.",
            ],
            revise_note=(
                "If any principle is violated: revise your selection, justification, and "
                "reasoning_steps accordingly. Set revised=true in the tool call and describe "
                "what changed in revision_notes. "
                "If all principles are satisfied, set revised=false and revision_notes to an "
                "empty string."
            ),
        )
        return ComposedPrompt(layers=[costar, cot, cai]).build()

    def run(self, project_brief: str) -> SpecAdvisorOutput:
        """Select a spec language for the given project brief."""
        system_prompt = self._build_system_prompt()

        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
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
