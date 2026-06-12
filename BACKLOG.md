# Backlog — Faber

> **Faber**: maker, artisan, architect. A prompt engineering project for adaptive formal specification.

Status: `[ ]` todo · `[~]` in progress · `[x]` done

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

Kuzu is not a storage layer that later gets a GNN bolted on. **It is the model.**
Every milestone grows the graph schema — new node types, new edge types, new learned edge weights.
The GNN is not trained offline and deployed; it is queried live against whatever has accumulated in Kuzu.

**Each milestone owns its own schema.** There is no single unified graph schema defined upfront.
Each milestone introduces the node types and edge types that its layer proof requires — no more.
These heterogeneous subgraphs cohabit Kuzu and are connected by cross-schema edges written
by the comparative feedback.

**The feedback IS the ML pass.** Every milestone's verification analysis is comparative by design:
M3 measures against M2, M4 against M3. That comparison is not documentation — it is the **cross-schema
edge** written between the two milestone subgraphs. The edge carries the delta as properties:
`confidence_delta`, `reasoning_step_count`, `evaluation_depth`, `revised`, `cai_principle_triggered`.

The GNN learns by traversing *across* these cross-schema edges — not within a single milestone's
subgraph. The learning signal lives in the topology of comparison, not in the node attributes alone.

```
M2 subgraph ←——— REASONING_ADDS ———→ M3 subgraph
  (SpecRun)    confidence_delta=+0.02    (SpecRun)
               step_count=7
               evaluation_depth=per-concern

M3 subgraph ←——— VERIFICATION_ADDS ——→ M4 subgraph
  (SpecRun)    revised=False (strong)     (SpecRun)
               revised=True (vague)
               cai_principle=3
```

**The cross-schema edge IS the gradient.** The GNN reads: "adding reasoning to structure improved
confidence by X and deepened evaluation from conclusion to per-concern." That is a learned weight
on the `REASONING_ADDS` edge type — an R-GCN weight matrix for that relation.

### Schema growth: each milestone contributes its own layer

| Milestone | Its own subgraph schema | Cross-schema edge to prior | Signal carried on the edge |
|---|---|---|---|
| M1 | `FrameworkLayer`, `ComposedChain`, `COMPOSES` | — | — |
| M2 | `SpecRun`, `SpecSelection`, `PRODUCED`, `USES_CHAIN` | — (first runs; no prior to compare) | — |
| M3 | `ReasoningStep`, `GROUNDS_REASONING` | `M2_SpecRun → REASONING_ADDS → M3_SpecRun` | `confidence_delta`, `step_count`, `evaluation_depth` |
| M4 | `RevisionEvent`, `TRIGGERED_REVISION`, `REVISED_TO` | `M3_SpecRun → VERIFICATION_ADDS → M4_SpecRun` | `revised`, `cai_principle`, `confidence_delta` |
| M5–M11 | Spec stack nodes per milestone | `MN_SpecRun → LAYER_ADDS → MN+1_SpecRun` | Per-milestone quality delta |
| M14–M18 | `CodeArtifact`, `GherkinScenario`, `TestResult` | `Spec_SpecRun → CODE_GENERATES → Build_SpecRun` | `first_gen_correct`, `test_coverage`, `convergence_turns` |

### The learning loop

```
Milestone proven → verification analysis written (comparative against prior milestone)
    ↓
Cross-schema edges written to Kuzu: MN_SpecRun → LAYER_ADDS → MN+1_SpecRun
    with delta properties as edge weights
    ↓
GNN message-passing traverses across cross-schema edges
    ↓
Query: "for this new brief, which path through the milestone graph
        produced the best quality signal?" → retrieves prior run by topology
    ↓
FewShot layer injects that run as a real example → better agent output
    ↓
Better output → richer verification analysis → stronger edge weights  (loop)
```

**After M3, the first meaningful cross-schema query:**
> *"Traverse M2 → REASONING_ADDS → M3. For runs where reasoning_step_count ≥ 5 and
> evaluation_depth = per-concern, what was the confidence_delta?
> Which SpecRun should I use as a FewShot example for a new complex brief?"*

This is a graph-topology traversal across heterogeneous milestone subgraphs —
not a text-similarity lookup, not a single-schema query.

---

## Milestone 0 — Infrastructure ✓

Goal: working devcontainer, Kuzu connected, Streamlit dashboard running, all deps installed.
Source: extracted and adapted from Senatus project.

- [x] Copy `.devcontainer/` from Senatus (`bootstrap-secrets.sh`, `devcontainer.json`)
- [x] Create `pyproject.toml` — core deps (`anthropic`, `langgraph`, `kuzu`, `chainlit`, `streamlit`, `pydantic`, `python-dotenv`, `tenacity`, `ruff`, `pytest`, `playwright`, `pytest-playwright`, `pytest-base-url`)
- [x] Adapt `src/agents/base.py` from Senatus
  - `build_prompt(layers: list[FrameworkLayer]) -> str` — assembles composed chain
  - `TokenUsage` / `SessionUsage` dataclasses intact
