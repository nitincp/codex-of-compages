# M02 — Layer 1 PoC: Single Agent, Structure Only

**Layer:** 1 — Single agent, structure layer (COSTAR)  
**Milestone:** M2 in BACKLOG.md  
**Status:** Complete  
**Date started:** 2026-06-12  
**Date completed:** 2026-06-12

---

## Hypothesis

A Structure layer (COSTAR alone) is sufficient to ground the Spec Advisor's language selection
task — producing coherent, differentiated selections for projects of different complexity.
This establishes the baseline all subsequent layers are measured against.

---

## Method

Implemented `SpecAdvisorAgent` using `COSTARPrompt` as the sole composition layer.
Forced tool-use (`tool_choice={"type": "any"}`) returns a typed `SpecAdvisorOutput`
(Pydantic model: `selected_lang`, `layer`, `justification`, `confidence`).

The COSTAR prompt encodes: project context + available spec languages (Context), the selection
task (Objective), formal analytical style (Style/Tone), the Spec Specialist as consumer
(Audience), and the tool call schema (Response Format).

Two representative briefs chosen to span the complexity range:
- **Simple**: "CRUD todo app with REST API and a PostgreSQL backend"
- **Complex**: "multi-region e-commerce platform with eventual consistency, distributed inventory, and CQRS event sourcing"

See BACKLOG.md [M2 section](../../BACKLOG.md#milestone-2--layer-1-poc-single-agent-structure-only-) for full task list.

---

## Gate Tests

> Spec Advisor selects different languages for projects of different complexity.  
> Justification is coherent. Baseline selection quality recorded for comparison.
>
> Specific assertions in `tests/test_m2_spec_advisor.py`:
> - `"CRUD todo app"` → `selected_lang` in `{JSON Schema, OpenAPI, Pydantic}`
> - `"multi-region e-commerce with eventual consistency"` → `selected_lang` in `{TLA+, CML, Alloy, Event-B}`
> - Both: `justification` non-empty and > 20 characters
> - Both: `confidence` in [0.0, 1.0]
> - Both: `layer` in `{system, domain, component, api}`
> - `simple.selected_lang != complex.selected_lang`

---

## Result

Hypothesis confirmed.

10/10 gate tests passing. COSTAR alone is sufficient to drive differentiated, coherent selection.

**Simple project (CRUD todo app):**
- `selected_lang`: `OpenAPI`
- `layer`: `api`
- `confidence`: 0.97
- Justification cited: multi-endpoint REST contract, HTTP methods, request/response payload schemas, PostgreSQL-backed data shapes — explicitly ruled out TLA+/CML/Alloy/Event-B as unnecessary for this complexity level.

**Complex project (multi-region e-commerce, eventual consistency, CQRS):**
- `selected_lang`: `TLA+`
- `layer`: `system`
- `confidence`: 0.95
- Justification cited: multi-region network partitions, convergence proofs via temporal logic, CQRS async event pipelines, distributed inventory safety (stock never goes negative under concurrent deduction).

Both selections align with the theoretical grounding: JSON Schema / OpenAPI for API-surface concerns; TLA+ for distributed systems safety and liveness. Justifications are substantive and cite specific project characteristics, not generic rationale.

Artifacts at `tests/artifacts/`:
- `m2_simple.json` — full input + output for the CRUD brief
- `m2_complex.json` — full input + output for the distributed brief

---

## Lessons

- COSTAR's **Audience** field is load-bearing for spec language selection: framing the output as "consumed by the Spec Specialist, which generates formal specs" causes the model to reason about what the downstream agent actually needs, not just what sounds plausible.
- Enumerating the available spec languages in the **Context** field (with brief use-case descriptors) is essential — without it, the model invents plausible-sounding but non-canonical language names.
- `tool_choice={"type": "any"}` with a single tool reliably avoids text-mode responses. Do not use `"auto"` for structured output in agent chains — it will occasionally skip the tool call. This is now ADR-004.
- Confidence scores (0.95–0.97) are high for both cases. This is expected for a single-layer structure prompt with clear candidates — the M3 baseline comparison will be more meaningful once reasoning steps are visible.

---

## Next Layer Can Rely On

- `SpecAdvisorAgent.run(project_brief)` returns a validated `SpecAdvisorOutput` — safe to call from pipeline or test fixture.
- COSTAR-grounded selection is differentiated across complexity levels — M3 (CoT) can use the same two test briefs and compare justification depth against this baseline.
- `selected_lang` is always a canonical language name from the enumerated list — downstream agents can pattern-match on it without normalisation.
- `SpecAdvisorOutput` is the Pydantic schema for the Spec Advisor's output throughout M2–M5 — M3/M4 extend it with additional fields (`reasoning_steps`, `revised`) rather than replacing it.
- Artifact format (`tests/artifacts/m2_*.json`) establishes the pattern for all subsequent milestone artifacts: `milestone`, `agent`, `composition`, `timestamp`, `input`, `output`.
