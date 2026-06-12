"""
M3 Kuzu schema contribution.

Schema owned by M3:

  SpecRun (node) — extends M2's SpecRun with two new fields:
    reasoning_step_count  INT64   — number of CoT steps produced (≥3 expected)
    evaluation_depth      STRING  — 'per_concern' | 'conclusion_only' | 'unknown'

  M3 adds to the shared SpecRun table (no new node table — same table, new columns added
  via ETL migration when upgrading from M2). Within the M3 milestone runner, the full
  extended schema is created directly.

  REASONING_ADDS (rel)
    FROM SpecRun (m2) TO SpecRun (m3)
    Cross-schema edge — the ML signal produced by adding CoT to COSTAR.
    Properties:
      confidence_delta          DOUBLE   — m3.confidence - m2.confidence (positive = gain)
      step_count                INT64    — number of reasoning steps in the M3 run
      evaluation_depth          STRING   — 'per_concern' | 'conclusion_only'
      adds_candidate_rejection  BOOLEAN  — True if any step explicitly dismisses a candidate lang

  SPEC_CAPTURED_IN (rel) — defined by M2; M3 reuses via IF NOT EXISTS.
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
    # M3 SpecRun — superset of M2 SpecRun; adds reasoning_step_count + evaluation_depth.
    # Created fresh in ephemeral gate-test DBs. In the persistent DB, ETL migration handles
    # the ALTER TABLE equivalent (blue-green rotation).
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
        "reasoning_step_count INT64, "
        "evaluation_depth STRING, "
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
    conn.execute(
        "CREATE REL TABLE IF NOT EXISTS REASONING_ADDS ("
        "FROM SpecRun TO SpecRun, "
        "confidence_delta DOUBLE, "
        "step_count INT64, "
        "evaluation_depth STRING, "
        "adds_candidate_rejection BOOLEAN"
        ")"
    )