- [x] Adapt `src/graph/schema.py` — `Specification`, `Requirement` NodeTypes; `GROUNDS`, `DERIVED_FROM`, `REFINES` EdgeTypes
- [x] Adapt `src/graph/store.py` — node/edge props; `write_node()`/`write_edge()` pattern
- [x] Stub `src/ui/app.py` — bare Chainlit shell (wired at M7)
- [x] Create `src/ui/dashboard.py` — Streamlit milestone runner + artifact viewer (primary UI)
- [x] Create `.env`: `MODEL_PROVIDER=anthropic`, `MODEL_NAME=claude-sonnet-4-6`, `KUZU_DB_PATH=data/kuzu`
- [x] Verify: `streamlit run src/ui/dashboard.py --server.port 8000` starts without errors
- [x] `tests/test_m0_dashboard.py` — Playwright smoke tests confirm dashboard renders correctly

**Verified**: dashboard loads, milestone selector present, Run button present, agent cards idle. 4/4 Playwright smoke tests + 2 screenshot captures passing. Screenshots at `tests/artifacts/m0_dashboard_idle.png` and `tests/artifacts/m0_run_result.png`.

---

## Milestone 1 — Layer 0 PoC: Framework Builders ✓

**What is being proven**: the atomic base layer. All framework builders produce correctly structured output and can be composed. Nothing else can be built until this is proven.

- [x] Implement `src/frameworks/costar.py` — `COSTARPrompt.build() -> str`
- [x] Implement `src/frameworks/crispe.py` — `CRISPEPrompt.build() -> str`
- [x] Implement `src/frameworks/clear.py` — `CLEARSession.build() -> str`
- [x] Implement `src/frameworks/race.py` — `RACEPrompt.build() -> str`
- [x] Implement `src/frameworks/persona.py` — `PersonaLayer.build() -> str`
- [x] Implement `src/frameworks/chain_of_thought.py` — `ChainOfThought.build() -> str`
- [x] Implement `src/frameworks/react.py` — `ReActLoop.build() -> str`
- [x] Implement `src/frameworks/constitutional_ai.py` — `ConstitutionalAI.build() -> str`
- [x] Implement `src/frameworks/few_shot.py` — `FewShot.build() -> str`
- [x] Implement `src/frameworks/composed.py` — `ComposedPrompt(layers=[...]).build() -> str`
  - Assembles layers in order, separated by `\n\n---\n\n`
  - Each layer labelled with its dimension in a comment (for logging/debugging)
- [x] Added `_dimension` class attribute to all 9 framework classes — values: `Structure`, `Reasoning`, `Verification`, `Technique`. Used by `ComposedPrompt` to prefix each non-empty layer output with `# [Dimension: ClassName]`.
- [x] `tests/test_m1_frameworks.py` — 22 tests across 5 categories:
  1. All section headers present in correct order (one test per builder)
  2. Empty optional fields omitted from output
  3. `ComposedPrompt` assembly order matches declaration order
  4. Empty layer skipped (not emitted as blank section)
  5. Dimension label present for each layer in composed output

**Verified**: 22/22 unit tests passing. All 9 builders produce correctly structured strings. `ComposedPrompt` assembles in declared order with `# [Dimension: ClassName]` prefixes. `_dimension` attribute is the M4.1 GNN seed source for `FrameworkLayer` node classification.

---

## Milestone 2 — Layer 1 PoC: Single Agent, Structure Only ✓

**What is being proven**: a structure layer alone (COSTAR) is sufficient to ground the Spec Advisor's core task — selecting a spec language. Establishes the baseline all subsequent layers are measured against.

- [x] `src/agents/schemas.py` — `SpecAdvisorOutput`: `selected_lang`, `layer`, `justification`, `confidence`
- [x] `src/agents/spec_advisor.py` — `SpecAdvisorAgent` with **COSTAR only** (no CoT, no CAI yet)
  - System prompt: `ComposedPrompt([COSTARPrompt(...)]).build()`
  - Forced tool-use (`tool_choice={"type": "any"}`) returning `SpecAdvisorOutput` — see ADR-004
- [x] Minimal pipeline: `spec_advisor → show_output → END`
- [x] `tests/test_m2_spec_advisor.py` — 10 tests:
  - Input: "CRUD todo app" → selected_lang is JSON Schema or OpenAPI
  - Input: "multi-region e-commerce with eventual consistency" → selected_lang is TLA+ or CML
  - Both: justification present and non-empty; confidence in [0.0, 1.0]; layer in valid set; selections differ

**Success criteria** (gate to M3):
> Spec Advisor selects different languages for projects of different complexity.
> Justification is coherent. Baseline selection quality recorded for comparison.

**Verified**: 10/10 unit tests passing. M1 regression clean (22/22).

*Simple brief (CRUD todo app)*: `OpenAPI`, `api` layer, confidence **0.97**. Justification cited: multi-endpoint REST contract, HTTP methods, request/response payload schemas, PostgreSQL-backed data shapes. Explicitly ruled out TLA+/CML/Alloy/Event-B as unnecessary for this complexity level.

*Complex brief (multi-region e-commerce, eventual consistency, CQRS)*: `TLA+`, `system` layer, confidence **0.95**. Justification cited: multi-region network partitions, convergence proofs via temporal logic, CQRS async event pipelines, distributed inventory safety (stock never goes negative under concurrent deduction).

