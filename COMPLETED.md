# Completed Milestones — Faber

Each section was proven against its explicit success criteria before the gate to the next
milestone opened. Evidence files (hypothesis · method · gate tests · deep analysis):
[`docs/evidence/`](docs/evidence/)

Status: all items here are `[x]` done and verified.

---

<a id="m0"></a>
## Milestone 0 — Infrastructure ✓

Goal: working devcontainer, Kuzu connected, Streamlit dashboard running, all deps installed.
Source: extracted and adapted from Senatus project.

- [x] Copy `.devcontainer/` from Senatus (`devcontainer.json`)
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

→ Evidence: [M00_infrastructure.md](docs/evidence/M00_infrastructure.md)

---

<a id="m1"></a>
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

→ Evidence: [M01_framework_builders.md](docs/evidence/M01_framework_builders.md)

---

<a id="m2"></a>
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

**Verified**: 10/10 unit tests passing. M1 regression clean (22/22).

*Simple brief (CRUD todo app)*: `OpenAPI`, `api` layer, confidence **0.97**. Justification cited: multi-endpoint REST contract, HTTP methods, request/response payload schemas, PostgreSQL-backed data shapes. Explicitly ruled out TLA+/CML/Alloy/Event-B as unnecessary for this complexity level.

*Complex brief (multi-region e-commerce, eventual consistency, CQRS)*: `TLA+`, `system` layer, confidence **0.95**. Justification cited: multi-region network partitions, convergence proofs via temporal logic, CQRS async event pipelines, distributed inventory safety (stock never goes negative under concurrent deduction).

**M2 baseline** (anchor for M3 comparison): single-paragraph justification, no step-by-step candidate evaluation, no reasoning trace visible in output. M3 will diff against this.

**Lessons / ADR triggers**:
- COSTAR `Audience` field is load-bearing for spec language selection: framing output as "consumed by Spec Specialist" causes the model to reason about downstream needs, not just surface plausibility.
- Enumerating available spec languages in `Context` with brief use-case descriptors is essential — without it the model invents non-canonical names.
- `tool_choice="auto"` intermittently skips the tool call on simple inputs → `{"type": "any"}` with a single tool. Promoted to ADR-004.

**GNN seed values** (fixes M4.1 null gap): `m2_simple.confidence = 0.97`, `m2_complex.confidence = 0.95`. These are the M2 baseline node features for `REASONING_ADDS` edge delta computation at M4.1.

→ Evidence: [M02_spec_advisor_structure.md](docs/evidence/M02_spec_advisor_structure.md)

---

<a id="m3"></a>
## Milestone 3 — Layer 2 PoC: Add Reasoning ✓

**What is being proven**: adding a Chain of Thought layer to the Spec Advisor makes its selection reasoning visible and auditable. Quality should improve or stay equal — never regress.

- [x] Add `ChainOfThought` layer to `SpecAdvisorAgent`
  - Steps: identify layer concerns → evaluate candidates → select + justify
- [x] `SpecAdvisorOutput` extended: add `reasoning_steps: list[str]` field
- [x] `tests/test_m2_spec_advisor.py` extended:
  - `reasoning_steps` is non-empty and contains ≥3 steps
  - Each step references a specific concern or candidate language
  - Selection quality ≥ M2 baseline (same test inputs, compare justification depth)

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

→ Evidence: [M03_reasoning_layer.md](docs/evidence/M03_reasoning_layer.md)

---

<a id="m4"></a>
## Milestone 4 — Layer 3 PoC: Add Verification ✓

**What is being proven**: the Constitutional AI critique-revision loop improves low-quality outputs and passes high-quality ones through. The loop is the self-correcting gate.

- [x] Add `ConstitutionalAI` layer to `SpecAdvisorAgent`
  - Criteria: justification references specific layer concerns, confidence ≥ 0.7, candidate evaluation present
- [x] `SpecAdvisorOutput` extended: `revised: bool`, `revision_notes: str`
- [x] `tests/test_m2_spec_advisor.py` extended:
  - **Regression test**: intentionally weak input (vague project brief) → `revised=True`, output improves
  - **Pass-through test**: strong input → `revised=False`, output unchanged
  - All M2 and M3 tests still pass (no regression)

**Verified**: 27/27 tests passing (23 M1 + 18 M2/M3 + 9 M4 — clean regression). Composition chain: `COSTARPrompt → ChainOfThought → ConstitutionalAI`.

