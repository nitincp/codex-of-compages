# Running Faber with Claude

How to work with Claude Code effectively across multi-session, multi-milestone work.
The patterns here are specific to this project's structure — not generic advice.

---

## Three session modes

Every session is one of three modes. Name it before you start — it determines what Claude should load and how it should reason.

| Mode | Goal | Start by reading |
|---|---|---|
| **Coding** | Implement a milestone task from BACKLOG.md | `BACKLOG.md` → active task + success criteria |
| **Analysis** | Query the live GNN, surface signals, update hypotheses | `analysis_opportunities.md` → confirmed signals + open queries |
| **Planning** | Design a new milestone, ADR, or schema | `docs/foundations/composition_framework.md` + current `BACKLOG.md` section |

These modes do not mix cleanly. If you find yourself switching mid-session, `/clear` and restart in the new mode.

---

## When to /clear

- Before switching between modes (coding → analysis, analysis → planning)
- After a milestone is fully proven and committed (clean slate for the next one)
- When Claude starts making mistakes on things it got right earlier (context has degraded)
- After a long analysis session before starting any code changes

Do **not** `/clear` mid-analysis if you're accumulating context about signals — that context is the point.

---

## Coding session workflow

1. Read `README.md` for current milestone state
2. Find the next `[ ]` task in `BACKLOG.md` — confirm the previous gate is proven
3. Check prior milestone's evidence file (`docs/evidence/M0{N}.md`) for "Next Layer Can Rely On"
4. Implement, run gate tests, confirm all prior milestone tests still green
5. Update `BACKLOG.md` (mark `[x]`), create or fill in the evidence file
6. Commit on a named branch: `m{N}/short-description`

**Never start a new milestone before all prior gate tests pass.** This is the always-working-set invariant.

---

## Analysis session workflow

The feedback loop Claude operates in:

```
python3 -m src.milestones.m{N}.run      ← seed one subgraph (repeat N times)
        ↓
ad-hoc query script against data/kuzu   ← Claude writes and runs this
        ↓
read output, identify signal            ← Claude decides what's worth persisting
        ↓
CREATE NODE TABLE IF NOT EXISTS AnalysisNote (...)
CREATE REL TABLE IF NOT EXISTS ANALYZED (FROM AnalysisNote TO ...)
        ↓
update analysis_opportunities.md        ← confirmed finding + new hypotheses
```

**Before seeding:** check how many `MilestoneRun` nodes already exist for this milestone:
```cypher
MATCH (r:MilestoneRun) WHERE r.milestone = 'm{N}' RETURN count(r)
```
Typically run 3× for stable signal. More runs reduce variance; diminishing returns after 5–6.

**After analysis:** always update `analysis_opportunities.md` before ending the session. An analysis that isn't written back is lost.

---

## Hypothesis lifecycle

Track every hypothesis through three states — confirmed, open, abandoned. All three matter.

```
Confirmed signal
  Finding: [what is true, with evidence]
  Evidence: [which runs, which query, what numbers]
  Confidence: high | medium

Open hypothesis
  Prediction: [what you expect to find]
  Testable when: [which milestone seeded, which condition met]
  Ready query: [Cypher to run when available]

Abandoned direction
  What was tried: [the hypothesis]
  Why it failed: [what the data showed instead]
  Don't repeat: [the specific wrong turn]
```

Abandoned directions are as valuable as confirmed signals — they prevent re-exploring dead ends in future sessions. `analysis_opportunities.md` tracks all three types.

---

## AnalysisNote pattern

Schema is invented on the fly per session — no predetermined structure. Start minimal:

```python
conn.execute("""
    CREATE NODE TABLE IF NOT EXISTS AnalysisNote (
        id STRING,
        milestone STRING,
        finding STRING,
        hypothesis_id STRING,
        direction STRING,         -- 'confirmed' | 'open' | 'abandoned'
        metric_before DOUBLE,
        metric_after DOUBLE,
        PRIMARY KEY (id)
    )
""")
conn.execute("""
    CREATE REL TABLE IF NOT EXISTS ANALYZED (
        FROM AnalysisNote TO SpecRun
    )
""")
```

Add columns as the finding demands. Do not predefine what might be useful — the signal determines the schema.

---

## Debugging layer output

When a composed prompt produces unexpected output, the layer that caused it is not obvious from the final result alone. Two techniques:

**Technique 1 — Log every layer:**
```bash
FABER_LOG_PROMPTS=true python3 -m src.milestones.m{N}.run
```
Each `build()` call logs its output. Find the layer where the prompt drifts.

