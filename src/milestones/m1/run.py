"""
M1 milestone runner — seeds one subgraph into the persistent Kuzu DB.

Usage:
    python3 -m src.milestones.m1.run [run-id]

Each invocation creates one MilestoneRun node + 9 FrameworkLayer nodes + CAPTURED_IN edges.
Run it N times with distinct run-ids to accumulate N subgraphs for comparison.

Example — 3 runs:
    python3 -m src.milestones.m1.run m1-run-001
    python3 -m src.milestones.m1.run m1-run-002
    python3 -m src.milestones.m1.run m1-run-003
"""

import argparse
import os
from pathlib import Path
from typing import cast

import kuzu
from dotenv import load_dotenv

from .graph.runner import seed

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed one M1 subgraph into the GNN")
    parser.add_argument("run_id", nargs="?", help="Run ID label (auto-generated if omitted)")
    parser.add_argument(
        "--model", default="local", help="Model label for this run (default: local)"
    )
    args = parser.parse_args()

    db_path = os.getenv("KUZU_DB_PATH", "data/kuzu")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    try:
        run_id = seed(conn, run_id=args.run_id, model=args.model)

        count = cast(list, cast(list, cast(kuzu.QueryResult, conn.execute(
            "MATCH (r:MilestoneRun {run_id: $rid})<-[:CAPTURED_IN]-(f) RETURN count(f)",
            parameters={"rid": run_id},
        )).get_all())[0])[0]

        all_runs = cast(list, cast(kuzu.QueryResult, conn.execute(
            "MATCH (r:MilestoneRun) RETURN r.run_id, r.timestamp ORDER BY r.timestamp"
        )).get_all())

        print(f"run_id  : {run_id}")
        print(f"db      : {db_path}")
        print(f"nodes   : {count} FrameworkLayer")
        print(f"total runs in DB: {len(all_runs)}")
        for rid, ts in all_runs:
            marker = " ← this run" if rid == run_id else ""
            print(f"  {rid}  {ts}{marker}")
    finally:
        conn.close()
        db.close()


if __name__ == "__main__":
    main()
