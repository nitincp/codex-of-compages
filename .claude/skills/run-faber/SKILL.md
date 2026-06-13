---
name: run-faber
description: Run, test, and drive the Faber project — gate tests, milestone runners, ETL, Streamlit dashboard. Use when asked to run, test, start, seed, or verify Faber.
---

# run-faber

Faber is a Python prompt engineering project. Its runnable surfaces are:
- **Gate tests** — fast, ephemeral, no API key needed
- **Milestone runners** — seed subgraphs into persistent `data/kuzu` (M2+ need `ANTHROPIC_API_KEY`)
- **ETL** — blue-green Kuzu schema migration
- **Streamlit dashboard** — web UI on port 8000

All commands run from `/workspace`. Driver: `.claude/skills/run-faber/smoke.sh`.

---

## Prerequisites

```bash
# Secrets (required for M2+ runners only — gate tests run without it)
source .devcontainer/bootstrap-secrets.sh

# Packages are pre-installed in the devcontainer; if missing:
# python3 -m pip install -e ".[dev]"
```

Verified working: `python3 -c "import kuzu, streamlit, anthropic; print('ok')"`

---

## Gate tests (agent path — most common)

```bash
# All proven milestones (M1 M2 M3 + ETL) — 67 tests, ~13s, no API key
bash .claude/skills/run-faber/smoke.sh tests

# Single milestone
bash .claude/skills/run-faber/smoke.sh m1
bash .claude/skills/run-faber/smoke.sh m3

# Direct pytest (same thing, more control)
python3 -m pytest src/milestones/m1/tests/ -q
python3 -m pytest src/milestones/m1/tests/ src/milestones/m2/tests/ src/milestones/m3/tests/ tests/etl/ -q
```

Gate tests use an ephemeral tmp Kuzu DB — they never touch `data/kuzu`.

---

## Milestone runners (seed persistent DB)

```bash
# M1 — no API key needed (pure Python, no LLM calls)
bash .claude/skills/run-faber/smoke.sh run m1

# M2, M3, M4 — require ANTHROPIC_API_KEY in environment
python3 -m src.milestones.m2.run               # auto run_id
python3 -m src.milestones.m3.run my-run-id     # explicit run_id

# Check what's seeded
python3 -c "
import kuzu
db = kuzu.Database('data/kuzu')
conn = kuzu.Connection(db)
r = conn.execute('MATCH (n:MilestoneRun) RETURN n.run_id, n.milestone ORDER BY n.timestamp')
while r.has_next(): print(r.get_next())
"
```

Run the same milestone N times to accumulate N subgraphs (3 runs = stable signal).

---

## ETL — schema migration

```bash
# Dry run (no DB changes)
python3 -m src.etl.migrate --to m3 --dry-run

# Live migration (blue-green rotation: data/kuzu → data/kuzu_bak_DATE, new → data/kuzu)
python3 -m src.etl.migrate --to m3

# Diff two milestone schemas
python3 -m src.etl.diff m2 m3
```

---

## Streamlit dashboard

```bash
# Start (blocks — Ctrl-C to stop)
streamlit run src/ui/dashboard.py --server.port 8000 --server.headless true

# Smoke-verify it serves (background + curl + kill)
bash .claude/skills/run-faber/smoke.sh dashboard
```

Dashboard is on port 8000. It's a dev/demo UI — milestone runners are the primary data path.

---

## Gotchas

- **`pip` not on PATH** — use `python3 -m pip` or `pip3`. In the devcontainer, packages are pre-installed.
- **M2+ runners need API key** — M1 runner is pure Python (framework builders, no LLM). M2+ call `anthropic`. Without the key they fail immediately with an auth error.
- **Gate tests vs persistent DB** — gate tests create a tmpdir Kuzu DB and discard it. They will never conflict with `data/kuzu`. The runner always writes to `data/kuzu`.
- **Streamlit `python3 -m streamlit`** — `streamlit` binary may not be on PATH; `python3 -m streamlit run ...` always works.
- **`src` import path** — all `python3 -m src.milestones.*` commands must be run from `/workspace` (the repo root). Subdir `cd` breaks the import path.
- **M4 runner not yet seeded** — M4.1 M4 is the active milestone. `src/milestones/m4/` exists for migration only; the GNN runner is not yet built.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'src'` | Run from `/workspace`, not a subdirectory |
| `kuzu.RuntimeError: Cannot open DB` | Another Python process has `data/kuzu` open. Kill it. |
| `anthropic.AuthenticationError` | Source secrets: `source .devcontainer/bootstrap-secrets.sh` |
| `streamlit: command not found` | Use `python3 -m streamlit run ...` |
| Gate tests pass but runner fails | Runner calls live LLM; gate tests do not. Check API key. |
