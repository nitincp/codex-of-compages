"""
M5 gate tests — Spec Advisor (COSTAR + ChainOfThought + ConstitutionalAI + CRISPE meta-prompt).

Validates schema correctness, three SpecRun nodes per run, MetaPromptEvent quality signals,
META_PROMPT_ADDS cross-schema edges for all 3 briefs (first full coverage), and the 3-hop
topology query. Includes one integration test that calls SpecSpecialistAgent live.

Fixture uses an ephemeral Kuzu DB with mocked outputs — no live API for unit tests.
Integration test (marked @pytest.mark.integration) requires ANTHROPIC_API_KEY.

For multi-run comparison and delta analysis, use the runner:
    python3 -m src.milestones.m5.run
"""

from __future__ import annotations

import kuzu
import pytest

from src.milestones.m5.agent import build_crispe_prompt
from src.milestones.m5.graph.runner import (
    _extract_section,
    infer_capacity_matches_lang,
    infer_crispe_field_count,
    infer_insight_char_count,
    seed,
)
from src.milestones.m5.graph.schema import ensure_schema
from src.milestones.m5.schema import SpecAdvisorOutput

# ---------------------------------------------------------------------------
# Mock outputs — M5 SpecAdvisorOutput with specialist_crispe_prompt built in
# ---------------------------------------------------------------------------


def _make_output(
    selected_lang: str,
    layer: str,
    justification: str,
    confidence: float,
    reasoning_steps: list[str],
    revised: bool,
    revision_notes: str,
) -> SpecAdvisorOutput:
    base = SpecAdvisorOutput(
        selected_lang=selected_lang,
        layer=layer,
        justification=justification,
        confidence=confidence,
        reasoning_steps=reasoning_steps,
        revised=revised,
        revision_notes=revision_notes,
    )
    return base.model_copy(update={"specialist_crispe_prompt": build_crispe_prompt(base)})


_SIMPLE_OUTPUT = _make_output(
    selected_lang="OpenAPI",
    layer="api",
    justification=(
        "The project is a simple REST API with CRUD operations on a single resource. "
        "OpenAPI is the standard contract language for REST services, covering endpoints, "
        "request/response schemas, and HTTP semantics."
    ),
    confidence=0.95,
    reasoning_steps=[
        "Identify concerns: REST endpoints, request/response schemas, HTTP semantics.",
        "Evaluate JSON Schema: covers data shapes but lacks endpoint semantics — dismissed.",
        "Evaluate OpenAPI: covers full REST surface "
        "(endpoints + schemas + HTTP methods) — selected.",
        "Evaluate TLA+/CML/Alloy: no concurrency or safety-critical constraints — dismissed.",
        "Select OpenAPI at api layer with confidence 0.95.",
    ],
    revised=False,
    revision_notes="",
)

_COMPLEX_OUTPUT = _make_output(
    selected_lang="TLA+",
    layer="system",
    justification=(
        "The platform requires multi-region active-active consistency with concurrent "
        "transaction handling and idempotency guarantees. TLA+ provides temporal logic "
        "for safety and liveness proofs across distributed nodes."
    ),
    confidence=0.93,
    reasoning_steps=[
        "Identify concerns: eventual consistency, concurrent transactions, idempotency, "
        "multi-region active-active deployment, regulatory audit trail.",
        "Evaluate TLA+: temporal logic covers replica convergence and liveness — strong candidate.",
        "Evaluate CML: session protocols cover choreography but lack global invariant "
        "assertion across replicas — insufficient.",
        "Evaluate Alloy: structural snapshots only, no temporal operators — dismissed.",
        "Evaluate Event-B: refinement overhead unjustified without certification requirement.",
        "Weigh candidates: TLA+ covers the dominant concerns with lower overhead than Event-B.",
        "Select TLA+ at system layer.",
        "Confidence 0.93: liveness proofs could be descoped if compensation logic is used instead.",
    ],
    revised=False,
    revision_notes="",
)

