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

## Milestone 4.1 — GraphRAG / GNN PoC: PE Evolution Captured and Queryable

**Pattern (established in M4.1 M0)**: each milestone owns `src/milestones/m{N}/graph/` with its own
schema and runner. `python3 -m src.milestones.m{N}.run` seeds one subgraph per invocation. Claude
analyzes via ad-hoc scripts, decides signals, writes `AnalysisNote` nodes on the fly.
`analysis_opportunities.md` is the cross-session grounding document.

M4.1 M0–M3 proven. **Gate to M4.1 M4 is open.**

---

### M4.1 M4 — M4 Run and Analysis + First Topology Query

**What is being proven**: M4 `RevisionEvent` nodes and `VERIFICATION_ADDS` cross-schema edges are
seeded. The first topology-based GNN retrieval is proven — given a run profile, the graph returns
the structurally most similar prior run by traversing cross-schema edges, not by keyword.

**Note**: restore M4 composition (COSTAR + CoT + CAI) from git commit `a966ce9` →
`src/milestones/m4/agent.py` `[M4-origin | src/agents/spec_advisor.py @ a966ce9]`.
M4 schema adds `revised: bool`, `revision_notes: str` — restore from the same commit.
Copy framework builders: `costar.py`, `chain_of_thought.py`, `constitutional_ai.py`, `composed.py` as `[M4-copy]`.

- [x] `src/milestones/m4/migration/` — schema snapshot + transform (done as part of M4.1 ETL)
- [x] Restore M4 agent + schema from git `a966ce9` into `src/milestones/m4/`
- [x] `src/milestones/m4/graph/schema.py` — `RevisionEvent` node table; `VERIFICATION_ADDS` rel table:
  - `RevisionEvent`: `run_id`, `brief_label`, `revised`, `cai_principle_triggered`, `assumption_inventory_added`
  - `VERIFICATION_ADDS` FROM M3 `SpecRun` TO M4 `SpecRun`: `revised`, `confidence_delta`, `cai_principle_triggered`, `signal_count_below_threshold`, `assumption_inventory_added`
- [x] `src/milestones/m4/graph/runner.py` — seeds `RevisionEvent` + `VERIFICATION_ADDS` edge from matched M3 `SpecRun`
- [x] `src/milestones/m4/run.py` — calls live M4 Spec Advisor for all three briefs (simple, complex, vague)
- [x] `src/milestones/m4/tests/test_m4_gnn.py` — 32 gate tests (ephemeral DB):
  - `RevisionEvent`: `revised=True` for vague brief, `revised=False` for strong briefs
  - `VERIFICATION_ADDS` edge exists with correct `confidence_delta` and `cai_principle_triggered`
  - Vague brief `SpecRun` has no incoming `REASONING_ADDS` — topological asymmetry preserved
  - **First GNN query** (topology-based retrieval): given `{revised=False, step_count ≥ 5, evaluation_depth=per_concern}`, traverse `REASONING_ADDS` + `VERIFICATION_ADDS`; assert vague NOT in results, complex IN results
- [x] Claude-in-loop: 3 CLI runs; OPP-2 (CAI revision rate), OPP-5 (cross-milestone token stack) analysed; H4 confirmed; 3 `AnalysisNote` nodes written
- [x] Update `analysis_opportunities.md`: OPP-2, OPP-5 completed; H4 confirmed

**Success criteria** (gate to M5):
> `VERIFICATION_ADDS` cross-schema edges seeded with delta properties. Vague brief topological asymmetry preserved.
> Topology-based retrieval returns structurally correct result. CAI revision rate measured, H4 resolved.
> M1+M2+M3 regression clean.

---

## Milestone 5 — Layer 4 PoC: Full Spec Advisor — Meta-Prompt Output

**What is being proven**: the Spec Advisor (COSTAR + CoT + CAI — M4 chain, unchanged) generates a
CRISPE meta-prompt programmatically from its structured output. That prompt, injected into a Spec
Specialist stub as its system prompt, produces a non-empty formal spec. This is the meta-prompting
moment: the Advisor's output becomes another agent's system prompt.

**Composition note**: CLEAR is not added — COSTAR already fills the Structure slot (one-dimension rule).
The CRISPE prompt is assembled in code via `_build_crispe_prompt(output)` using the `CRISPEPrompt`
builder, not as a new composition layer.

**GNN contribution**: `MetaPromptEvent` node (CRISPE quality signals per brief) + `META_PROMPT_ADDS`
cross-schema edge (FROM M4 SpecRun TO M5 SpecRun). First milestone where all 3 briefs have a
cross-schema edge (vague was excluded from VERIFICATION_ADDS; M4 seeded it so M5 can link all 3).

- [ ] `src/milestones/m5/migration/` — multi-pass structure; pass_01 planned:
  - `meta.json`: `source_milestone=m4, target_milestone=m5, reseed_tables=["FrameworkLayer"], passes=1`
  - `pass_01/schema.cypher` — complete DB snapshot at M5 (all tables including new ones)
  - `pass_01/transform.cypher` — `SpecRun` gains `specialist_crispe_prompt STRING`;
    adds `MetaPromptEvent` node table, `META_PROMPT_ADDS` rel table, `ANALYZED_META` rel table;
    backfills `specialist_crispe_prompt = ''` for M0–M4 `SpecRun` rows
  - pass_02+ added ad-hoc during Claude-in-loop analysis if schema needs to evolve

