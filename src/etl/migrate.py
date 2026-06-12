"""
ETL migration runner — blue-green Kuzu DB rotation.

Usage:
  python3 -m src.etl.migrate --to m2 [--dry-run] [--db data/kuzu]

Sequence:
  1. Read migration/meta.json from target milestone
  2. Execute COPY blocks in transform.cypher against source DB → Parquet files in tmp dir
  3. Create new empty DB from schema.cypher (skipped on --dry-run)
  4. Bulk-load Parquet into new DB: nodes first, rels second
  5. Re-seed reseed_tables from source code
  6. Verify row counts match source
  7. Rotate: data/kuzu → data/kuzu_bak_YYYYMMDD, new DB → data/kuzu
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, cast

import kuzu

_MILESTONES_DIR = Path("src/milestones")
_DEFAULT_DB = Path("data/kuzu")

# Maps rel table name → (from_col, to_col) in Parquet files exported by transform.cypher.
# All transform.cypher files use 'src_id' and 'dst_id' as the convention.
_REL_COL_DEFAULTS = ("src_id", "dst_id")


def _exec(
    conn: kuzu.Connection, query: str, params: dict[str, Any] | None = None
) -> kuzu.QueryResult:
    """Execute a string query; cast result to QueryResult (always the case for string input)."""
    return cast(kuzu.QueryResult, conn.execute(query, params or {}))


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_copy_blocks(transform_sql: str, output_dir: str) -> list[tuple[str, str]]:
    """
    Parse all COPY (...) TO 'path' blocks from transform.cypher.

    Returns [(table_name, executable_query)] with {output_dir} substituted.
    Line comments (--) are stripped before parsing.
    """
    lines = [
        line for line in transform_sql.split("\n")
        if not line.strip().startswith("--")
    ]
    text = "\n".join(lines).replace("{output_dir}", output_dir)

    pattern = re.compile(r"(COPY\s*\(.*?\)\s*TO\s*'[^']+')", re.DOTALL)
    blocks: list[tuple[str, str]] = []
    for match in pattern.finditer(text):
        query = match.group(1).strip()
        path_match = re.search(r"TO\s+'([^']+)'", query)
        if path_match:
            table_name = Path(path_match.group(1)).stem
            blocks.append((table_name, query))
    return blocks


def _execute_schema(conn: kuzu.Connection, schema_path: Path) -> None:
    """Execute each CREATE TABLE statement from schema.cypher."""
    text = schema_path.read_text()
    # Strip comments before splitting — comments may contain semicolons that
    # would otherwise be treated as statement delimiters.
    lines = [line for line in text.split("\n") if not line.strip().startswith("--")]
    for stmt in "\n".join(lines).split(";"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)


def _schema_tables(schema_path: Path) -> tuple[set[str], set[str]]:
    """Parse schema.cypher and return (node_table_names, rel_table_names)."""
    text = schema_path.read_text()
    nodes = set(re.findall(r"CREATE NODE TABLE (\w+)", text))
    rels = set(re.findall(r"CREATE REL TABLE (\w+)", text))
    return nodes, rels


def _count_table(conn: kuzu.Connection, table_name: str, is_rel: bool) -> int:
    query = (
        f"MATCH ()-[r:{table_name}]->() RETURN count(r)"
        if is_rel
        else f"MATCH (n:{table_name}) RETURN count(n)"
    )
    return cast(list, _exec(conn, query).get_next())[0]


# ---------------------------------------------------------------------------
# Reseed dispatch
# ---------------------------------------------------------------------------


def _reseed_table(conn: kuzu.Connection, table: str) -> None:
    """Re-seed a deterministic table from source code into an already-open new DB."""
    if table == "FrameworkLayer":
        from src.milestones.m1.graph.runner import reseed_frameworks
        run_ids = [
            cast(list, row)[0]
            for row in cast(
                list,
                _exec(conn, "MATCH (r:MilestoneRun {milestone: 'm1'}) RETURN r.run_id").get_all(),
            )
        ]
        if run_ids:
            reseed_frameworks(conn, run_ids)
    else:
        raise NotImplementedError(f"No reseed handler for table: {table!r}")


# ---------------------------------------------------------------------------
# Main migration pipeline
# ---------------------------------------------------------------------------


def migrate(
    target_milestone: str,
    dry_run: bool = False,
    db_path: Path = _DEFAULT_DB,
) -> None:
    mig_dir = _MILESTONES_DIR / target_milestone / "migration"
    if not mig_dir.exists():
        raise FileNotFoundError(f"Migration dir not found: {mig_dir}")

    meta = json.loads((mig_dir / "meta.json").read_text())
    reseed_tables: set[str] = set(meta.get("reseed_tables", []))
    schema_path = mig_dir / "schema.cypher"
    transform_path = mig_dir / "transform.cypher"

    node_tables, rel_tables = _schema_tables(schema_path)

    with tempfile.TemporaryDirectory(prefix="faber_etl_") as tmp:
        tmp_path = Path(tmp)

        # Step 1 — export source DB to Parquet
        src_db = kuzu.Database(str(db_path))
        src_conn = kuzu.Connection(src_db)

        transform_sql = transform_path.read_text()
        blocks = _parse_copy_blocks(transform_sql, str(tmp_path))

        print(f"Exporting {len(blocks)} table(s) from {db_path} …")
        for table_name, query in blocks:
            print(f"  → {table_name}.parquet")
            src_conn.execute(query)

        if dry_run:
            print("\n--dry-run: Parquet files written; stopping before DB creation.")
            for dry_file in sorted(tmp_path.glob("*.parquet")):
                print(f"  {dry_file.name}  ({dry_file.stat().st_size:,} bytes)")
            return

        # Step 2 — create new empty DB from schema.cypher
        new_db_path = db_path.parent / (db_path.name + "_new")
        if new_db_path.exists():
            shutil.rmtree(new_db_path)

        new_db = kuzu.Database(str(new_db_path))
        new_conn = kuzu.Connection(new_db)
        print(f"\nCreating new DB at {new_db_path} …")
        _execute_schema(new_conn, schema_path)

        # Step 3 — load nodes (nodes before rels; skip reseed_tables)
        parquet_files: dict[str, Path] = {
            f.stem: f for f in tmp_path.glob("*.parquet")
        }

        print("Loading nodes …")
        for table_name in node_tables:
            if table_name in reseed_tables:
                continue
            if table_name not in parquet_files:
                print(f"  (skip {table_name} — no Parquet exported)")
                continue
            path = parquet_files[table_name]
            print(f"  COPY {table_name} FROM parquet")
            new_conn.execute(f"COPY {table_name} FROM '{path}'")

        # Step 4 — re-seed deterministic tables
        for table in reseed_tables:
            print(f"  Reseeding {table} …")
            _reseed_table(new_conn, table)

        # Step 5 — load rels
        print("Loading rels …")
        for table_name in rel_tables:
            if table_name not in parquet_files:
                print(f"  (skip {table_name} — no Parquet exported)")
                continue
            path = parquet_files[table_name]
            from_col, to_col = _REL_COL_DEFAULTS
            print(f"  COPY {table_name} FROM parquet")
            new_conn.execute(
                f"COPY {table_name} FROM '{path}' "
                f"(from='{from_col}', to='{to_col}')"
            )

        # Step 6 — verify row counts
        print("\nVerifying …")
        all_ok = True
        for table_name in sorted(node_tables | rel_tables):
            is_rel = table_name in rel_tables
            # Tables new in this migration don't exist in the source DB — treat as 0
            try:
                src_count = _count_table(src_conn, table_name, is_rel)
            except RuntimeError:
                src_count = 0
            new_count = _count_table(new_conn, table_name, is_rel)
            status = "✓" if src_count == new_count else "✗"
            print(f"  {status}  {table_name}: {src_count} → {new_count}")
            if src_count != new_count:
                all_ok = False

        if not all_ok:
            # Clean up failed new DB
            del new_conn, new_db
            shutil.rmtree(new_db_path)
            raise RuntimeError("Row count mismatch — migration aborted. New DB removed.")

        # Step 7 — rotate DBs
        del new_conn, new_db
        del src_conn, src_db

        today = datetime.date.today().strftime("%Y%m%d")
        backup_path = db_path.parent / f"{db_path.name}_bak_{today}"
        print("\nRotating …")
        print(f"  {db_path} → {backup_path}")
        shutil.move(str(db_path), str(backup_path))
        print(f"  {new_db_path} → {db_path}")
        shutil.move(str(new_db_path), str(db_path))
        print(f"\nDone. Backup at {backup_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Kuzu ETL migration runner")
    parser.add_argument("--to", required=True, metavar="MILESTONE",
                        help="Target milestone (e.g. m2)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Export Parquet files only; do not create or rotate DB")
    parser.add_argument("--db", default=str(_DEFAULT_DB), metavar="PATH",
                        help=f"Kuzu DB path (default: {_DEFAULT_DB})")
    args = parser.parse_args()
    migrate(args.to, dry_run=args.dry_run, db_path=Path(args.db))


if __name__ == "__main__":
    main()