*Vague brief ("an app")*: OpenAPI, api layer, confidence 0.30, `revised=True`. CAI principle 3 triggered — brief had fewer than 2 concrete technical signals. Model lowered confidence from initial to 0.30, added explicit assumption inventory (REST interface, API contract as spec artefact), and flagged both assumptions as unvalidated. `revision_notes` explains the principle triggered and what changed.

*Simple brief (CRUD todo app)*: OpenAPI, api layer, confidence 0.95, `revised=False`. 7 reasoning steps. All CAI principles satisfied on first pass — brief supplies REST API and PostgreSQL as concrete signals.

*Complex brief (multi-region e-commerce)*: TLA+, system layer, confidence 0.95, `revised=False`. 8 reasoning steps. All CAI principles satisfied — eventual consistency, CQRS event sourcing, and distributed inventory are 3+ concrete technical signals with named candidate evaluation.

Pass-through semantics confirmed: strong inputs are unchanged by the CAI gate; `revision_notes` is empty. The gate only fires when the brief fails the underspecification threshold.

Artifacts: `tests/artifacts/m4_simple.json`, `tests/artifacts/m4_complex.json`, `tests/artifacts/m4_vague.json`.

→ Evidence: [M04_verification_layer.md](docs/evidence/M04_verification_layer.md)

---

<a id="m41"></a>
## Milestone 4.1 — GraphRAG / GNN PoC: PE Evolution Captured and Queryable

**What is being proven across M4.1 M0–M4**: the GNN substrate is not architectural intent — it is a
running, queryable graph. Each sub-milestone seeds one milestone's own subgraph into Kuzu, then Claude
writes cross-schema comparison edges (the ML signal) and `AnalysisNote` nodes (Claude's analytical
decisions). The sub-milestones are structured to mirror the Spec Council milestones: one GNN pass per
proven layer.

Until all sub-milestones pass, the *Graph Architecture — GNN First* section in BACKLOG.md is a claim, not a fact.

**Pattern (established in M4.1 M0)**: each milestone owns `src/milestones/m{N}/graph/` with its own
schema and runner. `python3 -m src.milestones.m{N}.run` seeds one subgraph per invocation. Claude
analyzes via ad-hoc scripts, decides signals, writes `AnalysisNote` nodes on the fly.
`analysis_opportunities.md` at repo root is the cross-session grounding document.

---

<a id="m41-m0"></a>
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

<a id="m41-m1"></a>
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

<a id="m41-m2"></a>
### M4.1 M2 — M2 Run and Analysis ✓

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

**Verified** (2026-06-12): 12/12 gate tests passing. 3 CLI runs seeded. 5 signals persisted to GNN.
M1 regression: 11/11 clean. M4.1 M2 is **proven** — gate to M4.1 M3 is open.

→ Evidence: [M04_1_graphrag_gnn_poc.md — M2 section](docs/evidence/M04_1_graphrag_gnn_poc.md)

---

<a id="m41-etl"></a>
### M4.1 ETL — Kuzu Schema Migration Infrastructure ✓

**What is being proven**: the ETL migration infrastructure works end-to-end. As the GNN substrate
grows across milestones, schema changes to existing tables (new columns, type changes, new rel
FROM/TO types) require a blue-green DB rotation — Kuzu has no `ALTER TABLE`. This milestone
establishes the tooling so future schema evolution is a managed, documented, reversible operation.

**Design** (`docs/foundations/kuzu_etl_strategy.md`):

Each milestone that changes an existing table owns a `migration/` directory. Single-pass
milestones (one structural change, no mid-milestone schema evolution) use the flat layout.
Multi-pass milestones (schema evolved during Claude-in-loop analysis within the same milestone)
use the directory layout — each pass is fully self-contained:

```
── single-pass (M1, M2, M4) ──────────────────────────────────────────────
src/milestones/m{N}/migration/
  meta.json          ← {source_milestone, target_milestone, reseed_tables}
  schema.cypher      ← DDL snapshot at milestone N
  transform.cypher   ← migration queries

── multi-pass (M3+) ───────────────────────────────────────────────────────
src/milestones/m{N}/migration/
  meta.json          ← {source_milestone, target_milestone, reseed_tables, passes: N}
  pass_01/
    schema.cypher    ← DDL after pass 1
    transform.cypher ← M(N-1) → MN structural migration
  pass_02/
    schema.cypher    ← DDL after pass 2 (= current state when passes=2)
    transform.cypher ← MN → MN schema evolution (Claude-in-loop driven)
  ...
```

