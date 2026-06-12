# CLAUDE.md

This file provides guidance to Claude Code when working with the Faber project.

## What this project is

**Faber** *(Latin: maker, artisan, architect)* — a prompt engineering project that transforms
requirements into a layered stack of formal specifications using a minimal council of LLM agents.

Faber evolved from **Senatus (agentic-gnn)**, which had the right architectural instinct — agent
council + Kuzu as a GraphRAG/GNN substrate — but was rigid and ad-hoc in execution (hard-coded
prompts, fixed pipelines). Faber provides the PE framework grounding that makes the system dynamic,
adaptive, and self-improving: prompts composed at runtime, spec stack depth scaling to complexity,
GNN accumulating signal across runs.

**Read `docs/foundations/composition_framework.md` first.** It is the central architectural document.
It defines the layered composition model, research grounding (8 papers), full agent chains,
and one-shot examples for every layer. Everything else references back to it.

Two innovations define Faber:
1. **Layered composition** — every agent prompt is a chain of industry-standard framework layers
   (Structure → Reasoning → Verification → Technique), assembled by `ComposedPrompt([...]).build()`
2. **Spec Advisor as meta-prompter** — selects spec language per layer, generates the Spec
   Specialist's entire prompt at runtime (meta-prompting, Suzgun & Kalai 2024)

## Execution Philosophy

**Systematic PoCs from base layers upward. Always-working set.**

Never build a new layer before the layer below it is proven.
Each milestone in `BACKLOG.md` has explicit success criteria — passing them is the gate to the next.

```
── Spec Council ──────────────────────────────────────────────────────────
M0  Infra         → M1 Framework builders  → M2 Structure only
M3  Add Reasoning → M4 Add Verification    → M5 Full agent + meta-prompt output
M6  First chain   → M7 Meta-prompt chain   → M8 Coordinator loop
M9  Kuzu graph    → M10 Multi-layer stack  → M11 Full spec council (traceability)
M12 SME Phase B   → M13 Robustness

── Build Council (placeholder — detail written after M13) ────────────────
M14 Developer agent + console app  → M15 API + UI (Test Engineer joins here)
M16 Clean-arch web app             → M17 Event-driven web app
M18 Ultimate: Faber generates its own dashboard
```

## Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the dashboard (primary UI — milestone runner + artifact viewer)
streamlit run src/ui/dashboard.py --server.port 8000

# Chainlit shell (interactive phases — not started by default)
# chainlit run src/ui/app.py --port 8001

# Inspect graph state (stop app first — Kuzu single-connection)
python3 scripts/graph_stats.py

# Lint + type check (ruff = style/imports; pyright = type errors)
ruff check .
ruff format .
pyright src/

# Tests — run per milestone to confirm layer is proven
pytest tests/test_m0_dashboard.py --base-url http://localhost:8000  # M0 gate (start dashboard first)
pytest tests/test_m1_frameworks.py     # M1 gate
pytest tests/test_m2_spec_advisor.py   # M2-M5 gates
pytest tests/test_sme_chain.py         # M6 gate
pytest tests/test_meta_chain.py        # M7 gate
pytest tests/test_coordinator.py       # M8 gate
pytest tests/test_graph_store.py       # M9 gate
pytest                                 # full suite (excludes playwright — needs live server)
```

## Testing methodology

Each milestone has two test layers:

1. **Unit / integration tests** (`pytest tests/test_<milestone>.py`) — fast, no server needed,
   run in CI. These are the primary gate for M1+.

2. **Playwright UI tests** (`pytest tests/test_m0_dashboard.py --base-url http://localhost:8000`)
   — verify the Streamlit dashboard renders correctly with live browser automation.
   Start the dashboard first, then run.  Used for M0 infra verification and any milestone
   that adds new dashboard UI behaviour.

The Streamlit dashboard (`src/ui/dashboard.py`) is the primary UI — it runs milestone test
suites and displays agent cards + artifacts. Chainlit (`src/ui/app.py`) is a stub kept for
the interactive agent chain wired in at M7.

## Environment