**M2 baseline** (anchor for M3 comparison): single-paragraph justification, no step-by-step candidate evaluation, no reasoning trace visible in output. M3 will diff against this.

**Lessons / ADR triggers**:
- COSTAR `Audience` field is load-bearing for spec language selection: framing output as "consumed by Spec Specialist" causes the model to reason about downstream needs, not just surface plausibility.
- Enumerating available spec languages in `Context` with brief use-case descriptors is essential — without it the model invents non-canonical names.
- `tool_choice="auto"` intermittently skips the tool call on simple inputs → `{"type": "any"}` with a single tool. Promoted to ADR-004.

**GNN seed values** (fixes M4.1 null gap): `m2_simple.confidence = 0.97`, `m2_complex.confidence = 0.95`. These are the M2 baseline node features for `REASONING_ADDS` edge delta computation at M4.1.

---

## Milestone 3 — Layer 2 PoC: Add Reasoning ✓

**What is being proven**: adding a Chain of Thought layer to the Spec Advisor makes its selection reasoning visible and auditable. Quality should improve or stay equal — never regress.

- [x] Add `ChainOfThought` layer to `SpecAdvisorAgent`
  - Steps: identify layer concerns → evaluate candidates → select + justify
- [x] `SpecAdvisorOutput` extended: add `reasoning_steps: list[str]` field
- [x] `tests/test_m2_spec_advisor.py` extended:
  - `reasoning_steps` is non-empty and contains ≥3 steps
  - Each step references a specific concern or candidate language
  - Selection quality ≥ M2 baseline (same test inputs, compare justification depth)

**Success criteria** (gate to M4):
> Reasoning steps are visible, auditable, and reference specific layer concerns.
> Selection quality is equal to or better than M2 baseline.

**Verified**: 41/41 tests passing (22 M1 + 10 M2 + 8 M3 — clean M1 regression).

Composition pattern: `COSTARPrompt → ChainOfThought`. Layers are assembled independently by `ComposedPrompt` — CoT is appended as a peer section, not injected into or wrapping COSTAR. The coupling is deliberate: COSTAR's `response_format` field instructs the model to populate `reasoning_steps` in the tool call; the CoT section provides the step-by-step scaffold. Two independent layers, one explicit handoff.

*Simple brief (CRUD todo app)*: OpenAPI, api layer, confidence 0.95. Produced 5 reasoning steps. Steps explicitly evaluated: JSON Schema (dismissed — lacks endpoint semantics), OpenAPI (selected — covers full REST surface: endpoints + schemas + status codes in one artefact), TLA+/CML/Alloy/Event-B (dismissed — no concurrency, safety-critical, or relational invariant concerns present). The reasoning correctly identified the absence of concerns as signal, not just the presence.

*Complex brief (multi-region e-commerce, eventual consistency, CQRS event sourcing)*: TLA+, system layer, confidence 0.93. Produced 8 reasoning steps. Per-concern evaluation:
- Eventual consistency → TLA+ (temporal logic over asynchronous replica convergence) vs Event-B (refinement overhead unjustified without certification requirement)
- CQRS event sourcing → TLA+ (command handlers + event log + read-model projections as interleaved state machines with ordering/idempotency constraints) vs CML (session protocols — covers choreography but lacks global invariant assertion)
- Distributed inventory (no-oversell invariant, liveness) → TLA+ (global `inventory ≥ 0` across replicas + liveness proof) vs Alloy (structural snapshots only — no temporal operators for convergence liveness)
- API surface → deferred to api/component layer; not dominant concern at system layer

Quality delta vs M2 baseline: M2 justification was a single-paragraph conclusion. M3 justification is grounded in explicit per-concern reasoning visible in the output schema — the model showed its working, not just its answer. The complex brief confidence dropped slightly (M2: 0.95 → M3: 0.93) reflecting genuine epistemic humility about whether liveness proofs could be descoped. The simple brief also dropped slightly (M2: 0.97 → M3: 0.95). Both deltas are −0.02 — consistent pattern: adding reasoning steps surfaces uncertainty the structure-only pass concealed.

Artifacts: `tests/artifacts/m3_simple.json`, `tests/artifacts/m3_complex.json`.

---

## Milestone 4 — Layer 3 PoC: Add Verification ✓

**What is being proven**: the Constitutional AI critique-revision loop improves low-quality outputs and passes high-quality ones through. The loop is the self-correcting gate.

- [x] Add `ConstitutionalAI` layer to `SpecAdvisorAgent`
  - Criteria: justification references specific layer concerns, confidence ≥ 0.7, candidate evaluation present
- [x] `SpecAdvisorOutput` extended: `revised: bool`, `revision_notes: str`
- [x] `tests/test_m2_spec_advisor.py` extended:
  - **Regression test**: intentionally weak input (vague project brief) → `revised=True`, output improves
  - **Pass-through test**: strong input → `revised=False`, output unchanged
  - All M2 and M3 tests still pass (no regression)

**Success criteria** (gate to M5):
> CAI gate demonstrably revises weak outputs. Strong outputs pass through unchanged.
> No regression in M2/M3 test cases.

