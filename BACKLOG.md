# Backlog — Faber

> **Faber**: maker, artisan, architect. A prompt engineering project for adaptive formal specification.

Status: `[ ]` todo · `[~]` in progress · `[x]` done

---

## Execution Philosophy

**Systematic PoCs from base layers upward.**

Each milestone proves a layer before the next layer is built on top of it.
A later milestone never breaks an earlier one — the system always has a working set.

```
M0  Infrastructure
M1  Layer 0 PoC  — Framework builders (the atomic base)
M2  Layer 1 PoC  — Single agent, Structure only
M3  Layer 2 PoC  — Add Reasoning layer
M4  Layer 3 PoC  — Add Verification (critique-revision loop)
M5  Layer 4 PoC  — Full single agent (all dimensions) + Meta-Prompt output
M6  Layer 5 PoC  — First agent chain: SME Agent → Spec Advisor
M7  Layer 6 PoC  — Meta-prompting chain: Spec Advisor → Spec Specialist
M8  Layer 7 PoC  — Verification in chain + Coordinator (ReAct gating)
M9  Layer 8 PoC  — Kuzu graph integration: Specification + GROUNDS edges
M10 Layer 9 PoC  — Multi-layer spec stack (3 layers, stateful Spec Advisor)
M11 Full council  — Test Engineer + complete traceability
M12 SME Phase B   — Persona library, multi-turn Reflexion
M13 Robustness    — Model flexibility, error handling, benchmarking
```

Each PoC has: defined input, defined output, explicit success criteria.
Passing all criteria = the layer is proven = safe to build the next layer on top.

See `docs/foundations/composition_framework.md` for the full framework architecture.

---

## Milestone 0 — Infrastructure

Goal: working devcontainer, Kuzu connected, Chainlit running, all deps installed.
Source: extract and adapt from Senatus project (link TBD).

- [ ] Copy `.devcontainer/` from Senatus (`bootstrap-secrets.sh`, `devcontainer.json`)
- [ ] Create `pyproject.toml` — same core deps as Senatus (`anthropic`, `langgraph`, `kuzu`, `chainlit`, `pydantic`, `python-dotenv`, `tenacity`, `ruff`, `pytest`)
- [ ] Adapt `src/agents/base.py` from Senatus
  - Add `build_prompt(layers: list[FrameworkLayer]) -> str` — assembles composed chain
  - Keep `TokenUsage` / `SessionUsage` dataclasses intact
- [ ] Adapt `src/graph/schema.py` — add `Specification`, `Requirement` NodeTypes; `GROUNDS`, `DERIVED_FROM`, `REFINES` EdgeTypes
- [ ] Adapt `src/graph/store.py` — add new node/edge props; keep `write_node()`/`write_edge()` pattern
- [ ] Stub `src/ui/app.py` — bare Chainlit shell
- [ ] Create `.env`: `MODEL_PROVIDER=anthropic`, `MODEL_NAME=claude-sonnet-4-6`, `KUZU_DB_PATH=data/kuzu`
- [ ] Verify: `chainlit run src/ui/app.py --port 8000` starts without errors

---

## Milestone 1 — Layer 0 PoC: Framework Builders

**What is being proven**: the atomic base layer. All framework builders produce correctly structured output and can be composed. Nothing else can be built until this is proven.

- [ ] Implement `src/frameworks/costar.py` — `COSTARPrompt.build() -> str`
- [ ] Implement `src/frameworks/crispe.py` — `CRISPEPrompt.build() -> str`
- [ ] Implement `src/frameworks/clear.py` — `CLEARSession.build() -> str`
- [ ] Implement `src/frameworks/race.py` — `RACEPrompt.build() -> str`
- [ ] Implement `src/frameworks/persona.py` — `PersonaLayer.build() -> str`
- [ ] Implement `src/frameworks/chain_of_thought.py` — `ChainOfThought.build() -> str`
- [ ] Implement `src/frameworks/react.py` — `ReActLoop.build() -> str`
- [ ] Implement `src/frameworks/constitutional_ai.py` — `ConstitutionalAI.build() -> str`
- [ ] Implement `src/frameworks/few_shot.py` — `FewShot.build() -> str`
- [ ] Implement `src/frameworks/composed.py` — `ComposedPrompt(layers=[...]).build() -> str`
  - Assembles layers in order, separated by `\n\n---\n\n`
  - Each layer labelled with its dimension in a comment (for logging/debugging)
