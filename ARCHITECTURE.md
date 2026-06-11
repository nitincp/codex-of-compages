# Faber — Architecture Document

> **Faber** *(Latin)*: maker, artisan, smith, architect.  
> A powerful engineering guild acting as galactic architects — building systems through a council of field agents.

**Prompt Engineering Project for Adaptive Formal Specification**  
**Author:** Nitin Pawar | **Date:** June 2026  
**Status:** Pre-implementation — architecture and PoC scoping  
**Companion documents:** `Greenfield_Development_Agent_Council-1.md`, `GraphRAG_GNN_Prompt_Engineering_Project_Final.md`

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

## How This Differs from Senatus

| Dimension | Senatus | Faber |
|---|---|---|
| Primary framing | Agent council for DDD modeling | Prompt engineering project |
| Spec strategy | Fixed (DDD → Gherkin) | Adaptive — Spec Advisor selects per layer |
| Inter-agent medium | Free-text DDD summaries | Formal spec artifacts |
| Agent prompts | Ad-hoc strings | Composed from CLEAR/COSTAR/RACE/CRISPE primitives |
| Complexity scaling | One mode | Spec stack depth = complexity |
| Pipeline | Fixed sequence | Recursive layered visits |
| Consensus | Optimistic (write, surface conflicts) | Deliberative (Coordinator gates layer transitions) |
| DDD role | Primary output | One selectable option at the domain layer |
| Human driver | Always required | SME Agent simulates human for automated flows |

Senatus is a capable implementation of layer 3 (domain-level CML/DDD) of Faber's spec ladder. It can be used as a plugin or reference implementation for that layer.

---

## Prompt Framework Layer

Frameworks are implemented as Python dataclasses with `build() -> str`.
Assembled via `ComposedPrompt([layer1, layer2, ...]).build()`.
Full reference and one-shot examples: `docs/foundations/composition_framework.md`.

**Taxonomy — four orthogonal dimensions:**

```
Structure    COSTAR, CRISPE, CLEAR, RACE       — prompt shape + output format
Reasoning    ChainOfThought, ReActLoop          — explicit, auditable thinking steps
Verification ConstitutionalAI                   — critique → revise loop, output gate
Technique    PersonaLayer, FewShot              — specific capability applied to task
```

**Composition rules:**
1. One layer per dimension per agent — no overlap, no contradiction
2. Structure first, Verification always last
3. The loop-back (Constitutional AI revision) is not optional — every agent gates its output

**Agent chains (summary — full detail in `docs/foundations/composition_framework.md`):**

```
SME Agent:       CLEAR → COSTAR → PersonaLayer → ConstitutionalAI ↩
Spec Advisor:    CLEAR → COSTAR → ChainOfThought → [emits CRISPE meta-prompt]
Spec Specialist: CRISPE (injected) → FewShot → ConstitutionalAI ↩
Coordinator:     CLEAR → ReActLoop
Test Engineer:   CRISPE → FewShot → ConstitutionalAI ↩
```

**VOICE is retired.** Replaced by: COSTAR (Structure) + PersonaLayer (Technique) + ConstitutionalAI (Verification).
See `docs/decisions/ADR-002_voice-retired.md`.

---

## The SME Agent

### Role

The SME Agent is a **full persona-driven multi-domain simulation agent**. It can embody any domain expert — a fintech product manager, a healthcare administrator, a logistics operations lead, a retail CTO — and drive realistic multi-turn requirements into the council across any domain.

It is not tied to a specific application domain. Its value is in the simulation itself: stress testing the council, enabling regression across builds, and powering demo sessions — all without a human in the loop.

In **human mode** the user IS the SME; the SME Agent is inactive.  
In **automated mode** the SME Agent drives the council programmatically, accumulating council responses across turns to produce realistic back-and-forth.  
In **augmented mode** (future) the SME Agent suggests or refines what the human types.

The council never distinguishes between the two modes. This is by design.