**Verified**: 27/27 tests passing (23 M1 + 18 M2/M3 + 9 M4 — clean regression). Composition chain: `COSTARPrompt → ChainOfThought → ConstitutionalAI`.

*Vague brief ("an app")*: OpenAPI, api layer, confidence 0.30, `revised=True`. CAI principle 3 triggered — brief had fewer than 2 concrete technical signals. Model lowered confidence from initial to 0.30, added explicit assumption inventory (REST interface, API contract as spec artefact), and flagged both assumptions as unvalidated. `revision_notes` explains the principle triggered and what changed.

*Simple brief (CRUD todo app)*: OpenAPI, api layer, confidence 0.95, `revised=False`. 7 reasoning steps. All CAI principles satisfied on first pass — brief supplies REST API and PostgreSQL as concrete signals.

*Complex brief (multi-region e-commerce)*: TLA+, system layer, confidence 0.95, `revised=False`. 8 reasoning steps. All CAI principles satisfied — eventual consistency, CQRS event sourcing, and distributed inventory are 3+ concrete technical signals with named candidate evaluation.

Pass-through semantics confirmed: strong inputs are unchanged by the CAI gate; `revision_notes` is empty. The gate only fires when the brief fails the underspecification threshold.

Artifacts: `tests/artifacts/m4_simple.json`, `tests/artifacts/m4_complex.json`, `tests/artifacts/m4_vague.json`.

---

## Milestone 4.1 — GraphRAG / GNN PoC: PE Evolution Captured and Queryable

**What is being proven across M4.1 M0–M4**: the GNN substrate is not architectural intent — it is a
running, queryable graph. Each sub-milestone seeds one milestone's own subgraph into Kuzu, then Claude
writes cross-schema comparison edges (the ML signal) and `AnalysisNote` nodes (Claude's analytical
decisions). The sub-milestones are structured to mirror the Spec Council milestones: one GNN pass per
proven layer.

Until all sub-milestones pass, the *Graph Architecture — GNN First* section above is a claim, not a fact.

**Pattern (established in M4.1 M0)**: each milestone owns `src/milestones/m{N}/graph/` with its own
schema and runner. `python3 -m src.milestones.m{N}.run` seeds one subgraph per invocation. Claude
analyzes via ad-hoc scripts, decides signals, writes `AnalysisNote` nodes on the fly.
`analysis_opportunities.md` at repo root is the cross-session grounding document.

---

### M4.1 M0 — GNN Grounding ✓

**What is being proven**: the architectural pattern for all M4.1 sub-milestones — self-contained
milestone layout, `MilestoneRun` subgraph model, runner CLI, Claude-in-loop `AnalysisNote` feedback,
`analysis_opportunities.md` as cross-session grounding. No unified schema. No artifact files.

- [x] Self-contained milestone layout established: `src/milestones/m{N}/{run.py,frameworks/,graph/schema.py,graph/runner.py,tests/}`
- [x] `MilestoneRun` anchor pattern: `(Node {id: "{run_id}:{name}"})-[:CAPTURED_IN]->(MilestoneRun)`
- [x] Runner CLI: `python3 -m src.milestones.m{N}.run [run-id]` — one invocation = one subgraph; run N times for N subgraphs
- [x] Gate test isolation: ephemeral tmp Kuzu DB, never writes to persistent `data/kuzu`
- [x] `AnalysisNote` pattern: `CREATE NODE TABLE IF NOT EXISTS` on the fly; `ANALYZED` rel edges; schema invented per session
- [x] `analysis_opportunities.md` created — OPP-1–OPP-7, H1–H5, Cypher queries ready to run
- [x] Claude's analytical role documented in `CLAUDE.md` — code captures raw features; Claude decides signals

**Verified**: pattern proven working. Gate test isolation confirmed. Persistent DB and ephemeral DB coexist without collision.

---

### M4.1 M1 — M1 Run and Analysis ✓

**What is being proven**: 9 framework builders are real `FrameworkLayer` nodes in the GNN. Multiple runs
accumulate as distinct subgraphs. Claude-in-loop analysis surfaces real signals from the live graph
and writes them back as `AnalysisNote` nodes.

- [x] `src/milestones/m1/graph/schema.py` — `MilestoneRun`, `FrameworkLayer`, `CAPTURED_IN` tables
  - `FrameworkLayer` PK: `"{run_id}:{name}"` — 9 nodes per run, all 9 dimensions captured
  - Raw features: `name`, `dimension`, `build_output`, `file_path`, `file_hash`, `file_size_bytes`, `build_time_ms`, `output_char_count`, `output_token_est`
- [x] `src/milestones/m1/graph/runner.py` — `extract()`, `seed(conn, run_id, model) → str`, `dump()` (dev util only)
- [x] `src/milestones/m1/run.py` — `python3 -m src.milestones.m1.run [run-id] [--model MODEL]`
- [x] `src/milestones/m1/tests/test_m1.py` — 11 tests: 8 gate + 2 ML-pass print-only; ephemeral DB; all scoped by `run_id`
- [x] 3 CLI runs executed; persistent DB accumulated 3 subgraphs
- [x] Claude-in-loop analysis: ad-hoc Cypher queries issued; ConstitutionalAI timing outlier identified (8.8× variance); FewShot most consistent (0.8×); noise floor established at 0.050ms
- [x] `AnalysisNote` nodes + `ANALYZED` edges written: 12 nodes, 108 edges

