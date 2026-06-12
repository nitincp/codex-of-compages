"""
Pydantic output schemas for all Faber agents.

Each schema mirrors the forced tool-use input_schema sent to the model.
Fields are added per milestone — see BACKLOG.md for which fields are active at each layer.
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