### Framework: CLEAR → COSTAR → PersonaLayer → ConstitutionalAI ↩

**VOICE is retired.** It baked three dimensions (Structure, Technique, Verification) into one
custom framework. Replaced by the standard composition stack. See `docs/decisions/ADR-002_voice-retired.md`.

The SME Agent composition chain:

```
CLEAR (Structure)         — session context: turn number, prior council output, domain brief
COSTAR (Structure)        — task shape: objective, output format, audience (Spec Advisor)
PersonaLayer (Technique)  — identity: role, background, domain priorities, communication style
ConstitutionalAI (Verification) ↩ — authenticity gate: sounds like a stakeholder? reacts
                                    to council? consistent with prior turns? revise if not.
```

`Interaction` history (conversation accumulation across turns) is carried in the COSTAR
`context` field in Phase A and in a dedicated `interaction` field in Phase B (Reflexion pattern).

### What the SME Agent produces

```
SMEOutput
  requirement_text      STRING   — the requirement, in domain-expert voice
  scenario_type         ENUM     — new_feature | change | removal | conflict
  domain_terms          LIST     — domain terminology used (feeds glossary)
  reacts_to_council     BOOL     — whether this turn responds to prior council output
  confidence            FLOAT    — how well-grounded in the persona this output is
  persona_used          STRING   — which persona was active
```

### Two phases

**Phase A** (Milestone 2 — early, cheap, immediately useful):
- Stateless per call — no conversation history
- Single generic persona, configured inline as a dict
- Enough to drive the Spec Advisor PoC and validate the pipeline automatically
- `simulate.py` runner: `--domain "e-commerce" --turns 3` → N requirement messages → N council passes

**Phase B** (Milestone 7 — after council is stable):
- YAML persona library in `src/agents/personas/` — any domain, any role
- Multi-turn conversation history — SME accumulates prior council responses across turns
- Full scenario coverage: change requests, removals/deprecations, conflicting requirements
- `sme: <domain>` command in Chainlit UI — start a live simulation observable in the browser
- Benchmark suite — fixed set of domains × scenarios; compare graph quality metrics across builds

**Why split?** Phase A unblocks automated testing for all subsequent milestones cheaply. Phase B waits until the council is stable so SME failures are clearly input-quality issues, not council bugs.

### Position in the pipeline

```
SME Agent  →  Spec Advisor (visit 1)  →  Spec Specialist  →  [more layers]  →  Test Engineer
    ↑                  ↑ (prior specs from Kuzu)                                     ↓
  (human or                                                                   Coordinator
   automated,                                                                 (gates each layer)
   multi-turn)
```

Phase A: SME fires once per session. Phase B: SME fires once per turn, reads council output, generates follow-up requirement for the next turn.

---

## The Spec Advisor

The Spec Advisor is the intellectual core of Faber. It is not a one-shot classifier — it is a **recurring council member** visited at each layer of the system decomposition.

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

| Agent | Framework | Role | Invoked |
|---|---|---|---|
| **SME Agent** | CLEAR → COSTAR → PersonaLayer → ConstitutionalAI ↩ | Multi-domain persona simulation; drives requirements across any domain | Once per turn (automated mode); stateless in Phase A, history-accumulating in Phase B |
| **Spec Advisor** | COSTAR → emits CRISPE | Selects spec language per layer; generates Spec Specialist prompt | Once per layer, first in each CLEAR turn |
| **Spec Specialist** | CRISPE (dynamic, from Spec Advisor) | Generates the formal spec in the selected language | Once per layer, after Spec Advisor |
| **Test Engineer** | CRISPE | Derives Gherkin tests from the full spec stack | Once, after all spec layers complete |
| **Coordinator** | CLEAR | Gates layer transitions; enforces CLEAR loop; surfaces conflicts | Throughout — meta-agent |

---

## Graph Schema

### New node types

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

### New edge types

