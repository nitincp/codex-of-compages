# ADR-004 — Forced Tool-Use for All Structured Agent Output

**Date:** 2026-06-12  
**Status:** Active  
**Supersedes:** —  
**Referenced by:** All agent implementations; `src/agents/spec_advisor.py`

---

## Context

Every Faber agent produces structured output (typed fields, not free text) that feeds
downstream agents or is validated by tests. Three extraction patterns exist:

1. **Prompt-based JSON extraction** — instruct the model to return JSON; parse the response text
2. **Output parser / regex extraction** — extract structured fields from free-text response
3. **Forced tool-use** — define a tool with an explicit JSON Schema; set `tool_choice` so the
   model must call it; extract `tool_use` block input directly

The structured output must be reliably parseable across all inputs, including edge cases
(ambiguous briefs, complex domains, long outputs). Parsing failures in a six-agent chain
are hard to recover from and produce silent corruption rather than a clear error.

This decision was confirmed in M2 implementation of `SpecAdvisorAgent`.

---

## Decision

All agents use forced tool-use with `tool_choice={"type": "any"}` and a single tool
whose `input_schema` mirrors the agent's Pydantic output model.

The pattern:
```python
response = client.messages.create(
    model=model,
    system=system_prompt,
    messages=[{"role": "user", "content": user_message}],
    tools=[TOOL_SCHEMA],          # single tool, schema mirrors Pydantic model
    tool_choice={"type": "any"},  # forces tool call; never text-mode
)
tool_block = next(b for b in response.content if b.type == "tool_use")
output = OutputModel(**tool_block.input)
```

`tool_choice` is always `{"type": "any"}`, never `"auto"`. A single tool is defined per
agent turn. The `input_schema` in the tool definition and the Pydantic `OutputModel` are
kept in sync — both are the authoritative definition of the output contract.

---

## Rationale

**Reliability.** With `tool_choice={"type": "any"}` and a single tool, the model has
no decision to make — it always produces the structured output. `"auto"` occasionally
skips the tool call and returns a text response, which fails silently at the parse step.

**Schema enforcement.** The `input_schema` is validated by the Anthropic API before
the model generates output. Required fields are enforced; type mismatches are rejected.
Prompt-based JSON extraction provides no such guarantee.

**Clean separation.** The tool call is the output contract. The system prompt (composed
framework layers) is the reasoning/instruction context. These are separate concerns —
the tool schema does not pollute the prompt, and the prompt does not duplicate the schema.

**Testability.** The Pydantic model is the single source of truth for field names and types.
Tests assert on typed fields (`output.selected_lang`, `output.confidence`), not on parsed
strings. Adding a field to the output schema requires one change (the Pydantic model) and
updates tool schema + test assertions naturally.

**Accumulating schema across milestones.** `SpecAdvisorOutput` gains fields at M3
(`reasoning_steps`), M4 (`revised`, `revision_notes`), and M5 (`specialist_crispe_prompt`).
Forced tool-use with a Pydantic model makes this additive — earlier milestone tests still
pass because new fields have defaults; new tests assert on the new fields.

---

## Alternatives Considered

**`tool_choice="auto"`**: the model occasionally produces a text response instead of
a tool call — particularly for ambiguous or very simple inputs where the model judges
a tool call unnecessary. This produces intermittent parse failures. Discovered in M2
testing. Rejected in favour of `{"type": "any"}`.

**Prompt-based JSON extraction** (`"Return a JSON object with fields..."`): produces
unquoted keys, trailing commas, markdown fences, and truncated output on longer responses.
Requires a fragile parser or a second cleanup call. Offers no schema enforcement.
Rejected.

**Output parsers / regex**: brittle to output format variation. Requires maintaining a
separate extraction layer alongside the prompt. Fails when the model uses different field
labels than expected. Rejected.

**Structured outputs (JSON mode)**: enforces JSON structure but not field schema.
Does not guarantee required fields are present. `tool_choice` with `input_schema` is
strictly more constrained. Rejected.

---

## Consequences

- Every agent defines exactly **one tool per turn**. Multi-tool definitions are not used —
  the model should not choose between output shapes.
- `tool_choice={"type": "any"}` is the **only permitted value** for agent output calls.
  Do not use `"auto"` or `{"type": "tool", "name": "..."}` (the latter is equivalent but
  requires the tool name to be hardcoded in two places).
- The Pydantic model and the tool `input_schema` must be **kept in sync manually**.
  A mismatch between the two will pass the API schema check but fail Pydantic validation
  at runtime. When adding a field to an output schema, update both.
- Each milestone that extends an output schema (`SpecAdvisorOutput` at M3, M4, M5)
  adds fields with defaults so earlier tests do not require modification.
