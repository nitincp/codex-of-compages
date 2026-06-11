# M01 — Layer 0 PoC: Framework Builders

**Layer:** 0 — Atomic base (framework builders)  
**Milestone:** M1 in BACKLOG.md  
**Status:** Pre-execution — hypothesis written  
**Date started:** —  
**Date completed:** —

---

## Hypothesis

All framework builders produce correctly structured output independently and can be composed
in sequence without interference. This is the atomic base layer.
Nothing else can be built until this is proven.

---

## Method

Implement all framework builder classes as Python dataclasses with `build() -> str`.
Each builder must:
- Return a non-empty string when all fields are populated
- Return an empty string (or omit sections) for unpopulated optional fields
- Compose cleanly when passed to `ComposedPrompt([...]).build()`

The test suite proves each builder in isolation first, then proves composition.
No LLM calls in M01 — this is pure Python unit testing.

Builders to prove: `COSTARPrompt`, `CRISPEPrompt`, `CLEARSession`, `RACEPrompt`,
`PersonaLayer`, `ChainOfThought`, `ReActLoop`, `ConstitutionalAI`, `FewShot`, `ComposedPrompt`.

See BACKLOG.md [M1 section](../../BACKLOG.md#milestone-1--layer-0-poc-framework-builders) for full task list.

---

## Gate Tests

> All builders produce correctly structured strings. `ComposedPrompt` assembles them
> in the declared order. Each layer is independently unit-testable.
>
> Specific assertions in `tests/test_frameworks.py`:
> - Each builder: all fields → all section headers present in correct order
> - Empty optional field → section omitted, no empty header left behind
> - `ComposedPrompt([costar, persona, cai]).build()` → sections appear in declared sequence
> - `FABER_LOG_PROMPTS=true` → logs layer names and output length without error

---

## Result

> [TBD — fill after gate tests pass]

---

## Lessons

> [TBD — fill after execution]

---

## Next Layer Can Rely On

> [TBD — fill after execution]
>
> Template for the expected entries (fill when complete):
> - "`ComposedPrompt([...]).build()` assembles layers in declared order — safe to rely on in M02+"
> - "Empty layers are silently skipped — callers do not need to guard against empty optional fields"
> - "Each builder is independently unit-testable — a layer failure is isolated, not cascading"