```
GROUNDS:       Specification → Specification    -- lower layer grounds in upper
DERIVED_FROM:  Specification → Requirement      -- spec traces to requirement
REFINES:       Specification → Specification    -- revision of same-layer spec
STATED_BY:     Requirement → (session metadata) -- traceability to SME turn
```

### Full traceability path

```
Requirement (from SME)
  → (DERIVED_FROM) ← Specification(layer=system, TLA+)
      → (GROUNDS) ← Specification(layer=domain, CML)
          → (GROUNDS) ← Specification(layer=component, OpenAPI)
              → (GROUNDS) ← Specification(layer=invariant, Alloy)
                  → (GROUNDS) ← Specification(layer=test, Gherkin)
```

---

## PoC Scope (Milestone 2 target)

Prove the core selection loop with one layer, end-to-end:

1. SME Agent produces a requirement (automated mode, generic domain expert persona)
2. Spec Advisor runs: classifies the domain layer, selects spec language, emits a CRISPE prompt
3. Spec Specialist runs with that prompt: produces a domain spec
4. `Requirement` and `Specification` nodes written to Kuzu with `DERIVED_FROM` edge
5. Output shown in Chainlit UI: SME requirement → Spec Advisor justification → spec content

**Success criteria:** Given two projects of different complexity (a simple CRUD app vs. a multi-service distributed system), the SME Agent produces domain-appropriate requirement text AND the Spec Advisor selects different spec languages with coherent justifications.

---

## Infra & Toolchain

To be extracted from the Senatus project. The following components are reusable with adaptation:

| Component | From Senatus | Changes for Faber |
|---|---|---|
| `BaseAgent` | `src/agents/base.py` | Add framework builder support — accepts a prompt builder, not a raw string |
| `GraphStore` | `src/graph/store.py` | Add `Specification`/`Requirement` nodes, new edge types |
| `GraphSchema` | `src/graph/schema.py` | Extend `NodeType`/`EdgeType` enums |
| Chainlit UI | `src/ui/app.py` | Layer visit progress display; SME mode toggle |
| LangGraph skeleton | `src/orchestration/council.py` | Rebuild for deliberative Coordinator-gated flow |
| devcontainer setup | `.devcontainer/` | Copy verbatim |
| `bootstrap-secrets.sh` | `.devcontainer/` | Copy verbatim |
| `pyproject.toml` deps | `pyproject.toml` | Same core deps |

**New components (no Senatus equivalent):**

```
src/frameworks/               — all prompt builder classes (CLEAR, COSTAR, CRISPE, RACE,
                                PersonaLayer, ChainOfThought, ReActLoop, ConstitutionalAI,
                                FewShot, ComposedPrompt)
src/agents/sme_agent.py       — SME Agent (CLEAR → COSTAR → PersonaLayer → ConstitutionalAI)
src/agents/spec_advisor.py    — Spec Advisor (CLEAR → COSTAR → CoT → emits CRISPE)
src/agents/spec_specialist.py — dynamically configured Spec Specialist (CRISPE → FewShot → CAI)
src/orchestration/coordinator.py — deliberative Coordinator (CLEAR → ReAct)
src/agents/personas/          — YAML persona files (Phase B)
```

---

## Directory Layout

