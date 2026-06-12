"""
M2 milestone runner — seeds two SpecRun subgraphs into the persistent Kuzu DB.

Usage:
    python3 -m src.milestones.m2.run [run-id]
    python3 -m src.milestones.m2.run [run-id] --model claude-sonnet-4-6

Each invocation:
  - Calls the M2 Spec Advisor (COSTAR-only) for two project briefs: simple + complex
  - Creates one MilestoneRun node + two SpecRun nodes + two SPEC_CAPTURED_IN edges
  - Prints a summary of the seeded nodes

Run it N times to accumulate N subgraphs for Claude-in-loop analysis.

Imports from src.milestones.m2.agent — NOT src.agents.spec_advisor.
"""

import argparse
import os
import time
from pathlib import Path
from typing import cast

import kuzu
from dotenv import load_dotenv

from src.milestones.m2.agent import SpecAdvisorAgent
from src.milestones.m2.graph.runner import seed
from src.milestones.m2.graph.schema import ensure_schema

load_dotenv()

_BRIEFS: list[tuple[str, str]] = [
    (
        "simple",
        "A REST API for a simple todo app with CRUD operations on task items, "
        "backed by a PostgreSQL database.",
    ),
    (
        "complex",
        "A distributed payment processing platform with multi-region active-active "
        "deployment, eventual consistency across regional nodes, concurrent transaction "
        "handling with idempotency guarantees, and a full audit trail for regulatory compliance.",
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed one M2 subgraph into the GNN")
    parser.add_argument("run_id", nargs="?", help="Run ID label (auto-generated if omitted)")
    parser.add_argument(
        "--model",
        default=os.getenv("MODEL_NAME", "claude-sonnet-4-6"),
        help="Model to use for inference (default: MODEL_NAME env or claude-sonnet-4-6)",
    )
    args = parser.parse_args()

    import datetime

    run_id = args.run_id or datetime.datetime.utcnow().strftime("m2-%Y%m%d-%H%M%S")
    db_path = os.getenv("KUZU_DB_PATH", "data/kuzu")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    try:
        ensure_schema(conn)

        # Idempotent: skip if this run already exists
        existing = {
            cast(list, row)[0]
            for row in cast(list, cast(kuzu.QueryResult, conn.execute(
                "MATCH (r:MilestoneRun) RETURN r.run_id"
            )).get_all())
        }
        if run_id in existing:
            print(f"run_id {run_id} already exists — choose a different id or omit for auto-gen")
            return

        # Create MilestoneRun anchor
        conn.execute(
            "CREATE (:MilestoneRun {run_id: $run_id, milestone: 'm2', "
            "model: $model, timestamp: $ts})",
            parameters={
                "run_id": run_id,
                "model": args.model,
                "ts": datetime.datetime.utcnow().isoformat() + "Z",
            },
        )

        agent = SpecAdvisorAgent()
        results = []

        for brief_label, brief_text in _BRIEFS:
            print(f"  [{brief_label}] calling M2 Spec Advisor...", end=" ", flush=True)
            t0 = time.perf_counter()
            output = agent.run(brief_text)
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)

            node_id = seed(
                conn=conn,
                output=output,
                brief_label=brief_label,
                run_id=run_id,
                model=args.model,
                latency_ms=latency_ms,
            )
            results.append((brief_label, output, latency_ms, node_id))
            print(f"done ({latency_ms:.0f}ms)")

        # Summary
        print(f"\nrun_id  : {run_id}")
        print(f"db      : {db_path}")
        print(f"model   : {args.model}")
        print(f"\n{'brief':<10} {'lang':<14} {'layer':<12} {'conf':>5} {'ms':>7}")
        print("-" * 52)
        for brief_label, output, latency_ms, _ in results:
            print(
                f"{brief_label:<10} {output.selected_lang:<14} {output.layer:<12} "
                f"{output.confidence:>5.2f} {latency_ms:>7.0f}"
            )

        _res = conn.execute(
            "MATCH (r:MilestoneRun {milestone: 'm2'}) RETURN r.run_id, r.timestamp "
            "ORDER BY r.timestamp"
        )
        # kuzu.Connection.execute may return a QueryResult with get_all(), or
        # a plain list depending on bindings. Handle both.
        all_runs = _res.get_all() if hasattr(_res, "get_all") else list(_res)
        print(f"\ntotal m2 runs in DB: {len(all_runs)}")
        for rid, ts in all_runs:
            marker = " ← this run" if rid == run_id else ""
            print(f"  {rid}  {ts}{marker}")

        usage = agent.session_usage
        print(
            f"\ntokens  : {usage.total_input_tokens} in / {usage.total_output_tokens} out "
            f"({usage.calls} calls)"
        )
    finally:
        conn.close()
        db.close()


if __name__ == "__main__":
    main()