**Verified**: 11/11 gate tests passing. Persistent DB: 3 MilestoneRun + 27 FrameworkLayer + 27 CAPTURED_IN + 12 AnalysisNote + 108 ANALYZED.

Confirmed signals:
- ConstitutionalAI: 8.8× timing variance ratio; anomaly threshold `range > 0.040ms`
- FewShot: 0.8× variance ratio — most consistent builder
- Noise floor: max 0.050ms — M2+ ML signal is LLM latency, not build_time_ms
- Full determinism: `build_output` and `file_hash` identical across all 3 runs

---

### M4.1 M2 — M2 Run and Analysis

**What is being proven**: M2 Spec Advisor calls (COSTAR only — the M2 composition, not the current M4 agent)
are captured as `SpecRun` nodes. Claude queries confidence distribution and latency across runs.
OPP-3 (COSTAR baseline) becomes testable.

**Note**: `src/agents/spec_advisor.py` is currently the M4 composition (COSTAR + CoT + CAI).
The M2 composition (COSTAR only, 4-field schema) must be restored from git commit `05f373d`
and frozen in `src/milestones/m2/` — the milestone is self-contained and never imports from `src/agents/`.

- [x] Restore M2 agent from git: `git show 05f373d:src/agents/spec_advisor.py` → `src/milestones/m2/agent.py`
  - Tag: `# [M2-origin | src/agents/spec_advisor.py @ 05f373d]`
  - Composition: COSTAR only — no CoT, no CAI
  - Tool schema: 4 fields only (`selected_lang`, `layer`, `justification`, `confidence`)
- [x] Restore M2 schema from git: `git show 05f373d:src/agents/schemas.py` → `src/milestones/m2/schema.py`
  - Tag: `# [M2-origin | src/agents/schemas.py @ 05f373d]`
  - 4 fields: `selected_lang`, `layer`, `justification`, `confidence` — no `reasoning_steps`, `revised`, `revision_notes`
- [x] Copy framework builders into `src/milestones/m2/frameworks/`:
  - `costar.py`, `composed.py` — tagged `[M2-copy | milestones/m1/frameworks/<name>.py]`
- [x] `src/milestones/m2/graph/schema.py` — `SpecRun` node table + `SPEC_CAPTURED_IN` rel:
  - `run_id`, `milestone`, `brief_label`, `selected_lang`, `layer`, `confidence`, `justification_char_count`, `latency_ms`, `model`, `timestamp`; PK: `"{run_id}:{brief_label}"`
  - Note: M2 uses `SPEC_CAPTURED_IN (FROM SpecRun TO MilestoneRun)` — Kuzu 0.11.3 cannot add a second FROM type to an existing rel table, so M2 owns a distinct anchoring rel name
- [x] `src/milestones/m2/graph/runner.py` — `seed(conn, output, brief_label, run_id, model, latency_ms)` — one `SpecRun` per call; `SPEC_CAPTURED_IN` to `MilestoneRun`
- [x] `src/milestones/m2/run.py` — `python3 -m src.milestones.m2.run [run-id] [--model MODEL]`
  - Imports from `src.milestones.m2.agent` — NOT `src.agents.spec_advisor`
  - Calls M2 agent for simple + complex briefs; seeds both `SpecRun` nodes
- [x] `src/milestones/m2/tests/test_m2_gnn.py` — 12 gate tests (ephemeral DB), all passing:
  - `SpecRun` present with `milestone='m2'`, `confidence` in [0, 1], `latency_ms > 0`
  - Simple brief → `selected_lang` in `{OpenAPI, JSON Schema}`; complex → `selected_lang` in `{TLA+, CML}`
  - `justification_char_count > 0`; node ids scoped to run; layer values valid
- [x] Claude-in-loop: run 3× via CLI; query confidence distribution, latency; write `AnalysisNote` for signals found
  - 5 AnalysisNote nodes: `m2-lang-determinism`, `m2-confidence-baseline`, `m2-latency-cold-start`, `m2-latency-warm-baseline`, `m2-justification-density`
  - 30 ANALYZED_SPEC + 20 ANALYZED_RUN edges written
  - New rel tables: `ANALYZED_SPEC (FROM AnalysisNote TO SpecRun)`, `ANALYZED_RUN (FROM AnalysisNote TO MilestoneRun)`
- [x] Update `analysis_opportunities.md`: M2 section added; OPP-3 baseline established; H6/H7/H8 added

**Success criteria** (gate to M4.1 M3):
> M2 composition frozen in milestone folder. `SpecRun` nodes seeded from live M2 agent calls.
> Claude-in-loop analysis surfaces ≥1 persisted signal. M1 regression clean.

**Verified** (2026-06-12): 12/12 gate tests passing. 3 CLI runs seeded. 5 signals persisted to GNN.
M1 regression: 11/11 clean. M4.1 M2 is **proven** — gate to M4.1 M3 is open.

