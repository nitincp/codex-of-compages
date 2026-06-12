# Kuzu ETL Strategy — Schema Migration Between Milestones

## Problem

Kuzu has no `ALTER TABLE`. Once a node or relationship table is created, its schema is
frozen. When a milestone needs to change an existing table — add a column, change a type,
rename a property, change a relationship's FROM/TO types — the only path is:

> export old DB → transform → load new DB → retire old DB

This happens at milestone boundaries, not continuously. Most milestones add new tables
(handled by `CREATE ... IF NOT EXISTS`) and never trigger an ETL. ETL is only needed when
an existing table's structure must change.

## Approach: Blue-Green DB Rotation with Cypher Transform Queries

Two Kuzu database objects can be open simultaneously in Python. The migration runner holds
connections to both old and new DB throughout the process.

```
Old DB (data/kuzu)
      │
      ▼
transform.cypher executed against old DB
  COPY (MATCH ... WITH transforms RETURN ...) TO '{tmp}/Table.parquet'
      │
      ▼
New empty DB created from schema.cypher
      │
      ▼
COPY TableName FROM '{tmp}/Table.parquet'   ← bulk load, not row-by-row
      │
      ▼
Re-seed deterministic tables (e.g. FrameworkLayer) via runner.seed()
      │
      ▼
Verify: row counts + FK spot-checks + gate tests green
      │
      ▼
Rotate: mv data/kuzu → data/kuzu_bak_YYYYMMDD
        mv data/kuzu_new → data/kuzu
```

## Key Kuzu Capabilities Used

**`COPY (Cypher query) TO 'file.parquet'`**
Transforms happen entirely in Cypher. The `WITH` clause adds new columns with defaults,
renames via aliases, computes derived values. Verified in Kuzu 0.11.3.

**`COPY TableName FROM 'file.parquet'`**
Bulk load into the new DB. Handles relationships too:
`COPY REL_TABLE FROM 'file.parquet' (from='NodeA', to='NodeB')`.

**`IMPORT DATABASE / EXPORT DATABASE`**
Available but not the primary path — these are all-or-nothing and don't support
per-table transformation. Used as a fallback for full DB backup before rotation.

**Two DB objects open simultaneously**
Python can hold connections to old and new DB in one process. Verified: row counts
match, no locking conflicts.

