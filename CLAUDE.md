# CLAUDE.md

Guidance for Claude Code sessions on Faber. For project overview and current milestone state, see `README.md`.

## Execution philosophy

**Systematic PoCs from base layers upward. Always-working set.**  
Never build a new layer before the layer below it is proven.  
Each milestone in `BACKLOG.md` has explicit success criteria — passing them is the gate to the next.  
`BACKLOG.md` = active tasks. `COMPLETED.md` = verified milestones (extracted to keep BACKLOG lean).

## Commands

```bash
pip install -e ".[dev]"

# Gate tests — one milestone at a time (ephemeral DB, fast)
pytest src/milestones/m{N}/tests/

# Milestone runner — seed one subgraph into persistent Kuzu DB
python3 -m src.milestones.m{N}.run            # auto-generates run_id
python3 -m src.milestones.m{N}.run my-run-id  # explicit run_id

# ETL migration (only when an existing table's structure must change)
python3 -m src.etl.migrate --to m{N} --dry-run
python3 -m src.etl.migrate --to m{N}

# Lint + type check
ruff check . && ruff format . && pyright src/
```

## Testing — two-tier separation (strict)

1. **Gate tests** (`pytest src/milestones/m{N}/tests/`) — ephemeral tmp Kuzu DB, no persistent state. Gate to the next milestone.
2. **Milestone runner** (`python3 -m src.milestones.m{N}.run`) — seeds one subgraph into persistent `data/kuzu`. Run N times to accumulate N subgraphs.

Gate tests **never** write to persistent DB. The runner **never** runs pytest.  
Claude decides when to run each based on the current goal (analysis vs. validation).

## Milestone layout

Each milestone is fully self-contained in `src/milestones/m{N}/` — no imports from `src/agents/` or other milestones:

```
src/milestones/m{N}/
  __init__.py       # milestone purpose + GNN contribution
  run.py            # CLI: python3 -m src.milestones.m{N}.run [run-id]
  frameworks/       # frozen copies tagged [MN-origin] or [MN-copy]
  graph/
    schema.py       # Kuzu node/rel tables owned by this milestone
    runner.py       # extract() + seed(conn, run_id) — pure capture, no analysis
  tests/
    test_m{N}.py    # gate tests (ephemeral DB)
```

Framework tagging: `# [M1-origin | src/frameworks/costar.py]` for the original; `# [M2-copy | ...]` for unchanged copies.

## Kuzu schema evolution

Full strategy and transform.cypher patterns: `docs/foundations/kuzu_etl_strategy.md`.

- **Adding new tables** → `CREATE NODE TABLE IF NOT EXISTS`. No ETL needed.
- **Changing existing tables** → blue-green rotation via `src/etl/migrate.py`. Kuzu has no `ALTER TABLE`.
- Migrations live in `src/milestones/m{N}/migration/`. Single-pass = flat layout. Multi-pass = `pass_01/`, `pass_02/` dirs.
- Never modify existing passes — always add a new one.
- `reseed_tables` in `meta.json` = deterministic tables re-seeded from source, not Parquet. No `COPY` block for these.
- After rotation, run gate tests against new DB path before discarding the backup.

## Claude's role

Claude is **both** code writer and analytical orchestrator.

**As code writer:** implements milestone structure, schema, runners, and tests per the patterns above.

**As analyst (Claude-in-loop):**
1. Runs `python3 -m src.milestones.m{N}.run` N times to accumulate subgraphs
2. Writes and executes ad-hoc Python scripts to query `data/kuzu`
3. Decides what signals are worth persisting — no predetermined schema
4. Creates `AnalysisNote` nodes + `ANALYZED` edges on the fly via `CREATE NODE TABLE IF NOT EXISTS`
5. Updates `analysis_opportunities.md` with confirmed findings and forward hypotheses

**Read `analysis_opportunities.md` at the start of any analytical session.**  
Analysis is **NOT** done in code — `runner.py` captures; Claude analyzes.

## Environment

Secrets in `/secrets/secrets.env`. Source via `.devcontainer/bootstrap-secrets.sh`.  
**NEVER put `ANTHROPIC_API_KEY` in `.env`.**

`.env`:
```
MODEL_PROVIDER=anthropic
MODEL_NAME=claude-sonnet-4-6
KUZU_DB_PATH=data/kuzu
FABER_LOG_PROMPTS=false    # set true to log each build() output when debugging layer output
```

## Key invariants

- **No artifact files** — data lives in Kuzu at `data/kuzu`. `dump()` in runner.py is a dev utility, never called automatically. No per-session JSON/JSONL exports.
- **Kuzu IS the GNN** — not just storage. Always query through the run anchor: `MATCH (r:MilestoneRun {run_id: $rid})<-[:CAPTURED_IN]-(n)`.
- **AnalysisNote is the feedback type** — schema invented ad-hoc per session, connected via `ANALYZED` edges. Never harden analysis into `runner.py`.
- **ConstitutionalAI is not optional** — every agent gates its output through it. Structure first, CAI last.
- **Never invent a new framework** — compose existing ones. Check `docs/foundations/composition_framework.md` first.
- **VOICE is retired** — replaced by COSTAR + PersonaLayer + ConstitutionalAI.
- **Spec Specialist has no fixed prompt** — it receives a CRISPE prompt generated at runtime by the Spec Advisor. This is the meta-prompting moment.
- **Consensus is deliberative** — Coordinator's ReAct loop gates every layer. Nothing writes to Kuzu without a `proceed` decision.

## Where to look

| Need | Document |
|---|---|
| Project overview, current milestone state | `README.md` |
| Architecture, agent tables, framework taxonomy | `ARCHITECTURE.md` |
| Framework composition, research grounding, one-shot examples | `docs/foundations/composition_framework.md` |
| Per-framework field reference | `docs/foundations/prompt_frameworks.md` |
| Kuzu ETL strategy, transform.cypher patterns | `docs/foundations/kuzu_etl_strategy.md` |
| Implementing a new agent, framework layer, or milestone | `docs/foundations/dev-guide.md` |
| Dev container setup, session modes, git workflow | `docs/running-with-claude.md` |
| Active tasks + milestone gates | `BACKLOG.md` |
| Verified milestones | `COMPLETED.md` |
| GNN signals, open hypotheses, Cypher queries | `analysis_opportunities.md` |
| Architecture decisions (ADRs) | `docs/decisions/` |
| Thesis arc + per-milestone hypotheses | `docs/thesis/CLAIM.md` |

## Git workflow

- **Never commit to `main` directly** — all work on branches; `main` is always green and proven
- **Branch naming:** `m{N}/description` (milestone), `chore/description` (docs/tooling), `fix/description` (bug), `analysis/hypothesis` (throwaway), `wip/description` (experimental, never PR'd)
- **Commit after every meaningful change** — gate tests passing, schema added, evidence file done, analysis findings written. If it would hurt to redo it, commit it.
- **One logical unit per commit** — do not batch unrelated changes
- **Conventional Commits format:** `feat(m4): add RevisionEvent`, `fix(schema): correct rel convention`, `chore(docs): add dev-guide`
- **Always** include `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>` in Claude-created commits
- Run `ruff check . && pyright src/` before committing any code change
- Never amend a pushed commit — new commit instead. Never force-push.
- Full workflow detail: `docs/running-with-claude.md` → Git workflow section
