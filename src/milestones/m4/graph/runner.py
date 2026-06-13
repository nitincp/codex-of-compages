"""
M4 runner — SpecRun (with CAI verification) + RevisionEvent + VERIFICATION_ADDS GNN seed.

Captures per Spec Advisor call (M4 composition: COSTAR + ChainOfThought + ConstitutionalAI):
  selected_lang              — formal spec language chosen
  layer                      — spec layer targeted
  confidence                 — model's reported confidence
  justification_char_count   — character length of justification
  reasoning_step_count       — number of CoT steps produced
  evaluation_depth           — 'per_concern' if steps name candidates, else 'conclusion_only'
  revised                    — True if CAI critique triggered a revision
  revision_notes             — description of what changed; empty if revised=False
  latency_ms                 — wall-clock time for the agent call

Also writes:
  RevisionEvent node — one per brief per run, capturing the CAI critique outcome
  VERIFICATION_ADDS edge — from matched M3 SpecRun to this M4 SpecRun (if m3_run_id given)

Public API:
  seed(conn, output, brief_label, run_id, model, latency_ms, m3_run_id=None) → str
    Ensures schema, writes one SpecRun node + SPEC_CAPTURED_IN + RevisionEvent.
    If m3_run_id is provided and a matching M3 SpecRun exists, writes VERIFICATION_ADDS.
    Returns the SpecRun node id ("{run_id}:{brief_label}").

  infer_cai_principle_triggered(output) → str
    "" if revised=False; "vague_brief_assumption_required" if confidence < 0.75; else
    "justification_or_reasoning_specificity".

  infer_assumption_inventory_added(output) → bool
    True if vague brief forced confidence < 0.75 and revised=True.

  infer_signal_count_below_threshold(output) → int
    1 if assumption_inventory_added, else 0.

Analysis is intentionally NOT done here. Code captures; Claude analyzes.
"""

from __future__ import annotations

import datetime
import re

import kuzu

from src.milestones.m3.graph.runner import infer_evaluation_depth
from src.milestones.m4.schema import SpecAdvisorOutput

from .schema import ensure_schema


def infer_cai_principle_triggered(output: SpecAdvisorOutput) -> str:
    if not output.revised:
        return ""
    if output.confidence < 0.75:
        return "vague_brief_assumption_required"
    return "justification_or_reasoning_specificity"


def infer_assumption_inventory_added(output: SpecAdvisorOutput) -> bool:
    return output.revised and output.confidence < 0.75


def infer_signal_count_below_threshold(output: SpecAdvisorOutput) -> int:
    return 1 if infer_assumption_inventory_added(output) else 0


def _infer_candidate_rejection(steps: list[str]) -> bool:
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
    m3_run_id: str | None = None,
) -> str:
    """
    Write one M4 SpecRun node + SPEC_CAPTURED_IN edge + RevisionEvent node.

    If m3_run_id is given and a matching M3 SpecRun exists for the same brief_label,
    writes a VERIFICATION_ADDS edge from that M3 node to this M4 node.

    Returns the SpecRun node id: "{run_id}:{brief_label}".
    """
    ensure_schema(conn)

    node_id = f"{run_id}:{brief_label}"
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    step_count = len(output.reasoning_steps)
    eval_depth = infer_evaluation_depth(output.reasoning_steps)
    cai_principle = infer_cai_principle_triggered(output)
    assumption_added = infer_assumption_inventory_added(output)
    signals_below = infer_signal_count_below_threshold(output)

    conn.execute(
        "CREATE (:SpecRun {"
        "id: $id, "
        "run_id: $run_id, "
        "milestone: 'm4', "
        "brief_label: $brief_label, "
        "selected_lang: $selected_lang, "
        "layer: $layer, "
        "confidence: $confidence, "
        "justification_char_count: $justification_char_count, "
        "reasoning_step_count: $reasoning_step_count, "
        "evaluation_depth: $evaluation_depth, "
        "revised: $revised, "
        "revision_notes: $revision_notes, "
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
            "revised": output.revised,
            "revision_notes": output.revision_notes,
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

    # RevisionEvent — one per brief per run
    conn.execute(
        "CREATE (:RevisionEvent {"
        "id: $id, "
        "run_id: $run_id, "
        "brief_label: $brief_label, "
        "revised: $revised, "
        "cai_principle_triggered: $cai_principle, "
        "assumption_inventory_added: $assumption_added"
        "})",
        parameters={
            "id": node_id,
            "run_id": run_id,
            "brief_label": brief_label,
            "revised": output.revised,
            "cai_principle": cai_principle,
            "assumption_added": assumption_added,
        },
    )

    if m3_run_id is not None:
        m3_node_id = f"{m3_run_id}:{brief_label}"
        result = conn.execute(
            "MATCH (s:SpecRun {id: $sid}) RETURN s.confidence",
            parameters={"sid": m3_node_id},
        )
        rows = result.get_all() if hasattr(result, "get_all") else list(result)
        if rows:
            m3_confidence = rows[0][0]
            confidence_delta = round(output.confidence - m3_confidence, 4)
            conn.execute(
                "MATCH (m3:SpecRun {id: $m3id}), (m4:SpecRun {id: $m4id}) "
                "CREATE (m3)-[:VERIFICATION_ADDS {"
                "revised: $revised, "
                "confidence_delta: $confidence_delta, "
                "cai_principle_triggered: $cai_principle, "
                "signal_count_below_threshold: $signals_below, "
                "assumption_inventory_added: $assumption_added"
                "}]->(m4)",
                parameters={
                    "m3id": m3_node_id,
                    "m4id": node_id,
                    "revised": output.revised,
                    "confidence_delta": confidence_delta,
                    "cai_principle": cai_principle,
                    "signals_below": signals_below,
                    "assumption_added": assumption_added,
                },
            )

    return node_id
