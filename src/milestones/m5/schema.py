# [M5-origin]
"""
Pydantic output schemas for M5.

SpecAdvisorOutput: M4 fields + specialist_crispe_prompt (appended in run(), not from LLM).
SpecialistOutput: spec_content, spec_lang, well_formedness_notes, confidence.
"""

from pydantic import BaseModel, Field


class SpecAdvisorOutput(BaseModel):
    """M5: COSTAR + ChainOfThought + ConstitutionalAI output + CRISPE meta-prompt."""

    selected_lang: str = Field(
        description="The formal specification language selected for this layer."
    )
    layer: str = Field(
        description="Which spec layer this targets: 'system', 'domain', 'component', or 'api'."
    )
    justification: str = Field(
        description="Why this language is the best fit. Must reference specific project "
        "characteristics."
    )
    confidence: float = Field(
        description="Confidence in the selection, 0.0 to 1.0.",
        ge=0.0,
        le=1.0,
    )
    reasoning_steps: list[str] = Field(
        description="Ordered reasoning steps. Each step references a concern or candidate "
        "language.",
        default_factory=list,
    )
    revised: bool = Field(
        description="True if the CAI critique triggered a revision.",
        default=False,
    )
    revision_notes: str = Field(
        description="What changed and why after CAI critique. Empty string if revised=False.",
        default="",
    )
    specialist_crispe_prompt: str = Field(
        description="CRISPE prompt generated from this output, injected as the Spec "
        "Specialist's system prompt.",
        default="",
    )


class SpecialistOutput(BaseModel):
    """Output of the Spec Specialist — the formal specification for a given brief and language."""

    spec_content: str = Field(
        description="The full formal specification text in the selected language."
    )
    spec_lang: str = Field(
        description="The formal specification language used (e.g. 'JSON Schema', 'TLA+', 'OpenAPI')."  # noqa: E501
    )
    well_formedness_notes: str = Field(
        description="Notes from the self-check for syntactic well-formedness and coverage."
    )
    confidence: float = Field(
        description="Confidence in the specification, 0.0 to 1.0.",
        ge=0.0,
        le=1.0,
    )
