"""
M4.1 ETL gate tests — ephemeral DBs only, never touches data/kuzu.

Tests:
  1. transform.cypher executes without error against a seeded m2 source DB
  2. schema.cypher (m1 + m2) creates valid DBs with correct tables/columns
  3. Full m2 migration pipeline: row counts in new DB match source
  4. diff m1 m2 reports correct NEW/UNCHANGED classification
  5. --dry-run writes Parquet files but does not create or rotate a new DB
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, cast

import kuzu
import pytest

from src.etl.diff import diff
from src.etl.migrate import _execute_schema, _parse_copy_blocks, _schema_tables, migrate


def _exec(
    conn: kuzu.Connection, query: str, params: dict[str, Any] | None = None
) -> kuzu.QueryResult:
    """Cast execute() result to QueryResult (always the case for string queries)."""
    return cast(kuzu.QueryResult, conn.execute(query, params or {}))


def _count(conn: kuzu.Connection, query: str) -> int:
    """Execute a count query and return the integer result."""
    return cast(list, _exec(conn, query).get_next())[0]

# ---------------------------------------------------------------------------
# Fixtures — ephemeral seeded source DB
# ---------------------------------------------------------------------------


def _seed_m2_db(conn: kuzu.Connection, run_id: str = "test-run-001") -> None:
    """Seed a minimal m2-shaped DB into an open connection."""
    from src.milestones.m1.graph.runner import seed as m1_seed
    from src.milestones.m2.graph.schema import ensure_schema as m2_ensure

    m1_seed(conn, run_id=run_id, model="test")
    m2_ensure(conn)

    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for brief in ("simple", "complex"):
        node_id = f"{run_id}:{brief}"
        conn.execute(
            "CREATE (:SpecRun {id: $id, run_id: $rid, milestone: 'm2', "
            "brief_label: $brief, selected_lang: 'OpenAPI', layer: 'api', "
            "confidence: 0.95, justification_char_count: 200, "
            "latency_ms: 800.0, model: 'test', timestamp: $ts})",
            parameters={"id": node_id, "rid": run_id, "brief": brief, "ts": ts},
        )
        conn.execute(
            "MATCH (s:SpecRun {id: $sid}), (r:MilestoneRun {run_id: $rid}) "
            "CREATE (s)-[:SPEC_CAPTURED_IN]->(r)",
            parameters={"sid": node_id, "rid": run_id},
        )

    # AnalysisNote + ANALYZED / ANALYZED_RUN / ANALYZED_SPEC
    conn.execute(
        "CREATE NODE TABLE IF NOT EXISTS AnalysisNote ("
        "id STRING, session STRING, by STRING, subject STRING, "
        "signal STRING, value STRING, note STRING, "
        "PRIMARY KEY (id))"
    )
    conn.execute(
        "CREATE REL TABLE IF NOT EXISTS ANALYZED (FROM AnalysisNote TO FrameworkLayer)"
    )
    conn.execute(
        "CREATE REL TABLE IF NOT EXISTS ANALYZED_RUN (FROM AnalysisNote TO MilestoneRun)"
    )
    conn.execute(
        "CREATE REL TABLE IF NOT EXISTS ANALYZED_SPEC (FROM AnalysisNote TO SpecRun)"
    )

    note_id = f"{run_id}:note-1"
    conn.execute(
        "CREATE (:AnalysisNote {id: $id, session: 'test', by: 'claude', "
        "subject: 'test-subject', signal: 'test-signal', value: '42', note: 'test note'})",
        parameters={"id": note_id},
    )

    # ANALYZED edge to one FrameworkLayer node
    fw_id = f"{run_id}:COSTARPrompt"
    conn.execute(
        "MATCH (a:AnalysisNote {id: $aid}), (f:FrameworkLayer {id: $fid}) "
        "CREATE (a)-[:ANALYZED]->(f)",
        parameters={"aid": note_id, "fid": fw_id},
    )
    # ANALYZED_RUN edge
    conn.execute(
        "MATCH (a:AnalysisNote {id: $aid}), (r:MilestoneRun {run_id: $rid}) "
        "CREATE (a)-[:ANALYZED_RUN]->(r)",
        parameters={"aid": note_id, "rid": run_id},
    )
    # ANALYZED_SPEC edge
    conn.execute(
        "MATCH (a:AnalysisNote {id: $aid}), (s:SpecRun {id: $sid}) "
        "CREATE (a)-[:ANALYZED_SPEC]->(s)",
        parameters={"aid": note_id, "sid": f"{run_id}:simple"},
    )


@pytest.fixture
def source_db(tmp_path):
    """Ephemeral m2-shaped source DB."""
    db_path = tmp_path / "source_db"
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)
    _seed_m2_db(conn)
    del conn, db
    return db_path


# ---------------------------------------------------------------------------
# 1. transform.cypher executes without error
# ---------------------------------------------------------------------------


def test_transform_cypher_m2_executes(source_db, tmp_path):
    """COPY blocks in m2/transform.cypher execute against a seeded m2 DB."""
    db = kuzu.Database(str(source_db))
    conn = kuzu.Connection(db)

    transform_path = Path("src/milestones/m2/migration/transform.cypher")
    sql = transform_path.read_text()
    output_dir = str(tmp_path / "parquet")
    Path(output_dir).mkdir()

    blocks = _parse_copy_blocks(sql, output_dir)
    assert len(blocks) > 0, "Expected at least one COPY block in m2/transform.cypher"

    for _, query in blocks:
        conn.execute(query)  # must not raise

    # Verify expected Parquet files were written
    written = {f.stem for f in Path(output_dir).glob("*.parquet")}
    assert "MilestoneRun" in written
    assert "SpecRun" in written
    assert "AnalysisNote" in written


# ---------------------------------------------------------------------------
# 2. schema.cypher creates valid DBs
# ---------------------------------------------------------------------------


def test_schema_cypher_m1_creates_valid_db(tmp_path):
    """m1/schema.cypher creates a DB with all M1 tables and correct columns."""
    db_path = tmp_path / "m1_schema_test"
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)

    schema_path = Path("src/milestones/m1/migration/schema.cypher")
    _execute_schema(conn, schema_path)

    node_tables, rel_tables = _schema_tables(schema_path)
    assert "MilestoneRun" in node_tables
    assert "FrameworkLayer" in node_tables
    assert "CAPTURED_IN" in rel_tables

    # Verify tables actually exist by querying them
    for t in node_tables:
        _exec(conn, f"MATCH (n:{t}) RETURN count(n)").get_next()
    for t in rel_tables:
        _exec(conn, f"MATCH ()-[r:{t}]->() RETURN count(r)").get_next()


def test_schema_cypher_m2_creates_valid_db(tmp_path):
    """m2/schema.cypher creates a DB with all M2 tables and correct columns."""
    db_path = tmp_path / "m2_schema_test"
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)

    schema_path = Path("src/milestones/m2/migration/schema.cypher")
    _execute_schema(conn, schema_path)

    node_tables, rel_tables = _schema_tables(schema_path)
    assert "MilestoneRun" in node_tables
    assert "FrameworkLayer" in node_tables
    assert "SpecRun" in node_tables
    assert "AnalysisNote" in node_tables
    assert "CAPTURED_IN" in rel_tables
    assert "SPEC_CAPTURED_IN" in rel_tables
    assert "ANALYZED" in rel_tables
    assert "ANALYZED_RUN" in rel_tables
    assert "ANALYZED_SPEC" in rel_tables

    # Verify all tables queryable
    for t in node_tables:
        _exec(conn, f"MATCH (n:{t}) RETURN count(n)").get_next()
    for t in rel_tables:
        _exec(conn, f"MATCH ()-[r:{t}]->() RETURN count(r)").get_next()


def test_schema_cypher_m2_specrun_columns(tmp_path):
    """SpecRun in m2 schema has all expected columns with correct types."""
    db_path = tmp_path / "m2_col_test"
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)
    _execute_schema(conn, Path("src/milestones/m2/migration/schema.cypher"))

    columns = {
        cast(list, row)[1]: cast(list, row)[2]
        for row in _exec(conn, 'CALL table_info("SpecRun") RETURN *').get_all()
    }

    assert "id" in columns and columns["id"] == "STRING"
    assert "confidence" in columns and columns["confidence"] == "DOUBLE"
    assert "latency_ms" in columns and columns["latency_ms"] == "DOUBLE"
    assert "justification_char_count" in columns and columns["justification_char_count"] == "INT64"


# ---------------------------------------------------------------------------
# 3. Full migration pipeline: row counts match
# ---------------------------------------------------------------------------


def test_full_migration_m2_row_counts(source_db):
    """Full m2 migration round-trips with correct row counts and no data loss."""
    # Run the migration against an isolated copy to avoid any side effects on tmp_path layout
    migrate(
        target_milestone="m2",
        dry_run=False,
        db_path=source_db,
    )

    # After rotation, source_db path now points to the new DB
    new_db = kuzu.Database(str(source_db))
    new_conn = kuzu.Connection(new_db)

    # Verify key tables survived migration
    mr_count = _count(new_conn, "MATCH (n:MilestoneRun) RETURN count(n)")
    sr_count = _count(new_conn, "MATCH (n:SpecRun) RETURN count(n)")
    an_count = _count(new_conn, "MATCH (n:AnalysisNote) RETURN count(n)")
    fl_count = _count(new_conn, "MATCH (n:FrameworkLayer) RETURN count(n)")

    assert mr_count == 1, f"Expected 1 MilestoneRun, got {mr_count}"
    assert sr_count == 2, f"Expected 2 SpecRun, got {sr_count}"
    assert an_count == 1, f"Expected 1 AnalysisNote, got {an_count}"
    assert fl_count == 9, f"Expected 9 FrameworkLayer (reseeded), got {fl_count}"

    # Rel tables
    ci_count = _count(new_conn, "MATCH ()-[r:CAPTURED_IN]->() RETURN count(r)")
    sci_count = _count(new_conn, "MATCH ()-[r:SPEC_CAPTURED_IN]->() RETURN count(r)")
    an_run = _count(new_conn, "MATCH ()-[r:ANALYZED_RUN]->() RETURN count(r)")
    an_spec = _count(new_conn, "MATCH ()-[r:ANALYZED_SPEC]->() RETURN count(r)")

    assert ci_count == 9, f"Expected 9 CAPTURED_IN, got {ci_count}"
    assert sci_count == 2, f"Expected 2 SPEC_CAPTURED_IN, got {sci_count}"
    assert an_run == 1
    assert an_spec == 1


def test_migration_data_integrity(source_db):
    """After migration, SpecRun data survives intact (no truncation or corruption)."""
    migrate("m2", dry_run=False, db_path=source_db)

    new_db = kuzu.Database(str(source_db))
    new_conn = kuzu.Connection(new_db)

    rows = cast(
        list,
        _exec(
            new_conn,
            "MATCH (s:SpecRun) RETURN s.brief_label, s.confidence, s.selected_lang "
            "ORDER BY s.brief_label",
        ).get_all(),
    )
    assert len(rows) == 2
    briefs = {cast(list, row)[0] for row in rows}
    assert briefs == {"complex", "simple"}
    for row in rows:
        row_list = cast(list, row)
        assert row_list[1] == pytest.approx(0.95)
        assert row_list[2] == "OpenAPI"


# ---------------------------------------------------------------------------
# 4. diff m1 → m2
# ---------------------------------------------------------------------------


def test_diff_m1_m2_new_tables():
    """diff m1 m2 reports SpecRun and AnalysisNote as NEW."""
    lines = diff("m1", "m2")
    new_nodes = {ln for ln in lines if ln.startswith("NEW") and "NODE" in ln}
    assert any("SpecRun" in ln for ln in new_nodes), f"Expected SpecRun NEW in {lines}"
    assert any("AnalysisNote" in ln for ln in new_nodes), f"Expected AnalysisNote NEW in {lines}"


def test_diff_m1_m2_unchanged_tables():
    """diff m1 m2 reports MilestoneRun and FrameworkLayer as UNCHANGED."""
    lines = diff("m1", "m2")
    unchanged = {ln for ln in lines if ln.startswith("UNCHANGED")}
    assert any("MilestoneRun" in ln for ln in unchanged)
    assert any("FrameworkLayer" in ln for ln in unchanged)


def test_diff_m1_m2_new_rels():
    """diff m1 m2 reports SPEC_CAPTURED_IN, ANALYZED, ANALYZED_RUN, ANALYZED_SPEC as NEW."""
    lines = diff("m1", "m2")
    new_rels = {ln for ln in lines if ln.startswith("NEW") and "REL" in ln}
    for rel in ("SPEC_CAPTURED_IN", "ANALYZED", "ANALYZED_RUN", "ANALYZED_SPEC"):
        assert any(rel in ln for ln in new_rels), f"Expected {rel} NEW in {lines}"


def test_diff_m1_m2_captured_in_unchanged():
    """CAPTURED_IN rel is in both m1 and m2 schemas — reported as UNCHANGED."""
    lines = diff("m1", "m2")
    assert any("UNCHANGED" in ln and "CAPTURED_IN" in ln for ln in lines)


# ---------------------------------------------------------------------------
# 5. --dry-run produces Parquet but does not rotate DB
# ---------------------------------------------------------------------------


def test_dry_run_writes_parquet_no_rotation(source_db):
    """--dry-run writes Parquet files but leaves the source DB untouched."""
    # Confirm source DB is intact pre-run
    db = kuzu.Database(str(source_db))
    conn = kuzu.Connection(db)
    pre_count = _count(conn, "MATCH (n:MilestoneRun) RETURN count(n)")
    del conn, db

    migrate("m2", dry_run=True, db_path=source_db)

    # Source DB still exists at original path (not rotated)
    assert source_db.exists(), "Source DB should not be rotated by --dry-run"

    # No backup DB created
    backup_candidates = list(source_db.parent.glob(f"{source_db.name}_bak_*"))
    assert not backup_candidates, f"--dry-run should not create backup: {backup_candidates}"

    # No new DB directory created
    new_db_path = source_db.parent / (source_db.name + "_new")
    assert not new_db_path.exists(), "--dry-run should not create new DB"

    # Source DB still readable with original data
    db = kuzu.Database(str(source_db))
    conn = kuzu.Connection(db)
    post_count = _count(conn, "MATCH (n:MilestoneRun) RETURN count(n)")
    assert post_count == pre_count


def test_dry_run_parquet_files_exist(source_db, capsys):
    """--dry-run produces Parquet files for each exported table."""
    # We can't directly inspect tmp files since migrate() manages its own tmpdir,
    # but we can verify it runs without error and prints expected output.
    migrate("m2", dry_run=True, db_path=source_db)
    captured = capsys.readouterr()
    assert "--dry-run" in captured.out
    assert "MilestoneRun.parquet" in captured.out


# ---------------------------------------------------------------------------
# M3 schema + migration (m2 → m3)
# ---------------------------------------------------------------------------


def test_schema_cypher_m3_creates_valid_db(tmp_path):
    """m3/schema.cypher creates a DB with all M3 tables including new ones."""
    db_path = tmp_path / "m3_schema_test"
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)

    schema_path = Path("src/milestones/m3/migration/schema.cypher")
    _execute_schema(conn, schema_path)

    node_tables, rel_tables = _schema_tables(schema_path)
    assert "SpecRun" in node_tables
    assert "REASONING_ADDS" in rel_tables

    for t in node_tables:
        _exec(conn, f"MATCH (n:{t}) RETURN count(n)").get_next()
    for t in rel_tables:
        _exec(conn, f"MATCH ()-[r:{t}]->() RETURN count(r)").get_next()


def test_schema_cypher_m3_specrun_columns(tmp_path):
    """SpecRun at M3 has reasoning_step_count and evaluation_depth columns."""
    db_path = tmp_path / "m3_col_test"
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)
    _execute_schema(conn, Path("src/milestones/m3/migration/schema.cypher"))

    columns = {
        cast(list, row)[1]: cast(list, row)[2]
        for row in _exec(conn, 'CALL table_info("SpecRun") RETURN *').get_all()
    }
    assert "reasoning_step_count" in columns and columns["reasoning_step_count"] == "INT64"
    assert "evaluation_depth" in columns and columns["evaluation_depth"] == "STRING"
    assert "confidence" in columns  # M2 columns preserved


def test_full_migration_m3_row_counts(source_db):
    """m2→m3 migration preserves row counts and backfills new SpecRun columns."""
    migrate("m3", dry_run=False, db_path=source_db)

    new_db = kuzu.Database(str(source_db))
    new_conn = kuzu.Connection(new_db)

    assert _count(new_conn, "MATCH (n:MilestoneRun) RETURN count(n)") == 1
    assert _count(new_conn, "MATCH (n:SpecRun) RETURN count(n)") == 2
    assert _count(new_conn, "MATCH (n:FrameworkLayer) RETURN count(n)") == 9

    # Backfill values for M2 rows
    for row in _exec(new_conn, "MATCH (s:SpecRun) RETURN s.reasoning_step_count, s.evaluation_depth"):
        assert cast(list, row)[0] == 0
        assert cast(list, row)[1] == "unknown"

    # REASONING_ADDS table exists and is empty (no M2 cross-schema edges to carry)
    assert _count(new_conn, "MATCH ()-[r:REASONING_ADDS]->() RETURN count(r)") == 0


# ---------------------------------------------------------------------------
# M3-shaped source fixture for m3 → m4 tests
# ---------------------------------------------------------------------------


def _seed_m3_db(conn: kuzu.Connection, run_id: str = "test-m3-001") -> None:
    """Seed a minimal m3-shaped DB: MilestoneRun + SpecRun (with reasoning fields) + REASONING_ADDS."""
    _execute_schema(conn, Path("src/milestones/m3/migration/schema.cypher"))

    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn.execute(
        "CREATE (:MilestoneRun {run_id: $rid, milestone: 'm3', model: 'test', timestamp: $ts})",
        parameters={"rid": run_id, "ts": ts},
    )
    for brief in ("simple", "complex"):
        node_id = f"{run_id}:{brief}"
        conn.execute(
            "CREATE (:SpecRun {id: $id, run_id: $rid, milestone: 'm3', "
            "brief_label: $brief, selected_lang: 'OpenAPI', layer: 'api', "
            "confidence: 0.94, justification_char_count: 220, latency_ms: 900.0, "
            "model: 'test', timestamp: $ts, reasoning_step_count: 5, "
            "evaluation_depth: 'per_concern'})",
            parameters={"id": node_id, "rid": run_id, "brief": brief, "ts": ts},
        )
        conn.execute(
            "MATCH (s:SpecRun {id: $sid}), (r:MilestoneRun {run_id: $rid}) "
            "CREATE (s)-[:SPEC_CAPTURED_IN]->(r)",
            parameters={"sid": node_id, "rid": run_id},
        )

    # One REASONING_ADDS edge to verify it survives m3→m4 migration
    conn.execute(
        "MATCH (s1:SpecRun {brief_label: 'simple'}), (s2:SpecRun {brief_label: 'complex'}) "
        "CREATE (s1)-[:REASONING_ADDS {confidence_delta: 0.02, step_count: 5, "
        "evaluation_depth: 'per_concern', adds_candidate_rejection: false}]->(s2)"
    )


@pytest.fixture
def source_db_m3(tmp_path):
    """Ephemeral m3-shaped source DB."""
    db_path = tmp_path / "source_db_m3"
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)
    _seed_m3_db(conn)
    del conn, db
    return db_path


# ---------------------------------------------------------------------------
# M4 schema + migration (m3 → m4)
# ---------------------------------------------------------------------------


def test_schema_cypher_m4_creates_valid_db(tmp_path):
    """m4/schema.cypher creates a DB with all M4 tables including new ones."""
    db_path = tmp_path / "m4_schema_test"
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)

    schema_path = Path("src/milestones/m4/migration/schema.cypher")
    _execute_schema(conn, schema_path)

    node_tables, rel_tables = _schema_tables(schema_path)
    assert "RevisionEvent" in node_tables
    assert "VERIFICATION_ADDS" in rel_tables
    assert "REASONING_ADDS" in rel_tables  # carried forward from M3

    for t in node_tables:
        _exec(conn, f"MATCH (n:{t}) RETURN count(n)").get_next()
    for t in rel_tables:
        _exec(conn, f"MATCH ()-[r:{t}]->() RETURN count(r)").get_next()


def test_schema_cypher_m4_specrun_columns(tmp_path):
    """SpecRun at M4 has revised and revision_notes in addition to M3 columns."""
    db_path = tmp_path / "m4_col_test"
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)
    _execute_schema(conn, Path("src/milestones/m4/migration/schema.cypher"))

    columns = {
        cast(list, row)[1]: cast(list, row)[2]
        for row in _exec(conn, 'CALL table_info("SpecRun") RETURN *').get_all()
    }
    assert "revised" in columns and columns["revised"] == "BOOL"
    assert "revision_notes" in columns and columns["revision_notes"] == "STRING"
    assert "reasoning_step_count" in columns  # M3 columns preserved


def test_full_migration_m4_row_counts(source_db_m3):
    """m3→m4 migration preserves SpecRun + REASONING_ADDS; adds RevisionEvent table."""
    migrate("m4", dry_run=False, db_path=source_db_m3)

    new_db = kuzu.Database(str(source_db_m3))
    new_conn = kuzu.Connection(new_db)

    assert _count(new_conn, "MATCH (n:SpecRun) RETURN count(n)") == 2
    assert _count(new_conn, "MATCH ()-[r:REASONING_ADDS]->() RETURN count(r)") == 1

    # Backfill values for M3 rows
    for row in _exec(new_conn, "MATCH (s:SpecRun) RETURN s.revised, s.revision_notes"):
        assert cast(list, row)[0] is False
        assert cast(list, row)[1] == ""

    # New tables exist and are empty
    assert _count(new_conn, "MATCH (n:RevisionEvent) RETURN count(n)") == 0
    assert _count(new_conn, "MATCH ()-[r:VERIFICATION_ADDS]->() RETURN count(r)") == 0


# ---------------------------------------------------------------------------
# diff: m2 → m3 and m3 → m4
# ---------------------------------------------------------------------------


def test_diff_m2_m3_specrun_changed():
    """diff m2 m3 reports SpecRun as CHANGED (reasoning columns added)."""
    lines = diff("m2", "m3")
    assert any("CHANGED" in ln and "SpecRun" in ln for ln in lines)


def test_diff_m2_m3_reasoning_adds_new():
    """diff m2 m3 reports REASONING_ADDS as NEW."""
    lines = diff("m2", "m3")
    assert any(ln.startswith("NEW") and "REASONING_ADDS" in ln for ln in lines)


def test_diff_m3_m4_specrun_changed():
    """diff m3 m4 reports SpecRun as CHANGED (revised + revision_notes added)."""
    lines = diff("m3", "m4")
    assert any("CHANGED" in ln and "SpecRun" in ln for ln in lines)


def test_diff_m3_m4_new_tables():
    """diff m3 m4 reports RevisionEvent as NEW NODE and VERIFICATION_ADDS as NEW REL."""
    lines = diff("m3", "m4")
    assert any(ln.startswith("NEW") and "RevisionEvent" in ln for ln in lines)
    assert any(ln.startswith("NEW") and "VERIFICATION_ADDS" in ln for ln in lines)