`meta.json["passes"]` is the source of truth for current state — `pass_{N}/` is always
the canonical schema and transform. `migrate.py` defaults to the latest pass automatically;
`--pass K` re-applies an earlier pass explicitly. `diff.py` resolves the schema for
comparison from `pass_{N}/schema.cypher` when passes are declared.

**Why multi-pass**: Claude-in-loop analysis may surface new signals that benefit from
richer schema mid-milestone (e.g. adding hypothesis-tracking columns to `AnalysisNote`
after the first few runs show what needs to be measured). A new pass directory captures
that evolution without disturbing the earlier proven pass. Earlier passes are never
modified — they are a stable grounding record of what was proven at each step.

`transform.cypher` uses Kuzu's `COPY (Cypher WITH transforms) TO parquet` — transforms
happen in Cypher. Comments carry WHY (default choices, backfill rationale, source schema
at the time of the pass). Each pass file is written for its specific source DB state.

**ETL runner** (`src/etl/`):
- `migrate.py` — `python3 -m src.etl.migrate --to m{N} [--pass K] [--dry-run]`
- `diff.py` — `python3 -m src.etl.diff m1 m2` (auto-resolves latest pass schema)

**Migration sequence** (migrate.py):
1. Read `meta.json` → resolve pass number (explicit `--pass K` or `meta["passes"]` for latest)
2. Execute each `COPY (...) TO '{tmp}/Table.parquet'` block from the resolved `transform.cypher`
3. Create new empty DB from the resolved `schema.cypher`
4. `COPY TableName FROM parquet` — nodes first, rels second
5. Re-seed `reseed_tables` (deterministic tables — e.g. `FrameworkLayer`)
6. Verify: row counts match source (tables new in target counted as 0 in source via try/except)
7. Rotate: `data/kuzu → data/kuzu_bak_YYYYMMDD`, new DB → `data/kuzu`

**Tasks**:

- [x] `src/etl/__init__.py`
- [x] `src/etl/migrate.py` — CLI orchestrator: parse `transform.cypher`, execute COPY blocks,
      create new DB from `schema.cypher`, bulk load Parquet, re-seed, verify, rotate.
      Multi-pass: `--pass K` selects `pass_KK/`; no `--pass` defaults to `meta["passes"]`
- [x] `src/etl/diff.py` — parse schema from two milestone migration dirs; auto-resolves latest
      pass via `meta.json["passes"]` when present; diffs CREATE TABLE statements (NEW/CHANGED/UNCHANGED)
- [x] `src/milestones/m1/migration/` — single-pass baseline (m1 is the origin, no prior schema)
  - `meta.json`: `{"source_milestone": null, "target_milestone": "m1", "reseed_tables": ["FrameworkLayer"]}`
  - `schema.cypher`: `MilestoneRun`, `FrameworkLayer`, `CAPTURED_IN` DDL
  - `transform.cypher`: identity queries (documents starting schema)
- [x] `src/milestones/m2/migration/` — single-pass, m1 → m2 (adds `SpecRun`, `AnalysisNote`, all rel tables)
  - `meta.json`: `{"source_milestone": "m1", "target_milestone": "m2", "reseed_tables": ["FrameworkLayer"]}`
  - `schema.cypher`: all tables at m2
  - `transform.cypher`: identity for `MilestoneRun`; new-table queries for `SpecRun`, `AnalysisNote`
- [x] `src/milestones/m3/migration/` — **multi-pass** (2 passes), m2 → m3:
  - `meta.json`: `{"source_milestone": "m2", "target_milestone": "m3", "reseed_tables": ["FrameworkLayer"], "passes": 2}`
  - `pass_01/`: M2 → M3 structural — `SpecRun` gains `reasoning_step_count`, `evaluation_depth`; `REASONING_ADDS` new; backfill M2 rows with `0 / 'unknown'`
  - `pass_02/`: M3 → M3 evolution — `AnalysisNote` gains `milestone`, `hypothesis_id`, `direction`, `metric_before`, `metric_after`; `SpecRun` reads existing M3 values directly (no data loss); `REASONING_ADDS` carried forward
