"""
M3 milestone runner — seeds M3 SpecRun subgraph and REASONING_ADDS cross-schema edges.

Usage:
    python3 -m src.milestones.m3.run [run-id]
    python3 -m src.milestones.m3.run [run-id] --model claude-sonnet-4-6
    python3 -m src.milestones.m3.run [run-id] --m2-run-id <m2-run-id>

Each invocation:
  - Calls the M3 Spec Advisor (COSTAR + ChainOfThought) for two briefs: simple + complex
  - Creates one MilestoneRun node + two SpecRun nodes + two SPEC_CAPTURED_IN edges
  - If --m2-run-id is given, writes REASONING_ADDS edges from matched M2 SpecRun nodes

Run N times to accumulate N subgraphs. Pass the same --m2-run-id each time to link
M3 runs back to a specific M2 baseline for delta comparison.

Imports from src.milestones.m3.agent — NOT src.agents.spec_advisor.
"""

import argparse
import datetime
import os
import time
from pathlib import Path
from typing import cast

import kuzu
from dotenv import load_dotenv

from src.milestones.m3.agent import SpecAdvisorAgent
from src.milestones.m3.graph.runner import seed
from src.milestones.m3.graph.schema import ensure_schema

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


def _latest_m2_run_id(conn: kuzu.Connection) -> str | None:
    """Return the most recent M2 MilestoneRun run_id, or None if no M2 runs exist."""
    result = conn.execute(
        "MATCH (r:MilestoneRun {milestone: 'm2'}) RETURN r.run_id, r.timestamp "
        "ORDER BY r.timestamp DESC LIMIT 1"
    )
    rows = result.get_all() if hasattr(result, "get_all") else list(result)
    if rows:
        return rows[0][0]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed one M3 subgraph into the GNN")
    parser.add_argument("run_id", nargs="?", help="Run ID label (auto-generated if omitted)")
    parser.add_argument(
        "--model",
        default=os.getenv("MODEL_NAME", "claude-sonnet-4-6"),
        help="Model to use for inference (default: MODEL_NAME env or claude-sonnet-4-6)",
    )
    parser.add_argument(
        "--m2-run-id",
        dest="m2_run_id",
        default=None,
        help="M2 run_id to link REASONING_ADDS edges from. "
        "If omitted, auto-selects the most recent M2 run.",
    )
    args = parser.parse_args()

    run_id = args.run_id or datetime.datetime.utcnow().strftime("m3-%Y%m%d-%H%M%S")
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

        # Resolve M2 run_id for REASONING_ADDS edges
        m2_run_id = args.m2_run_id or _latest_m2_run_id(conn)
        if m2_run_id:
            print(f"linking REASONING_ADDS → M2 run: {m2_run_id}")
        else:
            print("no M2 runs found in DB — REASONING_ADDS edges will not be written")

        # Create MilestoneRun anchor
        conn.execute(
            "CREATE (:MilestoneRun {run_id: $run_id, milestone: 'm3', "
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
            print(f"  [{brief_label}] calling M3 Spec Advisor...", end=" ", flush=True)
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
                m2_run_id=m2_run_id,
            )
            results.append((brief_label, output, latency_ms, node_id))
            print(f"done ({latency_ms:.0f}ms, {len(output.reasoning_steps)} steps)")

        # Summary
        print(f"\nrun_id  : {run_id}")
        print(f"db      : {db_path}")
        print(f"model   : {args.model}")
        print(f"\n{'brief':<10} {'lang':<14} {'layer':<12} {'conf':>5} {'steps':>6} {'ms':>7}")
        print("-" * 60)
        for brief_label, output, latency_ms, _ in results:
            print(
                f"{brief_label:<10} {output.selected_lang:<14} {output.layer:<12} "
                f"{output.confidence:>5.2f} {len(output.reasoning_steps):>6} {latency_ms:>7.0f}"
            )

        _res = conn.execute(
            "MATCH (r:MilestoneRun {milestone: 'm3'}) RETURN r.run_id, r.timestamp "
            "ORDER BY r.timestamp"
        )
        all_runs = _res.get_all() if hasattr(_res, "get_all") else list(_res)
        print(f"\ntotal m3 runs in DB: {len(all_runs)}")
        for rid, ts in all_runs:
            marker = " ← this run" if rid == run_id else ""
            print(f"  {rid}  {ts}{marker}")

        # Report REASONING_ADDS edges written
        if m2_run_id:
            _er = conn.execute(
                "MATCH (m2:SpecRun {run_id: $m2rid})-[e:REASONING_ADDS]->(m3:SpecRun {run_id: $m3rid}) "
                "RETURN m2.brief_label, e.confidence_delta, e.step_count, e.evaluation_depth",
                parameters={"m2rid": m2_run_id, "m3rid": run_id},
            )
            edge_rows = _er.get_all() if hasattr(_er, "get_all") else list(_er)
            if edge_rows:
                print(f"\nREASONING_ADDS edges (m2={m2_run_id} → m3={run_id}):")
                for brief, delta, steps, depth in edge_rows:
                    print(f"  {brief:<10} conf_delta={delta:+.3f}  steps={steps}  depth={depth}")

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
