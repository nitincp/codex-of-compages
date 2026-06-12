# ADR-003 — Constitutional AI as the Universal Verification Layer

**Date:** 2026-06-11  
**Status:** Active  
**Supersedes:** —  
**Referenced by:** All agent implementations; `docs/thesis/CLAIM.md`; ADR-001

---

## Context

Every agent in Faber produces structured output that feeds the next agent in the chain.
Low-quality output at one layer propagates and amplifies downstream — a weak justification
from the Spec Advisor becomes a malformed CRISPE prompt, which produces a spec the Test
Engineer cannot trace. There must be an output gate at every agent boundary.

Four patterns exist for gating agent output quality:

1. **Post-hoc human review** — a human checks the output before the chain proceeds
2. **LLM-as-judge** — a separate model call rates the output against a rubric
3. **Self-reflection** — the same model re-reads its output and scores it in a second pass
4. **Critique-revision loop** — the model critiques its output against explicit principles
   and revises if any principle is violated (Constitutional AI pattern)

The gate must work at inference time without human involvement, be explainable (the critique
is visible in the output), and be compatible with forced tool-use structured output.

---

## Decision

Every Faber agent's composition chain ends with a `ConstitutionalAI` layer.
The critique-revision loop runs inline: the model generates output, checks it against
numbered principles, and revises if any principle is violated — before returning the result.

Principles are agent-specific and encode the layer's quality criteria. Examples:
- Spec Advisor: "Justification references specific project characteristics", "Confidence ≥ 0.7"
- SME Agent: "This requirement would be said by a real [persona]", "Domain vocabulary is precise"
- Spec Specialist: "All required fields of the spec language are present", "No undefined symbols"

`ConstitutionalAI` is the last layer in every composition chain — after Structure and Reasoning
layers have shaped the output, Verification gates it.

---

## Rationale

**Inline, not a separate call.** Baking the critique-revision loop into the prompt means
a single API call per agent turn. A separate LLM-as-judge call doubles token cost and latency
per agent, which compounds across a six-agent chain.

**Principles are explicit and auditable.** The numbered principles in the ConstitutionalAI
layer are checked commitments — if the model violates one and revises, the revision is visible.
A silent self-reflection score is not auditable; a numbered-principle critique is.

**Research grounding.** Constitutional AI (Bai et al., Anthropic 2022) was designed for
Claude-family models. The critique-revision pattern is native to this model family, not
adapted from a different architecture. Using it here is using the right tool.

**Composability.** As a separate `Verification` dimension layer (per ADR-001), it can be
applied to any agent without touching Structure or Reasoning layers. Removing it for a
lightweight deployment tier is a one-line change in the composition chain.

**ACL 2024 grounding.** Sun et al. show that a separate critique/refine stage outperforms
a combined draft+critique prompt. The layer boundary enforces this separation by design.

---

## Alternatives Considered

**Human review at each boundary**: not viable for an automated council. Correct for
safety-critical production systems; wrong for a development-time prompt engineering framework.
Rejected.

**LLM-as-judge (separate model call)**: doubles API cost per agent turn. Introduces a
second model whose calibration may differ from the generating model. No inline revision —
a low score triggers a retry at the pipeline level, not a targeted fix. Rejected.

**Self-reflection / self-scoring without explicit principles**: produces inconsistent scores.
Without numbered principles, the model has no specific commitments to check against.
Useful for confidence estimation; insufficient as a quality gate. Rejected.

**No gate (trust the Structure layer)**: M4 will empirically test whether CAI improves
weak outputs and passes strong outputs through. Until disproven, the hypothesis is that
a gate is necessary. Removing it is a one-line change per ADR-001's composability guarantee.

---

## Consequences

- `ConstitutionalAI` appears last in every agent's composition chain — this is a **hard rule**,
  not a guideline. Placing a Structure or Reasoning layer after Verification breaks the
  critique-revision semantics.
- Principles must be specific to the agent's output schema — generic principles ("be accurate")
  produce no measurable gate effect. Each agent's principles should reference named fields
  and thresholds (`confidence ≥ 0.7`, `justification references project characteristics`).
- M4 is the empirical test of this ADR: it will verify that the gate demonstrably revises
  weak outputs and passes strong ones through. If M4 shows no improvement, this decision
  must be revisited.
- `revised: bool` and `revision_notes: str` fields added to `SpecAdvisorOutput` at M4
  make the gate's operation observable in the artifact record.
