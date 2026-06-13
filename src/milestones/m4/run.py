"""
M4 milestone runner — seeds M4 SpecRun subgraph, RevisionEvent nodes,
and VERIFICATION_ADDS cross-schema edges.

Usage:
    python3 -m src.milestones.m4.run [run-id]
    python3 -m src.milestones.m4.run [run-id] --model claude-sonnet-4-6
    python3 -m src.milestones.m4.run [run-id] --m3-run-id <m3-run-id>

Each invocation:
  - Calls the M4 Spec Advisor (COSTAR + ChainOfThought + ConstitutionalAI) for three briefs:
    simple, complex, and vague
  - Creates one MilestoneRun node + three SpecRun nodes + three RevisionEvent nodes
  - If --m3-run-id is given (or auto-detected), writes VERIFICATION_ADDS edges from matched
    M3 SpecRun nodes (simple + complex only — vague has no M3 counterpart)

Run N times to accumulate N subgraphs.

Imports from src.milestones.m4.agent — NOT src.agents.spec_advisor.
"""

import argparse
import datetime
import os
import time
from pathlib import Path
from typing import cast

import kuzu
from dotenv import load_dotenv

from src.milestones.m4.agent import SpecAdvisorAgent
from src.milestones.m4.graph.runner import seed
from src.milestones.m4.graph.schema import ensure_schema

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
    (
        "vague",
        "Build something to help our team collaborate better.",
    ),
]


def _latest_m3_run_id(conn: kuzu.Connection) -> str | None:
    """Return the most recent M3 MilestoneRun run_id, or None if no M3 runs exist."""
    result = conn.execute(
        "MATCH (r:MilestoneRun {milestone: 'm3'}) RETURN r.run_id, r.timestamp "
        "ORDER BY r.timestamp DESC LIMIT 1"
    )
    rows = result.get_all() if hasattr(result, "get_all") else list(result)
    if rows:
        return rows[0][0]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed one M4 subgraph into the GNN")
    parser.add_argument("run_id", nargs="?", help="Run ID label (auto-generated if omitted)")
    parser.add_argument(
        "--model",
        default=os.getenv("MODEL_NAME", "claude-sonnet-4-6"),
        help="Model to use for inference (default: MODEL_NAME env or claude-sonnet-4-6)",
    )
    parser.add_argument(
        "--m3-run-id",
        dest="m3_run_id",
        default=None,
        help="M3 run_id to link VERIFICATION_ADDS edges from. "
        "If omitted, auto-selects the most recent M3 run.",
    )
    args = parser.parse_args()

    run_id = args.run_id or datetime.datetime.utcnow().strftime("m4-%Y%m%d-%H%M%S")
    db_path = os.getenv("KUZU_DB_PATH", "data/kuzu")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    try:
        ensure_schema(conn)

        # Idempotent: skip if this run already exists
        existing = {
            cast(list, row)[0]
            for row in cast(
                list,
                cast(
                    kuzu.QueryResult, conn.execute("MATCH (r:MilestoneRun) RETURN r.run_id")
                ).get_all(),
            )
        }
        if run_id in existing:
            print(f"run_id {run_id} already exists — choose a different id or omit for auto-gen")
            return

        # Resolve M3 run_id for VERIFICATION_ADDS edges
        m3_run_id = args.m3_run_id or _latest_m3_run_id(conn)
        if m3_run_id:
            print(f"linking VERIFICATION_ADDS → M3 run: {m3_run_id}")
        else:
            print("no M3 runs found in DB — VERIFICATION_ADDS edges will not be written")

        # Create MilestoneRun anchor
        conn.execute(
            "CREATE (:MilestoneRun {run_id: $run_id, milestone: 'm4', "
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
            print(f"  [{brief_label}] calling M4 Spec Advisor...", end=" ", flush=True)
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
                m3_run_id=m3_run_id,
            )
            results.append((brief_label, output, latency_ms, node_id))
            revised_marker = " [REVISED]" if output.revised else ""
            print(f"done ({latency_ms:.0f}ms, {len(output.reasoning_steps)} steps){revised_marker}")

        # Summary table
        print(f"\nrun_id  : {run_id}")
        print(f"db      : {db_path}")
        print(f"model   : {args.model}")
        print(
            f"\n{'brief':<10} {'lang':<14} {'layer':<12} {'conf':>5} "
            f"{'steps':>6} {'revised':>8} {'ms':>7}"
        )
        print("-" * 70)
        for brief_label, output, latency_ms, _ in results:
            print(
                f"{brief_label:<10} {output.selected_lang:<14} {output.layer:<12} "
                f"{output.confidence:>5.2f} {len(output.reasoning_steps):>6} "
                f"{str(output.revised):>8} {latency_ms:>7.0f}"
            )

        _res = conn.execute(
            "MATCH (r:MilestoneRun {milestone: 'm4'}) RETURN r.run_id, r.timestamp "
            "ORDER BY r.timestamp"
        )
        all_runs = _res.get_all() if hasattr(_res, "get_all") else list(_res)
        print(f"\ntotal m4 runs in DB: {len(all_runs)}")
        for rid, ts in all_runs:
            marker = " ← this run" if rid == run_id else ""
            print(f"  {rid}  {ts}{marker}")

        # Report RevisionEvent summary
        _rev = conn.execute(
            "MATCH (e:RevisionEvent {run_id: $rid}) "
            "RETURN e.brief_label, e.revised, e.cai_principle_triggered, "
            "e.assumption_inventory_added",
            parameters={"rid": run_id},
        )
        rev_rows = _rev.get_all() if hasattr(_rev, "get_all") else list(_rev)
        if rev_rows:
            print(f"\nRevisionEvent nodes (run={run_id}):")
            for brief, revised, principle, assumption in rev_rows:
                print(
                    f"  {brief:<10} revised={str(revised):<6} "
                    f"principle={principle or '—':<36} assumption={assumption}"
                )

        # Report VERIFICATION_ADDS edges written
        if m3_run_id:
            _ev = conn.execute(
                "MATCH (m3:SpecRun {run_id: $m3rid})-[e:VERIFICATION_ADDS]"
                "->(m4:SpecRun {run_id: $m4rid}) "
                "RETURN m3.brief_label, e.revised, e.confidence_delta, "
                "e.cai_principle_triggered",
                parameters={"m3rid": m3_run_id, "m4rid": run_id},
            )
            edge_rows = _ev.get_all() if hasattr(_ev, "get_all") else list(_ev)
            if edge_rows:
                print(f"\nVERIFICATION_ADDS edges (m3={m3_run_id} → m4={run_id}):")
                for brief, revised, delta, principle in edge_rows:
                    print(
                        f"  {brief:<10} revised={str(revised):<6} "
                        f"conf_delta={delta:+.3f}  principle={principle or '—'}"
                    )

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
