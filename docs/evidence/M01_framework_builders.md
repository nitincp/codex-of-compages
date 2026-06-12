# M01 — Layer 0 PoC: Framework Builders

**Layer:** 0 — Atomic base (framework builders)  
**Milestone:** M1 in BACKLOG.md  
**Status:** Complete  
**Date started:** 2026-06-11  
**Date completed:** 2026-06-12

---

## Hypothesis

All framework builders produce correctly structured output independently and can be composed
in sequence without interference. This is the atomic base layer.
Nothing else can be built until this is proven.

---

## Method

Implemented all framework builder classes as Python dataclasses with `build() -> str`.
Each builder must:
- Return a non-empty string when all fields are populated
- Return an empty string (or omit sections) for unpopulated optional fields
- Compose cleanly when passed to `ComposedPrompt([...]).build()`

The test suite proves each builder in isolation first, then proves composition.
No LLM calls in M01 — pure Python unit testing.

Builders proven: `COSTARPrompt`, `CRISPEPrompt`, `CLEARSession`, `RACEPrompt`,
`PersonaLayer`, `ChainOfThought`, `ReActLoop`, `ConstitutionalAI`, `FewShot`, `ComposedPrompt`.

See BACKLOG.md [M1 section](../../BACKLOG.md#milestone-1--layer-0-poc-framework-builders-) for full task list.

---

## Gate Tests

> All builders produce correctly structured strings. `ComposedPrompt` assembles them
> in the declared order. Each layer is independently unit-testable.
>
> Specific assertions in `tests/test_m1_frameworks.py`:
> - Each builder: all fields → all section headers present in correct order
> - Empty optional field → section omitted, no empty header left behind
> - `ComposedPrompt([costar, persona, cai]).build()` → sections appear in declared sequence
> - Dimension label `# [Dimension: ClassName]` present for each layer in composed output

---

## Result

Hypothesis confirmed.

22/22 unit tests passing. All 10 builders produce correctly structured strings. `ComposedPrompt` assembles layers in declared order, separated by `\n\n---\n\n` dividers, with `# [Dimension: ClassName]` labels. Empty optional fields are silently skipped — no empty headers or orphaned dividers.

`test_save_m1_artifact` generates `tests/artifacts/m1_frameworks.json` on every run, recording sample `build()` output for all 10 builders. This serves as the baseline reference for M2+ layers.

---

## Lessons

- Dataclasses with default-empty string fields and a single `build()` method is the right pattern — each builder is testable in complete isolation with zero setup.
- The `_dimension` class attribute on each builder (read by `ComposedPrompt`) is the correct place to encode taxonomy membership — it keeps dimension knowledge in the framework, not in the composition layer.
- Empty-field omission (skipping sections with no content) must be tested explicitly — it is easy to accidentally render empty `**Header**\n` lines that break composed output readability.
- `FABER_LOG_PROMPTS=true` logging in `ComposedPrompt.build()` should be tested as a side-effect, not as a gate criterion — it is a debugging aid, not a correctness property.

---

## Next Layer Can Rely On

- `ComposedPrompt([...]).build()` produces section headers in declared order — safe to rely on in M02+.
- Empty layers (where `build()` returns `""`) are silently skipped — callers do not need to guard against empty optional fields.
- Each builder is independently unit-testable — a layer failure is isolated, not cascading.
- `# [Dimension: ClassName]` labels are present in every non-empty layer's output block — safe to assert on in composed output tests.
- The `_dimension` class attribute is the single source of truth for layer taxonomy — no need to maintain a separate registry.
