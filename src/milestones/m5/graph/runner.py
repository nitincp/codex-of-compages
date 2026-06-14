"""
M5 runner — SpecRun (with CRISPE meta-prompt) + MetaPromptEvent + META_PROMPT_ADDS GNN seed.

Captures per Spec Advisor call (M5 composition: COSTAR + ChainOfThought + ConstitutionalAI
+ build_crispe_prompt post-step):
  specialist_crispe_prompt  — CRISPE meta-prompt injected into the Spec Specialist
  (all M4 fields also captured)

Also writes:
  MetaPromptEvent node — one per brief per run, CRISPE quality signals
  META_PROMPT_ADDS edge — from M4 SpecRun to M5 SpecRun (all 3 briefs)

Public API:
  seed(conn, output, brief_label, run_id, model, latency_ms, m4_run_id=None) → str
    Ensures schema, writes one SpecRun node + SPEC_CAPTURED_IN + MetaPromptEvent.
    If m4_run_id is provided and a matching M4 SpecRun exists, writes META_PROMPT_ADDS.
    Returns the SpecRun node id ("{run_id}:{brief_label}").

  infer_crispe_field_count(prompt_str) → int
    Count how many of the 6 CRISPE section headers are present in the prompt.

  infer_capacity_matches_lang(capacity_str, selected_lang) → bool
    True if selected_lang appears (case-insensitive) in the capacity section text.

  infer_insight_char_count(prompt_str) → int
    Character count of the Insight section content.

Analysis is intentionally NOT done here. Code captures; Claude analyzes.
"""

from __future__ import annotations

import datetime
import re

import kuzu

from src.milestones.m3.graph.runner import infer_evaluation_depth
from src.milestones.m5.schema import SpecAdvisorOutput

from .schema import ensure_schema

_CRISPE_SECTIONS = ["Capacity", "Role", "Insight", "Statement", "Personality", "Experiment"]


def _extract_section(prompt_str: str, section_name: str) -> str:
    """Extract content of a named CRISPE section from the built prompt string."""
    pattern = rf"\*\*{section_name}\*\*\n(.*?)(?=\n\n\*\*|\Z)"
    match = re.search(pattern, prompt_str, re.DOTALL)
    return match.group(1).strip() if match else ""


def infer_crispe_field_count(prompt_str: str) -> int:
    """Count how many CRISPE section headers (**Section**) are present."""
    return sum(f"**{s}**" in prompt_str for s in _CRISPE_SECTIONS)


def infer_capacity_matches_lang(capacity_str: str, selected_lang: str) -> bool:
    """True if selected_lang appears (case-insensitive) in the capacity section text."""
    return selected_lang.lower() in capacity_str.lower()


def infer_insight_char_count(prompt_str: str) -> int:
    """Character count of the Insight section content."""
    return len(_extract_section(prompt_str, "Insight"))


def seed(
    conn: kuzu.Connection,
    output: SpecAdvisorOutput,
    brief_label: str,
    run_id: str,
    model: str,
    latency_ms: float,
    m4_run_id: str | None = None,
) -> str:
    """
    Write one M5 SpecRun node + SPEC_CAPTURED_IN edge + MetaPromptEvent node.

    If m4_run_id is given and a matching M4 SpecRun exists for the same brief_label,
    writes a META_PROMPT_ADDS edge from that M4 node to this M5 node.
    All 3 briefs (simple, complex, vague) get META_PROMPT_ADDS — first full coverage.

    Returns the SpecRun node id: "{run_id}:{brief_label}".
    """
    ensure_schema(conn)

    node_id = f"{run_id}:{brief_label}"
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    step_count = len(output.reasoning_steps)
    eval_depth = infer_evaluation_depth(output.reasoning_steps)
    prompt_str = output.specialist_crispe_prompt

    capacity_text = _extract_section(prompt_str, "Capacity")
    field_count = infer_crispe_field_count(prompt_str)
    cap_matches = infer_capacity_matches_lang(capacity_text, output.selected_lang)
    insight_chars = infer_insight_char_count(prompt_str)
    capacity_chars = len(capacity_text)
    statement_chars = len(_extract_section(prompt_str, "Statement"))

    conn.execute(
        "CREATE (:SpecRun {"
        "id: $id, "
        "run_id: $run_id, "
        "milestone: 'm5', "
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
        "timestamp: $timestamp, "
        "specialist_crispe_prompt: $specialist_crispe_prompt"
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
            "specialist_crispe_prompt": prompt_str,
        },
    )
    conn.execute(
        "MATCH (s:SpecRun {id: $sid}), (r:MilestoneRun {run_id: $rid}) "
        "CREATE (s)-[:SPEC_CAPTURED_IN]->(r)",
        parameters={"sid": node_id, "rid": run_id},
    )

    # MetaPromptEvent — one per brief per run
    conn.execute(
        "CREATE (:MetaPromptEvent {"
        "id: $id, "
        "run_id: $run_id, "
        "brief_label: $brief_label, "
        "crispe_field_count: $field_count, "
        "capacity_char_count: $capacity_chars, "
        "insight_char_count: $insight_chars, "
        "statement_char_count: $statement_chars, "
        "capacity_matches_lang: $cap_matches"
        "})",
        parameters={
            "id": node_id,
            "run_id": run_id,
            "brief_label": brief_label,
            "field_count": field_count,
            "capacity_chars": capacity_chars,
            "insight_chars": insight_chars,
            "statement_chars": statement_chars,
            "cap_matches": cap_matches,
        },
    )

    if m4_run_id is not None:
        m4_node_id = f"{m4_run_id}:{brief_label}"
        result = conn.execute(
            "MATCH (s:SpecRun {id: $sid}) RETURN s.id",
            parameters={"sid": m4_node_id},
        )
        rows = result.get_all() if hasattr(result, "get_all") else list(result)
        if rows:
            conn.execute(
                "MATCH (m4:SpecRun {id: $m4id}), (m5:SpecRun {id: $m5id}) "
                "CREATE (m4)-[:META_PROMPT_ADDS {"
                "crispe_field_count: $field_count, "
                "prompt_char_count: $prompt_char_count, "
                "capacity_matches_lang: $cap_matches"
                "}]->(m5)",
                parameters={
                    "m4id": m4_node_id,
                    "m5id": node_id,
                    "field_count": field_count,
                    "prompt_char_count": len(prompt_str),
                    "cap_matches": cap_matches,
                },
            )

    return node_id


def dump(conn: kuzu.Connection, run_id: str) -> None:
    """Dev utility — print M5 subgraph for a given run. Never called automatically."""
    result = conn.execute(
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN s.brief_label, s.selected_lang, s.layer, s.confidence, "
        "s.crispe_field_count, s.specialist_crispe_prompt",
        parameters={"rid": run_id},
    )
    rows = result.get_all() if hasattr(result, "get_all") else list(result)
    print(f"\nM5 subgraph — run_id: {run_id}")
    for row in rows:
        label, lang, layer, conf, _, prompt = row
        print(f"  {label:<10} {lang:<14} {layer:<12} conf={conf:.2f}  crispe_len={len(prompt)}")
