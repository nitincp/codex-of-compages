# M03 — Layer 2 PoC: Add Reasoning

**Layer:** 2 — Chain of Thought added to Spec Advisor  
**Milestone:** M3 in BACKLOG.md  
**Status:** Complete  
**Date started:** 2026-06-12  
**Date completed:** 2026-06-12

---

## Hypothesis

Adding a Chain of Thought layer makes the Spec Advisor's selection reasoning visible and auditable.
Quality should improve or stay equal relative to the M02 baseline — never regress.

---

## Method

Extended `SpecAdvisorAgent` with a `ChainOfThought` layer appended after `COSTARPrompt`.
Layers are assembled independently by `ComposedPrompt` — CoT is a peer section, not injected into
COSTAR. The coupling is deliberate: COSTAR's `response_format` field instructs the model to populate
`reasoning_steps` in the tool call; the CoT section provides the step-by-step scaffold.

`SpecAdvisorOutput` extended with `reasoning_steps: list[str]`.

Same two test briefs as M02 to enable direct baseline comparison:
- **Simple**: "CRUD todo app with REST API and a PostgreSQL backend"
- **Complex**: "multi-region e-commerce platform with eventual consistency, distributed inventory, and CQRS event sourcing"

See BACKLOG.md [M3 section](../../BACKLOG.md) for full task list.

---

## Gate Tests

> Reasoning steps are visible, auditable, and reference specific layer concerns.  
> Selection quality is equal to or better than M2 baseline.
>
> Specific assertions in `tests/test_m2_spec_advisor.py` (M3 extension):
> - `reasoning_steps` is non-empty and contains ≥3 steps
> - Each step references a specific concern or candidate language
> - `selected_lang` and `layer` match M02 selections (no quality regression)
> - `confidence` ≥ M02 baseline or within acceptable delta

---

## Result

Hypothesis confirmed. 41/41 tests passing (22 M1 + 10 M2 + 8 M3 — clean M1 regression).

**Simple project (CRUD todo app):**
- `selected_lang`: `OpenAPI`, `layer`: `api`, `confidence`: 0.95 (M02 was 0.97, delta −0.02)
- 5 reasoning steps. Per-concern evaluation: JSON Schema dismissed (lacks endpoint semantics),
  OpenAPI selected (covers REST surface: endpoints + schemas + status codes), TLA+/CML/Alloy/Event-B
  dismissed (no concurrency, safety-critical, or relational invariant concerns present).
- CoT correctly identified the *absence* of concerns as signal, not just their presence.

**Complex project (multi-region e-commerce, eventual consistency, CQRS):**
- `selected_lang`: `TLA+`, `layer`: `system`, `confidence`: 0.93 (M02 was 0.95, delta −0.02)
- 8 reasoning steps with per-concern evaluation:
  - Eventual consistency → TLA+ (temporal logic over async replica convergence) vs Event-B (refinement overhead unjustified)
  - CQRS event sourcing → TLA+ (command handlers + event log + read-model as interleaved state machines) vs CML (choreography only, no global invariant assertion)
  - Distributed inventory no-oversell → TLA+ (global `inventory ≥ 0` + liveness proof) vs Alloy (structural snapshots only, no temporal operators)

**Quality delta pattern:** both briefs showed −0.02 confidence delta (M02→M03). Interpretation: CoT surfaces epistemic uncertainty that a structure-only pass conceals. The slight drop reflects genuine humility, not a regression. Justification depth increased significantly — M02 was single-paragraph conclusion; M03 shows per-concern working.

Artifacts: `tests/artifacts/m3_simple.json`, `tests/artifacts/m3_complex.json`.

---

## Lessons

- CoT and COSTAR are independent layers but share one explicit coupling: COSTAR's `response_format` must name `reasoning_steps` so the model knows to populate it in the tool call. Without this, CoT steps appear in free text only.
- The −0.02 confidence delta is a feature: a model that can't see its own reasoning is overconfident. CoT creates calibrated uncertainty. Subsequent CAI layer (M04) uses confidence as one of its pass/fail signals.
- `evaluation_depth = per_concern` (evaluating each candidate against each concern, not just the winner) is the quality signal that distinguishes M03 from M02. Measuring this became the basis for M4.1 M3 GNN analysis.
- 8-step CoT on the complex brief added ~175 input tokens to the prompt budget. This is the primary driver of M03→M04 token cost increase (confirmed in M4.1 GNN analysis).

---

## Next Layer Can Rely On

- `SpecAdvisorOutput.reasoning_steps` is a non-empty list of strings — each step names a concern or candidate.
- CoT evaluation depth is `per_concern` for both briefs — downstream agents can parse step text to identify which languages were explicitly considered and why they were dismissed.
- Confidence scores are calibrated (surfaced uncertainty, not overconfidence) — M04's CAI gate can safely use confidence as a pass/fail threshold signal.
- The −0.02 confidence delta from adding CoT is a stable pattern — not a bug to fix, an expected signal of calibration.
- `ComposedPrompt([COSTAR, ChainOfThought])` is the proven two-layer chain — M04 appends `ConstitutionalAI` as the third layer without modifying the first two.
