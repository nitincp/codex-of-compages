# ADR-002 — VOICE Framework Retired

**Date:** 2026-06-11  
**Status:** Retired  
**Superseded by:** ADR-001 (layered composition)  
**Affected file:** `src/frameworks/voice.py` — preserved with RETIRED notice, must not be used

---

## Context

VOICE was designed as a dedicated persona-simulation framework for the SME Agent.
Five fields: Voice (identity), Ownership (domain scope), Interaction (conversation history),
Context (situational), Examine (authenticity gate).

The design rationale was: persona simulation has enough unique requirements
to warrant its own framework rather than repurposing a general one.

---

## Problem

VOICE was silently baking **three orthogonal dimensions** into a single framework:

| VOICE field | Actual dimension |
|---|---|
| Voice, Ownership | Technique — what the persona is and cares about |
| Context, Interaction | Structure — session framing and output context |
| Examine | Verification — authenticity gate: does this sound like a real [persona]? |

This violated ADR-001's one-layer-per-dimension rule before that rule was formalised.
It also created a custom framework with no research grounding — an "invented here" solution
that could not compose cleanly with industry-standard layers.

Concretely: if a future SME Agent needed a CoT reasoning step, there was no clean place
for it in VOICE. Interaction could be co-opted, but then two concerns lived in one field.

---

## Decision

VOICE is retired. The SME Agent's composition chain is:

```
CLEAR → COSTAR → PersonaLayer → ConstitutionalAI ↩
```

| Replaced by | Dimension | What it carries |
|---|---|---|
| `COSTAR` | Structure | Output format, session context, audience, tone |
| `PersonaLayer` | Technique | Persona identity: role, background, priorities, communication style |
| `ConstitutionalAI` | Verification | Authenticity gate: would a real [persona] actually say this? |

The `CLEAR` layer (Structure — session context) can be prepended when conversation history
across turns must be injected (used in SME Agent Phase B for Reflexion-style memory).

---

## Rationale

**No capability is lost.** Every VOICE field maps cleanly:

| VOICE field | Replaced by |
|---|---|
| Voice (identity) | `PersonaLayer.role` + `PersonaLayer.background` |
| Ownership (priorities/non-negotiables) | `PersonaLayer.priorities` |
| Interaction (conversation history) | `CLEAR.context` (or `COSTAR.context` if simpler) |
| Context (domain brief, scenario hint) | `COSTAR.context` |
| Examine (authenticity gate) | `ConstitutionalAI.principles` — e.g. "Would a real [persona] say this? If not, revise." |

**Each replacement layer is independently testable** — a failing authenticity check is a
ConstitutionalAI unit test failure, not a VOICE build() test failure.

**Each layer is research-grounded** — PersonaLayer is an established industry technique;
Constitutional AI is Anthropic 2022; COSTAR is an industry standard. VOICE had no citation.

---

## Preserved For

`src/frameworks/voice.py` is preserved with a RETIRED notice for historical reference.
The class is functional but must not be used in any new agent, test, or composition chain.
It serves as documentation of the rejected approach.
