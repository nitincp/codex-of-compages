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

# Gate tests — validate one milestone (ephemeral Kuzu, fast)
pytest src/milestones/m1/tests/   # M1 gate
pytest src/milestones/m2/tests/   # M2 gate (once M2 is built)
# ... and so on per milestone

# Milestone runner — seed one subgraph into persistent Kuzu DB
python3 -m src.milestones.m1.run            # auto-generates run_id
python3 -m src.milestones.m1.run my-run-id  # explicit run_id

# Run N times to accumulate N subgraphs for comparison:
python3 -m src.milestones.m1.run
python3 -m src.milestones.m1.run
python3 -m src.milestones.m1.run

# Lint + type check
ruff check .
ruff format .
pyright src/
```

## Testing methodology

Each milestone has two tiers:

1. **Gate tests** (`pytest src/milestones/m{N}/tests/`) — validate schema correctness and
   data quality for a single run. Use an ephemeral tmp Kuzu DB. Fast, isolated, no persistent
   state. These are the gate to proceed to the next milestone.

2. **Milestone runner** (`python3 -m src.milestones.m{N}.run`) — seeds one subgraph into
   the persistent DB (`data/kuzu`). Each invocation is one command; run it N times to create
   N subgraphs. Comparison and ML pass analysis is done by Claude ad-hoc after N runs,
   not in the test suite.

**Separation is strict:** gate tests never write to the persistent DB; the runner never runs
pytest. Claude decides when to run the runner and when to run gate tests.

## Milestone layout

Each milestone is fully self-contained in `src/milestones/m{N}/`:

```
src/milestones/m{N}/
  __init__.py           # milestone purpose + GNN contribution
  run.py                # CLI: python3 -m src.milestones.m{N}.run [run-id]
  frameworks/           # copies of relevant framework builders (tagged [MN-origin] or [MN-copy])
  graph/
    schema.py           # Kuzu node/rel tables owned by this milestone
    runner.py           # extract() + seed(conn, run_id) — pure capture, no analysis
  tests/
    test_m{N}.py        # gate tests (ephemeral DB, single run)
```

**Framework file tagging:** files copied from an earlier milestone carry a comment tag:
- `# [M1-origin | src/frameworks/costar.py]` — original source
- `# [M2-copy | identical to milestones/m1/frameworks/costar.py]` — copied unchanged

**Kuzu schema cohabitation:** all milestones write to the same `data/kuzu` database.
Each milestone owns its own node/rel table names (no collisions). Cross-milestone edges
(e.g., `REASONING_ADDS`, `VERIFICATION_ADDS`) link subgraphs from different milestones.

**No artifact files.** Data lives in Kuzu. `dump()` exists in runner.py as an optional dev
utility but is never called automatically. Do not create per-session JSON/JSONL exports.

## Kuzu schema evolution

**When existing schema does not fit new requirements**, use the ETL migration strategy.
Full design: `docs/foundations/kuzu_etl_strategy.md`.

Kuzu has no `ALTER TABLE`. When a milestone needs to change an existing node or rel table
(add a column, change a type, rename, add a second FROM type to a rel), the only path is
blue-green DB rotation: export old DB → transform → load new DB → retire old.

**This is NOT needed for adding new tables.** `CREATE NODE TABLE IF NOT EXISTS` handles that.
ETL is only triggered when an existing table's structure must change.

**Migration layout** — every milestone that changes an existing table owns a `migration/` dir.
Single-pass (one structural change): flat layout. Multi-pass (schema evolved mid-milestone
during Claude-in-loop analysis): directory per pass. `meta.json["passes"]` = current state.

```
── single-pass ────────────────────────────────────────────────────────────
src/milestones/m{N}/migration/
  meta.json          # {"source_milestone": "mX", "target_milestone": "mN", "reseed_tables": [...]}
  schema.cypher      # complete DDL snapshot at mN
  transform.cypher   # COPY (Cypher) TO parquet blocks in sequence

── multi-pass ─────────────────────────────────────────────────────────────
src/milestones/m{N}/migration/
  meta.json          # {..., "passes": 2}   ← current state = pass_02/
  pass_01/
    schema.cypher    # DDL after pass 1
    transform.cypher # M(N-1) → MN structural migration
  pass_02/
    schema.cypher    # DDL after pass 2 (= current state)
    transform.cypher # MN → MN schema evolution driven by analysis findings
```

