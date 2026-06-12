# [M1-origin | src/frameworks/composed.py]
"""
ComposedPrompt — assembles a chain of framework layers into a single prompt string.

Each layer must implement build() -> str.
Layers are assembled in declared order, separated by a section divider.
Empty layers (build() returns '') are skipped.

Usage:
    prompt = ComposedPrompt([
        CLEARSession(context=..., layering=..., execute=...),
        COSTARPrompt(context=..., objective=..., response_format=...),
        PersonaLayer(role=..., background=..., priorities=...),
        ConstitutionalAI(principles=[...]),
    ]).build()

The composed string is logged at construction time if FABER_LOG_PROMPTS=true.
"""

import os
from dataclasses import dataclass, field

DIVIDER = "\n\n---\n\n"


@dataclass
class ComposedPrompt:
    layers: list = field(default_factory=list)

    def build(self) -> str:
        parts = []
        for layer in self.layers:
            text = layer.build()
            if text and text.strip():
                dimension = getattr(layer, "_dimension", "Unknown")
                label = f"# [{dimension}: {type(layer).__name__}]"
                parts.append(f"{label}\n{text.strip()}")
        result = DIVIDER.join(parts)
        if os.getenv("FABER_LOG_PROMPTS", "").lower() == "true":
            layer_names = ", ".join(type(layer).__name__ for layer in self.layers)
            print(f"[ComposedPrompt] layers=[{layer_names}] length={len(result)}")
        return result