_VAGUE_OUTPUT = _make_output(
    selected_lang="JSON Schema",
    layer="domain",
    justification="No concrete technical signals. Assuming simple shared data model.",
    confidence=0.62,
    reasoning_steps=[
        "Identify concerns: brief mentions collaboration but names no technical properties.",
        "Evaluate JSON Schema: assumes a shared document model — default for unspecified tools.",
        "Confidence set below 0.75 per CAI principle 3: fewer than two concrete signals.",
    ],
    revised=True,
    revision_notes=(
        "CAI principle 3 triggered: brief provides fewer than two concrete technical signals. "
        "Confidence lowered to 0.62. Assumptions declared: shared document model assumed."
    ),
)

# M4 mock confidence values for META_PROMPT_ADDS delta calculation
_M4_SIMPLE_CONFIDENCE = 0.95
_M4_COMPLEX_CONFIDENCE = 0.93
_M4_VAGUE_CONFIDENCE = 0.62


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def m5_graph(tmp_path_factory):
    db = kuzu.Database(str(tmp_path_factory.mktemp("m5_kuzu") / "test.db"))
    conn = kuzu.Connection(db)

    m2_run_id = "m2-test-run"
    m3_run_id = "m3-test-run"
    m4_run_id = "m4-test-run"
    m5_run_id = "m5-test-run"
    model = "claude-sonnet-4-6"

    ensure_schema(conn)

    # Seed minimal M2 subgraph
    conn.execute(
        "CREATE (:MilestoneRun {run_id: $rid, milestone: 'm2', model: $model, timestamp: 'now'})",
        parameters={"rid": m2_run_id, "model": model},
    )
    for label, conf in [("simple", 0.97), ("complex", 0.95)]:
        conn.execute(
            "CREATE (:SpecRun {id: $id, run_id: $rid, milestone: 'm2', "
            "brief_label: $label, selected_lang: 'OpenAPI', layer: 'api', "
            "confidence: $conf, justification_char_count: 200, "
            "reasoning_step_count: 0, evaluation_depth: 'unknown', "
            "revised: false, revision_notes: '', "
            "latency_ms: 450.0, model: $model, timestamp: 'now', "
            "specialist_crispe_prompt: ''})",
            parameters={
                "id": f"{m2_run_id}:{label}",
                "rid": m2_run_id,
                "label": label,
                "conf": conf,
                "model": model,
            },
        )
    conn.execute(
        "MATCH (s:SpecRun {run_id: $rid}), (r:MilestoneRun {run_id: $rid}) "
        "CREATE (s)-[:SPEC_CAPTURED_IN]->(r)",
        parameters={"rid": m2_run_id},
    )

    # Seed minimal M3 subgraph (simple + complex only — vague not run at M3)
    conn.execute(
        "CREATE (:MilestoneRun {run_id: $rid, milestone: 'm3', model: $model, timestamp: 'now'})",
        parameters={"rid": m3_run_id, "model": model},
    )
    m3_nodes = [
        ("simple", "OpenAPI", "api", 0.97, 5),
        ("complex", "TLA+", "system", 0.95, 8),
    ]
    for label, lang, layer, conf, steps in m3_nodes:
        conn.execute(
            "CREATE (:SpecRun {id: $id, run_id: $rid, milestone: 'm3', "
            "brief_label: $label, selected_lang: $lang, layer: $layer, "
            "confidence: $conf, justification_char_count: 280, "
            "reasoning_step_count: $steps, evaluation_depth: 'per_concern', "
            "revised: false, revision_notes: '', "
            "latency_ms: 900.0, model: $model, timestamp: 'now', "
            "specialist_crispe_prompt: ''})",
            parameters={
                "id": f"{m3_run_id}:{label}",
                "rid": m3_run_id,
                "label": label,
                "lang": lang,
                "layer": layer,
                "conf": conf,
                "steps": steps,
                "model": model,
            },
        )
    conn.execute(
        "MATCH (s:SpecRun {run_id: $rid}), (r:MilestoneRun {run_id: $rid}) "
        "CREATE (s)-[:SPEC_CAPTURED_IN]->(r)",
        parameters={"rid": m3_run_id},
    )
    for label in ["simple", "complex"]:
        conn.execute(
            "MATCH (m2:SpecRun {id: $m2id}), (m3:SpecRun {id: $m3id}) "
            "CREATE (m2)-[:REASONING_ADDS {"
            "confidence_delta: 0.0, step_count: 5, "
            "evaluation_depth: 'per_concern', adds_candidate_rejection: true"
            "}]->(m3)",
            parameters={
                "m2id": f"{m2_run_id}:{label}",
                "m3id": f"{m3_run_id}:{label}",
            },
        )

    # Seed minimal M4 subgraph (all 3 briefs — vague included so M5 can link it)
    conn.execute(
        "CREATE (:MilestoneRun {run_id: $rid, milestone: 'm4', model: $model, timestamp: 'now'})",
        parameters={"rid": m4_run_id, "model": model},
    )
    m4_nodes = [
        ("simple", "OpenAPI", "api", _M4_SIMPLE_CONFIDENCE, 5, False),
        ("complex", "TLA+", "system", _M4_COMPLEX_CONFIDENCE, 8, False),
        ("vague", "JSON Schema", "domain", _M4_VAGUE_CONFIDENCE, 3, True),
    ]
    for label, lang, layer, conf, steps, revised in m4_nodes:
        conn.execute(
            "CREATE (:SpecRun {id: $id, run_id: $rid, milestone: 'm4', "
            "brief_label: $label, selected_lang: $lang, layer: $layer, "
            "confidence: $conf, justification_char_count: 220, "
            "reasoning_step_count: $steps, evaluation_depth: 'per_concern', "
            "revised: $revised, revision_notes: '', "
            "latency_ms: 800.0, model: $model, timestamp: 'now', "
            "specialist_crispe_prompt: ''})",
            parameters={
                "id": f"{m4_run_id}:{label}",
                "rid": m4_run_id,
                "label": label,
                "lang": lang,
                "layer": layer,
                "conf": conf,
                "steps": steps,
                "revised": revised,
                "model": model,
            },
        )
    conn.execute(
        "MATCH (s:SpecRun {run_id: $rid}), (r:MilestoneRun {run_id: $rid}) "
        "CREATE (s)-[:SPEC_CAPTURED_IN]->(r)",
        parameters={"rid": m4_run_id},
    )
    # VERIFICATION_ADDS: M3 → M4 for simple + complex only (vague excluded — no M3 vague)
    for label in ["simple", "complex"]:
        conn.execute(
            "MATCH (m3:SpecRun {id: $m3id}), (m4:SpecRun {id: $m4id}) "
            "CREATE (m3)-[:VERIFICATION_ADDS {"
            "revised: false, confidence_delta: 0.0, cai_principle_triggered: '', "
            "signal_count_below_threshold: 0, assumption_inventory_added: false"
            "}]->(m4)",
            parameters={
                "m3id": f"{m3_run_id}:{label}",
                "m4id": f"{m4_run_id}:{label}",
            },
        )

    # Create M5 MilestoneRun anchor
    conn.execute(
        "CREATE (:MilestoneRun {run_id: $rid, milestone: 'm5', model: $model, timestamp: 'now'})",
        parameters={"rid": m5_run_id, "model": model},
    )

    # Seed M5 via runner for all three briefs
    seed(conn, _SIMPLE_OUTPUT, "simple", m5_run_id, model, latency_ms=600.0, m4_run_id=m4_run_id)
    seed(conn, _COMPLEX_OUTPUT, "complex", m5_run_id, model, latency_ms=1800.0, m4_run_id=m4_run_id)
    seed(conn, _VAGUE_OUTPUT, "vague", m5_run_id, model, latency_ms=900.0, m4_run_id=m4_run_id)

    yield conn, m5_run_id, m4_run_id
    conn.close()
    db.close()


