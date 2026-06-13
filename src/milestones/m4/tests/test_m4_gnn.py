"""
M4 gate tests — Spec Advisor (COSTAR + ChainOfThought + ConstitutionalAI) GNN proof.

Validates a single run: schema correctness, three SpecRun nodes per run
(simple + complex + vague), RevisionEvent nodes, VERIFICATION_ADDS cross-schema edges,
topological asymmetry preservation, and the first GNN topology-based retrieval query.

Fixture uses an ephemeral Kuzu DB with mocked outputs — no live API required.

For multi-run comparison and delta analysis, use the runner:
    python3 -m src.milestones.m4.run
"""

from __future__ import annotations

import kuzu
import pytest

from src.milestones.m4.graph.runner import (
    infer_assumption_inventory_added,
    infer_cai_principle_triggered,
    infer_signal_count_below_threshold,
    seed,
)
from src.milestones.m4.graph.schema import ensure_schema
from src.milestones.m4.schema import SpecAdvisorOutput

# ---------------------------------------------------------------------------
# Mock outputs
# ---------------------------------------------------------------------------

_SIMPLE_OUTPUT = SpecAdvisorOutput(
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

_COMPLEX_OUTPUT = SpecAdvisorOutput(
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
        "Evaluate TLA+: temporal logic covers replica convergence, concurrent deduction, "
        "liveness (every transaction eventually commits or rolls back) — strong candidate.",
        "Evaluate CML: session protocols cover choreography but lack global invariant "
        "assertion across replicas — insufficient for consistency proofs.",
        "Evaluate Alloy: structural snapshots only, no temporal operators — dismissed.",
        "Evaluate Event-B: refinement overhead unjustified without certification requirement.",
        "Weigh candidates: TLA+ covers the dominant concerns (consistency + liveness) "
        "with lower overhead than Event-B.",
        "Select TLA+ at system layer.",
        "Confidence 0.93: slight epistemic humility — liveness proofs could be descoped if "
        "strong compensation logic is relied upon instead.",
    ],
    revised=False,
    revision_notes="",
)

_VAGUE_OUTPUT = SpecAdvisorOutput(
    selected_lang="JSON Schema",
    layer="domain",
    justification=(
        "The brief provides no concrete technical signals beyond team collaboration. "
        "Assuming a shared data model with simple structured records, JSON Schema is "
        "a low-overhead starting point. Confidence lowered per CAI principle 3."
    ),
    confidence=0.62,
    reasoning_steps=[
        "Identify concerns: the brief mentions collaboration but names no technical properties "
        "(no API surface, no concurrency, no data model).",
        "Evaluate JSON Schema: assumes a shared document/record model — reasonable default "
        "for unspecified collaboration tools.",
        "Confidence set below 0.75 per CAI principle 3: fewer than two concrete signals.",
    ],
    revised=True,
    revision_notes=(
        "CAI principle 3 triggered: brief provides fewer than two concrete technical signals. "
        "Confidence lowered to 0.62. Assumptions declared: shared document model, "
        "no real-time or concurrency requirements implied."
    ),
)

