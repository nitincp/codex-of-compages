# Faber — Architecture Document

> **Faber** *(Latin)*: maker, artisan, smith, architect.  
> A prompt engineering project that transforms requirements into a layered stack of formal specifications using a minimal council of LLM agents.

**Author:** Nitin Pawar | **Date:** June 2026  
**Status:** Active — M0–M4 proven; M4.1 GNN PoC in progress (M4.1 M0–M3 proven)

> This document captures **design intent**. For current implementation state and session guidance:
> - `README.md` — current milestone state, where to look for what
> - `CLAUDE.md` — implementation rules, commands, invariants
> - `docs/running-with-claude.md` — session management and analytical workflow
> - `BACKLOG.md` — milestone task lists with proven/pending items

---

## Vision

Faber transforms requirements into a stack of formal specifications — each layer expressed in the language best suited to its concerns — using a minimal council of LLM agents grounded in structured prompt engineering frameworks.

The core insight: **no single specification language is optimal at all levels of a system**. A distributed protocol needs TLA+; its domain model needs CML; its API contracts need OpenAPI; its invariants need Alloy; its observable behavior needs Gherkin. Faber's Spec Advisor navigates this landscape layer by layer, selecting the best-fit language at each granularity and generating a dynamically configured Spec Specialist for that layer.

The SME Agent stands at the other end: it simulates the human expert who drives requirements into the council, making automated pipeline testing possible without a human in the loop.

This is a **prompt engineering project first**. Every agent prompt is a **layered chain of industry-standard frameworks** — each layer contributing exactly one dimension (Structure, Reasoning, Verification, Technique). The composition of layers is the architecture. See `docs/foundations/composition_framework.md` for the full analysis, research grounding, and one-shot examples.

---

## Grounding Principles

1. **Layered Composition as Architecture** — every agent prompt is a chain of orthogonal framework layers assembled by `ComposedPrompt([...]).build()`. No ad-hoc strings. Each layer belongs to exactly one dimension: Structure, Reasoning, Verification, or Technique. One layer per dimension per agent. Empirically grounded in DSPy (NeurIPS 2023) and ACL 2024.

2. **Formal Specs as Inter-Agent Medium** — agents do not hand off free text. They hand off formal specifications. Specs are compact, verifiable, and language-agnostic intermediate representations.

3. **Adaptive Spec Selection** — the Spec Advisor selects the best-fit specification language per layer per system. There is no fixed spec language. DDD/CML is one option among many, appropriate for complex domain-heavy systems.

4. **Layered Spec Stack** — a system is modeled as a stack of interlocking specs, each grounding the layer below it. The stack depth corresponds to system complexity: simple projects use 2 layers; distributed enterprise systems use 5+.

5. **Minimal Agent Set** — 5 agents for the core council. Complexity is absorbed by the Spec Advisor's selection logic, not by adding more agents.

6. **CLEAR Closed-Loop as Session Protocol** — every council invocation is a CLEAR turn: Context → Layering → Execute → Assess → Reflect. The Coordinator enforces this loop; it does not short-circuit.

7. **Human-or-SME Transparency** — the council never knows whether requirements came from a human or the SME Agent. The SME Agent simulates the human domain expert faithfully enough that the pipeline is identical in both modes.

---

## The SME Agent

The SME Agent is a **full persona-driven multi-domain simulation agent**. It can embody any domain expert — fintech product manager, healthcare administrator, logistics lead, retail CTO — and drive realistic multi-turn requirements into the council across any domain.

It is not tied to a specific application domain. Its value is in the simulation: stress testing the council, enabling regression across builds, and powering demos without a human in the loop.

The council never distinguishes between human and SME Agent input. This is by design.

**Composition:** `CLEAR → COSTAR → PersonaLayer → ConstitutionalAI ↩`  
**Full detail:** `docs/foundations/composition_framework.md` — SME Agent section.  
**Phase A/B split and persona library:** `docs/foundations/dev-guide.md`.

---

## The Spec Advisor

