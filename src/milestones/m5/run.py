"""
M5 milestone runner — seeds M5 SpecRun subgraph, MetaPromptEvent nodes,
and META_PROMPT_ADDS cross-schema edges. Calls SpecSpecialistAgent for the complex brief.

Usage:
    python3 -m src.milestones.m5.run [run-id]
    python3 -m src.milestones.m5.run [run-id] --model claude-sonnet-4-6
    python3 -m src.milestones.m5.run [run-id] --m4-run-id <m4-run-id>

Each invocation:
  - Calls the M5 Spec Advisor (COSTAR + ChainOfThought + ConstitutionalAI + build_crispe_prompt)
    for three briefs: simple, complex, and vague
  - Creates one MilestoneRun node + three SpecRun nodes + three MetaPromptEvent nodes
  - If --m4-run-id is given (or auto-detected), writes META_PROMPT_ADDS edges from matched
    M4 SpecRun nodes (all 3 briefs — first full cross-schema coverage)
  - Calls SpecSpecialistAgent for the complex brief and prints spec_content[:200]

Run N times to accumulate N subgraphs.

Imports from src.milestones.m5.agent — NOT src.agents.
"""

import argparse
import datetime
import os
import time
from pathlib import Path
from typing import cast

import kuzu
from dotenv import load_dotenv

from src.milestones.m5.agent import SpecAdvisorAgent
from src.milestones.m5.graph.runner import seed
from src.milestones.m5.graph.schema import ensure_schema
from src.milestones.m5.spec_specialist import SpecSpecialistAgent

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