def _q(conn: kuzu.Connection, cypher: str, params: dict | None = None) -> list:
    result = conn.execute(cypher, parameters=params or {})
    if isinstance(result, list):
        rows: list = []
        for r in result:
            rows.extend(r.get_all())
        return rows
    return result.get_all()


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_meta_prompt_event_table_exists(m5_graph):
    conn, run_id, _ = m5_graph
    rows = _q(conn, "MATCH (e:MetaPromptEvent {run_id: $rid}) RETURN count(e)", {"rid": run_id})
    assert rows[0][0] == 3


def test_meta_prompt_adds_rel_exists(m5_graph):
    conn, run_id, m4_run_id = m5_graph
    rows = _q(
        conn,
        "MATCH (m4:SpecRun {run_id: $m4rid})-[:META_PROMPT_ADDS]->(m5:SpecRun {run_id: $m5rid}) "
        "RETURN count(*)",
        {"m4rid": m4_run_id, "m5rid": run_id},
    )
    assert rows[0][0] == 3, "META_PROMPT_ADDS must link all 3 briefs"


def test_analyzed_meta_rel_schema_created(m5_graph):
    """ANALYZED_META rel table exists in the schema (can be created without error)."""
    conn, _, _ = m5_graph
    # Create a test AnalysisNote and MetaPromptEvent to verify the rel table
    conn.execute(
        "CREATE (:AnalysisNote {id: 'test-note', session: 's', by: 'claude', "
        "subject: 'test', signal: 's', value: 'v', note: 'n', milestone: 'm5', "
        "hypothesis_id: '', direction: '', metric_before: 0.0, metric_after: 0.0})"
    )
    conn.execute(
        "CREATE (:MetaPromptEvent {id: 'test-meta', run_id: 'test', brief_label: 'test', "
        "crispe_field_count: 6, capacity_char_count: 10, insight_char_count: 50, "
        "statement_char_count: 80, capacity_matches_lang: true})"
    )
    conn.execute(
        "MATCH (a:AnalysisNote {id: 'test-note'}), (m:MetaPromptEvent {id: 'test-meta'}) "
        "CREATE (a)-[:ANALYZED_META]->(m)"
    )
    rows = _q(
        conn,
        "MATCH (a:AnalysisNote {id: 'test-note'})-[:ANALYZED_META]->(m:MetaPromptEvent) "
        "RETURN count(*)",
    )
    assert rows[0][0] == 1


