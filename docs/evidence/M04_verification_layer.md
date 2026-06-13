# M04 — Layer 3 PoC: Add Verification

**Layer:** 3 — Constitutional AI verification gate added to Spec Advisor  
**Milestone:** M4 in BACKLOG.md  
**Status:** Complete  
**Date started:** 2026-06-12  
**Date completed:** 2026-06-12

---

## Hypothesis

The Constitutional AI critique-revision loop improves low-quality outputs (vague briefs, weak
justifications) and passes high-quality outputs through unchanged. The gate is self-correcting:
it fires when and only when the output fails the underspecification threshold.

---

## Method

Extended `SpecAdvisorAgent` with `ConstitutionalAI` as the third layer after `COSTARPrompt → ChainOfThought`.
CAI principles for this agent:
1. Justification references at least 2 specific layer concerns (not generic rationale)
2. Candidate evaluation must be explicit (not just the selected language)
3. Confidence ≥ 0.7 (brief provides enough signal to select with confidence)

`SpecAdvisorOutput` extended with `revised: bool` and `revision_notes: str`.

Three briefs to test the gate's discrimination:
- **Simple** (strong): "CRUD todo app with REST API and a PostgreSQL backend"
- **Complex** (strong): "multi-region e-commerce platform with eventual consistency, distributed inventory, CQRS"
- **Vague** (weak): "an app"

See BACKLOG.md [M4 section](../../BACKLOG.md) for full task list.

---

## Gate Tests

> CAI gate demonstrably revises weak outputs. Strong outputs pass through unchanged.  
> No regression in M2/M3 test cases.
>
> Specific assertions in `tests/test_m2_spec_advisor.py` (M4 extension):
> - Vague brief → `revised=True`, `revision_notes` non-empty, `confidence` reflects uncertainty
> - Simple brief → `revised=False`, `revision_notes` empty, output unchanged from M03
> - Complex brief → `revised=False`, `revision_notes` empty, output unchanged from M03
> - All M2 (10) and M3 (8) tests still pass — no regression

---

## Result

Hypothesis confirmed. 27/27 M4 gate tests passing. 23/23 M1 + 18/18 M2/M3 regression tests clean.

**Vague brief ("an app"):**
- `selected_lang`: `OpenAPI`, `layer`: `api`, `confidence`: 0.30, `revised=True`
- CAI principle 3 triggered: brief supplies fewer than 2 concrete technical signals
- Revision added explicit assumption inventory: REST interface, API contract as spec artefact
- Both assumptions flagged as unvalidated in `revision_notes`
- Confidence lowered from initial pass to 0.30 — the gate correctly encoded uncertainty

**Simple brief (CRUD todo app):**
- `selected_lang`: `OpenAPI`, `layer`: `api`, `confidence`: 0.95, `revised=False`
- 7 reasoning steps. All CAI principles satisfied on first pass
- REST API + PostgreSQL = 2 concrete technical signals; candidate evaluation present; confidence above threshold
- `revision_notes` empty

**Complex brief (multi-region e-commerce):**
- `selected_lang`: `TLA+`, `layer`: `system`, `confidence`: 0.95, `revised=False`
- 8 reasoning steps. All CAI principles satisfied on first pass
- Eventual consistency + CQRS + distributed inventory = 3+ concrete signals; all named candidates evaluated
- `revision_notes` empty

**Pass-through semantics confirmed:** strong inputs are unchanged by the CAI gate. The gate fires when and only when the brief fails the underspecification threshold. This is the correct behaviour — CAI is a corrective gate, not a reformatter.

Artifacts: `tests/artifacts/m4_simple.json`, `tests/artifacts/m4_complex.json`, `tests/artifacts/m4_vague.json`.

---

## Lessons

- **The vague brief is the diagnostic brief.** The simple and complex briefs tell you if the agent works; the vague brief tells you if the gate works. M5+ should always include a vague input in the test suite.
- **CAI's value is in the assumption inventory.** The most useful product of a revision is not a better answer — it is the explicit list of what had to be assumed to give any answer at all. This is what low-confidence runs in production will surface.
- **Confidence is load-bearing.** Using `confidence < 0.7` as the underspecification threshold worked cleanly. The gate does not need a separate "quality score" — confidence calibrated by CoT (see M03) is the right signal.
- `revision_notes` being empty on pass-through is important — it makes `revised=False` machine-checkable, not just narrative. Downstream agents can branch on `revised` without parsing prose.

---

## Next Layer Can Rely On

- Full composition chain `COSTARPrompt → ChainOfThought → ConstitutionalAI` is proven end-to-end.
  This is the canonical Spec Advisor composition — M5+ extend it or derive from it.
- `revised=True` guarantees `revision_notes` is non-empty and `confidence < 0.7` — downstream agents can branch on `revised` safely.
- `revised=False` guarantees `revision_notes` is empty — no silent partial revisions.
- The vague brief ("an app") is the established regression brief for the CAI gate. Include it in any test suite that exercises the full composition chain.
- All three briefs (simple, complex, vague) are the canonical test triad for Spec Advisor through M13.
- `confidence` is calibrated and trustworthy as a quality signal — M4.1 M4 GNN analysis uses it as the primary edge property on `VERIFICATION_ADDS`.
