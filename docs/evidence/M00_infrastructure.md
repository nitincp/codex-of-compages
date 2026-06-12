# M00 — Infrastructure

**Layer:** 0 — Infrastructure  
**Milestone:** M0 in BACKLOG.md  
**Status:** Complete  
**Date started:** 2026-06-11  
**Date completed:** 2026-06-12

---

## Hypothesis

A working devcontainer is established for Faber by extracting and adapting the Senatus infra layer
(devcontainer, BaseAgent, GraphStore, Chainlit shell) with minimal changes —
providing a verified, isolated base for all subsequent milestones.

---

## Method

Extracted the following components from the Senatus project and adapted for Faber:

- `.devcontainer/` — `bootstrap-secrets.sh`, `devcontainer.json`
- `src/agents/base.py` — added `build_prompt(layers: list) -> str` alongside existing TokenUsage/SessionUsage
- `src/graph/schema.py` — extended `NodeType`/`EdgeType` enums for `Specification`, `Requirement`, `GROUNDS`, `DERIVED_FROM`, `REFINES`
- `src/graph/store.py` — new node/edge props; `write_node()`/`write_edge()` patterns intact
- `src/ui/dashboard.py` — new: Streamlit milestone runner + artifact viewer (primary UI, replacing Chainlit as verification surface)
- `src/ui/app.py` — bare Chainlit shell (kept as stub for M7+ interactive chain)
- `pyproject.toml` — core deps including `playwright` and `pytest-base-url` added for UI test layer

See BACKLOG.md [M0 section](../../BACKLOG.md#milestone-0--infrastructure-) for full task list.

---

## Gate Tests

> `streamlit run src/ui/dashboard.py --server.port 8000` starts without errors.  
> Dashboard renders heading, milestone selector, Run button, and idle agent cards.  
> Playwright smoke tests (`tests/test_m0_dashboard.py`) confirm all four.

---

## Result

Hypothesis confirmed.

Devcontainer provisions cleanly. All deps install via `pip install -e ".[dev]"`. Streamlit dashboard starts on port 8000 and renders correctly. Kuzu DB initialises at `data/kuzu/` on first run. No broken imports.

4/4 Playwright smoke tests passing. Two screenshots captured to `tests/artifacts/`:
- `m0_dashboard_idle.png` — dashboard in initial idle state
- `m0_run_result.png` — dashboard after running M1 test suite (showing pass/fail status)

One design pivot during execution: Streamlit proved more capable as a milestone verification surface than initially anticipated, so it was promoted to the primary UI. Chainlit retained as the interactive shell for M7+ agent chain wiring.

---

## Lessons

- Streamlit's `st.status` + `subprocess` pattern is sufficient to run pytest suites and stream results — no need for a bespoke test runner.
- Playwright with `pytest-base-url` is the right tool for dashboard smoke testing; the `--base-url` flag keeps test code URL-agnostic.
- Chainlit is better reserved for interactive multi-turn sessions (M7+) — forcing it into a verification role would have added complexity with no benefit.

---

## Next Layer Can Rely On

- `BaseAgent.__init__()` creates an Anthropic client and reads `MODEL_NAME` from env — safe to subclass without re-implementing client setup.
- `BaseAgent.build_prompt(layers)` delegates to `ComposedPrompt` — all agents get composition for free.
- `BaseAgent._log_usage(response.usage)` accumulates token counts into `session_usage` — call after every API response.
- `GraphStore.write_node()` / `write_edge()` are operational — M9+ can write to Kuzu without infrastructure work.
- Streamlit dashboard is the milestone verification surface — add new test suites to its selector, not a separate runner.
