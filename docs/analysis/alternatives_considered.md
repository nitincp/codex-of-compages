# Alternatives Considered

Analysis of approaches evaluated during Faber's design phase.
Not the architecture itself — the thinking behind it.

See [ADR-001](../decisions/ADR-001_layered-composition-over-monolithic.md) and
[ADR-002](../decisions/ADR-002_voice-retired.md) for the formal decision records.
See [docs/foundations/composition_framework.md](../foundations/composition_framework.md)
for the full research grounding and one-shot examples.

---

## Monolithic agent prompts

**What it is**: write a single ad-hoc string for each agent's system prompt.

**Why it was considered**: it is the default; requires no framework machinery.

**Why it was rejected**: not composable, not testable per-dimension.
A string change requires full agent re-testing. When output degrades, the cause is anywhere
in the string. DSPy (NeurIPS 2023) makes this argument explicitly: prompt pipelines
should be declarative modules, not ad-hoc strings.

---

## Single framework per agent (no composition)

**What it is**: pick one framework per agent — COSTAR for Spec Advisor, CRISPE for Spec Specialist, etc.

**Why it was considered**: cleaner than monolithic; at least each framework has named fields.

**Why it was rejected**: each agent has multi-dimensional needs that no single framework covers.
The SME Agent needs persona simulation (Technique), output structure (Structure), AND an
authenticity gate (Verification). Forcing all three into one framework creates VOICE — see below.

---

## VOICE — custom persona simulation framework

**What it was**: a custom 5-field framework (Voice, Ownership, Interaction, Context, Examine)
designed specifically for the SME Agent.

**Why it was considered**: persona simulation felt like a self-contained concern that warranted
its own framework. The field names were clear and purpose-built.

**Why it was retired**: VOICE was silently baking three orthogonal dimensions into one framework.
Voice + Ownership = Technique. Context + Interaction = Structure. Examine = Verification.
No single field name maps to a single dimension. Additionally, it was a custom "invented here"
framework with no research grounding, creating a maintenance burden outside the composition model.

Replaced by: `COSTAR` (Structure) + `PersonaLayer` (Technique) + `ConstitutionalAI` (Verification).
See [ADR-002](../decisions/ADR-002_voice-retired.md).

---

## DDD-first specification strategy

**What it is**: fix DDD/CML as the primary specification approach for all projects (as in Senatus).

**Why it was considered**: DDD is a well-established methodology with strong tooling and broad
understanding. Senatus already implements it. It is a natural starting point.

**Why it was rejected**: DDD/CML is optimal for complex domain-rich systems but is overkill
for a CRUD app. A payment gateway needs TLA+ for its protocol behavior, OpenAPI for its contracts,
and Alloy for its PCI invariants — DDD/CML captures only the domain model layer.
Faber's Spec Advisor makes DDD one selectable option among many, appropriate when the
domain structure is the primary concern.

---

## Tensions in the current design

These tensions are not resolved — they are held intentionally.
Each milestone produces evidence that refines our understanding of each one.

**T1 — Token cost compounds with layers.**
A 4-layer chain is 3–4× the prompt length of a single prompt.
*Current mitigation*: Constitutional AI runs inline (same API call, longer prompt) rather than
as a separate call. Only the Coordinator's ReAct loop genuinely benefits from a dedicated call.
Measured per milestone — do not assume; verify.

**T2 — Layers can contradict each other.**
A CLEAR context injecting "turn 2" can conflict with a COSTAR context injecting different history.
*Current rule*: one-layer-per-dimension prevents this; CLEAR is session-wide, COSTAR is task-specific.
If contradiction appears, it signals a dimension boundary violation — fix the layer, not the content.

**T3 — More layers, harder to debug.**
When output is wrong, which layer caused it?
*Current mitigation*: `FABER_LOG_PROMPTS=true` logs each `build()` output.
The systematic PoC approach (one layer added per milestone) means each addition has a baseline to diff against.

**T4 — Are structure frameworks necessary at all?**
A capable model given plain instructions might perform equivalently.
*Current position*: structure frameworks are a software engineering win regardless of model capability.
A `COSTARPrompt` with named fields is maintainable, reviewable, and composable. A string is not.
DSPy makes this argument explicitly. M02 will provide empirical evidence either way.

**T5 — Meta-prompting brittleness.**
If the Spec Advisor's CoT produces a poor CRISPE prompt, the Spec Specialist inherits the error.
*Current mitigations*: (1) Spec Advisor's CoT makes reasoning auditable — the Coordinator can inspect it.
(2) Spec Specialist's Constitutional AI gate catches output failures and triggers a Coordinator retry.
Errors surface, not propagate. M07 will validate this claim.

**T6 — Is this composable or just structured concatenation?**
The model sees a flat prompt at runtime, not "layers."
*Current position*: composability is a construction-time property, not a runtime one.
DSPy makes the same argument. The PoC-by-layer strategy provides the empirical proof:
add one layer at a time, measure each addition against the prior baseline.
