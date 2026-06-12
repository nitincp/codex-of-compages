# [M2-origin | src/agents/schemas.py @ 05f373d]
"""
Frozen M2 output schema for the Spec Advisor agent.

4-field schema: COSTAR-only baseline (no reasoning_steps, no revised, no revision_notes).
This schema is intentionally frozen — do not add fields from later milestones.
"""

from pydantic import BaseModel, Field


class SpecAdvisorOutput(BaseModel):
    """M2 baseline: structure-only Spec Advisor output."""

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