---

### M4.1 ETL — Kuzu Schema Migration Infrastructure

**What is being proven**: the ETL migration infrastructure works end-to-end. As the GNN substrate
grows across milestones, schema changes to existing tables (new columns, type changes, new rel
FROM/TO types) require a blue-green DB rotation — Kuzu has no `ALTER TABLE`. This milestone
establishes the tooling so future schema evolution is a managed, documented, reversible operation.

**Design** (`docs/foundations/kuzu_etl_strategy.md`):

Each milestone that changes an existing table owns a `migration/` directory:

```
src/milestones/m{N}/migration/
  meta.json          ← {source_milestone, target_milestone, reseed_tables}
  schema.cypher      ← complete DDL snapshot at milestone N (diff target + new DB creation)
  transform.cypher   ← all migration queries in sequence (executable + intent)
```

`transform.cypher` uses Kuzu's `COPY (Cypher WITH transforms) TO parquet` — transforms happen
in Cypher, no Python intermediary for structural changes. Comments carry the WHY (default
choices, backfill rationale, cross-milestone comparability warnings). The `WITH` clause
documents source schema (`n.col AS col`) and target additions (`0 AS new_col`) in the query
structure itself.

`schema.cypher` is the snapshot — `diff schema.cypher` between any two milestones gives the
full schema evolution without delta accumulation.

**ETL runner** (`src/etl/`):
- `migrate.py` — `python3 -m src.etl.migrate --to m{N} [--dry-run]`
- `diff.py` — `python3 -m src.etl.diff m1 m2` (compares `schema.cypher` files)

**Migration sequence** (migrate.py):
1. Read `meta.json` → resolve source/target milestone
2. Execute each `COPY (...) TO '{tmp}/Table.parquet'` block from `transform.cypher`
3. Create new empty DB from `schema.cypher`
4. `COPY TableName FROM parquet` — nodes first, rels second
5. Re-seed `reseed_tables` (deterministic tables — e.g. `FrameworkLayer`)
6. Verify: row counts, FK spot-checks, gate tests against new DB path
7. Rotate: `data/kuzu → data/kuzu_bak_YYYYMMDD`, new DB → `data/kuzu`

**Tasks**:

- [ ] `src/etl/__init__.py`
- [ ] `src/etl/migrate.py` — CLI orchestrator: parse `transform.cypher`, execute COPY blocks,
      create new DB from `schema.cypher`, bulk load Parquet, re-seed, verify, rotate
- [ ] `src/etl/diff.py` — parse `schema.cypher` from two milestone migration dirs,
      diff CREATE TABLE statements, output structured summary
- [ ] `src/milestones/m1/migration/` — baseline (m1 is the origin, no prior schema)
  - `meta.json`: `{"source_milestone": null, "target_milestone": "m1", "reseed_tables": ["FrameworkLayer"]}`
  - `schema.cypher`: `MilestoneRun`, `FrameworkLayer`, `CAPTURED_IN` DDL
  - `transform.cypher`: identity queries (m1 is baseline — no transform needed, documents the starting schema)
- [ ] `src/milestones/m2/migration/` — m1 → m2 (adds `SpecRun`, `AnalysisNote`, all rel tables)
  - `meta.json`: `{"source_milestone": "m1", "target_milestone": "m2", "reseed_tables": ["FrameworkLayer"]}`
  - `schema.cypher`: all tables at m2
  - `transform.cypher`: identity for `MilestoneRun`; new-table queries for `SpecRun`, `AnalysisNote`
- [ ] `tests/etl/test_etl.py` — gate tests (ephemeral DBs):
  - `transform.cypher` executes without error against a seeded source DB
  - `schema.cypher` creates a valid new DB (all tables present, correct column types)
  - Row counts in new DB match source after full migration pipeline
  - `diff m1 m2` lists `SpecRun`, `AnalysisNote` as NEW; `MilestoneRun`, `FrameworkLayer` as UNCHANGED
  - `--dry-run` produces Parquet files but does not create or rotate the new DB

**Success criteria** (gate to M4.1 M3):
> `python3 -m src.etl.migrate --to m2 --dry-run` completes without error.
> Full migrate pipeline round-trips m1 → m2 with correct row counts and no data loss.
> `python3 -m src.etl.diff m1 m2` reports correct NEW/UNCHANGED classification.
> Gate tests green. Existing M1+M2 gate tests unaffected (persistent DB untouched).

---

### M4.1 M3 — M3 Run and Analysis

**What is being proven**: M3 SpecRun nodes are seeded and the delta against M2 is captured as a
`REASONING_ADDS` cross-schema edge. H1 (CoT token density → reasoning depth) and H5 (delta dominated
by CoT 175-token contribution) are resolved from live data. OPP-1 runs as a live query.

**Note**: restore M3 composition (COSTAR + CoT, no CAI) from git commit `48a5b37` →
`src/milestones/m3/agent.py` `[M3-origin | src/agents/spec_advisor.py @ 48a5b37]`.
M3 schema adds `reasoning_steps: list[str]` — restore from the same commit.
Copy framework builders: `costar.py`, `chain_of_thought.py`, `composed.py` as `[M3-copy]`.

