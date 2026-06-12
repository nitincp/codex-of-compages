# Faber: A Layered Chain of Composable Prompt Engineering Frameworks

**The central architectural document.**  
All other design decisions reference back here.

**Author:** Nitin Pawar | **Date:** June 2026  
**Status:** Foundational — stable. Extend do not replace.

---

## The Thesis

> A single prompting technique applied to a complex agent task is like a single tool applied
> to all engineering problems. The advance is not in the techniques themselves —
> it is in their **systematic composition**.

Faber operationalises this thesis. Every agent prompt is a **chain of orthogonal layers**,
each drawn from an industry-standard framework, each contributing exactly one dimension.
The composition is the architecture.

This is not novel opinion. It is empirically demonstrated, patented, and grounded in
six research papers spanning 2022–2025.

---

## Research Foundations

### Prompt engineering + agent composition

| Paper | Authors | Year | Core thesis |
|---|---|---|---|
| [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903) | Wei et al., Google Brain | NeurIPS 2022 | Intermediate reasoning steps dramatically improve complex task performance in LLMs |
| [Constitutional AI: Harmlessness from AI Feedback](https://arxiv.org/abs/2212.08073) | Bai et al., Anthropic | 2022 | Generate → critique against explicit principles → revise until criteria pass. The critique-revision loop as a framework |
| [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) | Yao et al., Google + Princeton | 2022 | Interleaving reasoning traces with acting steps outperforms either alone; produces auditable, human-readable decisions |
| [DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines](https://arxiv.org/abs/2310.03714) | Khattab et al., Stanford | NeurIPS 2023 | Prompt pipelines should be declarative, composable modules — not ad-hoc strings. Composable modules outperform monolithic prompts by 25–65% |
| [Reflexion: Language Agents with Verbal Reinforcement Learning](https://proceedings.neurips.cc/paper_files/paper/2023/file/1b44b878bb782e6954cd888628510e90-Paper-Conference.pdf) | Shinn et al. | NeurIPS 2023 | Agents that reflect verbally on feedback and store it in episodic memory improve across trials without weight updates |
| [Meta-Prompting: Enhancing Language Models with Task-Agnostic Scaffolding](https://arxiv.org/abs/2401.12954) | Suzgun & Kalai, Stanford + OpenAI | 2024 | A single LM conductor routes subtasks to specialised expert LM instances with tailored instructions — the architecture maps directly to Faber's Spec Advisor + Spec Specialist |
| [Prompt Chaining or Stepwise Prompt? Refinement in Text Summarization](https://aclanthology.org/2024.findings-acl.449/) | Sun et al. | ACL Findings 2024 | Empirical proof: chained prompts (separate draft/critique/refine) consistently outperform monolithic prompts combining all stages |
| [Layered Multi-Prompt Engineering for Pre-Trained LLMs](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12493772) | US Patent 12493772 | 2025 | Industry validation — vector-store-driven layered prompt assembly; layers retrieved and composed for specific use cases |

**The key synthesis**: DSPy says *make it composable*. Meta-Prompting says *one conductor, many specialists*. ACL 2024 says *chains beat monoliths empirically*. Constitutional AI says *always close the verification loop*. Together they constitute the theoretical foundation for Faber's composition model.

### Knowledge graph substrate — GraphRAG + GNN

*The Kuzu-as-GraphRAG-with-GNN architecture originates in **Senatus (agentic-gnn)**, the predecessor
project. Senatus had the correct architectural instinct — a council of agents backed by a Kuzu graph
substrate — but its implementation was rigid and ad-hoc: prompts were hard-coded strings, pipelines
were fixed, and the system could not adapt to project complexity or learn across runs.*

*Faber's contribution is the prompt engineering grounding that transforms that rigid prototype into a
dynamic, adaptive, learning system. Because prompts are now composed at runtime from orthogonal layers
(not hard-coded), the spec stack adapts to complexity, the Spec Advisor selects languages it was not
pre-programmed for, and the GNN accumulates signal that improves future runs. The PE framework is what
makes the graph substrate live rather than static.*

| Paper | Authors | Year | Core thesis |
|---|---|---|---|
| [From Local to Global: A Graph RAG Approach to Query-Focused Summarization](https://arxiv.org/abs/2404.16130) | Edge et al., Microsoft | 2024 | Graph-structured retrieval over a knowledge graph enables community-level reasoning that vector RAG cannot — the graph topology is the retrieval signal, not text similarity |
| [Modeling Relational Data with Graph Convolutional Networks](https://arxiv.org/abs/1703.06103) | Schlichtkrull et al. | 2018 | R-GCN: each edge type carries its own learned weight matrix — the direct formulation for a graph whose edge types are semantically distinct (GROUNDS, DERIVED\_FROM, SELECTS, GENERATES…) |
| [Heterogeneous Information Network Embedding for Meta Path Based Proximity](https://arxiv.org/abs/2208.09025) | Various | 2022+ | HIN: multiple node types + edge types in one graph; cross-type message passing. The architecture Kuzu's schema implements at each milestone |

**The key synthesis for the graph layer**: GraphRAG says *topology beats embeddings for structured knowledge*. R-GCN says *each edge type is a separate learned relation — don't flatten them*. HIN says *agent outputs, spec artifacts, code artifacts, and test results can cohabit one graph if the schema is typed*. Together they position Kuzu not as a persistence layer but as a **live, queryable learning substrate** that grows one schema layer per Faber milestone.

---

## Framework Taxonomy — Three Orthogonal Dimensions

Every layer in a composed chain belongs to exactly one dimension. Layers do not overlap.
If two layers seem to overlap, one of them is in the wrong dimension.

```
┌─────────────────┬───────────────────────────────┬──────────────────────────┐
│ DIMENSION       │ WHAT IT CONTRIBUTES           │ FRAMEWORKS               │
├─────────────────┼───────────────────────────────┼──────────────────────────┤
│ Structure       │ Prompt shape, sections,        │ COSTAR, CRISPE,          │
│                 │ output format                  │ CLEAR, RACE              │
├─────────────────┼───────────────────────────────┼──────────────────────────┤
│ Reasoning       │ How the model thinks —         │ Chain of Thought,        │
│                 │ makes steps explicit+auditable │ ReAct, Tree of Thoughts  │
├─────────────────┼───────────────────────────────┼──────────────────────────┤
│ Verification    │ Critique pass + revision loop  │ Constitutional AI,       │
│                 │ — output gate before accept    │ Reflexion                │
├─────────────────┼───────────────────────────────┼──────────────────────────┤
│ Technique       │ Specific capability applied    │ Persona Prompting,       │
│                 │ to the task                    │ Few-shot, Self-Consistency│
└─────────────────┴───────────────────────────────┴──────────────────────────┘
```

**Two composition rules:**
1. **One layer per dimension** — no redundancy, no contradiction between layers
2. **Structure first, Verification last** — structure frames the task; verification always gates the output

---

## The Composition Model

The user's guiding example: `CLEAR → COSTAR → Persona → loops back for refinements`

```
CLEAR         →    COSTAR        →    Persona Prompting   →   Constitutional AI
(Structure)        (Structure)         (Technique)             (Verification)
    │                  │                     │                        │
session            task shape           identity /              critique +
context            + output fmt         voice layer             revise loop ↩
```

**The loop-back is the critical pattern.** Without it, composition is just concatenation.
With it, every agent has a self-correcting gate before producing output.

### Visual: how layers stack

```
┌─────────────────────────────────────────────────────┐  ← outer: session context
│  CLEAR (Structure)                                  │
│  ┌───────────────────────────────────────────────┐  │  ← inner: task definition
│  │  COSTAR (Structure)                           │  │
│  │  ┌─────────────────────────────────────────┐  │  │  ← identity / technique
│  │  │  Persona Prompting (Technique)          │  │  │
│  │  │  ┌───────────────────────────────────┐  │  │  │  ← reasoning (if needed)
│  │  │  │  Chain of Thought (Reasoning)     │  │  │  │
│  │  │  └───────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────┘  │
│  Constitutional AI (Verification) ← gates output    │  ← always outermost gate
│  revises ↩ if criteria fail                         │
└─────────────────────────────────────────────────────┘
```

---

## Full Chain Map — All Five Agents

```
┌──────────────────────────────────────────────────────────────────────────┐
│ SME AGENT                                                                │
│                                                                          │
│  CLEAR → COSTAR → Persona Prompting → Constitutional AI ↩               │
│  [session  [output    [who speaks,        [is this authentic?            │
│   context]  format]    domain voice]       stakeholder voice?]           │
│                                                                          │
│  Grounded in: CAI (Anthropic 2022), Persona = industry technique        │
└──────────────────────────────────────────────────────────────────────────┘
                │ requirement text
                ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ SPEC ADVISOR                              [THE META-PROMPTER]            │
│                                                                          │
│  CLEAR → COSTAR → Chain of Thought → META-PROMPT(CRISPE output)         │
│  [which    [select   [step through       [primary product:               │
│   layer]    output]   candidates]         a CRISPE prompt                │
│                                           for Spec Specialist]           │
│                                                                          │
│  Grounded in: Meta-Prompting (Suzgun & Kalai 2024), CoT (Wei 2022)      │
└──────────────────────────────────────────────────────────────────────────┘
                │ emits CRISPE prompt
                ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ SPEC SPECIALIST  (no fixed prompt — dynamically configured)              │
│                                                                          │
│  CRISPE (injected) → Few-shot → Constitutional AI ↩                     │
│  [from Spec Advisor  [spec syntax   [well-formed?                       │
│   at runtime]         examples       covers concerns?                   │
│                        from graph]    revise if not]                    │
│                                                                          │
│  Grounded in: DSPy composable modules (2023), CAI (2022)                │
└──────────────────────────────────────────────────────────────────────────┘
                │ formal spec + well-formedness notes
                ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ COORDINATOR                                                              │
│                                                                          │
│  CLEAR → ReAct                                                           │
│  [session   [Thought: assess spec quality                                │
│   loop]      Act: proceed | retry | escalate                            │
│              Observation: carry forward to next layer]                  │
│                                                                          │
│  Grounded in: ReAct (Yao et al. 2022)                                   │
└──────────────────────────────────────────────────────────────────────────┘
                │ proceed / retry / escalate
                ↓ (after all spec layers complete)
┌──────────────────────────────────────────────────────────────────────────┐
│ TEST ENGINEER                                                            │
│                                                                          │
│  CRISPE → Few-shot (spec-derived) → Constitutional AI ↩                 │
│  [Gherkin    [spec artifacts as      [traces to spec?                   │
│   specialist] Gherkin examples        implementable?                    │
│               pulled from graph]       revise if not]                   │
│                                                                          │
│  Grounded in: DSPy few-shot modules (2023), CAI (2022)                  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## One-Shot Examples Per Layer

**Domain throughout**: e-commerce payment gateway  
**SME persona**: Senior VP of Payments Product, 12 years in payments

---

### SME Agent — layer by layer

**Layer 1: CLEAR** *(Structure — session context)*

```
Context:  Turn 2. Domain: payment gateway.
          Turn 1: SME requested Visa/MC/AmEx network support.
          Council responded: DDD model — 3 BCs: NetworkAuth,
          SettlementEngine, DisputeResolution.
Layering: Requirements ingestion — turn 2
Execute:  Generate next requirement building on council's domain model
Assess:   Must read as a stakeholder business need, not a technical spec
Reflect:  Output feeds Spec Advisor as context for next layer visit
```

**Layer 2: COSTAR** *(Structure — task shape and output format)*

```
Context:  [CLEAR above] + council's BC model
Objective: Produce next requirement for the council
Style:    Business language, payments terminology natural
Tone:     Direct, risk-focused, compliance-aware
Audience: Spec Advisor (uses this to select spec language)
Response: { requirement_text, scenario_type, domain_terms }
```

**Layer 3: Persona Prompting** *(Technique — identity prefix)*

```
You are a Senior VP of Product at a mid-size payment processor.
12 years in payments. Priorities: PCI-DSS compliance, sub-200ms
settlement latency, chargeback rate below 0.1%.
You have just read the council's domain model above.
React to it as a business stakeholder, not a technologist.
```

**Layer 4: Constitutional AI** *(Verification — authenticity gate)*

```
Critique the requirement you just produced against these principles:
  1. Does it sound like a payments executive, not a software architect?
  2. Is it a business need, not a technical instruction?
  3. Is it consistent with the Visa/MC/AmEx requirement from turn 1?
  4. Does it react to or build on the council's domain model?
If any principle is violated, revise before outputting.
```

**Output** (post-critique, turn 2):

> *"The SettlementEngine needs to support same-day settlement for
> transactions under $500 — our enterprise clients need it and Visa
> is rolling out instant settlement APIs in Q3. Chargeback windows
> must stay under 30 days or we breach acquiring agreements. PCI
> scope should be limited to NetworkAuth only — DisputeResolution
> must not touch raw card data."*

---

### Spec Advisor — layer by layer *(visit 2, component layer)*

**Layer 1: CLEAR** *(which layer of the stack)*

```
Context:  Domain layer complete — CML spec in graph (3 BCs, 2 events,
          confidence 0.84). SME requirements: settlement timing, PCI
          scoping, chargeback SLA.
Layering: Component layer (visit 2 of 3 planned)
Execute:  Select best-fit spec language for component-layer concerns
Assess:   Justification must name the specific concerns it addresses
Reflect:  Generated CRISPE prompt + selection feeds Spec Specialist
```

**Layer 2: COSTAR** *(selection output format)*

```
Context:  Component concerns: service interfaces, API contracts,
          message schemas, BC integration points.
          Parent layer: CML map showing 3 BC relationships.
Objective: Select spec language that best expresses component contracts
Audience: Spec Specialist (receives the generated CRISPE prompt)
Response: { selected_lang, justification, specialist_crispe_prompt, confidence }
```

**Layer 3: Chain of Thought** *(step through candidates)*

```
Step 1: What must the component layer express?
        → API contracts between NetworkAuth ↔ SettlementEngine
        → Message schema for PaymentAuthorised event
        → PCI scope boundary (NetworkAuth only handles card data)

Step 2: Candidate evaluation:
        OpenAPI:  REST contracts ✓  event schemas ✓  PCI annotations ✓
        AsyncAPI: async messaging ✓  but primary interfaces are sync ✗
        CML:      domain model only, not contracts ✗
        Alloy:    structural invariants, not interface contracts ✗

Step 3: Select OpenAPI 3.1.
        Justification: captures sync + async contracts, supports
        security scheme annotations for PCI boundary, understood
        by engineers downstream.
```

**Layer 4: Meta-Prompt output** *(the Spec Advisor generates a CRISPE prompt)*

```python
# THE META-PROMPTING MOMENT — a prompt generating a prompt
CRISPEPrompt(
  capacity = "Act as an OpenAPI 3.1 specialist with expertise "
             "in payments API design and PCI-DSS scoping",
  role     = "Produce OpenAPI specs for the component layer of a "
             "payment gateway, grounded in the CML domain model above",
  insight  = f"Parent CML domain model:\n{cml_spec}\n\n"
             f"SME requirements: same-day settlement for <$500, "
             f"PCI scope = NetworkAuth only, chargeback SLA 30 days",
  statement= "Generate OpenAPI 3.1 specs for: (1) NetworkAuth "
             "authorization endpoint, (2) SettlementEngine settlement "
             "trigger, (3) PaymentAuthorised webhook schema. "
             "Mark PCI-scope endpoints with x-pci-scope: true.",
  experiment="Verify: all 3 BCs have at least one path. PCI annotation "
             "present on card-data paths. Revise any spec that omits "
             "a BC or lacks PCI annotation where required."
)
```

---

### Spec Specialist — layer by layer

**Layer 1: CRISPE** *(injected from Spec Advisor — not self-generated)*

```
[The CRISPE prompt produced above — this is the entire system prompt.
 The Spec Specialist has no other instructions.]
```

**Layer 2: Few-shot** *(syntax examples pulled from Kuzu)*

```yaml
# Prior session OpenAPI fragment (retrieved from graph):
paths:
  /authorize:
    post:
      summary: Authorize a payment
      x-pci-scope: true
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AuthRequest'
```

**Layer 3: Constitutional AI** *(well-formedness + coverage gate)*

```
Review your OpenAPI output against these criteria:
  1. All 3 BCs (NetworkAuth, SettlementEngine, DisputeResolution)
     have at least one path defined.
  2. x-pci-scope: true is present on /authorize and any path
     that receives card reference tokens.
  3. PaymentAuthorised webhook schema is defined.
  4. Syntax is valid OpenAPI 3.1.
Revise any section that fails a check. Report what was revised.
```

---

### Coordinator — assessing the OpenAPI output

**Layer 1: CLEAR**

```
Context:  Spec Specialist produced OpenAPI spec, confidence 0.78.
          3 paths present. PCI annotation on /authorize only.
          SettlementEngine /settlement/trigger receives card tokens
          but has no PCI annotation — gap identified.
Layering: Component layer — deciding proceed / retry / escalate
Execute:  Issue decision with explicit rationale
Assess:   Confidence ≥ 0.75, all BCs covered, no critical gaps
Reflect:  Decision + rationale appended to session state
```

**Layer 2: ReAct**

```
Thought:  Confidence 0.78 — above threshold (0.75). 3 paths present.
          BUT /settlement/trigger receives card reference tokens.
          SME said PCI scope = NetworkAuth only, yet SettlementEngine
          holds tokenised card refs. Gap is real — annotation missing.

Action:   retry — return Spec Specialist with targeted critique:
          "Add x-pci-scope annotation to /settlement/trigger.
           It receives card reference tokens even if NetworkAuth
           holds raw card data. Clarify with SME if needed."

Observation: Will re-run Spec Specialist with critique injected
             into CRISPE insight field. Coordinator escalates to
             user if retry count exceeds 2.
```

---

### Test Engineer — layer by layer

**Layer 1: CRISPE** *(role definition)*

```
Capacity:  Act as a BDD and Gherkin specification specialist
Role:      Produce Gherkin feature files grounded in the full spec
           stack (TLA+, CML, OpenAPI) stored in the graph
Insight:   [full spec stack injected from Kuzu]
Statement: Generate Gherkin features and scenarios. Each scenario
           must trace to at least one node in the spec stack.
Personality: Precise, minimal. No implementation detail in steps.
Experiment: After generating, verify each scenario cites the spec
            node it covers. Revise any uncited scenario.
```

**Layer 2: Few-shot** *(spec artifacts as Gherkin examples)*

```gherkin
# Derived from OpenAPI /authorize spec node:
Feature: Payment Authorization
  Scenario: Successful Visa authorization under PCI scope
    Given a Visa payment of $150
    When the authorization request is sent to NetworkAuth
    Then a PaymentAuthorised event is emitted
    And the event is routed to SettlementEngine
```

**Layer 3: Constitutional AI** *(traceability gate)*

```
Critique each Gherkin scenario:
  1. Does it trace to a named node in the spec stack?
     (OpenAPI path, CML domain event, or TLA+ invariant)
  2. Are Given/When/Then steps free of implementation detail?
  3. Is the scenario implementable from the spec alone?
If a scenario fails criterion 1, add a comment citing the spec node
or remove the scenario and flag it as ungrounded.
```

---

## The Debate

### For this architecture

- **Empirically grounded**: ACL 2024 proves chaining beats monolithic. DSPy proves composable modules beat ad-hoc strings (25–65% improvement).
- **Each layer is independently testable**: a broken COSTAR builder can be unit-tested without running the full agent. Layer 0 PoC proves the base before anything else is built.
- **Transparent reasoning**: CoT and ReAct make intermediate steps auditable — the Coordinator can inspect the Spec Advisor's candidate evaluation before trusting its selection.
- **Replaceable layers**: if Constitutional AI is overkill for a simple project, swap it out without touching other layers.
- **Research-aligned and named**: every layer maps to a cited technique. No "invented here" frameworks.

### Tensions to hold

**T1 — Token cost compounds.**  
A 4-layer chain is 3–4× the prompt length of a single prompt.  
*Counter*: Constitutional AI can run inline (same API call, longer prompt) rather than as a separate call. Only the Coordinator's ReAct loop genuinely benefits from a separate call. Measured cost per layer PoC — don't assume; verify.

**T2 — Layers can contradict each other.**  
A CLEAR context saying "turn 2" can conflict with a COSTAR context injecting different history.  
*Counter*: the one-layer-per-dimension rule prevents this. CLEAR is session-wide; COSTAR is task-specific. They are additive, not overlapping. If contradiction appears, it signals a dimension boundary violation — fix the layer design, not the content.

**T3 — More layers, harder to debug.**  
When output is wrong, which layer caused it?  
*Counter*: DSPy's insight applies — treat each layer as a separately logged module. Log the output of each `build()` call at construction time. The systematic PoC approach (M1: structure only → M2: add reasoning → M3: add verification) means each added layer has a known baseline to diff against.

**T4 — Are structure frameworks necessary at all?**  
A capable model given plain instructions might perform equivalently.  
*Counter*: structure frameworks are a *software engineering* win, independent of whether the model "needs" the sections labeled. A `COSTARPrompt` object with named fields is maintainable, reviewable, and composable. A string is not. DSPy makes this argument explicitly.

**T5 — Meta-prompting brittleness.**  
If the Spec Advisor's CoT produces a bad CRISPE prompt, the Spec Specialist inherits the error.  
*Counter*: two mitigations. The Spec Advisor's CoT makes reasoning auditable — the Coordinator can inspect it. The Spec Specialist's Constitutional AI gate catches output failures and triggers a Coordinator retry. Errors surface, not propagate.

**T6 — Is this composable or just structured concatenation?**  
The model sees a flat prompt at runtime, not "layers."  
*Counter*: composability is a *construction-time* property, not a runtime one. DSPy makes the same argument: the model's context is flat, but the engineer's abstraction is modular. The PoC-by-layer execution strategy provides the empirical proof — add one layer at a time, measure each addition.

---

## The Knowledge Graph Substrate

*Derived from Senatus (agentic-gnn). Kuzu is not a persistence layer — it is the system's learning model.*

Every milestone grows the Kuzu schema by adding new node types and edge types. Each project run
writes a new **heterogeneous instance subgraph** — structurally identical to prior runs, different
attributes. The GNN (R-GCN formulation) learns patterns across these parallel instances.

The **verification analysis written after each milestone** (the "Verified:" section in BACKLOG.md)
is the ML signal: a structured observation of which brief → composition → selection → confidence →
revision path was taken. It is a labeled training instance, not documentation.

**Each milestone owns its own schema.** There is no single unified graph schema defined upfront.
Each milestone introduces only the node and edge types its layer proof required. These heterogeneous
subgraphs cohabit Kuzu and are connected by **cross-schema comparison edges** written by the
milestone's verification analysis.

**The feedback IS the ML pass.** Every milestone's verification is comparative — M3 against M2,
M4 against M3. That comparison is not documentation: it is the cross-schema edge written between
the two subgraphs. The edge carries the delta as properties (`confidence_delta`, `step_count`,
`evaluation_depth`, `revised`, `cai_principle_triggered`). The GNN learns by traversing *across*
these edges, not within a single milestone's subgraph. The learning signal lives in the topology
of comparison.

| Milestone | Its own subgraph schema | Cross-schema edge to prior | Signal on the edge |
|---|---|---|---|
| M1 | `FrameworkLayer`, `ComposedChain`, `COMPOSES` | — | — |
| M2 | `SpecRun`, `SpecSelection`, `PRODUCED`, `USES_CHAIN` | — (first runs) | — |
| M3 | `ReasoningStep`, `GROUNDS_REASONING` | `M2_SpecRun → REASONING_ADDS → M3_SpecRun` | `confidence_delta`, `step_count`, `evaluation_depth` |
| M4 | `RevisionEvent`, `TRIGGERED_REVISION`, `REVISED_TO` | `M3_SpecRun → VERIFICATION_ADDS → M4_SpecRun` | `revised`, `cai_principle`, `confidence_delta` |
| M9–M11 | `Requirement`, `Specification`, `GROUNDS`, `DERIVED_FROM` | `SpecRun → SPEC_STACK_ADDS → SpecStackRun` | `layer_depth`, `stack_confidence` |
| M14–M18 | `CodeArtifact`, `GherkinScenario`, `TestResult` | `SpecStackRun → CODE_GENERATES → BuildRun` | `first_gen_correct`, `test_coverage` |

**GraphRAG vs vector RAG:** Faber's graph is built from *structured agent outputs* (forced tool-use
with typed schemas), not from text extraction. The topology is semantically precise. The cross-schema
edges carry deltas that no embedding can represent — "adding reasoning increased per-concern evaluation
depth from a single paragraph to 7 explicit steps" is a graph property, not a text similarity score.

---

## The Central Claim

> Faber is a **meta-prompting system** (Suzgun & Kalai, 2024) in which each agent
> prompt is a **composed chain of orthogonal framework layers** (DSPy, 2023),
> verified by a **critique-revision loop** (Constitutional AI, 2022), with
> the council's decisions made auditable by **explicit reasoning traces**
> (CoT + ReAct). Every agent output is persisted as a typed node or edge in a
> **live GraphRAG + GNN substrate** (Kuzu, derived from Senatus (agentic-gnn)) that grows
> one schema layer per milestone and enables topology-based retrieval across
> all prior project runs.
>
> Two architectural contributions:
> 1. **The composition** — not any individual technique, but their systematic layering
> 2. **The graph substrate** — Kuzu as a live R-GCN whose schema IS the milestone roadmap

---

## Implementation Map

```
src/frameworks/
├── costar.py            Structure  — COSTAR prompt builder
├── crispe.py            Structure  — CRISPE prompt builder
├── clear.py             Structure  — CLEAR session builder
├── race.py              Structure  — RACE lightweight builder
├── persona.py           Technique  — Persona Prompting layer
├── few_shot.py          Technique  — Few-shot examples layer
├── chain_of_thought.py  Reasoning  — CoT step-through builder
├── react.py             Reasoning  — ReAct thought/act/observe builder
└── constitutional_ai.py Verification — CAI critique-revision builder
```

Each class: a `dataclass` with a `build() -> str` method.  
Composition via `ComposedPrompt(layers=[...]).build()` — assembles in order.  
Each layer independently unit-testable before composition.
