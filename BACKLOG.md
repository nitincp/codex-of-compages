# Backlog — Faber

> **Faber**: maker, artisan, architect. A prompt engineering project for adaptive formal specification.

Status: `[ ]` todo · `[~]` in progress · `[x]` done

---

## Done

| Milestone | Date | Summary |
|---|---|---|
| **M0** Infrastructure | 2026-06-11 | [COMPLETED.md#m0](COMPLETED.md#m0) · [evidence](docs/evidence/M00_infrastructure.md) |
| **M1** Framework builders | 2026-06-11 | [COMPLETED.md#m1](COMPLETED.md#m1) · [evidence](docs/evidence/M01_framework_builders.md) |
| **M2** Spec Advisor — structure only | 2026-06-12 | [COMPLETED.md#m2](COMPLETED.md#m2) · [evidence](docs/evidence/M02_spec_advisor_structure.md) |
| **M3** Add reasoning (CoT) | 2026-06-12 | [COMPLETED.md#m3](COMPLETED.md#m3) · [evidence](docs/evidence/M03_reasoning_layer.md) |
| **M4** Add verification (CAI) | 2026-06-12 | [COMPLETED.md#m4](COMPLETED.md#m4) · [evidence](docs/evidence/M04_verification_layer.md) |
| **M4.1** M0–M4 + ETL — GNN substrate | 2026-06-13 | [M0](COMPLETED.md#m41-m0) · [M1](COMPLETED.md#m41-m1) · [M2](COMPLETED.md#m41-m2) · [ETL](COMPLETED.md#m41-etl) · [M3](COMPLETED.md#m41-m3) · [M4](COMPLETED.md#m41-m4) · [evidence](docs/evidence/M04_1_graphrag_gnn_poc.md) |
| **M5** Layer 4 PoC — Full Spec Advisor + meta-prompt output | 2026-06-13 | [COMPLETED.md#m5](COMPLETED.md#m5) · [evidence](docs/evidence/M05_meta_prompt.md) |
| **Chore** Devcontainer Optimization (Dockerfile migration) | 2026-06-14 | [COMPLETED.md#chore-devcontainer](COMPLETED.md#chore-devcontainer) |

---

## Execution Philosophy

**Systematic PoCs from base layers upward.**

Each milestone proves a layer before the next layer is built on top of it.
A later milestone never breaks an earlier one — the system always has a working set.

```
── Spec Council (M0–M13) ──────────────────────────────────────────────────
M0  Infrastructure
M1  Layer 0 PoC  — Framework builders (the atomic base)
M2  Layer 1 PoC  — Single agent, Structure only
M3  Layer 2 PoC  — Add Reasoning layer
M4  Layer 3 PoC  — Add Verification (critique-revision loop)
M4.1 GraphRAG/GNN PoC — PE evolution captured and queryable in Kuzu
M5  Layer 4 PoC  — Full single agent (all dimensions) + Meta-Prompt output
M6  Layer 5 PoC  — First agent chain: SME Agent → Spec Advisor
M7  Layer 6 PoC  — Meta-prompting chain: Spec Advisor → Spec Specialist
M8  Layer 7 PoC  — Verification in chain + Coordinator (ReAct gating)
M9  Layer 8 PoC  — Kuzu graph integration: Specification + GROUNDS edges
M10 Layer 9 PoC  — Multi-layer spec stack (3 layers, stateful Spec Advisor)
M11 Full spec council — complete traceability in Kuzu (no code gen yet)
M12 SME Phase B   — Persona library, multi-turn Reflexion
M13 Robustness    — Model flexibility, error handling, benchmarking

── Build Council (M14–M18, placeholder — detail written after M13) ────────
M14 Build foundations — Developer agent + simple console app
M15 App Tier 1        — Two-layer API + UI  (Test Engineer joins here)
M16 App Tier 2        — Clean architecture web app
M17 App Tier 3        — Event-driven web app
M18 Ultimate          — Faber generates and verifies its own dashboard
```

Each PoC has: defined input, defined output, explicit success criteria.
Passing all criteria = the layer is proven = safe to build the next layer on top.

See `docs/foundations/composition_framework.md` for the full framework architecture.

---

## Graph Architecture — GNN First

Full design, learning loop, schema growth table, and topology query: [`ARCHITECTURE.md — Graph Architecture`](ARCHITECTURE.md#graph-architecture--gnn-first).
First topology retrieval query: [`analysis_opportunities.md — OPP-8`](analysis_opportunities.md#opp-8-first-topology-based-retrieval-m4-seeded).

---

## Chore — LLM Observability (Langfuse self-hosted)

**Goal**: capture runtime telemetry for every LLM call and prompt pipeline run — full prompt text per layer, model response, token counts (input / output / cache read / cache write), latency, cost estimate, and agent identity — with per-milestone prompt versioning tracked in Langfuse. Langfuse runs on the host machine; the devcontainer connects via `host.docker.internal`.

**Why now**: milestone runners are black boxes. The only persistent artifact from a run is what Claude concluded (`AnalysisNote` nodes in Kuzu). There is no record of what each framework layer built, what was sent to the API, how tokens accumulated, or how prompt compositions changed across milestones.

**Langfuse host setup** (done once on the developer's machine, outside the devcontainer):
- [ ] Add `.langfuse/docker-compose.yml` to workspace (gitignored) — standard Langfuse v3 stack: Postgres + ClickHouse + Langfuse app + worker
- [ ] Document startup in `.devcontainer/README.md`: `docker compose -f .langfuse/docker-compose.yml up -d`; include first-run credential setup
- [ ] Add `.langfuse/` to `.gitignore`

**Python integration**:
- [ ] Add to `pyproject.toml` dev deps: `langfuse`, `opentelemetry-instrumentation-anthropic`
- [ ] Create `src/observability/` — `__init__.py`, `setup.py` (OTel init + `AnthropicInstrumentor().instrument()` + Langfuse OTEL exporter), graceful no-op when `LANGFUSE_HOST` is unset
- [ ] Add `@observe(name="milestone_run")` to each milestone `run.py` entry point
- [ ] Add `@observe(name="agent_{name}")` to each agent's `run()` method
- [ ] All existing gate tests pass unchanged — no HTTP calls, no side effects when `LANGFUSE_HOST` unset

**Ad-hoc logging cleanup** (Langfuse supersedes these):
- [ ] Remove `FABER_LOG_PROMPTS` print block from all 6 `composed.py` copies: `src/frameworks/composed.py` and `src/milestones/m{1–5}/frameworks/composed.py` — OTel auto-instrumentation captures the full composed prompt at the API boundary
- [ ] Remove `FABER_LOG_PROMPTS` from `.env` and from `devcontainer.json` `remoteEnv`
- [ ] Remove `FABER_LOG_PROMPTS` reference from `CLAUDE.md` `.env` example block
- [ ] Simplify `run.py` summary output in m1–m5: strip the per-brief token/latency table rows (Langfuse captures these via OTel spans); keep the Kuzu graph state section (total runs in DB, edges written, edge properties) — that data is not in Langfuse
- [ ] Keep as-is: ML pass `print()` blocks in gate test files (query ephemeral mock DB, not real API calls — Langfuse has no visibility); `print()` in `etl/migrate.py` / `etl/diff.py` (migration CLI, unrelated to LLM telemetry)

**Prompt versioning**:
- [ ] Register each milestone's framework composition as a versioned prompt in Langfuse (`langfuse.create_prompt(name="m{N}_pipeline", prompt=..., labels=["m{N}"])`) — enables diff view across milestone boundaries in Langfuse UI

**Kuzu span ingestion**:
- [ ] `src/observability/kuzu_exporter.py` — thin `SpanExporter` that on span-end upserts a `PromptTrace` node into Kuzu: `run_id`, `agent_id`, `milestone`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `latency_ms`, `cost_usd`, `model`
- [ ] `TRACE_OF` rel from `PromptTrace` → `MilestoneRun` — links telemetry into the existing GNN subgraph so token cost and latency become queryable graph signals

**Gate**:
- [ ] All existing milestone gate tests pass with observability initialised
- [ ] One integration test: a single `client.messages.create()` call produces a `PromptTrace` node in ephemeral Kuzu with correct `input_tokens` and `latency_ms > 0`

**Not a milestone gate** — does not block M6. Should follow the Devcontainer chore.

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

## Milestone 9 — Layer 8 PoC: Spec Stack Graph Integration

**Note**: Kuzu is first used in M4.1 (PE meta-graph). M9 adds the second schema layer — the spec
stack graph (`Requirement`, `Specification`, `GROUNDS` edges). Both graphs cohabit Kuzu; M9 proves
the spec artifact traceability chain, not Kuzu's first use.

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

## Milestone 11 — Full Spec Council: Complete Traceability

Goal: The spec council is complete and the full traceability chain is queryable end-to-end in Kuzu.
Test Engineer is **not** in this council — Gherkin without a running implementation is another spec layer,
not a verified test. It belongs in the build council (M14+) alongside Developer and ExecutionVerifier.

- [ ] Full 3-pass pipeline proven: `sme_agent → spec_advisor → spec_specialist → coordinator` × 3 layers
- [ ] Kuzu: full GROUNDS chain (system → domain → component) queryable
- [ ] Kuzu: `Requirement → DERIVED_FROM → Specification` path present for each layer
- [ ] `scripts/graph_stats.py` — display full traceability path as a readable chain
- [ ] `tests/test_full_council.py`:
  - Full pipeline run produces 3 Specification nodes in Kuzu
  - Each Specification has a GROUNDS edge to the layer above it
  - Requirement traces to all 3 layers via DERIVED_FROM
  - Coordinator issued `proceed` at each layer (or retry + proceed) — no uncaught escalation

**Success criteria (gate to M12):**
> A single pipeline run produces a complete, queryable spec stack in Kuzu.
> Every spec layer is grounded and traceable back to the original Requirement.
> The spec council stands on its own without code generation.

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

---

## Build Council — M14–M18 (placeholder track)

> These milestones will be detailed once M13 is proven.
>
> The spec council (M0–M13) produces formal specs + a Kuzu traceability graph.
> The build council (M14–M18) consumes that graph and produces running code + verified tests.
>
> The GNN is already running by M3 (see *Graph Architecture — GNN First* above).
> The build council does not introduce it — it scales it into a new signal class.
> Every generation attempt, test execution result, coverage signal, and code quality verdict
> becomes a new instance subgraph written back to Kuzu. The GNN now answers richer queries:
> which spec patterns produced correct code on first generation, which test topologies caught
> the most regressions, which layer combinations converged fastest under Coordinator retry.
> The graph grows from a spec traceability store into a full build-intelligence substrate.
>
> Two new agents join here: **Developer** and **Test Engineer**.
> A new **ExecutionVerifier** step replaces schema-conformance checks with actual test runs.

The complexity tiers below are both the *input brief complexity* and the *success bar*:
each tier must produce a runnable artifact whose own tests pass before the milestone is proven.

| Milestone | Input brief | Spec stack depth | Output |
|---|---|---|---|
| M14 | Simple console app | 1 layer (domain only) | Single-file CLI; passes its own tests |
| M15 | Two-layer API + UI | 2 layers (domain → component) | FastAPI + minimal frontend; runnable (Test Engineer joins here) |
| M16 | Clean-arch web app | 3 layers (system → domain → component) | Layered structure, DI, repo pattern |
| M17 | Event-driven web app | 4+ layers + async specs | CQRS / event bus wiring, async consumers |
| M18 | **Ultimate: self-generating dashboard** | Full council | Faber generates its own Streamlit UI + test suite; generated Playwright tests pass against it |

---

## Decisions Log

Full log: [`docs/decisions/decisions-log.md`](docs/decisions/decisions-log.md)  
ADRs: [`docs/decisions/`](docs/decisions/)