# ---------------------------------------------------------------------------
# SpecRun schema + specialist_crispe_prompt tests
# ---------------------------------------------------------------------------


def test_three_spec_run_nodes(m5_graph):
    conn, run_id, _ = m5_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) RETURN count(s)",
        {"rid": run_id},
    )
    assert rows[0][0] == 3


def test_spec_run_milestone_tag(m5_graph):
    conn, run_id, _ = m5_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN DISTINCT s.milestone",
        {"rid": run_id},
    )
    assert rows == [["m5"]]


def test_specialist_crispe_prompt_non_empty_all_briefs(m5_graph):
    conn, run_id, _ = m5_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN s.brief_label, s.specialist_crispe_prompt",
        {"rid": run_id},
    )
    for label, prompt in rows:
        assert prompt, f"{label}: specialist_crispe_prompt must be non-empty"


def test_crispe_prompt_contains_all_six_headers(m5_graph):
    conn, run_id, _ = m5_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN s.brief_label, s.specialist_crispe_prompt",
        {"rid": run_id},
    )
    expected_headers = [
        "**Capacity**",
        "**Role**",
        "**Insight**",
        "**Statement**",
        "**Personality**",
        "**Experiment**",
    ]
    for label, prompt in rows:
        for header in expected_headers:
            assert header in prompt, f"{label}: CRISPE prompt missing '{header}'"


# ---------------------------------------------------------------------------
# MetaPromptEvent quality signal tests
# ---------------------------------------------------------------------------


def test_meta_prompt_event_field_count_six_all_briefs(m5_graph):
    conn, run_id, _ = m5_graph
    rows = _q(
        conn,
        "MATCH (e:MetaPromptEvent {run_id: $rid}) RETURN e.brief_label, e.crispe_field_count",
        {"rid": run_id},
    )
    for label, count in rows:
        assert count == 6, f"{label}: crispe_field_count must be 6, got {count}"


