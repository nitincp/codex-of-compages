"""
M5 Kuzu schema contribution.

Schema owned by M5:

  SpecRun (node) — extends M4's SpecRun with one new field:
    specialist_crispe_prompt  STRING  — the CRISPE meta-prompt generated for the Spec Specialist

  MetaPromptEvent (node) — one per brief per run; captures CRISPE quality signals:
    id                    STRING   — "{run_id}:{brief_label}"
    run_id                STRING
    brief_label           STRING
    crispe_field_count    INT64    — number of non-empty CRISPE sections (6 expected)
    capacity_char_count   INT64    — char count of the Capacity section
    insight_char_count    INT64    — char count of the Insight section
    statement_char_count  INT64    — char count of the Statement section
    capacity_matches_lang BOOLEAN  — True if selected_lang appears in capacity text

  META_PROMPT_ADDS (rel)
    FROM SpecRun (m4) TO SpecRun (m5) — all 3 briefs (first full cross-schema coverage)
    Properties:
      crispe_field_count    INT64
      prompt_char_count     INT64    — total char count of the full CRISPE prompt
      capacity_matches_lang BOOLEAN

  ANALYZED_META (rel) — FROM AnalysisNote TO MetaPromptEvent (for Claude-in-loop)

  REASONING_ADDS, VERIFICATION_ADDS, SPEC_CAPTURED_IN — defined earlier; reused via IF NOT EXISTS.
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
    # M5 SpecRun — superset of M4; adds specialist_crispe_prompt.
    # Created fresh in ephemeral gate-test DBs. In the persistent DB, ETL migration
    # handles the column addition (blue-green rotation).
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
        "specialist_crispe_prompt STRING, "
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
    conn.execute(
        "CREATE NODE TABLE IF NOT EXISTS MetaPromptEvent ("
        "id STRING, "
        "run_id STRING, "
        "brief_label STRING, "
        "crispe_field_count INT64, "
        "capacity_char_count INT64, "
        "insight_char_count INT64, "
        "statement_char_count INT64, "
        "capacity_matches_lang BOOLEAN, "
        "PRIMARY KEY (id)"
        ")"
    )
    conn.execute(
        "CREATE REL TABLE IF NOT EXISTS META_PROMPT_ADDS ("
        "FROM SpecRun TO SpecRun, "
        "crispe_field_count INT64, "
        "prompt_char_count INT64, "
        "capacity_matches_lang BOOLEAN"
        ")"
    )
    conn.execute(
        "CREATE NODE TABLE IF NOT EXISTS AnalysisNote ("
        "id STRING, "
        "session STRING, "
        "by STRING, "
        "subject STRING, "
        "signal STRING, "
        "value STRING, "
        "note STRING, "
        "milestone STRING, "
        "hypothesis_id STRING, "
        "direction STRING, "
        "metric_before DOUBLE, "
        "metric_after DOUBLE, "
        "PRIMARY KEY (id)"
        ")"
    )
    conn.execute(
        "CREATE REL TABLE IF NOT EXISTS ANALYZED_META (FROM AnalysisNote TO MetaPromptEvent)"
    )
