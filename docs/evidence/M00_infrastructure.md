# M00 — Infrastructure

**Layer:** 0 — Infrastructure  
**Milestone:** M0 in BACKLOG.md  
**Status:** Pre-execution — hypothesis written  
**Date started:** —  
**Date completed:** —

---

## Hypothesis

A working devcontainer is established for Faber by extracting and adapting the Senatus infra layer
(devcontainer, BaseAgent, GraphStore, Chainlit shell) with minimal changes —
providing a verified, isolated base for all subsequent milestones.

---

## Method

Extract the following components from the Senatus project and adapt for Faber:

- `.devcontainer/` — `bootstrap-secrets.sh`, `devcontainer.json` (copy verbatim)
- `src/agents/base.py` — adapt: add `build_prompt(layers: list) -> str` method alongside the existing patterns
- `src/graph/schema.py` — extend `NodeType`/`EdgeType` enums for `Specification`, `Requirement`, `GROUNDS`, `DERIVED_FROM`, `REFINES`
- `src/graph/store.py` — add new node/edge props; keep `write_node()`/`write_edge()` patterns intact
- `src/ui/app.py` — bare Chainlit shell (no agent wiring yet)
- `pyproject.toml` — same core deps as Senatus (`anthropic`, `langgraph`, `kuzu`, `chainlit`, `pydantic`, `python-dotenv`, `tenacity`, `ruff`, `pytest`)

The `src/frameworks/` directory already exists with all builders from the pre-execution phase.

See BACKLOG.md [M0 section](../../BACKLOG.md#milestone-0--infrastructure) for full task list.

---

## Gate Tests

> `chainlit run src/ui/app.py --port 8000` starts without errors.  
> Kuzu DB initializes at `data/kuzu/` on first run.  
> `python -c "from src.frameworks import ComposedPrompt; print('ok')"` exits 0.  
> No broken imports from `src/frameworks/` or `src/agents/base.py`.  
> `ruff check .` exits 0.

---

## Result

> [TBD — fill after execution]

---

## Lessons

> [TBD — fill after execution]

---

## Next Layer Can Rely On

> [TBD — fill after execution]
