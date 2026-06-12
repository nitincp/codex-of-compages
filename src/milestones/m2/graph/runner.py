"""
M2 runner — SpecRun GNN seed.

Captures per Spec Advisor call (M2 composition):
  selected_lang          — formal spec language chosen
  layer                  — spec layer targeted (system/domain/component/api)
  confidence             — model's reported confidence (0.0–1.0)
  justification_char_count — character length of justification text
  latency_ms             — wall-clock time for the agent call

Public API:
  seed(conn, output, brief_label, run_id, model, latency_ms) → str
    Ensures schema, writes one SpecRun node + SPEC_CAPTURED_IN edge.
    Returns the node id ("{run_id}:{brief_label}").

Analysis is intentionally NOT done here. Code captures; Claude analyzes.
"""

from __future__ import annotations

import datetime

import kuzu

from src.milestones.m2.schema import SpecAdvisorOutput

from .schema import ensure_schema


def seed(
    conn: kuzu.Connection,
    output: SpecAdvisorOutput,
    brief_label: str,
    run_id: str,
    model: str,
    latency_ms: float,
) -> str:
    """
    Write one SpecRun node + SPEC_CAPTURED_IN edge to an existing MilestoneRun.

    The MilestoneRun node must already exist in the DB (created by run.py before calling seed).
    Returns the SpecRun node id: "{run_id}:{brief_label}".
    """
    ensure_schema(conn)

    node_id = f"{run_id}:{brief_label}"
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"

    conn.execute(
        "CREATE (:SpecRun {"
        "id: $id, "
        "run_id: $run_id, "
        "milestone: 'm2', "
        "brief_label: $brief_label, "
        "selected_lang: $selected_lang, "
        "layer: $layer, "
        "confidence: $confidence, "
        "justification_char_count: $justification_char_count, "
        "latency_ms: $latency_ms, "
        "model: $model, "
        "timestamp: $timestamp"
        "})",
        parameters={
            "id": node_id,
            "run_id": run_id,
            "brief_label": brief_label,
            "selected_lang": output.selected_lang,
            "layer": output.layer,
            "confidence": output.confidence,
            "justification_char_count": len(output.justification),
            "latency_ms": latency_ms,
            "model": model,
            "timestamp": timestamp,
        },
    )
    conn.execute(
        "MATCH (s:SpecRun {id: $sid}), (r:MilestoneRun {run_id: $rid}) "
        "CREATE (s)-[:SPEC_CAPTURED_IN]->(r)",
        parameters={"sid": node_id, "rid": run_id},
    )

    return node_id
