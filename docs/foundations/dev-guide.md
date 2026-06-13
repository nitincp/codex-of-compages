# Faber — Developer Guide

How to add new agents and framework layers. Read this when building M5+.

For agent composition chains and framework taxonomy, see `ARCHITECTURE.md`.  
For framework field reference and one-shot examples, see `docs/foundations/composition_framework.md`.

---

## Implementing a new agent

1. Define the composition chain (which frameworks, in which order — one per dimension, Structure first, CAI last)
2. Define the output schema in `src/agents/schemas.py` (Pydantic model)
3. Create `src/agents/your_agent.py` extending `BaseAgent`:
   - Build prompt: `ComposedPrompt([layer1, layer2, ...]).build()`
   - Forced structured output: `tool_choice="any"` with a single tool matching the Pydantic schema
   - `self._log_usage(response.usage)` after every API call
4. Write tests proving each composition layer in isolation before wiring into the council
5. Wire into `src/orchestration/council.py`
6. Add node props to `GraphStore._NODE_PROPS` and to the Kuzu schema

**Spec Specialist exception:** has no fixed system prompt — receives a CRISPE prompt generated at
runtime by the Spec Advisor (meta-prompting). Do not give it a static `build()` chain.

---

## Implementing a new framework layer

1. Identify which dimension it belongs to: Structure / Reasoning / Verification / Technique
2. If a layer in that dimension already exists for the target agent, reconsider — do you actually need it?
3. Create `src/frameworks/<name>.py` — Python dataclass with `build() -> str` and `_dimension: str`
4. Add to `src/frameworks/__init__.py`
5. Add unit tests to `tests/test_m1_frameworks.py`:
   - All section headers present in correct order
   - Empty optional fields omitted from output
   - Dimension label appears correctly when composed

**Never invent a new framework when you can compose existing ones.**  
Check `docs/foundations/composition_framework.md` before deciding a new one is needed.

---

## Implementing a new milestone (M4.1 sub-milestone pattern)

1. Create `src/milestones/m{N}/` — fully self-contained (no imports from `src/agents/` or other milestones)
2. Copy relevant framework builders and tag them: `# [MN-copy | milestones/m{prev}/frameworks/foo.py]`
3. Define graph schema in `graph/schema.py` — own node/rel table names, no collisions with prior milestones
4. Implement `graph/runner.py` — `extract()` + `seed(conn, run_id)`. Pure capture, no analysis logic.
5. Implement `run.py` — `python3 -m src.milestones.m{N}.run [run-id]`
6. Write gate tests in `tests/test_m{N}.py` against an ephemeral tmp DB
7. If adding a cross-milestone edge (e.g. `VERIFICATION_ADDS`): match prior milestone's `SpecRun` by `brief_label`

If an **existing** Kuzu table needs structural change, create `migration/` — see `docs/foundations/kuzu_etl_strategy.md`.  
If only **new** tables are added, `CREATE NODE TABLE IF NOT EXISTS` is sufficient — no migration.

---

## Python + Claude: project-specific techniques

### How Claude navigates this codebase

Claude reads `pyproject.toml` for package structure and `src/frameworks/__init__.py` for exported frameworks. The `_dimension` class attribute and `build() -> str` signature are the canonical contract for all framework classes — Claude checks these first.

**Type hints are load-bearing for Claude.** The Pydantic schemas in `src/agents/schemas.py` and typed return values in `runner.py` let Claude write correct Cypher queries and analysis scripts without reading full implementations. Keep them accurate.

### Running ad-hoc analysis scripts

Scripts are ephemeral — run inline, not committed:

```python
import kuzu
db = kuzu.Database("data/kuzu")
conn = kuzu.Connection(db)
result = conn.execute("""
    MATCH (r:MilestoneRun)<-[:CAPTURED_IN]-(s:SpecRun)
    WHERE r.milestone = 'm3'
    RETURN s.brief_label, s.confidence, s.reasoning_step_count
    ORDER BY s.confidence DESC
""")
while result.has_next():
    print(result.get_next())
```

Save the output; discard the script. The output informs the `AnalysisNote` schema.

### Pyright feedback loop

Run pyright on the milestone before seeding:
```bash
pyright src/milestones/m{N}/
```
Catches field name mismatches between Pydantic schema and Kuzu INSERT before runtime. Run this before any `seed()` implementation is considered done.

### Package isolation for milestone frameworks

Each milestone imports from its own `src/milestones/m{N}/frameworks/` — **not** from `src/frameworks/`. If Claude writes `from src.frameworks.costar import COSTARPrompt` inside a milestone file, it is wrong.

### Kuzu Cypher dialect — common Claude mistakes

- No `WITH ... LIMIT` for pagination — use `RETURN ... LIMIT N` directly
- `COPY REL FROM` requires named params: `(from='src_id', to='dst_id')`
- Node IDs in this project are string PKs — query by `{id: "run_id:name"}`, not internal ID
- `CREATE NODE TABLE IF NOT EXISTS` — the `IF NOT EXISTS` clause is required for ad-hoc `AnalysisNote` creation to be idempotent across sessions

### Anthropic SDK patterns

All agents use:
- `tool_choice={"type": "any"}` — forced tool use, never `"auto"`
- `response.content[0].input` — the tool call result dict (matches Pydantic schema)
- `self._log_usage(response.usage)` — after every API call

If Claude writes `tool_choice="auto"` or reads `response.content[0].text`, it is wrong for this project.