# M3 mock baselines (for VERIFICATION_ADDS delta computation)
_M3_SIMPLE_CONFIDENCE = 0.97
_M3_COMPLEX_CONFIDENCE = 0.95
_M3_SIMPLE_STEP_COUNT = 5
_M3_COMPLEX_STEP_COUNT = 8


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def m4_graph(tmp_path_factory):
    db = kuzu.Database(str(tmp_path_factory.mktemp("m4_kuzu") / "test.db"))
    conn = kuzu.Connection(db)

    m2_run_id = "m2-test-run"
    m3_run_id = "m3-test-run"
    m4_run_id = "m4-test-run"
    model = "claude-sonnet-4-6"

    ensure_schema(conn)

    # Seed minimal M2 subgraph (needed so REASONING_ADDS edges into M3 can be written)
    conn.execute(
        "CREATE (:MilestoneRun {run_id: $rid, milestone: 'm2', model: $model, timestamp: 'now'})",
        parameters={"rid": m2_run_id, "model": model},
    )
    for label, conf in [("simple", _M3_SIMPLE_CONFIDENCE), ("complex", _M3_COMPLEX_CONFIDENCE)]:
        conn.execute(
            "CREATE (:SpecRun {id: $id, run_id: $rid, milestone: 'm2', "
            "brief_label: $label, selected_lang: 'OpenAPI', layer: 'api', "
            "confidence: $conf, justification_char_count: 200, "
            "reasoning_step_count: 0, evaluation_depth: 'unknown', "
            "revised: false, revision_notes: '', "
            "latency_ms: 450.0, model: $model, timestamp: 'now'})",
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

    # Seed minimal M3 subgraph (simple + complex only — vague was not run at M3)
    conn.execute(
        "CREATE (:MilestoneRun {run_id: $rid, milestone: 'm3', model: $model, timestamp: 'now'})",
        parameters={"rid": m3_run_id, "model": model},
    )
    m3_nodes = [
        ("simple", "OpenAPI", "api", _M3_SIMPLE_CONFIDENCE, _M3_SIMPLE_STEP_COUNT),
        ("complex", "TLA+", "system", _M3_COMPLEX_CONFIDENCE, _M3_COMPLEX_STEP_COUNT),
    ]
    for label, lang, layer, conf, steps in m3_nodes:
        conn.execute(
            "CREATE (:SpecRun {id: $id, run_id: $rid, milestone: 'm3', "
            "brief_label: $label, selected_lang: $lang, layer: $layer, "
            "confidence: $conf, justification_char_count: 280, "
            "reasoning_step_count: $steps, evaluation_depth: 'per_concern', "
            "revised: false, revision_notes: '', "
            "latency_ms: 900.0, model: $model, timestamp: 'now'})",
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
    # REASONING_ADDS: M2 → M3 for simple and complex
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

    # Create M4 MilestoneRun anchor
    conn.execute(
        "CREATE (:MilestoneRun {run_id: $rid, milestone: 'm4', model: $model, timestamp: 'now'})",
        parameters={"rid": m4_run_id, "model": model},
    )

    # Seed M4 via runner for all three briefs
    seed(conn, _SIMPLE_OUTPUT, "simple", m4_run_id, model, latency_ms=500.0, m3_run_id=m3_run_id)
    seed(conn, _COMPLEX_OUTPUT, "complex", m4_run_id, model, latency_ms=1500.0, m3_run_id=m3_run_id)
    seed(conn, _VAGUE_OUTPUT, "vague", m4_run_id, model, latency_ms=800.0, m3_run_id=m3_run_id)

    yield conn, m4_run_id, m3_run_id
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
# Gate tests — MilestoneRun + SpecRun schema
# ---------------------------------------------------------------------------


def test_milestone_run_node_created(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(conn, "MATCH (r:MilestoneRun {run_id: $rid}) RETURN r.milestone", {"rid": run_id})
    assert rows == [["m4"]]


def test_three_spec_run_nodes(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) RETURN count(s)",
        {"rid": run_id},
    )
    assert rows[0][0] == 3


def test_spec_run_milestone_tag(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN DISTINCT s.milestone",
        {"rid": run_id},
    )
    assert rows == [["m4"]]


def test_spec_run_brief_labels(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN s.brief_label ORDER BY s.brief_label",
        {"rid": run_id},
    )
    labels = {r[0] for r in rows}
    assert labels == {"simple", "complex", "vague"}


def test_node_ids_scoped_to_run(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(conn, "MATCH (s:SpecRun {run_id: $rid}) RETURN s.id", {"rid": run_id})
    ids = {r[0] for r in rows}
    assert ids == {f"{run_id}:simple", f"{run_id}:complex", f"{run_id}:vague"}


def test_confidence_in_range(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN s.brief_label, s.confidence",
        {"rid": run_id},
    )
    for label, conf in rows:
        assert 0.0 <= conf <= 1.0, f"{label}: confidence {conf} out of range"


def test_layer_values_valid(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN s.brief_label, s.layer",
        {"rid": run_id},
    )
    valid_layers = {"system", "domain", "component", "api"}
    for label, layer in rows:
        assert layer in valid_layers, f"{label}: invalid layer '{layer}'"


# ---------------------------------------------------------------------------
# Gate tests — revised field (CAI verification signal)
# ---------------------------------------------------------------------------


def test_vague_brief_revised_true(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (s:SpecRun {id: $id}) RETURN s.revised",
        {"id": f"{run_id}:vague"},
    )
    assert rows[0][0] is True, "vague brief must have revised=True"


def test_simple_brief_revised_false(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (s:SpecRun {id: $id}) RETURN s.revised",
        {"id": f"{run_id}:simple"},
    )
    assert rows[0][0] is False, "simple brief must have revised=False"


def test_complex_brief_revised_false(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (s:SpecRun {id: $id}) RETURN s.revised",
        {"id": f"{run_id}:complex"},
    )
    assert rows[0][0] is False, "complex brief must have revised=False"


def test_vague_confidence_below_threshold(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (s:SpecRun {id: $id}) RETURN s.confidence",
        {"id": f"{run_id}:vague"},
    )
    assert rows[0][0] < 0.75, "vague brief confidence must be below 0.75 (CAI principle 3)"


# ---------------------------------------------------------------------------
# Gate tests — RevisionEvent nodes
# ---------------------------------------------------------------------------


def test_three_revision_events(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (e:RevisionEvent {run_id: $rid}) RETURN count(e)",
        {"rid": run_id},
    )
    assert rows[0][0] == 3


def test_revision_event_vague_revised_true(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (e:RevisionEvent {id: $id}) RETURN e.revised, e.assumption_inventory_added",
        {"id": f"{run_id}:vague"},
    )
    revised, assumption = rows[0]
    assert revised is True
    assert assumption is True


def test_revision_event_simple_revised_false(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (e:RevisionEvent {id: $id}) RETURN e.revised, e.cai_principle_triggered",
        {"id": f"{run_id}:simple"},
    )
    revised, principle = rows[0]
    assert revised is False
    assert principle == ""


def test_revision_event_complex_revised_false(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (e:RevisionEvent {id: $id}) RETURN e.revised, e.cai_principle_triggered",
        {"id": f"{run_id}:complex"},
    )
    revised, principle = rows[0]
    assert revised is False
    assert principle == ""


def test_revision_event_vague_cai_principle(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (e:RevisionEvent {id: $id}) RETURN e.cai_principle_triggered",
        {"id": f"{run_id}:vague"},
    )
    assert rows[0][0] == "vague_brief_assumption_required"


# ---------------------------------------------------------------------------
# Gate tests — VERIFICATION_ADDS cross-schema edges
# ---------------------------------------------------------------------------


def test_verification_adds_edges_exist_for_simple_and_complex(m4_graph):
    conn, run_id, m3_run_id = m4_graph
    rows = _q(
        conn,
        "MATCH (m3:SpecRun {run_id: $m3rid})-[:VERIFICATION_ADDS]->(m4:SpecRun {run_id: $m4rid}) "
        "RETURN count(*)",
        {"m3rid": m3_run_id, "m4rid": run_id},
    )
    assert rows[0][0] == 2, f"expected 2 VERIFICATION_ADDS edges, got {rows[0][0]}"


def test_no_verification_adds_for_vague(m4_graph):
    conn, run_id, m3_run_id = m4_graph
    rows = _q(
        conn,
        "MATCH (m3:SpecRun {run_id: $m3rid})-[:VERIFICATION_ADDS]->(m4:SpecRun {id: $vague_id}) "
        "RETURN count(*)",
        {"m3rid": m3_run_id, "vague_id": f"{run_id}:vague"},
    )
    assert rows[0][0] == 0, "vague brief must have no incoming VERIFICATION_ADDS edge"


def test_verification_adds_confidence_delta_matches(m4_graph):
    conn, run_id, m3_run_id = m4_graph
    rows = _q(
        conn,
        "MATCH (m3:SpecRun {run_id: $m3rid})-[e:VERIFICATION_ADDS]->(m4:SpecRun {run_id: $m4rid}) "
        "RETURN m4.brief_label, m3.confidence, m4.confidence, e.confidence_delta",
        {"m3rid": m3_run_id, "m4rid": run_id},
    )
    assert len(rows) == 2
    for label, m3_conf, m4_conf, delta in rows:
        expected = round(m4_conf - m3_conf, 4)
        assert abs(delta - expected) < 0.001, f"{label}: delta {delta} != expected {expected}"


def test_verification_adds_cai_principle_on_revised_edge(m4_graph):
    """All VERIFICATION_ADDS edges for non-vague briefs have empty cai_principle_triggered."""
    conn, run_id, m3_run_id = m4_graph
    rows = _q(
        conn,
        "MATCH (m3:SpecRun {run_id: $m3rid})-[e:VERIFICATION_ADDS]->(m4:SpecRun {run_id: $m4rid}) "
        "RETURN m4.brief_label, e.revised, e.cai_principle_triggered",
        {"m3rid": m3_run_id, "m4rid": run_id},
    )
    for label, revised, principle in rows:
        assert revised is False, f"{label}: edge revised must be False for strong briefs"
        assert principle == "", f"{label}: principle must be empty for non-revised edge"


# ---------------------------------------------------------------------------
# Gate test — topological asymmetry: vague has no incoming cross-schema edges
# ---------------------------------------------------------------------------


def test_vague_spec_run_has_no_incoming_reasoning_adds(m4_graph):
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (src:SpecRun)-[:REASONING_ADDS]->(vague:SpecRun {id: $id}) RETURN count(*)",
        {"id": f"{run_id}:vague"},
    )
    assert rows[0][0] == 0, "vague M4 SpecRun must have no incoming REASONING_ADDS"


def test_complex_and_simple_have_incoming_cross_schema_edges(m4_graph):
    conn, run_id, _ = m4_graph
    for label in ["simple", "complex"]:
        rows = _q(
            conn,
            "MATCH (src:SpecRun)-[:VERIFICATION_ADDS]->(s:SpecRun {id: $id}) RETURN count(*)",
            {"id": f"{run_id}:{label}"},
        )
        assert rows[0][0] == 1, f"{label} must have one incoming VERIFICATION_ADDS edge"


# ---------------------------------------------------------------------------
# Gate test — First GNN topology-based retrieval query
#
# Given profile: {revised=False, step_count ≥ 5, evaluation_depth=per_concern}
# Traverse REASONING_ADDS | VERIFICATION_ADDS edges.
# Assert: result includes 'complex' nodes; does NOT include 'vague'.
# ---------------------------------------------------------------------------


def test_gnn_topology_retrieval_excludes_vague(m4_graph):
    """
    Topology-based retrieval: filter by profile inline with cross-schema edge traversal.
    Vague SpecRun has no edges — the MATCH pattern excludes it structurally.
    """
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (s:SpecRun)-[:REASONING_ADDS|VERIFICATION_ADDS]-(neighbor:SpecRun) "
        "WHERE s.revised = false "
        "  AND s.reasoning_step_count >= 5 "
        "  AND s.evaluation_depth = 'per_concern' "
        "RETURN DISTINCT s.brief_label, s.milestone, s.reasoning_step_count "
        "ORDER BY s.reasoning_step_count DESC",
    )
    assert len(rows) > 0, "topology query must return at least one result"
    result_labels = {r[0] for r in rows}  # r = (brief_label, milestone, step_count)
    assert "vague" not in result_labels, (
        f"vague must not appear in topology retrieval result; got: {result_labels}"
    )
    assert "complex" in result_labels, (
        f"complex must appear in topology retrieval result; got: {result_labels}"
    )


def test_gnn_topology_top_result_is_complex(m4_graph):
    """Top result by step_count is m4_complex or m3_complex — the highest-signal node."""
    conn, run_id, _ = m4_graph
    rows = _q(
        conn,
        "MATCH (s:SpecRun)-[:REASONING_ADDS|VERIFICATION_ADDS]-(neighbor:SpecRun) "
        "WHERE s.revised = false "
        "  AND s.reasoning_step_count >= 5 "
        "  AND s.evaluation_depth = 'per_concern' "
        "RETURN DISTINCT s.brief_label, s.milestone, s.reasoning_step_count "
        "ORDER BY s.reasoning_step_count DESC "
        "LIMIT 1",
    )
    assert len(rows) == 1
    label, milestone, _ = rows[0]
    assert label == "complex", f"top result must be 'complex', got '{label}' ({milestone})"
    assert milestone in {"m3", "m4"}, f"top result must be m3 or m4, got {milestone}"


# ---------------------------------------------------------------------------
# Unit tests — inference helpers
# ---------------------------------------------------------------------------


def test_infer_cai_principle_not_revised():
    out = SpecAdvisorOutput(
        selected_lang="OpenAPI",
        layer="api",
        justification="...",
        confidence=0.95,
        reasoning_steps=["a", "b"],
        revised=False,
        revision_notes="",
    )
    assert infer_cai_principle_triggered(out) == ""


def test_infer_cai_principle_vague():
    out = SpecAdvisorOutput(
        selected_lang="JSON Schema",
        layer="domain",
        justification="...",
        confidence=0.62,
        reasoning_steps=["a"],
        revised=True,
        revision_notes="vague brief, fewer than two signals",
    )
    assert infer_cai_principle_triggered(out) == "vague_brief_assumption_required"


def test_infer_cai_principle_specificity():
    out = SpecAdvisorOutput(
        selected_lang="OpenAPI",
        layer="api",
        justification="...",
        confidence=0.85,
        reasoning_steps=["a"],
        revised=True,
        revision_notes="made justification more specific",
    )
    assert infer_cai_principle_triggered(out) == "justification_or_reasoning_specificity"


def test_infer_assumption_inventory_added_true():
    out = SpecAdvisorOutput(
        selected_lang="JSON Schema",
        layer="domain",
        justification="...",
        confidence=0.62,
        reasoning_steps=[],
        revised=True,
        revision_notes="...",
    )
    assert infer_assumption_inventory_added(out) is True


def test_infer_assumption_inventory_added_false_not_revised():
    out = SpecAdvisorOutput(
        selected_lang="TLA+",
        layer="system",
        justification="...",
        confidence=0.93,
        reasoning_steps=[],
        revised=False,
        revision_notes="",
    )
    assert infer_assumption_inventory_added(out) is False


def test_infer_signal_count_below_threshold_vague():
    out = SpecAdvisorOutput(
        selected_lang="JSON Schema",
        layer="domain",
        justification="...",
        confidence=0.62,
        reasoning_steps=[],
        revised=True,
        revision_notes="...",
    )
    assert infer_signal_count_below_threshold(out) == 1


def test_infer_signal_count_below_threshold_strong():
    out = SpecAdvisorOutput(
        selected_lang="TLA+",
        layer="system",
        justification="...",
        confidence=0.93,
        reasoning_steps=[],
        revised=False,
        revision_notes="",
    )
    assert infer_signal_count_below_threshold(out) == 0


# ---------------------------------------------------------------------------
# ML pass — surface raw signal (printed, not asserted)
# ---------------------------------------------------------------------------


def test_ml_verification_delta_profile(m4_graph, capsys):
    conn, run_id, m3_run_id = m4_graph
    rows = _q(
        conn,
        "MATCH (m3:SpecRun {run_id: $m3rid})-[e:VERIFICATION_ADDS]->(m4:SpecRun {run_id: $m4rid}) "
        "RETURN m4.brief_label, m4.selected_lang, m4.reasoning_step_count, "
        "e.revised, e.confidence_delta, e.cai_principle_triggered, "
        "e.assumption_inventory_added",
        {"m3rid": m3_run_id, "m4rid": run_id},
    )
    with capsys.disabled():
        print("\n\n=== ML pass: VERIFICATION_ADDS delta profile (m4) ===")
        print(
            f"  {'brief':<10} {'lang':<14} {'steps':>6} "
            f"{'revised':>8} {'conf_delta':>11} {'principle':<38} {'assumption':>10}"
        )
        print("  " + "-" * 100)
        for brief, lang, steps, revised, delta, principle, assumption in rows:
            print(
                f"  {brief:<10} {lang:<14} {steps:>6} "
                f"{str(revised):>8} {delta:>+11.3f} {(principle or '—'):<38} {str(assumption):>10}"
            )