The Spec Advisor is the intellectual core of Faber — a **recurring council member** visited at each layer of the system decomposition, not a one-shot classifier.

### What it does at each visit

1. **Receives** the current layer's context: project brief, parent-layer specs already in the graph, and the layer being addressed
2. **Classifies** the layer's primary concerns (concurrency, domain structure, contracts, invariants, behavior)
3. **Selects** the best-fit specification language for those concerns, with explicit justification
4. **Emits** two artifacts:
   - A COSTAR-structured **selection justification** (why this language at this layer)
   - A CRISPE-structured **Spec Specialist prompt** for this layer, injected with parent-layer specs as context

### Spec language selection heuristics (not rules)

| Layer concern | Candidate languages |
|---|---|
| Distributed behavior, concurrency, liveness | TLA+ |
| Domain structure, bounded contexts | CML (DDD DSL), Evans-style DDD |
| API contracts, message schemas | OpenAPI, AsyncAPI, Avro |
| Structural invariants, safety properties | Alloy |
| Observable behavior, acceptance criteria | Gherkin/BDD |
| Simple CRUD, data shape | JSON Schema, OpenAPI |
| Domain-specific (finance, healthcare, etc.) | Custom DSL appropriate to domain |

A spec language can appear at multiple layers. The Spec Advisor selects based on what the layer **needs to express**, not a fixed assignment.

---

## Layered Spec Visit Pattern

A full system decomposition visits the Spec Advisor once per layer. Each visit is a CLEAR turn. Simple projects use 2 layers; enterprise systems use 5+.

```
Visit 1 — System level
  Concerns: distributed behavior, concurrency, protocols
  Example output: TLA+ spec
  Stored as: Specification(layer=system, lang=TLA+)

Visit 2 — Domain level
  Concerns: bounded contexts, aggregates, domain events
  Context: TLA+ spec from Visit 1
  Example output: CML context map
  Stored as: Specification(layer=domain, lang=CML)
  Edge: GROUNDS → Visit 1 spec

Visit 3 — Component level
  Concerns: API contracts, service interfaces
  Context: CML domain model
  Example output: OpenAPI spec per bounded context
  Stored as: Specification(layer=component, lang=OpenAPI)
  Edge: GROUNDS → Visit 2 spec

Visit 4 — Invariant level
  Concerns: structural constraints, safety properties
  Context: component contracts
  Example output: Alloy model
  Stored as: Specification(layer=invariant, lang=Alloy)
  Edge: GROUNDS → Visit 3 spec

Visit 5 — Test/behavior level
  Concerns: observable acceptance criteria
  Context: all above specs
  Example output: Gherkin feature files
  Stored as: Specification(layer=test, lang=Gherkin)
  Edge: GROUNDS → Visit 4 spec
```

For simple projects the Spec Advisor visits layers 2 and 5 only. Spec stack depth is the complexity dial.

---

## Minimal Agent Council (5 agents)

| Agent | Composition | Role | Invoked |
|---|---|---|---|
| **SME Agent** | `CLEAR → COSTAR → PersonaLayer → CAI ↩` | Multi-domain persona simulation; drives requirements across any domain | Once per turn (automated); stateless Phase A, history-accumulating Phase B |
| **Spec Advisor** | `CLEAR → COSTAR → CoT → [emits CRISPE]` | Selects spec language per layer; generates Spec Specialist prompt at runtime | Once per layer visit |
| **Spec Specialist** | `CRISPE (injected) → FewShot → CAI ↩` | Generates the formal spec in the selected language | Once per layer, after Spec Advisor |
| **Test Engineer** | `CRISPE → FewShot → CAI ↩` | Derives Gherkin tests from the full spec stack | Once, after all spec layers complete |
| **Coordinator** | `CLEAR → ReActLoop` | Gates layer transitions; enforces CLEAR loop; surfaces conflicts | Throughout — meta-agent |

**The meta-prompting moment:** Spec Specialist has no fixed system prompt. Its entire prompt is generated at runtime by the Spec Advisor (a CRISPE prompt, injected with parent-layer specs). This is the architectural contribution that makes spec language selection adaptive rather than hard-coded.