def test_capacity_matches_lang_all_briefs(m5_graph):
    conn, run_id, _ = m5_graph
    rows = _q(
        conn,
        "MATCH (e:MetaPromptEvent {run_id: $rid}) RETURN e.brief_label, e.capacity_matches_lang",
        {"rid": run_id},
    )
    for label, matches in rows:
        assert matches is True, f"{label}: capacity_matches_lang must be True"


def test_insight_char_count_above_50_simple_complex(m5_graph):
    conn, run_id, _ = m5_graph
    for label in ["simple", "complex"]:
        rows = _q(
            conn,
            "MATCH (e:MetaPromptEvent {id: $id}) RETURN e.insight_char_count",
            {"id": f"{run_id}:{label}"},
        )
        assert rows[0][0] > 50, f"{label}: insight_char_count must be > 50"


def test_vague_insight_shorter_than_complex(m5_graph):
    conn, run_id, _ = m5_graph
    vague_rows = _q(
        conn,
        "MATCH (e:MetaPromptEvent {id: $id}) RETURN e.insight_char_count",
        {"id": f"{run_id}:vague"},
    )
    complex_rows = _q(
        conn,
        "MATCH (e:MetaPromptEvent {id: $id}) RETURN e.insight_char_count",
        {"id": f"{run_id}:complex"},
    )
    vague_chars = vague_rows[0][0]
    complex_chars = complex_rows[0][0]
    assert vague_chars < complex_chars, (
        f"vague insight ({vague_chars}) must be shorter than complex ({complex_chars})"
    )


def test_capacity_char_count_positive_all_briefs(m5_graph):
    conn, run_id, _ = m5_graph
    rows = _q(
        conn,
        "MATCH (e:MetaPromptEvent {run_id: $rid}) RETURN e.brief_label, e.capacity_char_count",
        {"rid": run_id},
    )
    for label, chars in rows:
        assert chars > 0, f"{label}: capacity_char_count must be positive"


def test_statement_char_count_positive_all_briefs(m5_graph):
    conn, run_id, _ = m5_graph
    rows = _q(
        conn,
        "MATCH (e:MetaPromptEvent {run_id: $rid}) RETURN e.brief_label, e.statement_char_count",
        {"rid": run_id},
    )
    for label, chars in rows:
        assert chars > 0, f"{label}: statement_char_count must be positive"


# ---------------------------------------------------------------------------
# META_PROMPT_ADDS cross-schema edge tests — all 3 briefs
# ---------------------------------------------------------------------------


def test_meta_prompt_adds_all_three_briefs(m5_graph):
    conn, run_id, m4_run_id = m5_graph
    rows = _q(
        conn,
        "MATCH (m4:SpecRun {run_id: $m4rid})-[:META_PROMPT_ADDS]->(m5:SpecRun {run_id: $m5rid}) "
        "RETURN m5.brief_label ORDER BY m5.brief_label",
        {"m4rid": m4_run_id, "m5rid": run_id},
    )
    labels = {r[0] for r in rows}
    assert labels == {"simple", "complex", "vague"}, (
        f"expected all 3 briefs in META_PROMPT_ADDS, got {labels}"
    )


def test_meta_prompt_adds_edge_crispe_field_count_six(m5_graph):
    conn, run_id, m4_run_id = m5_graph
    rows = _q(
        conn,
        "MATCH (m4:SpecRun {run_id: $m4rid})-[e:META_PROMPT_ADDS]->(m5:SpecRun {run_id: $m5rid}) "
        "RETURN m5.brief_label, e.crispe_field_count",
        {"m4rid": m4_run_id, "m5rid": run_id},
    )
    for label, count in rows:
        assert count == 6, f"{label}: edge crispe_field_count must be 6, got {count}"


def test_meta_prompt_adds_edge_capacity_matches_lang(m5_graph):
    conn, run_id, m4_run_id = m5_graph
    rows = _q(
        conn,
        "MATCH (m4:SpecRun {run_id: $m4rid})-[e:META_PROMPT_ADDS]->(m5:SpecRun {run_id: $m5rid}) "
        "RETURN m5.brief_label, e.capacity_matches_lang",
        {"m4rid": m4_run_id, "m5rid": run_id},
    )
    for label, matches in rows:
        assert matches is True, f"{label}: edge capacity_matches_lang must be True"