- [ ] `tests/test_frameworks.py`:
  - Each builder: all fields → all section headers present in correct order
  - Empty optional field → section omitted
  - `ComposedPrompt([costar, persona, cai]).build()` → sections appear in correct sequence
  - Dimension label present for each layer in composed output

**Success criteria** (gate to M2):
> All builders produce correctly structured strings. ComposedPrompt assembles them
> in the declared order. Each layer is independently unit-testable.

---

## Milestone 2 — Layer 1 PoC: Single Agent, Structure Only

**What is being proven**: a structure layer alone (COSTAR) is sufficient to ground the Spec Advisor's core task — selecting a spec language. Establishes the baseline all subsequent layers are measured against.

- [ ] `src/agents/schemas.py` — `SpecAdvisorOutput`: `selected_lang`, `layer`, `justification`, `confidence`
- [ ] `src/agents/spec_advisor.py` — `SpecAdvisorAgent` with **COSTAR only** (no CoT, no CAI yet)
  - Uses `COSTARPrompt` to build system prompt
  - Forced tool-use returning `SpecAdvisorOutput`
- [ ] Minimal pipeline: `spec_advisor → show_output → END`
- [ ] `tests/test_spec_advisor.py`:
  - Input: "CRUD todo app" → selected_lang is JSON Schema or OpenAPI
  - Input: "multi-region e-commerce with eventual consistency" → selected_lang is TLA+ or CML
  - Both: justification present and non-empty

**Success criteria** (gate to M3):
> Spec Advisor selects different languages for projects of different complexity.
> Justification is coherent. Baseline selection quality recorded for comparison.

---

## Milestone 3 — Layer 2 PoC: Add Reasoning

**What is being proven**: adding a Chain of Thought layer to the Spec Advisor makes its selection reasoning visible and auditable. Quality should improve or stay equal — never regress.

- [ ] Add `ChainOfThought` layer to `SpecAdvisorAgent`
  - Steps: identify layer concerns → evaluate candidates → select + justify
- [ ] `SpecAdvisorOutput` extended: add `reasoning_steps: list[str]` field
- [ ] `tests/test_spec_advisor.py` extended:
  - `reasoning_steps` is non-empty and contains ≥3 steps
  - Each step references a specific concern or candidate language
  - Selection quality ≥ M2 baseline (same test inputs, compare justification depth)

**Success criteria** (gate to M4):
> Reasoning steps are visible, auditable, and reference specific layer concerns.
> Selection quality is equal to or better than M2 baseline.

---

## Milestone 4 — Layer 3 PoC: Add Verification

**What is being proven**: the Constitutional AI critique-revision loop improves low-quality outputs and passes high-quality ones through. The loop is the self-correcting gate.

- [ ] Add `ConstitutionalAI` layer to `SpecAdvisorAgent`
  - Criteria: justification references specific layer concerns, confidence ≥ 0.7, candidate evaluation present
- [ ] `SpecAdvisorOutput` extended: `revised: bool`, `revision_notes: str`
- [ ] `tests/test_spec_advisor.py` extended:
  - **Regression test**: intentionally weak input (vague project brief) → `revised=True`, output improves
  - **Pass-through test**: strong input → `revised=False`, output unchanged
  - All M2 and M3 tests still pass (no regression)

**Success criteria** (gate to M5):
> CAI gate demonstrably revises weak outputs. Strong outputs pass through unchanged.
> No regression in M2/M3 test cases.

---

## Milestone 5 — Layer 4 PoC: Full Spec Advisor — Meta-Prompt Output

