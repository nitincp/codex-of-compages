# Faber

**Faber** *(Latin: maker, artisan, architect)* — a prompt engineering project that transforms
requirements into a layered stack of formal specifications using a minimal council of LLM agents.

Each agent prompt is a **composed chain of framework layers** (Structure → Reasoning → Verification → Technique),
assembled at runtime via `ComposedPrompt([...]).build()`. The GNN substrate (Kuzu) accumulates signal
across runs and is queryable live — it is not a storage layer bolted on later, it is the model.

---

## Current state — June 2026

| Track | Status |
|---|---|
| M0 Infrastructure | ✓ proven |
| M1 Framework builders (Layer 0) | ✓ proven — 22/22 tests |
| M2 Spec Advisor, structure only (Layer 1) | ✓ proven — 10/10 tests |
| M3 Add Reasoning / CoT (Layer 2) | ✓ proven — 19/19 tests |
| M4 Add Verification / CAI (Layer 3) | ✓ proven — 27/27 tests |
| M4.1 GNN PoC sub-milestones | M0–M4 ✓ — 74/74 tests |
| M5 Full Spec Advisor + meta-prompt (Layer 4) | ✓ proven — 30/30 tests; 104 total — **M6 is next** |
| M6–M13 Spec Council | not started |
| M14–M18 Build Council | not started |

**Next task:** M6 — FewShot retrieval from Kuzu graph (topology-based example selection for Spec Advisor).

---

## Milestone sequence

```
── Spec Council ──────────────────────────────────────────────────────────────
M0   Infra            M1  Framework builders   M2  Structure only
M3   Add Reasoning    M4  Add Verification      M4.1 GNN PoC (sub-milestones)
M5   Full single agent + meta-prompt output
M6   First chain: SME Agent → Spec Advisor
M7   Meta-prompting: Spec Advisor → Spec Specialist
M8   Verification in chain + Coordinator (ReAct gating)
M9   Kuzu graph integration: Specification + GROUNDS edges
M10  Multi-layer spec stack (3 layers, stateful Spec Advisor)
M11  Full spec council — complete traceability in Kuzu
M12  SME Phase B — persona library, multi-turn Reflexion
M13  Robustness — model flexibility, error handling, benchmarking

── Build Council (detail written after M13) ──────────────────────────────────
M14  Developer agent + console app
M15  API + UI  (Test Engineer joins)
M16  Clean-architecture web app
M17  Event-driven web app
M18  Ultimate: Faber generates and verifies its own dashboard
```

---

## Where to look for what

| Question | Document |
|---|---|
| What is the architecture and why? | [ARCHITECTURE.md](ARCHITECTURE.md) |
| What frameworks exist and how are they composed? | [docs/foundations/composition_framework.md](docs/foundations/composition_framework.md) |
| What is proven, what is next, what are the gates? | [BACKLOG.md](BACKLOG.md) — active tasks |
| What was proven and is now complete? | [COMPLETED.md](COMPLETED.md) — verified milestones |
| What signals has the GNN surfaced? What hypotheses are open? | [analysis_opportunities.md](analysis_opportunities.md) |
| How do I implement a new agent or framework? | [docs/foundations/dev-guide.md](docs/foundations/dev-guide.md) |
| How do I work with Claude across sessions? | [docs/running-with-claude.md](docs/running-with-claude.md) |
| Why were specific decisions made? | [docs/decisions/](docs/decisions/) — ADR log |
| What is the thesis arc? | [docs/thesis/CLAIM.md](docs/thesis/CLAIM.md) |
| Navigate all docs | [docs/INDEX.md](docs/INDEX.md) |

---

## Framework taxonomy

```
Structure    COSTAR, CRISPE, CLEAR, RACE       src/frameworks/{costar,crispe,clear,race}.py
Reasoning    ChainOfThought, ReActLoop          src/frameworks/{chain_of_thought,react}.py
Verification ConstitutionalAI                   src/frameworks/constitutional_ai.py
Technique    PersonaLayer, FewShot              src/frameworks/{persona,few_shot}.py
Composition  ComposedPrompt                     src/frameworks/composed.py
```

**Composition rules:** one layer per dimension per agent; Structure first; Verification always last.

---

## Agent council

| Agent | Composition | Role |
|---|---|---|
| SME Agent | `CLEAR → COSTAR → PersonaLayer → CAI ↩` | Multi-domain persona simulation |
| Spec Advisor | `CLEAR → COSTAR → CoT → [emits CRISPE]` | Language selector + meta-prompter |
| Spec Specialist | `CRISPE (injected) → FewShot → CAI ↩` | Formal spec generator |
| Coordinator | `CLEAR → ReActLoop` | Deliberative gate |

The Spec Specialist has **no fixed prompt** — it receives a CRISPE prompt generated at runtime
by the Spec Advisor. This is the meta-prompting moment central to the project.

---

## Getting started

**Recommended: dev container** — the project ships a `.devcontainer/` that wires everything automatically.

1. Open in VS Code → "Reopen in Container" (or `Dev Containers: Rebuild and Reopen in Container`)
2. `postCreateCommand` runs automatically: installs `pip install -e ".[dev]"`
3. Secrets and API keys are managed using `.env` in the workspace root; no host bind mount is required.
4. Ports 8000 and 8501 are forwarded automatically

**Without dev container:**

```bash
# Install
pip install -e ".[dev]"

# Verify
streamlit run src/ui/dashboard.py --server.port 8000
```

See `.devcontainer/devcontainer.json` for the full configuration and `docs/running-with-claude.md` for session workflow.

---

## Commands

```bash
# Gate tests for a milestone (ephemeral DB, fast)
pytest src/milestones/m{N}/tests/

# Seed one subgraph into the persistent GNN (run N times to accumulate N subgraphs)
python3 -m src.milestones.m{N}.run

# Streamlit dashboard
streamlit run src/ui/dashboard.py --server.port 8000

# Lint + type check
ruff check . && ruff format . && pyright src/

# ETL migration (when an existing table's structure must change)
python3 -m src.etl.migrate --to m{N} --dry-run
python3 -m src.etl.migrate --to m{N}
```

---

## Key invariants

- **Always-working set** — a later milestone never breaks an earlier one. Gate tests for all prior milestones must stay green.
- **No analysis in runner.py** — `runner.py` captures raw features; Claude-in-loop writes ad-hoc scripts, queries the live graph, and persists findings as `AnalysisNote` nodes.
- **No artifact files** — data lives in Kuzu at `data/kuzu`. No per-session JSON exports.
- **ETL only for structural changes** — `CREATE NODE TABLE IF NOT EXISTS` handles new tables. ETL is triggered only when an existing table's schema must change (Kuzu has no `ALTER TABLE`).
- **Milestone layout is self-contained** — each `src/milestones/m{N}/` owns its frameworks (tagged `[MN-copy]`), schema, runner, and tests. No imports from `src/agents/` or other milestones.