def test_meta_prompt_adds_edge_prompt_char_count_positive(m5_graph):
    conn, run_id, m4_run_id = m5_graph
    rows = _q(
        conn,
        "MATCH (m4:SpecRun {run_id: $m4rid})-[e:META_PROMPT_ADDS]->(m5:SpecRun {run_id: $m5rid}) "
        "RETURN m5.brief_label, e.prompt_char_count",
        {"m4rid": m4_run_id, "m5rid": run_id},
    )
    for label, count in rows:
        assert count > 0, f"{label}: edge prompt_char_count must be positive"


# ---------------------------------------------------------------------------
# Topological asymmetry: vague has no VERIFICATION_ADDS path
# ---------------------------------------------------------------------------


def test_vague_has_no_verification_adds_incoming(m5_graph):
    conn, _, m4_run_id = m5_graph
    rows = _q(
        conn,
        "MATCH (src:SpecRun)-[:VERIFICATION_ADDS]->(m4:SpecRun {id: $id}) RETURN count(*)",
        {"id": f"{m4_run_id}:vague"},
    )
    assert rows[0][0] == 0, "vague M4 SpecRun must have no incoming VERIFICATION_ADDS"


def test_vague_has_meta_prompt_adds_incoming(m5_graph):
    """Vague IS linked by META_PROMPT_ADDS — first full coverage milestone."""
    conn, run_id, m4_run_id = m5_graph
    rows = _q(
        conn,
        "MATCH (m4:SpecRun {id: $m4id})-[:META_PROMPT_ADDS]->(m5:SpecRun {id: $m5id}) "
        "RETURN count(*)",
        {"m4id": f"{m4_run_id}:vague", "m5id": f"{run_id}:vague"},
    )
    assert rows[0][0] == 1, "vague must have one incoming META_PROMPT_ADDS edge"


# ---------------------------------------------------------------------------
# 3-hop topology query: REASONING_ADDS → VERIFICATION_ADDS → META_PROMPT_ADDS
# Strong briefs in results; vague absent (no VERIFICATION_ADDS path)
# ---------------------------------------------------------------------------


def test_three_hop_topology_excludes_vague(m5_graph):
    """
    3-hop path: REASONING_ADDS → VERIFICATION_ADDS → META_PROMPT_ADDS.
    Vague is absent — there is no VERIFICATION_ADDS edge pointing to the vague M4 SpecRun,
    so the 3-hop path cannot reach the vague M5 SpecRun.
    """
    conn, run_id, _ = m5_graph
    rows = _q(
        conn,
        "MATCH (m2:SpecRun)-[:REASONING_ADDS]->(m3:SpecRun)"
        "-[v:VERIFICATION_ADDS]->(m4:SpecRun)"
        "-[:META_PROMPT_ADDS]->(m5:SpecRun {run_id: $m5rid}) "
        "WHERE v.revised = false "
        "RETURN DISTINCT m5.brief_label",
        {"m5rid": run_id},
    )
    result_labels = {r[0] for r in rows}
    assert "vague" not in result_labels, (
        f"vague must not appear in 3-hop topology result; got: {result_labels}"
    )


def test_three_hop_topology_includes_strong_briefs(m5_graph):
    conn, run_id, _ = m5_graph
    rows = _q(
        conn,
        "MATCH (m2:SpecRun)-[:REASONING_ADDS]->(m3:SpecRun)"
        "-[v:VERIFICATION_ADDS]->(m4:SpecRun)"
        "-[:META_PROMPT_ADDS]->(m5:SpecRun {run_id: $m5rid}) "
        "WHERE v.revised = false "
        "RETURN DISTINCT m5.brief_label",
        {"m5rid": run_id},
    )
    result_labels = {r[0] for r in rows}
    assert "complex" in result_labels, f"complex must appear in 3-hop result; got: {result_labels}"
    assert "simple" in result_labels, f"simple must appear in 3-hop result; got: {result_labels}"


