"""
M4 Kuzu schema contribution.

Schema owned by M4:

  SpecRun (node) — extends M3's SpecRun with two new fields:
    revised        BOOLEAN  — True if CAI critique triggered a revision
    revision_notes STRING   — which principle was violated; empty if revised=False

  RevisionEvent (node) — one per brief per run; captures the CAI critique outcome:
    id                       STRING   — "{run_id}:{brief_label}"
    run_id                   STRING
    brief_label              STRING
    revised                  BOOLEAN
    cai_principle_triggered  STRING   — "" if no principle triggered
    assumption_inventory_added BOOLEAN — True if vague brief forced assumption declaration

  VERIFICATION_ADDS (rel)
    FROM SpecRun (m3) TO SpecRun (m4)
    Cross-schema edge — the ML signal produced by adding CAI to COSTAR+CoT.
    Properties:
      revised                    BOOLEAN
      confidence_delta           DOUBLE   — m4.confidence - m3.confidence
      cai_principle_triggered    STRING
      signal_count_below_threshold INT64  — 1 if vague brief triggered, else 0
      assumption_inventory_added BOOLEAN

  REASONING_ADDS (rel) — defined by M3; M4 reuses via IF NOT EXISTS.
  SPEC_CAPTURED_IN (rel) — defined by M2; M4 reuses via IF NOT EXISTS.
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
    # M4 SpecRun — superset of M3 SpecRun; adds revised + revision_notes.
    # Created fresh in ephemeral gate-test DBs. In the persistent DB, ETL migration
    # handles the column additions (blue-green rotation).
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
        "revised BOOLEAN, "
        "revision_notes STRING, "
        "latency_ms DOUBLE, "
        "model STRING, "
        "timestamp STRING, "
        "PRIMARY KEY (id)"
        ")"
    )
    conn.execute("CREATE REL TABLE IF NOT EXISTS SPEC_CAPTURED_IN (FROM SpecRun TO MilestoneRun)")
    conn.execute(
        "CREATE REL TABLE IF NOT EXISTS REASONING_ADDS ("
        "FROM SpecRun TO SpecRun, "
        "confidence_delta DOUBLE, "
        "step_count INT64, "
        "evaluation_depth STRING, "
        "adds_candidate_rejection BOOLEAN"
        ")"
    )
    conn.execute(
        "CREATE NODE TABLE IF NOT EXISTS RevisionEvent ("
        "id STRING, "
        "run_id STRING, "
        "brief_label STRING, "
        "revised BOOLEAN, "
        "cai_principle_triggered STRING, "
        "assumption_inventory_added BOOLEAN, "
        "PRIMARY KEY (id)"
        ")"
    )
    conn.execute(
        "CREATE REL TABLE IF NOT EXISTS VERIFICATION_ADDS ("
        "FROM SpecRun TO SpecRun, "
        "revised BOOLEAN, "
        "confidence_delta DOUBLE, "
        "cai_principle_triggered STRING, "
        "signal_count_below_threshold INT64, "
        "assumption_inventory_added BOOLEAN"
        ")"
    )
