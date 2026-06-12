"""
M3 gate tests — Spec Advisor (COSTAR + ChainOfThought) GNN proof.

Validates a single run: schema correctness, two SpecRun nodes per run (simple + complex),
reasoning fields, SPEC_CAPTURED_IN edges, and REASONING_ADDS cross-schema edges.
Fixture uses an ephemeral Kuzu DB with mocked outputs — no live API required.

For multi-run comparison and delta analysis, use the runner:
    python3 -m src.milestones.m3.run

Run it N times, then query the persistent DB ad-hoc.
"""

from __future__ import annotations

import kuzu
import pytest

from src.milestones.m3.graph.runner import infer_evaluation_depth, seed
from src.milestones.m3.graph.schema import ensure_schema
from src.milestones.m3.schema import SpecAdvisorOutput

_SIMPLE_OUTPUT = SpecAdvisorOutput(
    selected_lang="OpenAPI",
    layer="api",
    justification=(
        "The project is a simple REST API with CRUD operations on a single resource. "
        "OpenAPI is the standard contract language for REST services."
    ),
    confidence=0.95,
    reasoning_steps=[
        "Identify concerns: REST endpoints, request/response schemas, HTTP semantics.",
        "Evaluate JSON Schema: covers data shapes but lacks endpoint semantics — dismissed.",
        "Evaluate OpenAPI: covers full REST surface (endpoints + schemas + HTTP methods) — selected.",
        "Evaluate TLA+/CML/Alloy: no concurrency or safety-critical constraints present — dismissed.",
        "Select OpenAPI at api layer with confidence 0.95.",
    ],
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
        "Evaluate Alloy: structural snapshots only, no temporal operators for liveness — dismissed.",
        "Evaluate Event-B: refinement overhead unjustified without certification requirement.",
        "Weigh candidates: TLA+ covers the dominant concerns (consistency + liveness) "
        "with lower overhead than Event-B.",
        "Select TLA+ at system layer.",
        "Confidence 0.93: slight epistemic humility — liveness proofs could be descoped if "
        "strong compensation logic is relied upon instead.",
    ],
)

# M2 mock outputs (for REASONING_ADDS delta computation)
_M2_SIMPLE_CONFIDENCE = 0.97
_M2_COMPLEX_CONFIDENCE = 0.95


@pytest.fixture(scope="module")
def m3_graph(tmp_path_factory):
    db = kuzu.Database(str(tmp_path_factory.mktemp("m3_kuzu") / "test.db"))
    conn = kuzu.Connection(db)

    m2_run_id = "m2-test-run"
    run_id = "m3-test-run"
    model = "claude-sonnet-4-6"

    ensure_schema(conn)

    # Seed a minimal M2 subgraph so REASONING_ADDS edges can be written
    conn.execute(
        "CREATE (:MilestoneRun {run_id: $rid, milestone: 'm2', "
        "model: $model, timestamp: 'now'})",
        parameters={"rid": m2_run_id, "model": model},
    )
    conn.execute(
        "CREATE (:SpecRun {id: $id, run_id: $rid, milestone: 'm2', "
        "brief_label: 'simple', selected_lang: 'OpenAPI', layer: 'api', "
        f"confidence: {_M2_SIMPLE_CONFIDENCE}, justification_char_count: 200, "
        "reasoning_step_count: 0, evaluation_depth: 'unknown', "
        "latency_ms: 450.0, model: $model, timestamp: 'now'})",
        parameters={"id": f"{m2_run_id}:simple", "rid": m2_run_id, "model": model},
    )
    conn.execute(
        "CREATE (:SpecRun {id: $id, run_id: $rid, milestone: 'm2', "
        "brief_label: 'complex', selected_lang: 'TLA+', layer: 'system', "
        f"confidence: {_M2_COMPLEX_CONFIDENCE}, justification_char_count: 320, "
        "reasoning_step_count: 0, evaluation_depth: 'unknown', "
        "latency_ms: 1100.0, model: $model, timestamp: 'now'})",
        parameters={"id": f"{m2_run_id}:complex", "rid": m2_run_id, "model": model},
    )
    conn.execute(
        "MATCH (s:SpecRun {run_id: $rid}), (r:MilestoneRun {run_id: $rid}) "
        "CREATE (s)-[:SPEC_CAPTURED_IN]->(r)",
        parameters={"rid": m2_run_id},
    )

    # Create M3 MilestoneRun
    conn.execute(
        "CREATE (:MilestoneRun {run_id: $rid, milestone: 'm3', "
        "model: $model, timestamp: 'now'})",
        parameters={"rid": run_id, "model": model},
    )

    seed(conn, _SIMPLE_OUTPUT, "simple", run_id, model, latency_ms=520.0, m2_run_id=m2_run_id)
    seed(conn, _COMPLEX_OUTPUT, "complex", run_id, model, latency_ms=1380.0, m2_run_id=m2_run_id)

    yield conn, run_id, m2_run_id
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
# Gate tests — SpecRun schema
# ---------------------------------------------------------------------------