Secrets: copy `.devcontainer/bootstrap-secrets.sh` from Senatus. Secrets in `/secrets/secrets.env`.
**Never put `ANTHROPIC_API_KEY` in `.env`.**

`.env`:
```
MODEL_PROVIDER=anthropic
MODEL_NAME=claude-sonnet-4-6
KUZU_DB_PATH=data/kuzu
FABER_LOG_PROMPTS=false    # set true to log each build() output for debugging
```

## Spec Council agents (M0–M13)

| Agent | Composition chain | Role |
|---|---|---|
| SME Agent | `CLEAR → COSTAR → PersonaLayer → ConstitutionalAI ↩` | Multi-domain persona sim |
| Spec Advisor | `CLEAR → COSTAR → ChainOfThought → [emits CRISPE]` | Meta-prompter; lang selector |
| Spec Specialist | `CRISPE (injected) → FewShot → ConstitutionalAI ↩` | Formal spec generator |
| Coordinator | `CLEAR → ReActLoop` | Deliberative gate |

## Build Council agents (M14–M18, placeholder)

| Agent | Candidate chain | Role |
|---|---|---|
| Developer | `CRISPE (injected) → FewShot → ConstitutionalAI ↩` | Code generation from spec stack |
| Test Engineer | `CRISPE → FewShot (spec-derived) → ConstitutionalAI ↩` | Gherkin scenarios; runs against generated code |
| ExecutionVerifier | TBD | Sandboxed runner; feeds pass/fail back to Coordinator |

## Framework taxonomy

```
Structure    COSTAR, CRISPE, CLEAR, RACE       src/frameworks/{costar,crispe,clear,race}.py
Reasoning    ChainOfThought, ReActLoop          src/frameworks/{chain_of_thought,react}.py
Verification ConstitutionalAI                   src/frameworks/constitutional_ai.py
Technique    PersonaLayer, FewShot              src/frameworks/{persona,few_shot}.py
Composition  ComposedPrompt                     src/frameworks/composed.py
```

**Rules:**
- One layer per dimension per agent
- Structure first, Verification always last
- `ConstitutionalAI` is not optional — every agent gates its output through it
- Never invent a new framework — compose existing ones. If you feel the need,
  check `docs/foundations/composition_framework.md` first.

## Key architecture reminders

- **Spec Specialist has no fixed system prompt** — receives a CRISPE prompt generated
  at runtime by the Spec Advisor. This is the meta-prompting moment.
- **Consensus is deliberative** — Coordinator's ReAct loop gates every layer.
  Nothing writes to Kuzu without Coordinator `proceed` decision.
- **Spec stack depth = complexity** — simple projects: 2 layers; enterprise: 5+
- **FABER_LOG_PROMPTS=true** logs each `build()` output — use when debugging which
  layer produced a bad output
- **Kuzu IS the GNN model, not just storage** — every milestone grows the graph schema (new node/edge types). Each project run writes a new instance subgraph. The verification analysis written after each milestone proof is the ML signal (labeled training instance). The GNN is queryable live from M3 onward — agents retrieve structurally similar prior projects by graph topology, not text similarity.
- **VOICE is retired** — replaced by COSTAR + PersonaLayer + ConstitutionalAI

## Implementing a new agent

1. Define composition chain (which frameworks, in which order)
2. Define output schema in `src/agents/schemas.py` (Pydantic)
3. Create `src/agents/your_agent.py` extending `BaseAgent`
   - Build prompt: `ComposedPrompt([layer1, layer2, ...]).build()`
   - Forced `tool_choice` for structured output
   - `self._log_usage(response.usage)` after every API call
4. Write tests proving each layer before wiring into council
5. Wire into `src/orchestration/council.py`
6. Add node props to `GraphStore._NODE_PROPS` and schema

## Implementing a new framework layer

1. Identify which dimension it belongs to (Structure / Reasoning / Verification / Technique)
2. If a layer in that dimension already exists for the agent, reconsider — do you need it?
3. Create `src/frameworks/<name>.py` — dataclass with `build() -> str`
4. Add to `src/frameworks/__init__.py`
5. Add unit test to `tests/test_m1_frameworks.py`
