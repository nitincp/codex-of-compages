# Running Faber with Claude

How to work with Claude Code effectively across multi-session, multi-milestone work.

**Setup:** `.devcontainer/README.md` | **Git workflow:** `docs/git-workflow.md` | **Python techniques:** `docs/foundations/dev-guide.md`

---

## Three session modes

| Mode | Goal | Start by reading |
|---|---|---|
| **Coding** | Implement a milestone task | `BACKLOG.md` → active task + success criteria |
| **Analysis** | Query the live GNN, surface signals | `analysis_opportunities.md` → confirmed signals + open queries |
| **Planning** | Design a new milestone, ADR, or schema | `docs/foundations/composition_framework.md` + `BACKLOG.md` |

These modes do not mix cleanly. If you find yourself switching mid-session, `/clear` and restart in the new mode.

---

## When to /clear

- Before switching modes (coding → analysis, analysis → planning)
- After a milestone is fully proven and committed
- When Claude starts making mistakes on things it got right earlier (context has degraded)

Do **not** `/clear` mid-analysis if you're accumulating context about signals — that context is the point.

---

## Coding session workflow

1. Read `README.md` for current milestone state
2. Find the next `[ ]` task in `BACKLOG.md` — confirm the previous gate is proven
3. Read `docs/evidence/M0{N-1}.md` → "Next Layer Can Rely On" before starting
4. Implement, run gate tests, confirm all prior milestone tests still green
5. Mark `[x]` in `BACKLOG.md`, create or fill in the evidence file
6. Commit on a named branch: `m{N}/short-description`

**Never start a new milestone before all prior gate tests pass.**

---

## Analysis session workflow

```
python3 -m src.milestones.m{N}.run      ← seed one subgraph (repeat N times)
        ↓
ad-hoc query script against data/kuzu   ← Claude writes and runs this (ephemeral)
        ↓
read output, identify signal            ← Claude decides what's worth persisting
        ↓
CREATE NODE TABLE IF NOT EXISTS AnalysisNote (...)
CREATE REL TABLE IF NOT EXISTS ANALYZED (FROM AnalysisNote TO ...)
        ↓
update analysis_opportunities.md        ← confirmed finding + new hypotheses
```

**Before seeding:** check existing run count:
```cypher
MATCH (r:MilestoneRun) WHERE r.milestone = 'm{N}' RETURN count(r)
```
3 runs gives stable signal. Diminishing returns after 5–6.

**After analysis:** always update `analysis_opportunities.md` before ending. An analysis not written back is lost.

---

## Hypothesis lifecycle

Track every hypothesis in three states — all three matter:

```
Confirmed signal
  Finding: [what is true, with evidence]
  Evidence: [which runs, which query, what numbers]

Open hypothesis
  Prediction: [what you expect]
  Testable when: [condition]
  Ready query: [Cypher to run]

Abandoned direction
  What was tried: [the hypothesis]
  Why it failed: [what the data showed]
  Don't repeat: [the specific wrong turn]
```

Abandoned directions prevent re-exploring dead ends. `analysis_opportunities.md` tracks all three.

---

## AnalysisNote pattern

Schema is invented on the fly — no predetermined structure. Start minimal, add columns as the finding demands:

```python
conn.execute("""
    CREATE NODE TABLE IF NOT EXISTS AnalysisNote (
        id STRING, milestone STRING, finding STRING,
        hypothesis_id STRING,
        direction STRING,         -- 'confirmed' | 'open' | 'abandoned'
        metric_before DOUBLE, metric_after DOUBLE,
        PRIMARY KEY (id)
    )
""")
conn.execute("CREATE REL TABLE IF NOT EXISTS ANALYZED (FROM AnalysisNote TO SpecRun)")
```

---

## Debugging layer output

**Log every layer:**
```bash
FABER_LOG_PROMPTS=true python3 -m src.milestones.m{N}.run
```
Each `build()` call logs output. Find the layer where the prompt drifts.

**Isolate in the REPL:** import one layer at a time, call `.build()`, print. Comment out layers until the problem disappears.

---

## ETL trigger checklist

- Adding a **new** table → `CREATE NODE TABLE IF NOT EXISTS`. No ETL.
- Changing an **existing** table → blue-green rotation via `src/etl/migrate.py`. See `docs/foundations/kuzu_etl_strategy.md`.
- Mid-milestone schema evolution → add `pass_{N+1}/` to the existing `migration/` dir.
- New-milestone change → new `migration/` dir in the new milestone folder.

---

## Cross-session orientation (< 2 min)

```bash
# What milestones are seeded?
python3 scripts/graph_stats.py

# What's proven?     → README.md current state table
# What's open?       → analysis_opportunities.md
# What's next?       → BACKLOG.md, first [ ] item
```

---

## What Claude must never do

- Put analysis logic in `runner.py` — the runner captures; Claude analyzes
- Create JSON/JSONL artifact files — data lives in Kuzu
- Invent a new framework layer — compose existing ones
- Start a new milestone before prior gate tests all pass
- Write to the persistent DB from gate tests
- Put `ANTHROPIC_API_KEY` in `.env`
- Commit directly to `main`
