"""
M3 runner — SpecRun (with reasoning) + REASONING_ADDS GNN seed.

Captures per Spec Advisor call (M3 composition: COSTAR + ChainOfThought):
  selected_lang              — formal spec language chosen
  layer                      — spec layer targeted
  confidence                 — model's reported confidence
  justification_char_count   — character length of justification
  reasoning_step_count       — number of CoT steps produced
  evaluation_depth           — 'per_concern' if steps name candidates, else 'conclusion_only'
  latency_ms                 — wall-clock time for the agent call

Also writes a REASONING_ADDS edge from the matched M2 SpecRun to the M3 SpecRun,
carrying the delta signal produced by adding the CoT layer.

Public API:
  seed(conn, output, brief_label, run_id, model, latency_ms, m2_run_id=None) → str
    Ensures schema, writes one SpecRun node + SPEC_CAPTURED_IN edge.
    If m2_run_id is provided, also writes REASONING_ADDS edge from matched M2 SpecRun.
    Returns the node id ("{run_id}:{brief_label}").

  infer_evaluation_depth(steps) → str
    Classifies reasoning depth: 'per_concern' if any step names a candidate language.

Analysis is intentionally NOT done here. Code captures; Claude analyzes.
"""

from __future__ import annotations

import datetime
import re

import kuzu

from src.milestones.m3.schema import SpecAdvisorOutput

from .schema import ensure_schema

_LANG_KEYWORDS = {
    "json schema", "openapi", "pydantic", "tla+", "tla", "cml",
    "alloy", "event-b", "eventb",
}


def infer_evaluation_depth(steps: list[str]) -> str:
    """'per_concern' if any step names a candidate language, else 'conclusion_only'."""
    combined = " ".join(steps).lower()
    for kw in _LANG_KEYWORDS:
        if kw in combined:
            return "per_concern"
    return "conclusion_only"


def _infer_candidate_rejection(steps: list[str]) -> bool:
    """True if any step explicitly dismisses or rejects a candidate language."""
    dismissal_patterns = [
        r"\b(dismiss|rule out|not suitable|rejected|too|over-engineered|unnecessary|"
        r"no concurrency|no distributed|absent|deferred|not dominant|does not)\b",
    ]
    combined = " ".join(steps).lower()
    for pattern in dismissal_patterns:
        if re.search(pattern, combined):
            return True
    return False


def seed(
    conn: kuzu.Connection,
    output: SpecAdvisorOutput,
    brief_label: str,
    run_id: str,
    model: str,
    latency_ms: float,
    m2_run_id: str | None = None,
) -> str:
    """
    Write one M3 SpecRun node + SPEC_CAPTURED_IN edge.

    If m2_run_id is given and a matching M2 SpecRun exists for the same brief_label,
    writes a REASONING_ADDS edge from that M2 node to this M3 node.

    Returns the SpecRun node id: "{run_id}:{brief_label}".
    """
    ensure_schema(conn)

    node_id = f"{run_id}:{brief_label}"
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    step_count = len(output.reasoning_steps)
    eval_depth = infer_evaluation_depth(output.reasoning_steps)

    conn.execute(
        "CREATE (:SpecRun {"
        "id: $id, "
        "run_id: $run_id, "
        "milestone: 'm3', "
        "brief_label: $brief_label, "
        "selected_lang: $selected_lang, "
        "layer: $layer, "
        "confidence: $confidence, "
        "justification_char_count: $justification_char_count, "
        "reasoning_step_count: $reasoning_step_count, "
        "evaluation_depth: $evaluation_depth, "
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
            "reasoning_step_count": step_count,
            "evaluation_depth": eval_depth,
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

    if m2_run_id is not None:
        m2_node_id = f"{m2_run_id}:{brief_label}"
        # Check that the M2 SpecRun exists before creating the cross-schema edge
        result = conn.execute(
            "MATCH (s:SpecRun {id: $sid}) RETURN s.confidence",
            parameters={"sid": m2_node_id},
        )
        rows = result.get_all() if hasattr(result, "get_all") else list(result)
        if rows:
            m2_confidence = rows[0][0]
            confidence_delta = round(output.confidence - m2_confidence, 4)
            adds_rejection = _infer_candidate_rejection(output.reasoning_steps)
            conn.execute(
                "MATCH (m2:SpecRun {id: $m2id}), (m3:SpecRun {id: $m3id}) "
                "CREATE (m2)-[:REASONING_ADDS {"
                "confidence_delta: $confidence_delta, "
                "step_count: $step_count, "
                "evaluation_depth: $evaluation_depth, "
                "adds_candidate_rejection: $adds_rejection"
                "}]->(m3)",
                parameters={
                    "m2id": m2_node_id,
                    "m3id": node_id,
                    "confidence_delta": confidence_delta,
                    "step_count": step_count,
                    "evaluation_depth": eval_depth,
                    "adds_rejection": adds_rejection,
                },
            )

    return node_id