**Parquet as the bridge**
Kuzu exports to Parquet; Kuzu imports from Parquet. PyArrow 24.0.0 is available if
Python-level transforms are needed (cross-table computations, conditional logic beyond
Cypher's `WITH`). For structural transforms (add column, rename, cast), pure Cypher
is sufficient and preferred.

## Deterministic vs Irreplaceable Data

| Category | Tables | ETL approach |
|---|---|---|
| Deterministic | `FrameworkLayer` | Re-seed from source code via `m1.graph.runner.seed()` |
| Irreplaceable | `MilestoneRun`, `SpecRun`, `AnalysisNote`, all rel tables | Transform Parquet + `COPY FROM` |

`FrameworkLayer` is 100% deterministic from `build()` calls on source code. Re-seeding
produces identical data under any new schema. Transforming stale records is both
unnecessary and error-prone.

## Migration File Structure

Each milestone that changes an existing table owns a `migration/` directory:

```
src/milestones/m{N}/migration/
  meta.json          ← source_milestone, target_milestone, reseed_tables
  schema.cypher      ← complete DDL for the target DB (snapshot)
  transform.cypher   ← all migration queries in sequence (executable + intent)
```

Milestones that only add new tables do not need a `migration/` directory.

### `schema.cypher` — The Snapshot

Full DDL for the new DB — every `CREATE NODE TABLE` and `CREATE REL TABLE` for all
tables that exist at this milestone. Used by the ETL runner to create the empty new DB.
Also used by the diff script for milestone comparison.

```cypher
CREATE NODE TABLE MilestoneRun (
  run_id STRING, milestone STRING, model STRING, timestamp STRING,
  PRIMARY KEY (run_id)
);

CREATE NODE TABLE SpecRun (
  id STRING, run_id STRING, milestone STRING, brief_label STRING,
  selected_lang STRING, layer STRING, confidence DOUBLE,
  justification_char_count INT64, latency_ms DOUBLE, model STRING,
  timestamp STRING, reasoning_step_count INT64, evaluation_depth DOUBLE,
  PRIMARY KEY (id)
);

-- ... all tables
```

### `transform.cypher` — Queries + Intent

All migration queries in one file, mirroring the structure of `schema.cypher`.
Each table gets a `COPY (query) TO parquet` block. Comments carry the intent —
WHY a default was chosen, WHAT the source schema was, WHAT changed.

```cypher
-- Transform: m2 → m3

-- MilestoneRun: unchanged
COPY (
  MATCH (n:MilestoneRun)
  RETURN n.run_id AS run_id, n.milestone AS milestone,
         n.model AS model, n.timestamp AS timestamp
) TO '{output_dir}/MilestoneRun.parquet'

-- SpecRun: + reasoning_step_count INT64, + evaluation_depth DOUBLE
--   reasoning_step_count: CoT steps were not counted in M2 (COSTAR structure only,
--     no explicit reasoning enumeration). Pre-M3 runs default to 0. Not comparable
--     to M3 runs on this dimension — GNN queries must filter by milestone.
--   evaluation_depth: Candidate evaluation was implicit in M2 output, not measured.
--     0.0 marks absence of measurement, not a zero-depth evaluation.
COPY (
  MATCH (n:SpecRun)
  WITH n.id AS id, n.run_id AS run_id, n.milestone AS milestone,
       n.brief_label AS brief_label, n.selected_lang AS selected_lang,
       n.layer AS layer, n.confidence AS confidence,
       n.justification_char_count AS justification_char_count,
       n.latency_ms AS latency_ms, n.model AS model, n.timestamp AS timestamp,
       0 AS reasoning_step_count,
       0.0 AS evaluation_depth
  RETURN *
) TO '{output_dir}/SpecRun.parquet'

-- REASONING_ADDS: new relationship in m3
COPY (
  MATCH (s:SpecRun)-[:SPEC_CAPTURED_IN]->(m:MilestoneRun)
  RETURN s.id AS from_id, m.run_id AS to_id
) TO '{output_dir}/REASONING_ADDS.parquet'
```

### `meta.json` — Runner Metadata

```json
{
  "source_milestone": "m2",
  "target_milestone": "m3",
  "reseed_tables": ["FrameworkLayer"]
}
```

`reseed_tables`: tables skipped by the transform runner and instead re-seeded from
source code after the new DB is created. These tables have no block in `transform.cypher`.

## ETL Runner and Diff Script

```
src/etl/
  migrate.py     ← CLI: python3 -m src.etl.migrate --to m3 [--dry-run]
  diff.py        ← CLI: python3 -m src.etl.diff m2 m5
```

### `migrate.py` — execution sequence

1. Read `src/milestones/m{N}/migration/meta.json`
2. Create temp output directory
3. Execute each `COPY (...) TO` block in `transform.cypher` against old DB
   (substituting `{output_dir}` with temp path)
4. Create new empty DB from `schema.cypher`
5. `COPY TableName FROM parquet` for each output file (nodes first, rels second)
6. Re-seed `reseed_tables` via their milestone runner's `seed()` function
7. Verify: row counts match source, FK spot-checks, gate tests
8. Rotate: `mv data/kuzu → data/kuzu_bak_YYYYMMDD`, `mv new → data/kuzu`

`--dry-run` stops before creating the new DB — lets you inspect transformed Parquet files.

### `diff.py` — schema comparison

Compares `schema.cypher` from two milestone migration directories:

```bash
python3 -m src.etl.diff m2 m5
```

```
Schema diff: m2 → m5
─────────────────────
NEW       SpecRun.reasoning_step_count INT64
NEW       SpecRun.evaluation_depth DOUBLE
NEW       REL REASONING_ADDS (SpecRun → MilestoneRun)
NEW       NODE VerificationRun
UNCHANGED MilestoneRun
UNCHANGED FrameworkLayer
```

Parses `CREATE NODE TABLE` and `CREATE REL TABLE` statements from both files,
diffs the column lists and table presence. No delta accumulation — reads two
complete snapshots directly.

## What Triggers an ETL

| Change type | ETL needed? |
|---|---|
| Add new node or rel table | No — `CREATE ... IF NOT EXISTS` |
| Add column to existing table | Yes |
| Remove column from existing table | Yes |
| Change column type | Yes |
| Rename column | Yes |
| Add second FROM type to existing rel table | Yes — Kuzu 0.11.3 cannot do this in-place |
| New cross-milestone edge between existing node types | No — new rel table |

## AnalysisNote: Special Handling

`AnalysisNote` is ad-hoc — its schema is invented per analytical session via
`CREATE NODE TABLE IF NOT EXISTS`. The ETL runner must discover its actual schema
at runtime before exporting:

```python
props = conn.execute('CALL table_info("AnalysisNote") RETURN *').get_as_df()
```

The `transform.cypher` block for `AnalysisNote` uses `RETURN n.*` rather than named
aliases, and the runner generates the column list dynamically. AnalysisNote columns
are never dropped — historical findings are permanent.

## Alternatives Considered and Rejected

**DuckDB via Kuzu extension**: Kuzu 0.11.3 has a DuckDB extension (`INSTALL duckdb`)
but it enables Kuzu to read DuckDB databases, not the reverse. DuckDB is not installed.
Adding it provides SQL transforms over PyArrow's compute API for simple structural
transforms — not justified until transforms require cross-table SQL joins.

**CocoIndex**: Designed for incremental index maintenance from changing source data.
Wrong abstraction for one-shot structural schema migration. Requires Python ≥ 3.11
(environment runs 3.10).

**LangChain Graph Transformers**: Extracts knowledge graphs from text documents via LLM.
Categorically wrong — schema migration is not knowledge extraction.

**NetworkX**: Graph algorithm library (`get_as_networkx()` is built into Kuzu's client).
Appropriate when migration requires topology reasoning (community detection, centrality
before reshaping). Faber's migrations through M13 are structural only; revisit at M10+
if cross-milestone graph structure needs algorithmic reshaping.

**Row-by-row Python inserts**: Verified feasible (two DB objects open simultaneously,
167ms for 8 rows). Not used — `COPY FROM parquet` is the correct bulk load path.