```
faber/
├── ARCHITECTURE.md          — this document
├── CLAUDE.md                — Claude Code instructions
├── BACKLOG.md               — milestone breakdown
├── pyproject.toml           — dependencies
├── .env                     — non-sensitive config (gitignored)
├── .devcontainer/           — devcontainer + bootstrap-secrets
├── data/kuzu/               — Kuzu graph DB (gitignored)
├── scripts/
│   └── graph_stats.py       — inspect graph state
├── docs/
│   ├── INDEX.md                        — thesis navigator (entry point)
│   ├── thesis/CLAIM.md                 — central claim + per-milestone hypotheses
│   ├── foundations/
│   │   ├── composition_framework.md    — research grounding, agent chains, one-shot examples
│   │   └── prompt_frameworks.md        — per-framework field reference
│   ├── decisions/                      — ADR log (one file per architectural decision)
│   ├── evidence/                       — PoC results (one file per milestone)
│   └── analysis/                       — alternatives considered, tensions, debates
├── src/
│   ├── frameworks/
│   │   ├── clear.py             — CLEAR session protocol builder
│   │   ├── costar.py            — COSTAR structured output builder
│   │   ├── crispe.py            — CRISPE technical generation builder
│   │   ├── race.py              — RACE lightweight generation builder
│   │   ├── persona.py           — PersonaLayer technique builder
│   │   ├── chain_of_thought.py  — ChainOfThought reasoning builder
│   │   ├── react.py             — ReActLoop reasoning builder
│   │   ├── constitutional_ai.py — ConstitutionalAI verification builder
│   │   ├── few_shot.py          — FewShot technique builder
│   │   └── composed.py          — ComposedPrompt assembler
│   ├── agents/
│   │   ├── base.py              — BaseAgent
│   │   ├── sme_agent.py         — SME Agent (CLEAR → COSTAR → PersonaLayer → CAI)
│   │   ├── spec_advisor.py      — Spec Advisor (CLEAR → COSTAR → CoT → emits CRISPE)
│   │   ├── spec_specialist.py   — dynamically configured (CRISPE injected → FewShot → CAI)
│   │   ├── test_engineer.py     — Test Engineer (CRISPE → FewShot → CAI)
│   │   ├── schemas.py           — Pydantic output schemas for all agents
│   │   └── personas/            — YAML persona files (Phase B)
│   ├── graph/
│   │   ├── schema.py            — NodeType/EdgeType enums
│   │   └── store.py             — GraphStore (Kuzu)
│   ├── orchestration/
│   │   ├── council.py           — LangGraph graph definition
│   │   └── coordinator.py       — deliberative Coordinator (CLEAR → ReAct)
│   └── ui/
│       └── app.py               — Chainlit app
└── tests/
    ├── test_frameworks.py       — unit tests for all prompt builders (M1 gate)
    ├── test_spec_advisor.py     — selection loop tests (M2–M5 gates)
    ├── test_sme_chain.py        — inter-agent context tests (M6 gate)
    ├── test_meta_chain.py       — meta-prompting chain tests (M7 gate)
    ├── test_coordinator.py      — Coordinator retry loop tests (M8 gate)
    └── test_graph_store.py      — Kuzu integration tests (M9 gate)
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Faber** as project name | Latin for maker/artisan/architect — the guild metaphor maps onto the agent council; "homo faber" (man as maker) grounds the PE-first philosophy |
| SME Agent on CLEAR → COSTAR → PersonaLayer → CAI (VOICE retired) | VOICE baked Structure + Technique + Verification into one custom framework. Replaced by the standard composition stack: CLEAR (session context), COSTAR (output format), PersonaLayer (identity), ConstitutionalAI (authenticity gate). See `docs/decisions/ADR-002_voice-retired.md` |
| SME Agent is council-transparent | The council never knows if input is human or SME Agent. The SME Agent is not tied to any specific domain — it simulates any domain expert persona. Enables automated testing, regression, and benchmark runs without special council code paths |
| Prompt frameworks as Python classes | Composability, testability, and consistency — a COSTARPrompt object can be inspected and modified; a raw string cannot |
| Spec Advisor emits CRISPE prompt | The Spec Specialist's behavior IS its prompt; generating it is the Spec Advisor's primary product |
| DDD/CML is one option, not the default | DDD suits complex domain-rich systems; lighter formalisms serve simpler projects better |
| Deliberative consensus | Spec quality at lower layers depends on correctness of specs above — optimistic writes would propagate errors silently |
| 5 agents max | SME Agent + Spec Advisor + Spec Specialist + Test Engineer + Coordinator. Complexity is in Spec Advisor's selection logic, not headcount |
| Separate repo from Senatus | Different grounding principles (PE-first vs council-first), different consensus model, different graph schema |