**What is being proven**: the Spec Advisor, with all four layers active, produces a CRISPE prompt (meta-prompt) that is coherent and sufficient to drive a Spec Specialist. This is the meta-prompting moment.

- [ ] `SpecAdvisorOutput` extended: `specialist_crispe_prompt: str`
- [ ] Spec Advisor chain now: `CLEAR → COSTAR → CoT → CAI → MetaPromptOutput(CRISPE)`
- [ ] `src/agents/spec_specialist.py` — `SpecSpecialistAgent` stub
  - Accepts a CRISPE prompt string at call time; no fixed system prompt
  - Forced tool-use returning `SpecialistOutput`: `spec_content`, `spec_lang`, `well_formedness_notes`, `confidence`
- [ ] Integration test: Spec Advisor output → feed `specialist_crispe_prompt` → Spec Specialist → `spec_content` is non-empty and mentions domain terms from input
- [ ] `tests/test_meta_prompt.py`:
  - Generated CRISPE prompt contains all 6 CRISPE fields
  - `capacity` field matches the selected spec language
  - `insight` field contains domain context from the original brief

**Success criteria** (gate to M6):
> The Spec Advisor generates a CRISPE prompt that, when injected into the Spec Specialist,
> produces a non-empty formal spec mentioning domain terms from the original brief.

---

## Milestone 6 — Layer 5 PoC: First Agent Chain

**What is being proven**: two agents composed in sequence. SME Agent output feeds Spec Advisor input. The Spec Advisor's selection reflects the SME's domain vocabulary — proving inter-agent context flows correctly.

- [ ] `src/agents/schemas.py` — `SMEOutput`: `requirement_text`, `scenario_type`, `domain_terms`, `reacts_to_council`, `confidence`, `persona_used`
- [ ] `src/agents/sme_agent.py` — `SMEAgent`
  - Chain: `CLEAR → COSTAR → PersonaLayer → ConstitutionalAI`
  - Accepts: `domain_brief`, `scenario_hint`, `persona` dict
  - Forced tool-use returning `SMEOutput`
- [ ] Pipeline: `sme_agent → spec_advisor → show_output → END`
- [ ] `tests/test_sme_chain.py`:
  - Fintech persona → requirement uses payments terminology → Spec Advisor selects language appropriate for fintech domain
  - Healthcare persona, same domain brief → different terminology, potentially different spec language
  - Domain terms from `SMEOutput.domain_terms` appear in Spec Advisor's `insight` field

**Success criteria** (gate to M7):
> Domain terms from SME output appear in Spec Advisor context.
> Different personas applied to same brief produce measurably different
> requirement text AND influence Spec Advisor's selection.

---

## Milestone 7 — Layer 6 PoC: Meta-Prompting Chain

**What is being proven**: the full meta-prompting chain works end-to-end. SME → Spec Advisor (generates CRISPE) → Spec Specialist (receives CRISPE) → formal spec output. This is the core of Faber's architecture proven in one chain.

- [ ] Full `SpecSpecialistAgent` implementation
  - Chain: `CRISPE (injected) → FewShot → ConstitutionalAI`
  - Few-shot layer: initially empty (no prior specs in graph yet)
- [ ] Pipeline: `sme_agent → spec_advisor → spec_specialist → show_output → END`
- [ ] `src/ui/app.py` — show full chain: SME requirement → Advisor selection + justification + reasoning → Specialist spec content
- [ ] `tests/test_meta_chain.py`:
  - Spec Specialist's system prompt is exactly the CRISPE prompt generated by Spec Advisor
  - Formal spec output mentions at least 2 domain terms from SME output
  - `spec_lang` in SpecialistOutput matches `selected_lang` in SpecAdvisorOutput
  - CAI critique pass runs; `well_formedness_notes` present

**Success criteria** (gate to M8):
> A single pipeline run (SME → Advisor → Specialist) produces a formal spec in the
> Advisor-selected language, grounded in the SME's domain terminology. The full
> meta-prompting chain is proven end-to-end.