# ---------------------------------------------------------------------------
# Unit tests — inference helpers
# ---------------------------------------------------------------------------


def test_infer_crispe_field_count_full_prompt():
    prompt = _SIMPLE_OUTPUT.specialist_crispe_prompt
    assert infer_crispe_field_count(prompt) == 6


def test_infer_crispe_field_count_empty():
    assert infer_crispe_field_count("") == 0


def test_infer_capacity_matches_lang_true():
    assert infer_capacity_matches_lang("OpenAPI specialist", "OpenAPI") is True


def test_infer_capacity_matches_lang_case_insensitive():
    assert infer_capacity_matches_lang("openapi specialist", "OpenAPI") is True


def test_infer_capacity_matches_lang_false():
    assert infer_capacity_matches_lang("JSON Schema specialist", "TLA+") is False


def test_infer_insight_char_count_simple():
    prompt = _SIMPLE_OUTPUT.specialist_crispe_prompt
    chars = infer_insight_char_count(prompt)
    assert chars > 50, f"simple insight must be > 50 chars, got {chars}"


def test_infer_insight_char_count_equals_justification():
    """insight section content == the justification string."""
    output = _SIMPLE_OUTPUT
    expected = len(output.justification)
    actual = infer_insight_char_count(output.specialist_crispe_prompt)
    assert actual == expected, f"insight char count {actual} != justification length {expected}"


def test_capacity_section_contains_selected_lang():
    for output in [_SIMPLE_OUTPUT, _COMPLEX_OUTPUT, _VAGUE_OUTPUT]:
        cap = _extract_section(output.specialist_crispe_prompt, "Capacity")
        assert output.selected_lang in cap, f"{output.selected_lang} not found in capacity: '{cap}'"


# ---------------------------------------------------------------------------
# ML pass — surface raw signal (printed, not asserted)
# ---------------------------------------------------------------------------


def test_ml_meta_prompt_signal_profile(m5_graph, capsys):
    conn, run_id, m4_run_id = m5_graph
    rows = _q(
        conn,
        "MATCH (m4:SpecRun {run_id: $m4rid})-[e:META_PROMPT_ADDS]->(m5:SpecRun {run_id: $m5rid}) "
        "RETURN m5.brief_label, m5.selected_lang, e.crispe_field_count, "
        "e.prompt_char_count, e.capacity_matches_lang",
        {"m4rid": m4_run_id, "m5rid": run_id},
    )
    with capsys.disabled():
        print("\n\n=== ML pass: META_PROMPT_ADDS signal profile (m5) ===")
        print(
            f"  {'brief':<10} {'lang':<14} {'crispe_fields':>13} "
            f"{'prompt_chars':>12} {'cap_match':>9}"
        )
        print("  " + "-" * 65)
        for brief, lang, fields, chars, cap_match in rows:
            print(f"  {brief:<10} {lang:<14} {fields:>13} {chars:>12} {str(cap_match):>9}")


# ---------------------------------------------------------------------------
# Integration test — live SpecSpecialistAgent call (requires ANTHROPIC_API_KEY)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_spec_specialist_produces_non_empty_spec():
    """
    Integration: SpecSpecialistAgent called with complex CRISPE →
    spec_content non-empty, spec_lang matches selected_lang.
    """
    from src.milestones.m5.spec_specialist import SpecSpecialistAgent

    brief = (
        "A distributed payment processing platform with multi-region active-active "
        "deployment, eventual consistency across regional nodes, concurrent transaction "
        "handling with idempotency guarantees, and a full audit trail for regulatory compliance."
    )
    specialist = SpecSpecialistAgent()
    spec = specialist.run(brief, _COMPLEX_OUTPUT.specialist_crispe_prompt)

    assert spec.spec_content, "spec_content must be non-empty"
    assert spec.spec_lang, "spec_lang must be non-empty"
    assert spec.spec_lang == _COMPLEX_OUTPUT.selected_lang, (
        f"spec_lang '{spec.spec_lang}' must match selected_lang '{_COMPLEX_OUTPUT.selected_lang}'"
    )
    assert 0.0 <= spec.confidence <= 1.0
