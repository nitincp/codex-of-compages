# ADR-001 — Layered Composition over Monolithic Agent Prompts

**Date:** 2026-06-11  
**Status:** Active  
**Supersedes:** —  
**Referenced by:** All agent implementations; `docs/thesis/CLAIM.md`

---

## Context

When building LLM agent prompts there are three natural approaches:

1. **Monolithic strings** — write the full prompt as a single ad-hoc string
2. **Single framework per agent** — pick one prompting framework (COSTAR, CRISPE, etc.) per agent
3. **Layered composition** — compose multiple orthogonal framework layers; each layer contributes one dimension

Faber has five agents with distinct primary concerns:

| Agent | Concerns |
|---|---|
| SME Agent | Persona fidelity, stakeholder voice authenticity, conversation history |
| Spec Advisor | Selection reasoning, spec language justification, meta-prompt generation |
| Spec Specialist | Technical generation, formal syntax correctness, coverage of domain |
| Coordinator | Deliberation, auditable decisions, loop control |
| Test Engineer | Traceability to spec, BDD syntax, scenario coverage |

No single framework covers all of these. COSTAR excels at structured output but has no reasoning trace. CRISPE excels at technical generation but has no deliberation model. Constitutional AI alone has no task structure.

---

## Decision

Every agent prompt is built by `ComposedPrompt([layer1, layer2, ...]).build()`. Each layer belongs to exactly one dimension. The four dimensions and their frameworks:

```
Structure    COSTAR, CRISPE, CLEAR, RACE   — prompt shape, output format, section headers
Reasoning    ChainOfThought, ReActLoop     — explicit, auditable thinking steps
Verification ConstitutionalAI              — critique → revise loop, output gate
Technique    PersonaLayer, FewShot         — specific capability applied to task
```

**Two hard rules:**
1. One layer per dimension per agent — no redundancy, no contradiction between layers
2. Structure first, Verification always last

---

## Rationale

**DSPy (Khattab et al., NeurIPS 2023)**: composable declarative modules outperform monolithic prompts by 25–65%. The argument applies directly: a `COSTARPrompt` object with named fields is maintainable, reviewable, and composable; a raw string is not.

**ACL 2024 (Sun et al.)**: chained prompts (separate draft / critique / refine stages) consistently outperform prompts combining all stages. This is the direct empirical grounding for the critique-revision loop as a separate layer.

**Constitutional AI (Bai et al., Anthropic 2022)**: the critique-revision loop as a verifiable output gate. Achievable only as a separate Verification layer — baking it into the Structure layer defeats its purpose.

**Independent testability**: a broken COSTAR builder fails a unit test in M01, not a production run in M07. The systematic PoC strategy (M01: prove all builders) is enabled by layer-level testability.

**Replaceability**: if ConstitutionalAI is too expensive for a simple project tier, it is removed without touching Structure or Reasoning layers. If ChainOfThought is replaced by TreeOfThoughts, the Verification layer is unaffected.

---

## Alternatives Considered

**Monolithic strings**: not composable, not testable per-dimension, not maintainable as the agent evolves. A prompt string change requires full agent re-testing. Rejected.

**Single framework per agent**: better than monolithic but cannot handle multi-dimensional needs. The SME Agent needs persona simulation (Technique), output structure (Structure), AND an authenticity gate (Verification). A single framework cannot serve three dimensions without conflation. Rejected.

**Custom frameworks** (e.g., VOICE — see ADR-002): invented here, not research-grounded. Creates a maintenance burden and cannot be composed with industry-standard layers without dimension overlap. Retired (ADR-002).

---

## Consequences

- One layer per dimension per agent is a **hard rule**, not a guideline. If a new agent seems to need two Structure layers, this signals a dimension boundary error — fix the layer design, not the rule.
- Systematic PoC execution is **necessary**: M01 proves the base layer (all builders); each subsequent milestone adds one layer and measures its effect against the previous baseline. You cannot skip a layer.
- Token cost is higher per agent call — measured per milestone. Mitigation: Constitutional AI can run inline (same call, longer prompt) rather than as a second call. Only the Coordinator's ReAct loop benefits from a dedicated call.
- Debugging requires per-layer logging. `FABER_LOG_PROMPTS=true` logs each `build()` output. When output is wrong, diff against the previous milestone's baseline to identify which layer introduced the error.
