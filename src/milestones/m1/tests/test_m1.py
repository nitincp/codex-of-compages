"""
M1 gate tests — Framework Builder GNN proof.

Validates a single run: schema correctness, 9 FrameworkLayer nodes per run,
file provenance, determinism, timing sanity. Fixture uses an ephemeral Kuzu DB.

For multi-run comparison and ML pass queries, use the runner:
    python3 -m src.milestones.m1.run <run-id>

Run it N times, then query the persistent DB ad-hoc.
"""

import hashlib
from pathlib import Path

import kuzu
import pytest

from src.milestones.m1.graph.runner import seed

_M1_DIR = Path(__file__).parent.parent


@pytest.fixture(scope="module")
def m1_graph(tmp_path_factory):
    db = kuzu.Database(str(tmp_path_factory.mktemp("m1_kuzu") / "test.db"))
    conn = kuzu.Connection(db)
    run_id = seed(conn)
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


def test_milestone_run_node_created(m1_graph):
    conn, run_id = m1_graph
    rows = _q(conn, "MATCH (r:MilestoneRun {run_id: $rid}) RETURN r.milestone", {"rid": run_id})
    assert rows == [["m1"]]


def test_nine_framework_nodes(m1_graph):
    conn, run_id = m1_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:CAPTURED_IN]-(f:FrameworkLayer) RETURN count(f)",
        {"rid": run_id},
    )
    assert rows[0][0] == 9


def test_all_four_dimensions_present(m1_graph):
    conn, run_id = m1_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:CAPTURED_IN]-(f:FrameworkLayer) "
        "RETURN DISTINCT f.dimension ORDER BY f.dimension",
        {"rid": run_id},
    )
    assert {r[0] for r in rows} == {"Structure", "Reasoning", "Verification", "Technique"}


def test_dimension_counts(m1_graph):
    conn, run_id = m1_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:CAPTURED_IN]-(f:FrameworkLayer) "
        "RETURN f.dimension, count(f) ORDER BY f.dimension",
        {"rid": run_id},
    )
    counts = {r[0]: r[1] for r in rows}
    assert counts == {"Structure": 4, "Reasoning": 2, "Verification": 1, "Technique": 2}


def test_build_output_non_empty(m1_graph):
    conn, run_id = m1_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:CAPTURED_IN]-(f:FrameworkLayer) "
        "WHERE f.build_output = '' RETURN f.name",
        {"rid": run_id},
    )
    assert rows == []


def test_file_provenance_captured(m1_graph):
    conn, run_id = m1_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:CAPTURED_IN]-(f:FrameworkLayer) "
        "RETURN f.name, f.file_path, f.file_hash, f.file_size_bytes ORDER BY f.name",
        {"rid": run_id},
    )
    assert len(rows) == 9
    for name, file_path, file_hash, file_size in rows:
        assert file_path and file_hash and file_size > 0, f"{name}: missing provenance"


def test_source_files_exist_and_hashes_match(m1_graph):
    conn, run_id = m1_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:CAPTURED_IN]-(f:FrameworkLayer) "
        "RETURN f.name, f.file_path, f.file_hash",
        {"rid": run_id},
    )
    for name, rel_path, stored_hash in rows:
        abs_path = _M1_DIR / rel_path
        assert abs_path.exists(), f"{name}: source file not found at {abs_path}"
        assert hashlib.sha256(abs_path.read_bytes()).hexdigest() == stored_hash, \
            f"{name}: hash mismatch"


def test_timing_and_size_metrics(m1_graph):
    conn, run_id = m1_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:CAPTURED_IN]-(f:FrameworkLayer) "
        "RETURN f.name, f.build_time_ms, f.output_char_count, f.output_token_est",
        {"rid": run_id},
    )
    assert len(rows) == 9
    for _, build_time, char_count, token_est in rows:
        assert build_time >= 0 and char_count > 0 and token_est > 0
        assert abs(token_est - (char_count // 4)) <= 1


def test_captured_in_edges(m1_graph):
    conn, run_id = m1_graph
    rows = _q(
        conn,
        "MATCH (f:FrameworkLayer {run_id: $rid})-[:CAPTURED_IN]->(r:MilestoneRun) "
        "RETURN count(f)",
        {"rid": run_id},
    )
    assert rows[0][0] == 9


# ---------------------------------------------------------------------------
# ML pass — surface raw signal from this run (printed, not asserted)
# ---------------------------------------------------------------------------


def test_ml_token_density_by_dimension(m1_graph, capsys):
    conn, run_id = m1_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:CAPTURED_IN]-(f:FrameworkLayer) "
        "RETURN f.dimension, f.name, f.output_token_est, f.output_char_count "
        "ORDER BY f.dimension, f.output_token_est DESC",
        {"rid": run_id},
    )
    assert len(rows) == 9
    with capsys.disabled():
        print("\n\n=== ML pass: token density by dimension ===")
        print(f"  {'Dimension':<14} {'Framework':<22} {'tokens_est':>10} {'chars':>8}")
        print("  " + "-" * 58)
        for dim, name, tokens, chars in rows:
            print(f"  {dim:<14} {name:<22} {tokens:>10} {chars:>8}")


def test_ml_file_expansion(m1_graph, capsys):
    conn, run_id = m1_graph
    rows = _q(
        conn,
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:CAPTURED_IN]-(f:FrameworkLayer) "
        "RETURN f.name, f.dimension, f.output_char_count, f.file_size_bytes "
        "ORDER BY f.output_char_count * 1.0 / f.file_size_bytes DESC",
        {"rid": run_id},
    )
    with capsys.disabled():
        print("\n\n=== ML pass: output chars / source bytes ===")
        print(f"  {'Framework':<22} {'Dimension':<14} {'out_chars':>9} {'src_bytes':>9} {'ratio':>6}")
        print("  " + "-" * 65)
        for name, dim, out_chars, src_bytes in rows:
            ratio = out_chars / src_bytes if src_bytes else 0
            print(f"  {name:<22} {dim:<14} {out_chars:>9} {src_bytes:>9} {ratio:>6.3f}")