- [ ] Restore M3 agent + schema from git `48a5b37` into `src/milestones/m3/`
- [ ] `src/milestones/m3/graph/schema.py` — `SpecRun` extended with `reasoning_step_count`, `evaluation_depth`; `REASONING_ADDS` rel table:
  - FROM `SpecRun` (m2) TO `SpecRun` (m3): `confidence_delta`, `step_count`, `evaluation_depth`, `adds_candidate_rejection`
- [ ] `src/milestones/m3/graph/runner.py` — seeds M3 `SpecRun` + `REASONING_ADDS` edge from matched M2 `SpecRun` (same brief label)
- [ ] `src/milestones/m3/run.py` — calls live M3 Spec Advisor (COSTAR+CoT); links to most recent M2 run for same brief
- [ ] `src/milestones/m3/tests/test_m3_gnn.py` — gate tests (ephemeral DB):
  - `SpecRun` has `reasoning_step_count ≥ 3` and `evaluation_depth = per_concern`
  - `REASONING_ADDS` edge exists between M2 and M3 `SpecRun` for same brief label
  - `confidence_delta` on edge matches `confidence_m3 - confidence_m2`
- [ ] Claude-in-loop: run OPP-1 query; resolve H1 and H5 from real graph data; write `AnalysisNote`
- [ ] Update `analysis_opportunities.md`: H1 and H5 updated to `confirmed` or `refuted`

**Success criteria** (gate to M4.1 M4):
> `REASONING_ADDS` cross-schema edges exist with delta properties. OPP-1 query returns results.
> H1 + H5 resolved with graph evidence. M1+M2 regression clean.

---

### M4.1 M4 — M4 Run and Analysis + First Topology Query

**What is being proven**: M4 `RevisionEvent` nodes and `VERIFICATION_ADDS` cross-schema edges are
seeded. The first topology-based GNN retrieval is proven — given a run profile, the graph returns
the structurally most similar prior run by traversing cross-schema edges, not by keyword.

**Note**: restore M4 composition (COSTAR + CoT + CAI) from git commit `a966ce9` →
`src/milestones/m4/agent.py` `[M4-origin | src/agents/spec_advisor.py @ a966ce9]`.
M4 schema adds `revised: bool`, `revision_notes: str` — restore from the same commit.
Copy framework builders: `costar.py`, `chain_of_thought.py`, `constitutional_ai.py`, `composed.py` as `[M4-copy]`.

- [ ] Restore M4 agent + schema from git `a966ce9` into `src/milestones/m4/`
- [ ] `src/milestones/m4/graph/schema.py` — `RevisionEvent` node table; `VERIFICATION_ADDS` rel table:
  - `RevisionEvent`: `run_id`, `brief_label`, `revised`, `cai_principle_triggered`, `assumption_inventory_added`
  - `VERIFICATION_ADDS` FROM M3 `SpecRun` TO M4 `SpecRun`: `revised`, `confidence_delta`, `cai_principle_triggered`, `signal_count_below_threshold`, `assumption_inventory_added`
- [ ] `src/milestones/m4/graph/runner.py` — seeds `RevisionEvent` + `VERIFICATION_ADDS` edge from matched M3 `SpecRun`
- [ ] `src/milestones/m4/run.py` — calls live M4 Spec Advisor for all three briefs (simple, complex, vague)
- [ ] `src/milestones/m4/tests/test_m4_gnn.py` — gate tests (ephemeral DB):
  - `RevisionEvent`: `revised=True` for vague brief, `revised=False` for strong briefs
  - `VERIFICATION_ADDS` edge exists with correct `confidence_delta` and `cai_principle_triggered`
  - Vague brief `SpecRun` has no incoming `REASONING_ADDS` — topological asymmetry preserved
  - **First GNN query** (topology-based retrieval): given `{revised=False, step_count ≥ 5, evaluation_depth=per_concern}`, traverse `REASONING_ADDS` + `VERIFICATION_ADDS`; assert result is `m4_complex` or `m3_complex`, not `m4_vague`
- [ ] Claude-in-loop: run OPP-2 (CAI revision rate), OPP-5 (cross-milestone token stack); resolve H4; write `AnalysisNote`
- [ ] Update `analysis_opportunities.md`: OPP-2, OPP-5 completed; H4 resolved

**Success criteria** (gate to M5):
> `VERIFICATION_ADDS` cross-schema edges seeded with delta properties. Vague brief topological asymmetry preserved.
> Topology-based retrieval returns structurally correct result. CAI revision rate measured, H4 resolved.
> M1+M2+M3 regression clean.

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