def test_milestone_run_node_created(m3_graph):
    conn, run_id, _ = m3_graph
    rows = _q(conn, "MATCH (r:MilestoneRun {run_id: $rid}) RETURN r.milestone", {"rid": run_id})
    assert rows == [["m3"]]


def test_two_spec_run_nodes(m3_graph):
    conn, run_id, _ = m3_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN count(s)",
        {"rid": run_id},
    )
    assert rows[0][0] == 2


def test_spec_run_milestone_tag(m3_graph):
    conn, run_id, _ = m3_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN DISTINCT s.milestone",
        {"rid": run_id},
    )
    assert rows == [["m3"]]


def test_reasoning_step_count_at_least_three(m3_graph):
    conn, run_id, _ = m3_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN s.brief_label, s.reasoning_step_count",
        {"rid": run_id},
    )
    assert len(rows) == 2
    for label, step_count in rows:
        assert step_count >= 3, f"{label}: reasoning_step_count {step_count} < 3"


def test_evaluation_depth_is_per_concern(m3_graph):
    conn, run_id, _ = m3_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN s.brief_label, s.evaluation_depth",
        {"rid": run_id},
    )
    assert len(rows) == 2
    for label, depth in rows:
        assert depth == "per_concern", f"{label}: expected per_concern, got {depth}"


def test_confidence_in_range(m3_graph):
    conn, run_id, _ = m3_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN s.brief_label, s.confidence",
        {"rid": run_id},
    )
    assert len(rows) == 2
    for label, confidence in rows:
        assert 0.0 <= confidence <= 1.0, f"{label}: confidence {confidence} out of range"


def test_latency_positive(m3_graph):
    conn, run_id, _ = m3_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN s.brief_label, s.latency_ms",
        {"rid": run_id},
    )
    for label, latency in rows:
        assert latency > 0, f"{label}: latency_ms must be positive"


def test_justification_char_count_positive(m3_graph):
    conn, run_id, _ = m3_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN s.brief_label, s.justification_char_count",
        {"rid": run_id},
    )
    for label, char_count in rows:
        assert char_count > 0, f"{label}: justification_char_count must be positive"


def test_simple_brief_lang(m3_graph):
    conn, run_id, _ = m3_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})"
        "<-[:SPEC_CAPTURED_IN]-(s:SpecRun {brief_label: 'simple'}) "
        "RETURN s.selected_lang",
        {"rid": run_id},
    )
    assert len(rows) == 1
    lang = rows[0][0]
    assert lang in {"OpenAPI", "JSON Schema"}, f"simple brief got unexpected lang: {lang}"


def test_complex_brief_lang(m3_graph):
    conn, run_id, _ = m3_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})"
        "<-[:SPEC_CAPTURED_IN]-(s:SpecRun {brief_label: 'complex'}) "
        "RETURN s.selected_lang",
        {"rid": run_id},
    )
    assert len(rows) == 1
    lang = rows[0][0]
    assert lang in {"TLA+", "CML"}, f"complex brief got unexpected lang: {lang}"


def test_node_ids_scoped_to_run(m3_graph):
    conn, run_id, _ = m3_graph
    rows = _q(
        conn,
        "MATCH (s:SpecRun {run_id: $rid}) RETURN s.id",
        {"rid": run_id},
    )
    ids = {r[0] for r in rows}
    assert ids == {f"{run_id}:simple", f"{run_id}:complex"}


def test_layer_values_valid(m3_graph):
    conn, run_id, _ = m3_graph
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
# Gate tests — REASONING_ADDS cross-schema edges
# ---------------------------------------------------------------------------


