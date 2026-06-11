"""
Faber prompt engineering framework layer builders.

Each class implements build() -> str and belongs to exactly one dimension:

  Structure    COSTAR, CRISPE, CLEAR, RACE
  Reasoning    ChainOfThought, ReActLoop
  Verification ConstitutionalAI
  Technique    PersonaLayer, FewShot

Compose with ComposedPrompt([layer1, layer2, ...]).build().
One layer per dimension. Structure first, Verification last.

See docs/composition_framework.md for the full architecture.
"""

from .chain_of_thought import ChainOfThought
from .clear import CLEARSession
from .composed import ComposedPrompt
from .constitutional_ai import ConstitutionalAI
from .costar import COSTARPrompt
from .crispe import CRISPEPrompt
from .few_shot import FewShot
from .persona import PersonaLayer
from .race import RACEPrompt
from .react import ReActLoop

__all__ = [
    # Structure
    "CLEARSession",
    "COSTARPrompt",
    "CRISPEPrompt",
    "RACEPrompt",
    # Reasoning
    "ChainOfThought",
    "ReActLoop",
    # Verification
    "ConstitutionalAI",
    # Technique
    "PersonaLayer",
    "FewShot",
    # Composition
    "ComposedPrompt",
]