- [x] `src/milestones/m4/migration/` — single-pass, m3 → m4 (SpecRun gains `revised`, `revision_notes`; adds `RevisionEvent`, `VERIFICATION_ADDS`)
  - `meta.json`: `{"source_milestone": "m3", "target_milestone": "m4", "reseed_tables": ["FrameworkLayer"]}`
  - `schema.cypher`: full DDL at m4
  - `transform.cypher`: backfill `revised=false`, `revision_notes=''` for M3 rows; carries `REASONING_ADDS` forward
- [x] `tests/etl/test_etl.py` — 25 gate tests (ephemeral DBs):
  - `transform.cypher` / pass directories execute without error against seeded source DBs (m2, m3)
  - `schema.cypher` creates valid DBs with correct tables and column types (m1–m4, and m3 pass_02)
  - Row counts match after full migration pipeline (m2, m3 pass 1, m3 pass 2, m3→m4)
  - `diff m1 m2` lists `SpecRun`, `AnalysisNote` as NEW; `MilestoneRun`, `FrameworkLayer` as UNCHANGED
  - `diff m2 m3` reports `SpecRun` as CHANGED, `REASONING_ADDS` as NEW (reads m3 pass_02 schema)
  - `diff m3 m4` reports `SpecRun` as CHANGED, `RevisionEvent` and `VERIFICATION_ADDS` as NEW
  - `--dry-run` produces Parquet files but does not create or rotate the new DB
  - Pass 2 preserves M3 `SpecRun` values; pass 1 applies hardcoded backfill

**Implementation notes**:
- `migrate.py` verify step uses try/except on source conn — tables new in target counted as 0 in source
- `diff.py` rel-table regex updated to match tables with properties (`REASONING_ADDS`, `VERIFICATION_ADDS`)
- `reseed_frameworks()` added to `m1/graph/runner.py` — called by ETL for FrameworkLayer reseed path
- `migrate.py` gracefully skips export of tables absent in source schema (e.g. `REASONING_ADDS` when migrating from M2)

**Verified** (2026-06-12): 25/25 ETL gate tests passing. 44/44 total tests clean (M1+M2+M3+ETL).
Migration files in place for m1–m4. M3 uses 2-pass directory layout. `diff.py` auto-resolves
latest pass schema. Gate to M4.1 M3 is open.

→ Strategy: [kuzu_etl_strategy.md](docs/foundations/kuzu_etl_strategy.md)

---

<a id="m41-m3"></a>
### M4.1 M3 — M3 Run and Analysis ✓

**What is being proven**: M3 SpecRun nodes are seeded and the delta against M2 is captured as a
`REASONING_ADDS` cross-schema edge. H1 (CoT token density → reasoning depth) and H5 (delta dominated
by CoT 175-token contribution) are resolved from live data. OPP-1 runs as a live query.
Schema evolution mid-milestone proves the multi-pass ETL pattern in practice.

**Note**: M3 composition (COSTAR + CoT, no CAI) restored from git commit `48a5b37` →
`src/milestones/m3/agent.py` `[M3-origin | src/agents/spec_advisor.py @ 48a5b37]`.
Framework builders tagged `[M3-copy]`. Milestone is fully self-contained — no imports from `src/agents/`.

- [x] `src/milestones/m3/migration/` — 2-pass directory layout (evolved during Claude-in-loop analysis)
- [x] Restore M3 agent + schema from git `48a5b37` into `src/milestones/m3/`
- [x] `src/milestones/m3/graph/schema.py` — `SpecRun` extended with `reasoning_step_count`, `evaluation_depth`; `REASONING_ADDS` rel table:
  - FROM `SpecRun` (m2) TO `SpecRun` (m3): `confidence_delta`, `step_count`, `evaluation_depth`, `adds_candidate_rejection`
- [x] `src/milestones/m3/graph/runner.py` — `infer_evaluation_depth(steps)` → `'per_concern'` if any step names a candidate language keyword, else `'conclusion_only'`; seeds M3 `SpecRun` + `REASONING_ADDS` edge from matched M2 `SpecRun` (same brief label)
- [x] `src/milestones/m3/run.py` — calls live M3 Spec Advisor (COSTAR+CoT); auto-selects most recent M2 run if `--m2-run-id` not given
- [x] `src/milestones/m3/tests/test_m3_gnn.py` — 19 gate tests (ephemeral DB):
  - `SpecRun` has `reasoning_step_count ≥ 3` and `evaluation_depth = per_concern`
  - `REASONING_ADDS` edge exists between M2 and M3 `SpecRun` for same brief label
  - `confidence_delta` on edge matches `confidence_m3 - confidence_m2`
  - ML pass: prints REASONING_ADDS delta profile table