def test_reasoning_adds_edges_exist(m3_graph):
    conn, run_id, m2_run_id = m3_graph
    rows = _q(
        conn,
        "MATCH (m2:SpecRun {run_id: $m2rid})-[:REASONING_ADDS]->(m3:SpecRun {run_id: $m3rid}) "
        "RETURN count(*)",
        {"m2rid": m2_run_id, "m3rid": run_id},
    )
    assert rows[0][0] == 2, f"expected 2 REASONING_ADDS edges, got {rows[0][0]}"


def test_reasoning_adds_confidence_delta_matches(m3_graph):
    conn, run_id, m2_run_id = m3_graph
    rows = _q(
        conn,
        "MATCH (m2:SpecRun {run_id: $m2rid})-[e:REASONING_ADDS]->(m3:SpecRun {run_id: $m3rid}) "
        "RETURN m3.brief_label, m2.confidence, m3.confidence, e.confidence_delta",
        {"m2rid": m2_run_id, "m3rid": run_id},
    )
    assert len(rows) == 2
    for label, m2_conf, m3_conf, delta in rows:
        expected = round(m3_conf - m2_conf, 4)
        assert abs(delta - expected) < 0.001, (
            f"{label}: delta {delta} != expected {expected}"
        )


def test_reasoning_adds_step_count_matches_node(m3_graph):
    conn, run_id, m2_run_id = m3_graph
    rows = _q(
        conn,
        "MATCH (m2:SpecRun {run_id: $m2rid})-[e:REASONING_ADDS]->(m3:SpecRun {run_id: $m3rid}) "
        "RETURN m3.brief_label, m3.reasoning_step_count, e.step_count",
        {"m2rid": m2_run_id, "m3rid": run_id},
    )
    for label, node_steps, edge_steps in rows:
        assert node_steps == edge_steps, (
            f"{label}: node step_count {node_steps} != edge step_count {edge_steps}"
        )


def test_reasoning_adds_evaluation_depth_per_concern(m3_graph):
    conn, run_id, m2_run_id = m3_graph
    rows = _q(
        conn,
        "MATCH (m2:SpecRun {run_id: $m2rid})-[e:REASONING_ADDS]->(m3:SpecRun {run_id: $m3rid}) "
        "RETURN m3.brief_label, e.evaluation_depth",
        {"m2rid": m2_run_id, "m3rid": run_id},
    )
    for label, depth in rows:
        assert depth == "per_concern", f"{label}: expected per_concern on edge, got {depth}"


# ---------------------------------------------------------------------------
# Unit tests — infer_evaluation_depth helper
# ---------------------------------------------------------------------------


def test_infer_depth_per_concern_with_lang_name():
    steps = ["Evaluate OpenAPI for REST endpoints.", "Dismiss TLA+ — no concurrency."]
    assert infer_evaluation_depth(steps) == "per_concern"


def test_infer_depth_conclusion_only_without_lang():
    steps = ["Identify concerns: data shapes.", "Select based on complexity."]
    assert infer_evaluation_depth(steps) == "conclusion_only"


# ---------------------------------------------------------------------------
# ML pass — surface raw signal (printed, not asserted)
# ---------------------------------------------------------------------------


def test_ml_reasoning_delta_profile(m3_graph, capsys):
    conn, run_id, m2_run_id = m3_graph
    rows = _q(
        conn,
        "MATCH (m2:SpecRun {run_id: $m2rid})-[e:REASONING_ADDS]->(m3:SpecRun {run_id: $m3rid}) "
        "RETURN m3.brief_label, m3.selected_lang, m3.reasoning_step_count, "
        "e.confidence_delta, e.evaluation_depth, e.adds_candidate_rejection",
        {"m2rid": m2_run_id, "m3rid": run_id},
    )
    with capsys.disabled():
        print("\n\n=== ML pass: REASONING_ADDS delta profile (m3) ===")
        print(
            f"  {'brief':<10} {'lang':<14} {'steps':>6} "
            f"{'conf_delta':>11} {'depth':<14} {'rejection':>9}"
        )
        print("  " + "-" * 72)
        for brief, lang, steps, delta, depth, rejection in rows:
            print(
                f"  {brief:<10} {lang:<14} {steps:>6} "
                f"{delta:>+11.3f} {depth:<14} {str(rejection):>9}"
            )
