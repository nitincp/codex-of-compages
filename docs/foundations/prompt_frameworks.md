# Prompt Frameworks Reference — Faber

Framework builders are architectural primitives, not documentation style.
Each is implemented as a Python dataclass with `build() -> str` in `src/frameworks/`.

**Composition rule**: one layer per dimension per agent. Structure first, Verification last.
Full composition model, research grounding, and one-shot examples: `composition_framework.md`.

---

## Taxonomy

| Dimension | Framework | Class | Used by |
|---|---|---|---|
| Structure | COSTAR | `COSTARPrompt` | Spec Advisor (primary structure) |
| Structure | CRISPE | `CRISPEPrompt` | Spec Specialist (injected), Test Engineer |
| Structure | CLEAR | `CLEARSession` | All agents (session context layer) |
| Structure | RACE | `RACEPrompt` | Utility / lightweight tasks |
| Reasoning | Chain of Thought | `ChainOfThought` | Spec Advisor (selection reasoning) |
| Reasoning | ReAct | `ReActLoop` | Coordinator (deliberative gating) |
| Verification | Constitutional AI | `ConstitutionalAI` | SME Agent, Spec Specialist, Test Engineer |
| Technique | Persona | `PersonaLayer` | SME Agent (persona identity) |
| Technique | Few-Shot | `FewShot` | Spec Specialist, Test Engineer (examples from graph) |
| — | Composition | `ComposedPrompt` | All agents — assembles the chain |

> **VOICE is retired.** It combined three dimensions into one custom framework.
> Replaced by: `COSTARPrompt` (Structure) + `PersonaLayer` (Technique) + `ConstitutionalAI` (Verification).
> See `docs/decisions/ADR-002_voice-retired.md`.

---

## COSTAR — Structured output / high-stakes selection (Spec Advisor)

Used when an agent makes a consequential selection or produces a formal document.
The Spec Advisor uses COSTAR to structure its own output, then emits a CRISPE prompt.

| Field | Purpose |
|---|---|
| `context` | System description + all parent-layer specs from graph |
| `objective` | What this layer needs to capture or decide |
| `style` | Formal notation with plain-English rationale |
| `tone` | Rigorous, collaborative |
| `audience` | Which agent(s) consume this output |
| `response_format` | Expected output structure and constraints |

```python
COSTARPrompt(
    context=f"Project: {brief}\nPrior layer specs:\n{prior_specs}",
    objective="Select the best-fit specification language for the domain layer",
    audience="Spec Specialist and Coordinator",
    response_format="Tool call: selected_lang, justification, specialist_crispe_prompt, confidence",
).build()
```

---

## CRISPE — Technical generation / complex reasoning (Spec Specialist, Test Engineer)

Used for generating formal spec content. The Spec Specialist receives a CRISPE prompt
*generated at runtime by the Spec Advisor* — it has no fixed system prompt of its own.

| Field | Purpose |
|---|---|
| `capacity` | Act as a [spec language] specialist |
| `role` | This agent's role in the council for this layer |
| `insight` | Context injected from parent-layer specs |
| `statement` | The specific generation task |
| `personality` | Precise, minimal, verifiable |
| `experiment` | Generate + self-check for syntactic correctness and coverage |

```python
# Emitted by Spec Advisor — becomes Spec Specialist's entire system prompt
CRISPEPrompt(
    capacity="Act as a CML (Context Mapper Language) specification specialist",
    role="Produce a CML context map for the domain layer of this system",
    insight=f"Parent-layer TLA+ spec:\n{tla_spec}",
    statement=f"Model the bounded contexts and aggregates for: {brief}",
).build()
```

---

## CLEAR — Session protocol (Coordinator, SME Agent Phase B)

Used to structure every council turn and gate layer transitions.
Also used as the outermost layer in agents that need explicit session context injection.

| Field | Purpose |
|---|---|
| `context` | What is known; what prior layers produced |
| `layering` | Which spec layer is being addressed now |
| `execute` | The agent task for this turn |
| `assess` | Validation criteria — what makes this layer's output acceptable |
| `reflect` | What changed; what the next layer inherits; open questions |

---

## RACE — Lightweight generation (utility tasks)

For lower-stakes outputs where full COSTAR overhead is unnecessary.

| Field | Purpose |
|---|---|
| `role` | Brief agent identity |
| `action` | Specific generation task |
| `context` | Minimal necessary context |
| `execute` | Output format and constraints |

---

## PersonaLayer — Persona identity (SME Agent)

Technique layer. Carries who speaks and how. Part of the SME Agent's composition chain
alongside COSTAR (Structure) and ConstitutionalAI (Verification).

| Field | Purpose |
|---|---|
| `role` | Job title, years of experience, domain |
| `background` | Domain expertise, track record, what they care about |
| `priorities` | Non-negotiables; what they will push back on |
| `communication_style` | How they speak: direct/formal/skeptical/etc. |

```python
PersonaLayer(
    role="Senior VP of Product, mid-size payment processor, 12 years in payments",
    background="Deep compliance expertise — PCI-DSS, ISO 8583, acquiring agreements",
    priorities="Sub-200ms settlement, chargeback rate below 0.1%, PCI scope minimised",
    communication_style="Direct, risk-focused, skeptical of over-engineering. "
                        "Uses domain terminology naturally.",
).build()
```

---

## ChainOfThought — Explicit reasoning steps (Spec Advisor)

Reasoning layer. Makes the Spec Advisor's candidate evaluation visible and auditable.
The Coordinator can inspect the `reasoning_steps` field in the output before trusting the selection.

| Field | Purpose |
|---|---|
| `steps` | Ordered list of reasoning steps (populated at construction time or left empty for model to fill) |
| `preamble` | Instruction to think step-by-step before answering |

---

## ReActLoop — Deliberative gating (Coordinator)

Reasoning layer. Used by the Coordinator to produce auditable proceed/retry/escalate decisions.

| Field | Purpose |
|---|---|
| `thought_prompt` | What to reason about before acting |
| `action_options` | Valid actions: `["proceed", "retry", "escalate"]` |
| `observation_note` | What to carry forward to the next loop iteration |

---

## ConstitutionalAI — Critique-revision gate (SME Agent, Spec Specialist, Test Engineer)

Verification layer. Always the **last** layer in a composition chain.
Principles are stated explicitly; the model critiques its own output and revises before returning.

| Field | Purpose |
|---|---|
| `principles` | List of criteria the output must satisfy |
| `revise_note` | Instruction: revise if any criterion is violated, before returning |

```python
ConstitutionalAI(
    principles=[
        "Does the requirement sound like a business stakeholder, not a software architect?",
        "Is it consistent with prior requirements in this session?",
        "Does it react coherently to the council's last response?",
    ]
).build()
```

---

## FewShot — Examples from graph (Spec Specialist, Test Engineer)

Technique layer. Provides 1–3 examples of the target output format.
In Spec Specialist: prior specs of the same language, retrieved from Kuzu.
In Test Engineer: Gherkin scenarios derived from existing spec nodes.

| Field | Purpose |
|---|---|
| `examples` | List of `(label, content)` tuples |
| `preamble` | Instruction before examples |

---

## ComposedPrompt — Chain assembler

Not a framework itself — assembles a chain of layers into a single prompt string.
Layers are joined by `\n\n---\n\n`. Empty layers (where `build()` returns `""`) are skipped.

```python
prompt = ComposedPrompt([
    CLEARSession(context=..., layering=..., execute=...),
    COSTARPrompt(context=..., objective=..., response_format=...),
    PersonaLayer(role=..., background=..., priorities=...),
    ConstitutionalAI(principles=[...]),
]).build()
```