- [x] Claude-in-loop: 3 CLI runs; H1, H5, H6, H7, H8 resolved; 6 `AnalysisNote` nodes written
- [x] `AnalysisNote` schema evolved mid-milestone (pass 2): added `milestone`, `hypothesis_id`, `direction`, `metric_before`, `metric_after` — proves multi-pass ETL in practice
- [x] `analysis_opportunities.md` updated: H1/H5/H6 confirmed, H7/H8 refuted, new signal added

**Confirmed signals (3-run analysis)**:

| Brief | Lang | Conf mean | Conf range | Steps mean | Depth |
|---|---|---|---|---|---|
| simple | OpenAPI | 0.977 | 0.010 | 6.67 | per_concern |
| complex | TLA+ | 0.970 | **0.000** | 8.67 | per_concern |

| Hypothesis | Result | Key evidence |
|---|---|---|
| H1 CoT density → reasoning depth | **confirmed** | 6/6 runs: `per_concern`, ≥5 named-candidate steps |
| H5 M2→M3 delta dominated by CoT (175 tokens) | **confirmed** | Budget: 115 → 290 = +175 exactly (COSTAR unchanged) |
| H6 CoT narrows complex conf_range (0.040 → <0.020) | **confirmed (exceeded)** | Complex range = **0.000** — all 3 runs: 0.970 exact |
| H7 Complexity-latency inversion persists at M3 | **refuted** | Complex 25,401ms > simple 22,814ms — reversed by CoT output volume |
| H8 M3 just_chars > M2 for complex only | **refuted** | simple +16.8% (761→889), complex −1.2% (1326→1310) |

New signal: `adds_candidate_rejection` asymmetry — simple always explicitly dismisses TLA+/Alloy;
complex often implicit (TLA+ dominance obvious, dismissal unstated). Lives on `REASONING_ADDS` edge.

**Verified** (2026-06-12): 19/19 gate tests passing. 44/44 total tests clean (M1+M2+M3+ETL).
3 CLI runs seeded. 6 `AnalysisNote` nodes written. Multi-pass ETL proven in practice (2 passes, M3).
Gate to M4.1 M4 is open.

→ Evidence: [M04_1_graphrag_gnn_poc.md](docs/evidence/M04_1_graphrag_gnn_poc.md)

---

<a id="m41-m4"></a>
### M4.1 M4 — M4 Run and Analysis + First Topology Query ✓

**What is being proven**: M4 `RevisionEvent` nodes and `VERIFICATION_ADDS` cross-schema edges are
seeded. The first topology-based GNN retrieval is proven — given a run profile
`{revised=False, step_count ≥ 5, evaluation_depth=per_concern}`, the graph returns the structurally
most similar prior run by traversing cross-schema edges, not by keyword. Vague brief topological
asymmetry confirmed: no incoming `VERIFICATION_ADDS` edge (no M3 counterpart), excluded by structure.

**Note**: M4 composition (COSTAR + CoT + CAI) restored from git `a966ce9` →
`src/milestones/m4/agent.py` `[M4-origin | src/agents/spec_advisor.py @ a966ce9]`.
Framework builders tagged `[M4-copy]`. Milestone self-contained — no imports from `src/agents/`.

- [x] `src/milestones/m4/migration/` — single-pass (m3 → m4): `SpecRun` gains `revised`, `revision_notes`; adds `RevisionEvent`, `VERIFICATION_ADDS`; backfills M3 rows with `false/''`. 12 tables verified.
- [x] Restore M4 agent + schema from git `a966ce9` into `src/milestones/m4/`
- [x] `src/milestones/m4/graph/schema.py` — `RevisionEvent` node; `VERIFICATION_ADDS` rel (5 edge props: `revised`, `confidence_delta`, `cai_principle_triggered`, `signal_count_below_threshold`, `assumption_inventory_added`)
- [x] `src/milestones/m4/graph/runner.py` — seeds `RevisionEvent` + optional `VERIFICATION_ADDS` edge from matched M3 `SpecRun` (simple/complex only — vague has no M3 counterpart)
- [x] `src/milestones/m4/run.py` — calls live M4 Spec Advisor for three briefs: simple, complex, vague; `--m3-run-id` auto-detects most recent M3 run
- [x] `src/milestones/m4/tests/test_m4_gnn.py` — 32 gate tests (ephemeral DB):
  - `RevisionEvent`: `revised=True` for vague, `revised=False` for simple/complex
  - `VERIFICATION_ADDS` edge with correct `confidence_delta` and `cai_principle_triggered`
  - Vague `SpecRun` has no incoming `REASONING_ADDS` — topological asymmetry preserved
  - **First GNN topology query**: `{revised=False, step_count≥5, depth=per_concern}` traverses `REASONING_ADDS|VERIFICATION_ADDS`; asserts vague NOT in results, complex IN results
