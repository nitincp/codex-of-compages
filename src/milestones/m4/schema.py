# [M4-origin | src/agents/schemas.py @ a966ce9]
"""
Pydantic output schema for the M4 Spec Advisor (COSTAR + ChainOfThought + ConstitutionalAI).

Frozen for the M4 milestone — do not import from src.agents.schemas.
"""

from pydantic import BaseModel, Field


class SpecAdvisorOutput(BaseModel):
    """M4: structure (COSTAR) + reasoning (ChainOfThought) + verification (ConstitutionalAI)."""

    selected_lang: str = Field(
        description="The formal specification language selected for this layer "
        "(e.g. 'JSON Schema', 'OpenAPI', 'TLA+', 'CML', 'Alloy', 'Event-B')."
    )
    layer: str = Field(
        description="Which spec layer this targets: 'system', 'domain', 'component', or 'api'."
    )
    justification: str = Field(
        description="Why this language is the best fit for the project brief and layer. "
        "Must reference specific project characteristics."
    )
    confidence: float = Field(
        description="Confidence in the selection, 0.0 (uncertain) to 1.0 (certain).",
        ge=0.0,
        le=1.0,
    )
    reasoning_steps: list[str] = Field(
        description="Ordered reasoning steps taken to reach the selection. "
        "Each step should reference a specific concern (e.g. concurrency, data shape) "
        "or a candidate language evaluated.",
        default_factory=list,
    )
    revised: bool = Field(
        description="True if the Constitutional AI critique found a principle violation "
        "and the output was revised. False if all principles were satisfied on the first pass.",
        default=False,
    )
    revision_notes: str = Field(
        description="Description of what was changed and why. Empty string if revised=False.",
        default="",
    )