---

## Milestone 8 — Layer 7 PoC: Coordinator + Verification in Chain

**What is being proven**: the deliberative consensus model works. Coordinator detects low-confidence output and triggers retry. The loop terminates correctly (proceed, retry up to limit, or escalate).

- [ ] `src/agents/schemas.py` — `CoordinatorDecision`: `decision` (proceed|retry|escalate), `rationale`, `critique_for_retry`
- [ ] `src/orchestration/coordinator.py` — `CoordinatorAgent`
  - Chain: `CLEAR → ReAct`
  - Evaluates Spec Specialist output; issues decision
  - Retry limit: 2 (escalate to user on 3rd failure)
- [ ] Pipeline: `sme_agent → spec_advisor → spec_specialist → coordinator → [retry loop or proceed]`
- [ ] `tests/test_coordinator.py`:
  - Mock low-confidence SpecialistOutput (confidence=0.4) → decision=retry, critique_for_retry non-empty
  - Mock high-confidence output (confidence=0.85) → decision=proceed
  - Retry loop: low confidence twice → third attempt → decision=escalate
  - ReAct `Thought` field in CoordinatorDecision is non-empty and references specific output properties

**Success criteria** (gate to M9):
> Coordinator correctly identifies low-confidence output and triggers retry.
> Retry loop terminates. ReAct reasoning is auditable.

---

## Milestone 9 — Layer 8 PoC: Kuzu Graph Integration

**What is being proven**: spec artifacts are persisted with GROUNDS edges forming a queryable traceability chain. The graph is the system of record.

- [ ] `GraphStore` handles `Requirement` and `Specification` node writes
- [ ] `GraphStore` handles `GROUNDS`, `DERIVED_FROM`, `REFINES` edge writes
  - Note: verify Kuzu STRING column size for `spec_content` field
- [ ] Pipeline `commit_to_graph` step writes all agent outputs
- [ ] `scripts/graph_stats.py` — show Specification nodes, GROUNDS chain, Requirement → Spec path
- [ ] `tests/test_graph_store.py`:
  - Write 2 Specification nodes (domain + component layers)
  - Write GROUNDS edge between them
  - Query: traverse GROUNDS from component → domain → correct source node
  - Write Requirement node + DERIVED_FROM edge to Specification → traverse correctly
- [ ] Few-shot layer in Spec Specialist now pulls prior specs of the same language from Kuzu

**Success criteria** (gate to M10):
> A 2-layer spec chain (domain → component) with GROUNDS edge is written to Kuzu
> and queryable in both directions. Requirement traces to its derived Specification.
> Few-shot layer in Spec Specialist retrieves a real example from the graph.

---

## Milestone 10 — Layer 9 PoC: Multi-Layer Spec Stack

**What is being proven**: Spec Advisor is stateful across visits. 3-layer stack (system → domain → component) produces GROUNDS chain in Kuzu. Stack depth scales with project complexity.

- [ ] `SpecAdvisorAgent` loads prior-layer specs from Kuzu as context on each visit
- [ ] `council.py` — 3-pass pipeline: each pass is `spec_advisor → spec_specialist → coordinator → write_to_graph`
- [ ] UI: layer-by-layer progress (layer name, lang selected, confidence, Coordinator decision)
- [ ] `tests/test_spec_stack.py`:
  - Simple project → Spec Advisor visits 2 layers (domain + test)
  - Complex distributed project → Spec Advisor visits 3 layers (system + domain + component)
  - Each visit's CRISPE prompt contains the prior layer's spec in the `insight` field
  - Kuzu contains full GROUNDS chain for both

**Success criteria** (gate to M11):
> Two projects of different complexity produce spec stacks of different depths.
> Each layer's spec is grounded in the layer above it.
> Stack is fully queryable as a GROUNDS chain in Kuzu.

---

## Milestone 11 — Full Council: Test Engineer + Traceability

Goal: Test Engineer generates Gherkin from the full spec stack. Full traceability path queryable end-to-end.