- [x] Claude-in-loop: 3 CLI runs; OPP-2 (CAI revision rate), OPP-5 (token stack) analysed; H4 confirmed; 3 `AnalysisNote` nodes written
- [x] `analysis_opportunities.md` updated: OPP-2, OPP-5 closed; H4 confirmed

**Confirmed signals (3-run analysis)**:

| Brief | Lang | Revised | Conf mean | Conf range | Steps mean |
|---|---|---|---|---|---|
| simple | OpenAPI | False (0/3) | 0.963 | 0.020 | 7.0 |
| complex | TLA+ | False (0/3) | 0.963 | 0.020 | 8.0 |
| vague | OpenAPI | **True (3/3)** | **0.400** | 0.150 | 5.0 |

| Hypothesis | Result | Key evidence |
|---|---|---|
| H4 CAI revision rate < 30% when conf ≥ 0.7 | **confirmed** | simple+complex 0% revised (conf 0.95–0.97); vague 100% revised (conf 0.35–0.50) — binary split |

**VERIFICATION_ADDS deltas** (M3 → M4, clear briefs only): simple avg −0.017, complex avg −0.007. CAI does not inflate confidence for well-specified briefs.

**Token stack (OPP-5)**: COSTAR=115, CoT=175, CAI=162. M4 total = 452 tokens ≈ 24% of total API input per call (~1,892 tokens). Remaining 76% is tool schema + brief.

**Topological isolation**: vague `SpecRun` has no `VERIFICATION_ADDS` incoming edge — excluded from topology query by structure, not filter.

**Verified** (2026-06-13): 32/32 M4 gate tests passing. 74/74 total tests clean (M1+M2+M3+ETL+M4).
3 CLI runs seeded. 3 `AnalysisNote` nodes written. Migration: 12 tables verified, blue-green rotation clean.

→ Evidence: [M04_1_graphrag_gnn_poc.md](docs/evidence/M04_1_graphrag_gnn_poc.md)

---

<a id="m5"></a>
## Milestone 5 — Layer 4 PoC: Full Spec Advisor — Meta-Prompt Output ✓

**What is being proven**: the Spec Advisor (M4 chain: COSTAR + CoT + CAI, unchanged) can programmatically generate a CRISPE meta-prompt from its structured output. That prompt, injected into a Spec Specialist stub as its system prompt, produces a non-empty formal spec. All 6 CRISPE fields are populated for all 3 briefs. `META_PROMPT_ADDS` cross-schema edges cover all 3 briefs — first full cross-schema coverage in the chain.

- [x] `src/milestones/m5/agent.py` — `SpecAdvisorAgent` (M4 chain, unchanged) + `build_crispe_prompt(output)` post-LLM step
  - `capacity = "{selected_lang} specialist"`, `role` = fixed council role, `insight = output.justification`, `statement` = scoped to `output.layer`, `personality`/`experiment` = `CRISPEPrompt` defaults
  - CRISPE prompt appended to `SpecAdvisorOutput.specialist_crispe_prompt` (not from LLM call)
