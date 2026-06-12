"""
M1 Kuzu schema contribution.

Schema owned by M1:

  MilestoneRun (node)
    run_id     PK — e.g. "m1-20260612-001" or caller-supplied label
    milestone  "m1"
    model      model identifier used for this run (or "local" for pure Python runs)
    timestamp  ISO-8601 UTC

  FrameworkLayer (node)
    id         PK — "{run_id}:{name}" — unique per run, allows multiple runs to coexist
    name       framework class name (e.g. "COSTARPrompt") — queryable across runs
    run_id     which MilestoneRun this node belongs to
    dimension  Structure | Reasoning | Verification | Technique
    build_output   actual prompt text produced by build() — the GNN node feature
    file_path      path relative to milestones/m1/ (e.g. "frameworks/costar.py")
    file_hash      SHA-256 hex of file content — change detection across runs
    file_size_bytes source file size in bytes
    build_time_ms  time to execute build() in milliseconds
    output_char_count  character length of build_output
    output_token_est   token estimate (chars // 4, GPT-style heuristic)

  CAPTURED_IN (rel)
    FrameworkLayer → MilestoneRun
    Each FrameworkLayer node is anchored to the run that produced it.
    Subgraph isolation: MATCH (r:MilestoneRun {run_id: $rid})<-[:CAPTURED_IN]-(f)

Schema is intentionally raw — no derived or analytical columns.
Analysis is Claude's responsibility per session; written to analysis_opportunities.md.
"""

import kuzu


def ensure_schema(conn: kuzu.Connection) -> None:
    conn.execute(
        "CREATE NODE TABLE IF NOT EXISTS MilestoneRun ("
        "run_id STRING, "
        "milestone STRING, "
        "model STRING, "
        "timestamp STRING, "
        "PRIMARY KEY (run_id)"
        ")"
    )
    conn.execute(
        "CREATE NODE TABLE IF NOT EXISTS FrameworkLayer ("
        "id STRING, "
        "name STRING, "
        "run_id STRING, "
        "dimension STRING, "
        "build_output STRING, "
        "file_path STRING, "
        "file_hash STRING, "
        "file_size_bytes INT64, "
        "build_time_ms DOUBLE, "
        "output_char_count INT64, "
        "output_token_est INT64, "
        "PRIMARY KEY (id)"
        ")"
    )
    conn.execute(
        "CREATE REL TABLE IF NOT EXISTS CAPTURED_IN "
        "(FROM FrameworkLayer TO MilestoneRun)"
    )