| Date | Decision | Reason |
|---|---|---|
| 2026-06-12 | CAI principle 3 encodes the underspecification threshold as a deterministic rule | "Fewer than two concrete technical signals → revised=True + confidence < 0.75" gives the test a reliable trigger without depending on the model's self-assessment of vagueness. The threshold is a quality criterion (epistemic honesty), not a procedural rule — CAI's purpose is to force the model to surface its uncertainty rather than hide it behind a confident-sounding but assumption-driven selection. |
| 2026-06-12 | CoT steps scaffold reasoning; COSTAR `response_format` is the handoff | CoT and COSTAR are assembled as peer sections by `ComposedPrompt` — no wrapping or mutation. COSTAR's `response_format` field is the only coupling: it names `reasoning_steps` as a required tool field. This makes the handoff explicit and both layers independently testable. |
| 2026-06-12 | CoT layer elicits per-concern candidate evaluation, not just a conclusion | M3 artifact showed the model evaluating TLA+ vs Event-B vs CML vs Alloy per-concern before selecting. M2 baseline produced a single-paragraph conclusion. The step scaffold ("for each concern, name candidates and evaluate fit") is what caused the richer evaluation — the model followed the scaffold literally. |
| 2026-06-12 | Forced tool-use (`tool_choice={"type":"any"}`) for all structured agent output | `"auto"` intermittently skips the tool call on simple inputs. Single tool per turn + `"any"` eliminates parse failures. See ADR-004 |
| 2026-06-12 | Streamlit dashboard as primary UI; Chainlit retained as stub | Streamlit milestone runner proved sufficient for M0 verification. Chainlit kept as interactive shell for M7+ agent chain wiring. Playwright (`pytest-playwright` + `pytest-base-url`) added as UI test layer alongside unit tests |
| 2026-06-11 | Named **Faber** | Latin: maker/artisan/architect. Guild-of-agents metaphor. "Homo faber" grounds the PE-first philosophy |
| 2026-06-11 | Composition over single-framework assignment | DSPy (2023) + ACL 2024 empirically prove composable chains outperform monolithic prompts. Each dimension is independently testable |
| 2026-06-11 | Systematic PoC execution by layer | Each layer proven before next built on it. Always-working set at every milestone. Regression caught immediately |
| 2026-06-11 | VOICE framework retired | Was a custom framework baking three dimensions into one. Replaced by: COSTAR (Structure) + Persona Prompting (Technique) + Constitutional AI (Verification) — all industry-standard |
| 2026-06-11 | SME Agent on COSTAR + Persona + CAI | COSTAR structures the output, Persona Prompting grounds the voice, CAI gates authenticity. Three industry-standard layers replacing one custom one |
| 2026-06-11 | Meta-prompting named explicitly | The Spec Advisor's primary product is a CRISPE prompt. This IS meta-prompting (Suzgun & Kalai 2024). Naming it makes the architecture self-documenting |
| 2026-06-11 | **ADR-003** — Constitutional AI as the universal verification gate | Every agent's composition chain ends with `ConstitutionalAI`. Principles are agent-specific and reference named fields and thresholds. Inline critique-revision (single API call) — not a separate LLM-as-judge call. M4 is the empirical test: if it shows no improvement on weak inputs, this decision must be revisited. See `docs/decisions/ADR-003_constitutional-ai-as-verification-layer.md` |
| 2026-06-12 | **ADR-004** — Forced tool-use (`tool_choice={"type":"any"}`) for all structured agent output | `"auto"` intermittently skips the tool call on simple inputs — discovered during M2 implementation. Single tool per turn + `"any"` eliminates silent parse failures. Additive schema pattern: `SpecAdvisorOutput` gains fields at M3/M4/M5 without breaking earlier tests. See `docs/decisions/ADR-004_forced-tool-use-for-structured-output.md` |
| deferred | **ADR-005** — Coordinator-gated deliberative consensus (pending M8) | Decision held back intentionally — better written when M8 proves it. Rationale must be grounded in empirical evidence from the retry/escalate loop, not upfront design intent. Write after M8 gate tests pass. |
| 2026-06-11 | Reflexion for SME Phase B multi-turn | Shinn et al. NeurIPS 2023 validates verbal episodic memory for multi-trial improvement without weight updates. Exact pattern needed for accumulating council responses |
| 2026-06-11 | Deliberative consensus (Coordinator-gated) | Spec quality at lower layers depends on correctness above. CLEAR + ReAct makes decisions auditable. Errors surface, not propagate |
| 2026-06-12 | Kuzu positioned as GraphRAG + GNN substrate, not a persistence layer | Derived from Senatus (agentic-gnn) (predecessor project from which Faber was forked). The architectural decision — Kuzu as a live R-GCN whose schema grows one layer per milestone — was established in Senatus (agentic-gnn) and carried forward. GraphRAG (Edge et al. 2024) and R-GCN (Schlichtkrull et al. 2018) are the grounding papers. |
| 2026-06-11 | Separate repo from Senatus (agentic-gnn) | Senatus (agentic-gnn) is the predecessor. It had the correct architectural instinct — agent council + Kuzu GraphRAG/GNN substrate — but its implementation was rigid and ad-hoc: hard-coded prompts, fixed pipelines, no ability to adapt to project complexity or learn across runs. Faber provides the PE framework grounding that transforms that prototype into a dynamic, adaptive, evolving system. Prompts are composed at runtime from orthogonal layers; the spec stack adapts depth to complexity; the GNN accumulates signal that improves future runs. The PE framework is what makes the graph substrate live rather than static. Shared: devcontainer/toolchain (M0), Kuzu graph substrate design. Faber's own: the entire composition model. |