- [x] `src/milestones/m5/spec_specialist.py` — `SpecSpecialistAgent` stub: receives CRISPE string as system prompt; forced tool-use returns `SpecialistOutput`
- [x] `src/milestones/m5/schema.py` — `SpecAdvisorOutput` (M4 fields + `specialist_crispe_prompt`), `SpecialistOutput` (`spec_content`, `spec_lang`, `well_formedness_notes`, `confidence`)
- [x] `src/milestones/m5/graph/schema.py` — `MetaPromptEvent` node (CRISPE quality signals per brief per run), `META_PROMPT_ADDS` rel (FROM SpecRun m4 TO SpecRun m5), `ANALYZED_META` rel (FROM AnalysisNote TO MetaPromptEvent)
- [x] `src/milestones/m5/graph/runner.py` — `seed()` writes SpecRun + MetaPromptEvent + META_PROMPT_ADDS for all 3 briefs; `infer_crispe_field_count()`, `infer_capacity_matches_lang()`, `infer_insight_char_count()` helpers
- [x] `src/milestones/m5/migration/pass_01/` — adds `specialist_crispe_prompt STRING` to `SpecRun`; backfills `''` for pre-M5 rows
- [x] `src/milestones/m5/tests/test_m5.py` — 30 gate tests (ephemeral DB):
  - Schema: `MetaPromptEvent`, `META_PROMPT_ADDS`, `ANALYZED_META` tables exist
  - `specialist_crispe_prompt` non-empty for all 3 briefs
  - CRISPE prompt contains all 6 headers (`**Capacity**` … `**Experiment**`)
  - `crispe_field_count=6` for all 3 briefs; `capacity_matches_lang=True` for all 3
  - `insight_char_count > 50` for simple + complex; vague insight < complex
  - `META_PROMPT_ADDS` edge for all 3 briefs (first full coverage)
  - 3-hop topology (REASONING_ADDS → VERIFICATION_ADDS → META_PROMPT_ADDS): simple + complex reachable; vague absent
  - Integration test: `SpecSpecialistAgent` called with complex CRISPE → `spec_content` non-empty, `spec_lang == 'TLA+'`
- [x] ETL migration run: M4 → M5 blue-green rotation (15 tables verified; `MetaPromptEvent`/`META_PROMPT_ADDS`/`ANALYZED_META` new; `SpecRun` gains `specialist_crispe_prompt`)
- [x] Claude-in-loop: 3 CLI runs (`m5-20260613-224118`, `m5-20260613-224509`, `m5-20260613-224727`); 7 `AnalysisNote` nodes + 63 `ANALYZED_META` edges written
- [x] `analysis_opportunities.md` updated: M5 section added; OPP-4 deferred to M7; H2 deferred

**Verified** (2026-06-13): 30/30 M5 gate tests passing. 104/104 total tests clean (30 M5 + 74 prior). 3 CLI runs seeded. 7 signals persisted. ETL migration clean (15 tables verified after rotation).

**Confirmed signals (3-run analysis):**

| Brief | Lang | Layer | Conf mean | Conf range | Revised | CRISPE fc | insight_chars (avg) |
|---|---|---|---|---|---|---|---|
| complex | TLA+ | system | 0.950 | **0.000** | never | 6 | 1,222 |
| simple | OpenAPI | api | 0.950 | **0.000** | never | 6 | 851 |
| vague | OpenAPI | api | 0.400 | **0.000** | **always** | 6 | 754 |

_All 9/9 MetaPromptEvent nodes: `crispe_field_count=6`, `capacity_matches_lang=True`._

Key findings:
- **CRISPE is structurally invariant**: field_count=6 and capacity_match=True for 100% of runs/briefs.
- **Confidence zero-variance at M5**: 0.000 range for all 3 briefs — strongest confidence lock across all milestones (tighter than M4 vague: 0.150 range, and M3 simple: 0.010 range).
- **Insight section carries all brief-specific information**: Statement (194 chars, fixed) and Capacity (~16 chars, fixed template) are template-driven. Insight is the sole variable-length field.
- **Vague has 7× higher insight variance** than simple (207 vs 29 chars range) — low-signal briefs produce unstable justifications.
- **3-hop topology confirmed end-to-end**: REASONING_ADDS (M2→M3) → VERIFICATION_ADDS (M3→M4) → META_PROMPT_ADDS (M4→M5) reachable for simple + complex; vague absent by design (no VERIFICATION_ADDS input).
- **Real LLM behavior vs mocks**: vague brief selects OpenAPI/api in all real runs (both M4 and M5), not JSON Schema/domain as mock fixtures assumed.
- **Tool schema non-compliance**: SpecSpecialistAgent's `required` fields (`well_formedness_notes`, `confidence`) sometimes omitted by the LLM. Fixed with Pydantic defaults — `spec_content` + `spec_lang` are always returned.

→ Evidence: [M05_meta_prompt.md](docs/evidence/M05_meta_prompt.md)