---

## Graph Schema

### Node types (Spec Council — wired from M9)

```
Specification
  id          STRING PRIMARY KEY
  layer       STRING    -- system | domain | component | invariant | test
  spec_lang   STRING    -- TLA+, CML, Alloy, OpenAPI, Gherkin, JSON Schema, ...
  content     STRING    -- the spec artifact text
  confidence  DOUBLE
  visit_num   INT64     -- which Spec Advisor visit produced this

Requirement
  id          STRING PRIMARY KEY
  text        STRING    -- the requirement as stated by SME (human or agent)
  scenario_type STRING  -- new_feature | change | removal | conflict
  persona_used  STRING  -- which SME persona produced this (empty if human)
```

### Edge types

```
GROUNDS:       Specification → Specification    -- lower layer grounds in upper
DERIVED_FROM:  Specification → Requirement      -- spec traces to requirement
REFINES:       Specification → Specification    -- revision of same-layer spec
STATED_BY:     Requirement → (session metadata) -- traceability to SME turn
```

### GNN PoC schema (M4.1 track — live in data/kuzu now)

Each M4.1 sub-milestone owns its own tables. Cross-milestone edges carry the ML signal:

```
MilestoneRun    — subgraph anchor per invocation
FrameworkLayer  — M1: 9 framework builders, raw build metrics
SpecRun         — M2/M3/M4: Spec Advisor output per brief
RevisionEvent   — M4: CAI revision state per run
CAPTURED_IN     — Node → MilestoneRun anchor edge
REASONING_ADDS  — M2 SpecRun → M3 SpecRun: confidence_delta, step_count, evaluation_depth
VERIFICATION_ADDS — M3 SpecRun → M4 SpecRun: revised, cai_principle_triggered
AnalysisNote    — Claude's analytical findings (schema invented ad-hoc per session)
ANALYZED        — AnalysisNote → any node: the feedback layer
```

### Full traceability path (Spec Council, M9+)

```
Requirement (from SME)
  → (DERIVED_FROM) ← Specification(layer=system, TLA+)
      → (GROUNDS) ← Specification(layer=domain, CML)
          → (GROUNDS) ← Specification(layer=component, OpenAPI)
              → (GROUNDS) ← Specification(layer=invariant, Alloy)
                  → (GROUNDS) ← Specification(layer=test, Gherkin)
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Faber** as project name | Latin for maker/artisan/architect — the guild metaphor maps onto the agent council; "homo faber" (man as maker) grounds the PE-first philosophy |
| SME Agent on CLEAR → COSTAR → PersonaLayer → CAI (VOICE retired) | VOICE baked Structure + Technique + Verification into one custom framework. Replaced by the standard composition stack. See `docs/decisions/ADR-002_voice-retired.md` |
| SME Agent is council-transparent | The council never knows if input is human or SME Agent. Enables automated testing, regression, and benchmark runs without special council code paths |
| Prompt frameworks as Python dataclasses | Composability, testability, consistency — a COSTARPrompt object is inspectable and modifiable; a raw string is not. Each class independently unit-testable. |
| Spec Advisor emits CRISPE prompt at runtime | The Spec Specialist's behaviour IS its prompt. Generating it is the Spec Advisor's primary product — this is the meta-prompting moment (Suzgun & Kalai 2024). |
| DDD/CML is one option, not the default | DDD suits complex domain-rich systems; lighter formalisms serve simpler projects better. The Spec Advisor selects based on concerns, not convention. |
| Deliberative consensus | Spec quality at lower layers depends on correctness at higher layers — optimistic writes would propagate errors silently. Coordinator gates every transition. |
| 5 agents max | Complexity is in the Spec Advisor's selection logic, not headcount. Adding agents is not the answer. |
| GNN-first substrate | Kuzu is not a storage layer — it is the model. Every milestone grows the schema. Cross-milestone edges (REASONING_ADDS, VERIFICATION_ADDS) carry the learning signal across runs. |