- [ ] `src/milestones/m5/frameworks/` — copy from M4, add `crispe.py`:
  - `costar.py`, `chain_of_thought.py`, `constitutional_ai.py`, `composed.py`
    `[M5-copy | milestones/m4/frameworks/<name>.py]`
  - `crispe.py` `[M5-copy | src/frameworks/crispe.py]`

- [ ] `src/milestones/m5/schema.py` — `[M5-origin]`:
  - `SpecAdvisorOutput`: M4 fields + `specialist_crispe_prompt: str`
  - `SpecialistOutput`: `spec_content`, `spec_lang`, `well_formedness_notes`, `confidence`

- [ ] `src/milestones/m5/agent.py` — `[M5-origin]` `SpecAdvisorAgent`:
  - Composition: `COSTAR → ChainOfThought → ConstitutionalAI` (M4 chain, unchanged)
  - `_build_crispe_prompt(output) → str`: fills `CRISPEPrompt` from output fields
    (`capacity = "{selected_lang} specialist"`, `insight = justification`,
    `statement` scoped to layer; `role`, `personality`, `experiment` fixed)
  - `run()` appends `specialist_crispe_prompt` to output after the LLM call

- [ ] `src/milestones/m5/spec_specialist.py` — `[M5-origin]` `SpecSpecialistAgent` stub:
  - System prompt = injected CRISPE string at call time; no `ComposedPrompt` chain
  - Forced tool-use returning `SpecialistOutput`
  - Scoped to `m5/` only — promoted to `src/agents/` at M7

- [ ] `src/milestones/m5/graph/schema.py`:
  - `MetaPromptEvent` node: `id`, `run_id`, `brief_label`, `crispe_field_count`,
    `capacity_char_count`, `insight_char_count`, `statement_char_count`, `capacity_matches_lang`
  - `META_PROMPT_ADDS` rel (FROM `SpecRun` TO `SpecRun` — M4→M5, all 3 briefs):
    `crispe_field_count`, `prompt_char_count`, `capacity_matches_lang`
  - `ANALYZED_META` rel (FROM `AnalysisNote` TO `MetaPromptEvent`) — for Claude-in-loop

- [ ] `src/milestones/m5/graph/runner.py`:
  - `infer_crispe_field_count(prompt_str) → int`
  - `infer_capacity_matches_lang(capacity_str, selected_lang) → bool`
  - `infer_insight_char_count(prompt_str) → int`
  - `seed()`: `SpecRun` (milestone=`'m5'`) + `SPEC_CAPTURED_IN` + `MetaPromptEvent`;
    `META_PROMPT_ADDS` from M4 `SpecRun` → M5 `SpecRun` for all 3 briefs
  - `dump()` — dev utility, never called automatically

- [ ] `src/milestones/m5/run.py`:
  - 3 briefs → M5 `SpecRun` + `MetaPromptEvent` + `META_PROMPT_ADDS` from M4
  - `--m4-run-id` arg (auto-detects most recent M4 run)
  - Calls `SpecSpecialistAgent` for complex brief; prints `spec_content[:200]` as validation
  - Summary table: `brief | lang | layer | conf | crispe_fields | cap_matches | spec_len | ms`

- [ ] `src/milestones/m5/tests/test_m5.py` — ~30 gate tests (ephemeral DB, mock outputs, no LLM):
  - Schema creation: all new tables (`MetaPromptEvent`, `META_PROMPT_ADDS`, `ANALYZED_META`)
  - `SpecRun.specialist_crispe_prompt` non-empty for all 3 briefs
  - CRISPE prompt contains all 6 section headers
  - `capacity_matches_lang=True` for simple + complex; CRISPE quality degrades for vague
  - `insight_char_count > 50` for simple + complex; vague insight shorter than complex
  - `MetaPromptEvent` node per brief with correct properties (`crispe_field_count == 6`)
  - `META_PROMPT_ADDS` edge for **all 3 briefs** (first full cross-schema coverage)
  - Edge properties correct per brief
  - **3-hop topology query** (`REASONING_ADDS → VERIFICATION_ADDS → META_PROMPT_ADDS`):
    strong briefs in results; vague filtered structurally via `revised=True` on `VERIFICATION_ADDS`
  - 1 `@pytest.mark.integration`: `SpecSpecialistAgent` called with complex CRISPE →
    `spec_content` non-empty, `spec_lang` matches `selected_lang`
  - M1+M2+M3+ETL+M4 regression: 74 prior tests green

- [ ] Claude-in-loop: 3 CLI runs; ad-hoc Cypher analysis of `MetaPromptEvent` signals;
  `AnalysisNote` nodes written via `ANALYZED_META` edges using evolved schema
  (`milestone`, `hypothesis_id`, `direction`, `metric_before`, `metric_after`);
  add `pass_02` to migration if analysis surfaces new schema needs

- [ ] `docs/evidence/M05_meta_prompt.md` — create at start (hypothesis + method + gate tests);
  fill Result / Lessons / Next at milestone end

**Success criteria** (gate to M6):
> All 6 CRISPE fields present and non-empty for all 3 briefs. `capacity` mentions `selected_lang`.
> `insight` grounded in project brief (char count > 50 for non-vague).
> `META_PROMPT_ADDS` edge from M4→M5 `SpecRun` for all 3 briefs (complete cross-schema coverage).
> 3-hop topology query returns structurally correct result.
> `SpecSpecialistAgent` called with injected CRISPE returns non-empty `spec_content` with `spec_lang`
> matching `selected_lang`. 74 prior tests green.

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
