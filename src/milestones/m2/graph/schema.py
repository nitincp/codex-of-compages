"""
M2 Kuzu schema contribution.

Schema owned by M2:

  SpecRun (node)
    id         PK — "{run_id}:{brief_label}" — unique per run per brief
    run_id     which MilestoneRun this node belongs to
    milestone  "m2" (or "m3", "m4" — shared across spec council milestones)
    brief_label  short identifier for the project brief (e.g. "simple", "complex")
    selected_lang  formal spec language chosen (e.g. "OpenAPI", "TLA+")
    layer          spec layer targeted: system | domain | component | api
    confidence     0.0–1.0 — model's reported confidence in the selection
    justification_char_count  character length of justification text
    latency_ms     wall-clock time for the agent call in milliseconds
    model          model identifier used for this run
    timestamp      ISO-8601 UTC

  SPEC_CAPTURED_IN (rel)
    SpecRun → MilestoneRun
    M2-owned anchoring relationship. Named distinctly from M1's CAPTURED_IN
    (FROM FrameworkLayer TO MilestoneRun) to avoid Kuzu rel-table type conflicts.
    Subgraph isolation: MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s)

MilestoneRun is defined by M1; CREATE NODE TABLE IF NOT EXISTS is a no-op when it exists.
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
        "CREATE NODE TABLE IF NOT EXISTS SpecRun ("
        "id STRING, "
        "run_id STRING, "
        "milestone STRING, "
        "brief_label STRING, "
        "selected_lang STRING, "
        "layer STRING, "
        "confidence DOUBLE, "
        "justification_char_count INT64, "
        "latency_ms DOUBLE, "
        "model STRING, "
        "timestamp STRING, "
        "PRIMARY KEY (id)"
        ")"
    )
    conn.execute(
        "CREATE REL TABLE IF NOT EXISTS SPEC_CAPTURED_IN "
        "(FROM SpecRun TO MilestoneRun)"
    )
