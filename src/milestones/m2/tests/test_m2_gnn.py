"""
M2 gate tests — Spec Advisor (COSTAR-only) GNN proof.

Validates a single run: schema correctness, two SpecRun nodes per run (simple + complex),
field constraints, SPEC_CAPTURED_IN edges. Fixture uses an ephemeral Kuzu DB with mocked
Spec Advisor calls — no live API required.

For multi-run comparison and confidence distribution analysis, use the runner:
    python3 -m src.milestones.m2.run

Run it N times, then query the persistent DB ad-hoc.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import kuzu
import pytest

from src.milestones.m2.graph.runner import seed
from src.milestones.m2.graph.schema import ensure_schema
from src.milestones.m2.schema import SpecAdvisorOutput

_SIMPLE_OUTPUT = SpecAdvisorOutput(
    selected_lang="OpenAPI",
    layer="api",
    justification=(
        "The project is a simple REST API with CRUD operations on a single resource. "
        "OpenAPI is the standard contract language for REST services and directly "
        "captures the endpoint structure, request/response schemas, and HTTP semantics "
        "of this todo app without unnecessary formalism."
    ),
    confidence=0.92,
)

_COMPLEX_OUTPUT = SpecAdvisorOutput(
    selected_lang="TLA+",
    layer="system",
    justification=(
        "The platform requires multi-region active-active consistency with concurrent "
        "transaction handling and idempotency guarantees. TLA+ is the appropriate language "
        "for specifying safety (no duplicate charge) and liveness (every transaction "
        "eventually commits or rolls back) properties across distributed nodes."
    ),
    confidence=0.88,
)


@pytest.fixture(scope="module")
def m2_graph(tmp_path_factory):
    db = kuzu.Database(str(tmp_path_factory.mktemp("m2_kuzu") / "test.db"))
    conn = kuzu.Connection(db)

    run_id = "m2-test-run"
    model = "claude-sonnet-4-6"

    ensure_schema(conn)
    conn.execute(
        "CREATE (:MilestoneRun {run_id: $run_id, milestone: 'm2', model: $model, timestamp: 'now'})",
        parameters={"run_id": run_id, "model": model},
    )

    seed(conn, _SIMPLE_OUTPUT, "simple", run_id, model, latency_ms=420.5)
    seed(conn, _COMPLEX_OUTPUT, "complex", run_id, model, latency_ms=1105.3)

    yield conn, run_id
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
# Gate tests
# ---------------------------------------------------------------------------


def test_milestone_run_node_created(m2_graph):
    conn, run_id = m2_graph
    rows = _q(conn, "MATCH (r:MilestoneRun {run_id: $rid}) RETURN r.milestone", {"rid": run_id})
    assert rows == [["m2"]]


def test_two_spec_run_nodes(m2_graph):
    conn, run_id = m2_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN count(s)",
        {"rid": run_id},
    )
    assert rows[0][0] == 2


def test_spec_run_milestone_tag(m2_graph):
    conn, run_id = m2_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN DISTINCT s.milestone",
        {"rid": run_id},
    )
    assert rows == [["m2"]]


def test_confidence_in_range(m2_graph):
    conn, run_id = m2_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN s.brief_label, s.confidence",
        {"rid": run_id},
    )
    assert len(rows) == 2
    for label, confidence in rows:
        assert 0.0 <= confidence <= 1.0, f"{label}: confidence {confidence} out of range"


def test_latency_positive(m2_graph):
    conn, run_id = m2_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN s.brief_label, s.latency_ms",
        {"rid": run_id},
    )
    assert len(rows) == 2
    for label, latency in rows:
        assert latency > 0, f"{label}: latency_ms must be positive"


def test_justification_char_count_positive(m2_graph):
    conn, run_id = m2_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN s.brief_label, s.justification_char_count",
        {"rid": run_id},
    )
    assert len(rows) == 2
    for label, char_count in rows:
        assert char_count > 0, f"{label}: justification_char_count must be positive"


def test_simple_brief_lang(m2_graph):
    conn, run_id = m2_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun {brief_label: 'simple'}) "
        "RETURN s.selected_lang",
        {"rid": run_id},
    )
    assert len(rows) == 1
    lang = rows[0][0]
    assert lang in {"OpenAPI", "JSON Schema"}, f"simple brief got unexpected lang: {lang}"


def test_complex_brief_lang(m2_graph):
    conn, run_id = m2_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun {brief_label: 'complex'}) "
        "RETURN s.selected_lang",
        {"rid": run_id},
    )
    assert len(rows) == 1
    lang = rows[0][0]
    assert lang in {"TLA+", "CML"}, f"complex brief got unexpected lang: {lang}"


def test_spec_captured_in_edges(m2_graph):
    conn, run_id = m2_graph
    rows = _q(
        conn,
        "MATCH (s:SpecRun {run_id: $rid})-[:SPEC_CAPTURED_IN]->(r:MilestoneRun) "
        "RETURN count(s)",
        {"rid": run_id},
    )
    assert rows[0][0] == 2


def test_node_ids_scoped_to_run(m2_graph):
    conn, run_id = m2_graph
    rows = _q(
        conn,
        "MATCH (s:SpecRun {run_id: $rid}) RETURN s.id ORDER BY s.brief_label",
        {"rid": run_id},
    )
    ids = {r[0] for r in rows}
    assert ids == {f"{run_id}:simple", f"{run_id}:complex"}


def test_layer_values_valid(m2_graph):
    conn, run_id = m2_graph
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
# ML pass — surface raw signal from this run (printed, not asserted)
# ---------------------------------------------------------------------------


def test_ml_confidence_and_latency_profile(m2_graph, capsys):
    conn, run_id = m2_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:SPEC_CAPTURED_IN]-(s:SpecRun) "
        "RETURN s.brief_label, s.selected_lang, s.layer, s.confidence, "
        "s.latency_ms, s.justification_char_count "
        "ORDER BY s.brief_label",
        {"rid": run_id},
    )
    with capsys.disabled():
        print("\n\n=== ML pass: confidence + latency profile (m2) ===")
        print(
            f"  {'brief':<10} {'lang':<14} {'layer':<12} "
            f"{'conf':>6} {'ms':>8} {'just_chars':>10}"
        )
        print("  " + "-" * 64)
        for brief, lang, layer, conf, ms, chars in rows:
            print(f"  {brief:<10} {lang:<14} {layer:<12} {conf:>6.3f} {ms:>8.1f} {chars:>10}")