Add a new pass (never modify existing passes) when mid-milestone analysis reveals richer
schema needs. `migrate.py` defaults to latest pass; `--pass K` re-applies an earlier one.
`diff.py` auto-resolves `pass_{N}/schema.cypher` when `passes` is declared.

**`transform.cypher` pattern** — transforms happen in Cypher, not Python:

```cypher
-- TableName: what changed and why
COPY (
  MATCH (n:TableName)
  RETURN n.existing_col AS existing_col,  -- source schema (existed before)
         0 AS new_col                     -- target addition + intent comment
) TO '{output_dir}/TableName.parquet'
```

Rel tables use `src_id`/`dst_id` as the FROM/TO column convention (loaded with
`COPY REL FROM 'file.parquet' (from='src_id', to='dst_id')`). New tables introduced
in a migration (no rows in source) are excluded from `transform.cypher` entirely —
the verify step handles missing source tables via try/except (count = 0).

**`schema.cypher`** (or `pass_{N}/schema.cypher` for multi-pass) is the snapshot.
To see what changed between any two milestones:

```bash
python3 -m src.etl.diff m2 m5   # structured output; auto-resolves latest pass schema
```

**To run a migration:**

```bash
python3 -m src.etl.migrate --to m{N} --dry-run   # inspect transformed Parquet first
python3 -m src.etl.migrate --to m{N}              # full rotation (latest pass)
python3 -m src.etl.migrate --to m{N} --pass 1     # re-apply an earlier pass explicitly
```

**Deterministic tables** (e.g. `FrameworkLayer`) are listed in `reseed_tables` — the runner
re-seeds them from source code rather than transforming stale Parquet. Do not write a
`COPY` block for them in `transform.cypher`.

**After rotation**, gate tests run against the new persistent DB path to verify correctness
before the old DB backup is discarded.

## Claude's role

Claude is **both** code writer and analytical orchestrator in this project.

**As code writer:** implements milestone structure, schema, runners, and tests following
the patterns above.

**As analyst (Claude-in-loop):**
1. Runs `python3 -m src.milestones.m{N}.run` N times to accumulate subgraphs
2. Writes and executes ad-hoc Python scripts to query the persistent Kuzu DB
3. Reads the output, decides what signals are worth persisting — no predetermined schema
4. Creates `AnalysisNote` nodes and `ANALYZED` edges on the fly using
   `CREATE NODE TABLE IF NOT EXISTS AnalysisNote (...)` and
   `CREATE REL TABLE IF NOT EXISTS ANALYZED (FROM AnalysisNote TO ...)`
5. Updates `analysis_opportunities.md` with confirmed findings and forward hypotheses

**`analysis_opportunities.md`** (repo root) is the cross-session grounding document.
Read it at the start of any analytical session. It contains confirmed signals, open
hypotheses, and Cypher queries ready to run when their `available_when` condition is met.

**The feedback loop:**
```
seed(conn)          raw features in Kuzu          (code, deterministic)
        ↓
N × run command     N subgraphs accumulate        (Claude commands)
        ↓
ad-hoc query script surfaces signal               (Claude writes + runs)
        ↓
AnalysisNote nodes  findings written back         (Claude decides schema)
        ↓
analysis_opportunities.md updated                 (Claude records hypotheses)
```

Analysis is NOT done in code. `runner.py` captures; Claude analyzes.

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
- **Kuzu IS the GNN model, not just storage** — every milestone grows the graph schema (new node/edge types). Each run writes a new `MilestoneRun` subgraph anchored by `CAPTURED_IN` edges. `AnalysisNote` nodes written by Claude connect via `ANALYZED` edges and form the ML signal layer. The GNN is queryable live from M1 onward — Claude and agents retrieve prior findings by graph traversal, not text search.
- **MilestoneRun is the subgraph anchor** — `(FrameworkLayer)-[:CAPTURED_IN]->(MilestoneRun)`. Multiple runs of the same milestone coexist in the same DB. Always query through the run: `MATCH (r:MilestoneRun {run_id: $rid})<-[:CAPTURED_IN]-(f)`.
- **AnalysisNote is the feedback type** — ad-hoc, schema created on the fly, connected via `ANALYZED` edges. Never harden analysis into `runner.py` — that's Claude's domain.
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