**Technique 2 — Isolate in the REPL:**
```python
from src.milestones.m{N}.frameworks.costar import COSTARPrompt
from src.milestones.m{N}.frameworks.chain_of_thought import ChainOfThought
from src.frameworks.composed import ComposedPrompt

prompt = ComposedPrompt([
    COSTARPrompt(objective="...", output="..."),
    ChainOfThought(task="..."),
]).build()
print(prompt)
```
Comment out layers one by one until the problem disappears.

---

## ETL trigger checklist

Before creating a migration, confirm you actually need one:

- [ ] Am I adding a **new** table? → `CREATE NODE TABLE IF NOT EXISTS`. No ETL.
- [ ] Am I changing an **existing** table's structure (add column, change type, rename)? → ETL needed.
- [ ] Is this a mid-milestone schema evolution? → Add `pass_{N+1}/` to an existing `migration/` dir.
- [ ] Is this a new-milestone change? → New `migration/` dir in the new milestone folder.

See `docs/foundations/kuzu_etl_strategy.md` for the full pattern.

---

## Cross-session grounding

At the start of any session where you're not sure what's been done:

```bash
# What milestones are seeded?
python3 scripts/graph_stats.py    # or:
# MATCH (r:MilestoneRun) RETURN r.milestone, count(r) as runs ORDER BY r.milestone

# What's proven?
# → README.md current state table

# What signals are confirmed, what's open?
# → analysis_opportunities.md

# What's the next task?
# → BACKLOG.md, first [ ] item
```

These four answers orient any session in under two minutes.

---

## What Claude should never do

- Put analysis logic in `runner.py` — the runner captures; Claude analyzes
- Create JSON/JSONL artifact files — data lives in Kuzu
- Invent a new framework layer — compose existing ones (`docs/foundations/composition_framework.md`)
- Start a new milestone before prior gate tests all pass
- Write to the persistent DB from gate tests
- Put `ANTHROPIC_API_KEY` in `.env`

---

## Python + Claude: project-specific techniques

### How Claude navigates this codebase

Claude reads `pyproject.toml` to understand the package structure and dependencies. It reads `src/frameworks/__init__.py` to know which frameworks are exported. It uses the `_dimension` class attribute and `build() -> str` signature as the canonical contract for all framework classes — these are the two things Claude checks first when asked about a framework.

**Type hints are load-bearing for Claude** — the Pydantic schemas in `src/agents/schemas.py` and the typed return values in `runner.py` give Claude the field names and types it needs to write correct Cypher queries and ad-hoc analysis scripts without reading the full implementation. Keep them accurate.

### Running ad-hoc analysis scripts

Claude writes and runs scripts inline, not as committed files. Pattern:

```python
# scripts are ephemeral — run via python3, not stored
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

Save the output; discard the script. The output informs the `AnalysisNote` schema. The script is not the artifact.

### Leveraging pyright for fast Claude feedback loops

Before running a milestone, ask Claude to type-check the new code:

```bash
pyright src/milestones/m{N}/
```

Pyright catches field name mismatches between the Pydantic schema and the Kuzu INSERT immediately — much faster than discovering them at runtime. Claude should run this before every `seed()` implementation is considered done.

### Package isolation for milestone frameworks

Each milestone copies framework builders into `src/milestones/m{N}/frameworks/` and imports from there — not from `src/frameworks/`. This means Claude can safely modify a framework for a future milestone without breaking prior milestone's frozen copies.

If Claude tries to `from src.frameworks.costar import COSTARPrompt` inside a milestone, it is wrong — redirect to the local copy.

### When Claude writes Cypher queries

Kuzu's Cypher dialect differences from Neo4j that trip up Claude:
- **No `WITH ... LIMIT`** as a pagination pattern — use `RETURN ... LIMIT N` directly
- **`COPY REL FROM`** requires `(from='col', to='col')` named params — not positional
- **Node IDs are string PKs** in this project — not auto-generated integers. Always query by `{id: "run_id:name"}` pattern, not by internal ID.
- **`CREATE NODE TABLE IF NOT EXISTS`** — the `IF NOT EXISTS` clause is what enables ad-hoc AnalysisNote schema creation without erroring on second run.

### Anthropic SDK patterns used in this project

All agents use:
- `client.messages.create(model=..., tools=[...], tool_choice={"type": "any"})` — forced tool use, never `"auto"`
- `response.content[0].input` — the tool call result (a dict matching the Pydantic schema)
- `self._log_usage(response.usage)` — always called after every API call

If Claude writes an agent that uses `tool_choice="auto"` or accesses `response.content[0].text`, it is wrong for this project's pattern.
