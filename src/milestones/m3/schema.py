# [M3-origin | src/agents/schemas.py @ 48a5b37]
"""
Pydantic output schema for the M3 Spec Advisor (COSTAR + ChainOfThought).

Frozen for the M3 milestone — do not import from src.agents.schemas.
"""

from pydantic import BaseModel, Field


class SpecAdvisorOutput(BaseModel):
    """M3: structure (COSTAR) + reasoning (ChainOfThought) Spec Advisor output."""

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