def _latest_m4_run_id(conn: kuzu.Connection) -> str | None:
    """Return the most recent M4 MilestoneRun run_id, or None if no M4 runs exist."""
    result = conn.execute(
        "MATCH (r:MilestoneRun {milestone: 'm4'}) RETURN r.run_id, r.timestamp "
        "ORDER BY r.timestamp DESC LIMIT 1"
    )
    rows = result.get_all() if hasattr(result, "get_all") else list(result)
    if rows:
        return rows[0][0]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed one M5 subgraph into the GNN")
    parser.add_argument("run_id", nargs="?", help="Run ID label (auto-generated if omitted)")
    parser.add_argument(
        "--model",
        default=os.getenv("MODEL_NAME", "claude-sonnet-4-6"),
        help="Model to use for inference (default: MODEL_NAME env or claude-sonnet-4-6)",
    )
    parser.add_argument(
        "--m4-run-id",
        dest="m4_run_id",
        default=None,
        help="M4 run_id to link META_PROMPT_ADDS edges from. "
        "If omitted, auto-selects the most recent M4 run.",
    )
    args = parser.parse_args()

    run_id = args.run_id or datetime.datetime.utcnow().strftime("m5-%Y%m%d-%H%M%S")
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

        # Resolve M4 run_id for META_PROMPT_ADDS edges
        m4_run_id = args.m4_run_id or _latest_m4_run_id(conn)
        if m4_run_id:
            print(f"linking META_PROMPT_ADDS → M4 run: {m4_run_id}")
        else:
            print("no M4 runs found in DB — META_PROMPT_ADDS edges will not be written")

        # Create MilestoneRun anchor
        conn.execute(
            "CREATE (:MilestoneRun {run_id: $run_id, milestone: 'm5', "
            "model: $model, timestamp: $ts})",
            parameters={
                "run_id": run_id,
                "model": args.model,
                "ts": datetime.datetime.utcnow().isoformat() + "Z",
            },
        )

        advisor = SpecAdvisorAgent()
        results = []
        complex_output = None

        for brief_label, brief_text in _BRIEFS:
            print(f"  [{brief_label}] calling M5 Spec Advisor...", end=" ", flush=True)
            t0 = time.perf_counter()
            output = advisor.run(brief_text)
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)

            node_id = seed(
                conn=conn,
                output=output,
                brief_label=brief_label,
                run_id=run_id,
                model=args.model,
                latency_ms=latency_ms,
                m4_run_id=m4_run_id,
            )
            results.append((brief_label, output, latency_ms, node_id))
            revised_marker = " [REVISED]" if output.revised else ""
            print(
                f"done ({latency_ms:.0f}ms, {len(output.reasoning_steps)} steps, "
                f"crispe_len={len(output.specialist_crispe_prompt)}){revised_marker}"
            )
            if brief_label == "complex":
                complex_output = (brief_text, output)

        # Call SpecSpecialistAgent for complex brief as validation
        if complex_output is not None:
            brief_text, adv_output = complex_output
            print("\n  [complex] calling SpecSpecialistAgent...", end=" ", flush=True)
            t0 = time.perf_counter()
            specialist = SpecSpecialistAgent()
            spec = specialist.run(brief_text, adv_output.specialist_crispe_prompt)
            spec_ms = round((time.perf_counter() - t0) * 1000, 2)
            print(f"done ({spec_ms:.0f}ms, lang={spec.spec_lang}, conf={spec.confidence:.2f})")
            print(f"\n  spec_content[:200]:\n{spec.spec_content[:200]}")

        # Summary table
        print(f"\nrun_id  : {run_id}")
        print(f"db      : {db_path}")
        print(f"model   : {args.model}")
        print(
            f"\n{'brief':<10} {'lang':<14} {'layer':<12} {'conf':>5} "
            f"{'steps':>6} {'crispe_fields':>13} {'cap_match':>9} {'crispe_len':>10} {'ms':>7}"
        )
        print("-" * 95)
        for brief_label, output, latency_ms, _ in results:
            from src.milestones.m5.graph.runner import (
                _extract_section,
                infer_capacity_matches_lang,
                infer_crispe_field_count,
            )

            prompt = output.specialist_crispe_prompt
            field_count = infer_crispe_field_count(prompt)
            cap_text = _extract_section(prompt, "Capacity")
            cap_match = infer_capacity_matches_lang(cap_text, output.selected_lang)
            print(
                f"{brief_label:<10} {output.selected_lang:<14} {output.layer:<12} "
                f"{output.confidence:>5.2f} {len(output.reasoning_steps):>6} "
                f"{field_count:>13} {str(cap_match):>9} {len(prompt):>10} {latency_ms:>7.0f}"
            )

        _res = conn.execute(
            "MATCH (r:MilestoneRun {milestone: 'm5'}) RETURN r.run_id, r.timestamp "
            "ORDER BY r.timestamp"
        )
        all_runs = _res.get_all() if hasattr(_res, "get_all") else list(_res)
        print(f"\ntotal m5 runs in DB: {len(all_runs)}")
        for rid, ts in all_runs:
            marker = " ← this run" if rid == run_id else ""
            print(f"  {rid}  {ts}{marker}")

        # Report MetaPromptEvent summary
        _meta = conn.execute(
            "MATCH (e:MetaPromptEvent {run_id: $rid}) "
            "RETURN e.brief_label, e.crispe_field_count, e.insight_char_count, "
            "e.capacity_matches_lang",
            parameters={"rid": run_id},
        )
        meta_rows = _meta.get_all() if hasattr(_meta, "get_all") else list(_meta)
        if meta_rows:
            print(f"\nMetaPromptEvent nodes (run={run_id}):")
            for brief, fields, insight_chars, cap_match in meta_rows:
                print(
                    f"  {brief:<10} crispe_fields={fields}  "
                    f"insight_chars={insight_chars}  cap_match={cap_match}"
                )

        if m4_run_id:
            _ev = conn.execute(
                "MATCH (m4:SpecRun {run_id: $m4rid})-[e:META_PROMPT_ADDS]"
                "->(m5:SpecRun {run_id: $m5rid}) "
                "RETURN m4.brief_label, e.crispe_field_count, e.prompt_char_count, "
                "e.capacity_matches_lang",
                parameters={"m4rid": m4_run_id, "m5rid": run_id},
            )
            edge_rows = _ev.get_all() if hasattr(_ev, "get_all") else list(_ev)
            if edge_rows:
                print(f"\nMETA_PROMPT_ADDS edges (m4={m4_run_id} → m5={run_id}):")
                for brief, fields, prompt_chars, cap_match in edge_rows:
                    print(
                        f"  {brief:<10} crispe_fields={fields}  "
                        f"prompt_chars={prompt_chars}  cap_match={cap_match}"
                    )

        usage = advisor.session_usage
        print(
            f"\ntokens  : {usage.total_input_tokens} in / {usage.total_output_tokens} out "
            f"({usage.calls} calls)"
        )
    finally:
        conn.close()
        db.close()


if __name__ == "__main__":
    main()