- [ ] `src/agents/test_engineer.py` — `TestEngineerAgent`
  - Chain: `CRISPE → FewShot (spec-derived) → ConstitutionalAI`
  - Input: all Specification nodes from Kuzu for current session
  - Output: Gherkin features + scenarios
- [ ] Graph: `COVERED_BY` edge from `GherkinScenario → Specification`
- [ ] Full traceability path queryable: Requirement → TLA+ → CML → OpenAPI → Gherkin
- [ ] Invoked by Coordinator after all spec layers complete

---

## Milestone 12 — SME Agent Phase B: Persona Library + Reflexion

Goal: Full persona-driven multi-domain simulation. Multi-turn history accumulation (Reflexion pattern). Benchmark suite.

- [ ] `src/agents/personas/` — YAML persona library
  - Schema: `role`, `domain`, `priorities`, `communication_style`, `sample_requests`
  - Initial set: `fintech_pm.yaml`, `healthcare_admin.yaml`, `logistics_ops_lead.yaml`, `retail_cto.yaml`
- [ ] SME Agent multi-turn: accumulates prior council responses as Reflexion episodic memory
  - `interaction` field in COSTAR layer populated with conversation history across turns
  - Implements Reflexion pattern (Shinn et al. NeurIPS 2023)
- [ ] `scripts/simulate.py` — `--persona fintech_pm --domain "payment gateway" --turns 5`
- [ ] `scripts/benchmark.py` — fixed domains × personas × scenario sequences; quality metrics across builds
- [ ] `sme: <domain>` command in Chainlit UI

---

## Milestone 13 — Robustness + Model Flexibility

- [ ] Ollama integration — validate forced tool-use reliability with smaller models
- [ ] Confidence calibration — replace hardcoded values with LLM-derived scoring
- [ ] Session persistence — re-hydrate spec stack from Kuzu on restart
- [ ] Error handling — API failures, Kuzu write errors, Coordinator retry limit exceeded
- [ ] Layer-level logging — log each `build()` output per agent turn for debugging

---

## Decisions Log

| Date | Decision | Reason |
|---|---|---|
| 2026-06-11 | Named **Faber** | Latin: maker/artisan/architect. Guild-of-agents metaphor. "Homo faber" grounds the PE-first philosophy |
| 2026-06-11 | Composition over single-framework assignment | DSPy (2023) + ACL 2024 empirically prove composable chains outperform monolithic prompts. Each dimension is independently testable |
| 2026-06-11 | Systematic PoC execution by layer | Each layer proven before next built on it. Always-working set at every milestone. Regression caught immediately |
| 2026-06-11 | VOICE framework retired | Was a custom framework baking three dimensions into one. Replaced by: COSTAR (Structure) + Persona Prompting (Technique) + Constitutional AI (Verification) — all industry-standard |
| 2026-06-11 | SME Agent on COSTAR + Persona + CAI | COSTAR structures the output, Persona Prompting grounds the voice, CAI gates authenticity. Three industry-standard layers replacing one custom one |
| 2026-06-11 | Meta-prompting named explicitly | The Spec Advisor's primary product is a CRISPE prompt. This IS meta-prompting (Suzgun & Kalai 2024). Naming it makes the architecture self-documenting |
| 2026-06-11 | Constitutional AI as the verification layer | Anthropic's own framework, designed for Claude. Critique-revision loop is the natural fit for all output gates in Faber agents |
| 2026-06-11 | Reflexion for SME Phase B multi-turn | Shinn et al. NeurIPS 2023 validates verbal episodic memory for multi-trial improvement without weight updates. Exact pattern needed for accumulating council responses |
| 2026-06-11 | Deliberative consensus (Coordinator-gated) | Spec quality at lower layers depends on correctness above. CLEAR + ReAct makes decisions auditable. Errors surface, not propagate |
| 2026-06-11 | Separate repo from Senatus | Different grounding: PE-first vs council-first. Different schema. Shared toolchain extracted and adapted |
