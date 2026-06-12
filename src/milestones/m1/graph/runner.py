"""
M1 runner — Framework Builder GNN seed and artifact export.

Captures per framework builder:
  build_output       — the actual prompt structure build() produces (GNN node feature)
  file_path          — which source file produced this (provenance)
  file_hash          — SHA-256 of file content (change detection across A/B runs)
  file_size_bytes    — source file size
  build_time_ms      — execution time of build() (performance signal)
  output_char_count  — prompt length in characters
  output_token_est   — token estimate (chars // 4, GPT-style heuristic)

Public API:
  extract() → list[dict]              pure Python, no Kuzu — callable by downstream milestones
  seed(conn) → list[dict]             ensure_schema + write nodes, returns records
  dump(conn, output_path) → None      export seeded data as JSON artifact for Claude analysis

Analysis is intentionally NOT done here. dump() writes raw features so Claude can query
the GNN and prior artifacts across milestones, decide what signals are interesting this
session, and write artifacts/m1_analysis.json freely. Code captures; Claude analyzes.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any, cast

import kuzu

from ..frameworks.chain_of_thought import ChainOfThought
from ..frameworks.clear import CLEARSession
from ..frameworks.constitutional_ai import ConstitutionalAI
from ..frameworks.costar import COSTARPrompt
from ..frameworks.crispe import CRISPEPrompt
from ..frameworks.few_shot import FewShot
from ..frameworks.persona import PersonaLayer
from ..frameworks.race import RACEPrompt
from ..frameworks.react import ReActLoop
from .schema import ensure_schema

_M1_DIR = Path(__file__).parent.parent  # src/milestones/m1/


# ---------------------------------------------------------------------------
# Sample instances — one per framework builder.
#
# These are representative instantiations grounded in the Spec Council's
# actual usage context. Their build() outputs become the FrameworkLayer
# node features in the GNN — the prompt structures that later milestones
# reference when writing COMPOSES and USES_CHAIN edges.
# ---------------------------------------------------------------------------

_INSTANCES: list[tuple[Any, str]] = [
    (
        COSTARPrompt(
            context=(
                "Spec Advisor council session. Project brief: REST API service for a todo app "
                "with a PostgreSQL backend."
            ),
            objective=(
                "Select the optimal formal specification language for the given project layer."
            ),
            style="Formal and analytical",
            tone="Rigorous and precise",
            audience="Spec Specialist agent — consumes the selection to generate a formal spec",
            response_format=(
                "Call report_spec_selection with: selected_lang, layer, justification, confidence"
            ),
        ),
        "frameworks/costar.py",
    ),
    (
        CRISPEPrompt(
            capacity="TLA+ formal specification specialist",
            role="Spec Specialist",
            insight=(
                "Distributed e-commerce system with eventual consistency and CQRS event sourcing. "
                "System-layer TLA+ spec required."
            ),
            statement=(
                "Generate a TLA+ specification for the inventory module covering the no-oversell "
                "safety invariant and eventual-convergence liveness property."
            ),
            personality="Precise, minimal, and verifiable",
            experiment=(
                "Generate the spec, then self-check for syntactic well-formedness and coverage "
                "of the stated safety and liveness objectives."
            ),
        ),
        "frameworks/crispe.py",
    ),
    (
        CLEARSession(
            context=(
                "Prior layer: system-level TLA+ spec produced covering distributed consistency. "
                "Now addressing the domain layer for the order management subdomain."
            ),
            layering="System → Domain → Component",
            execute=(
                "Select a spec language and generate a domain model for order management, "
                "grounded in the system-layer invariants."
            ),
            assess=(
                "Does the domain spec reference the system-level invariants? "
                "Is the language appropriate for domain-level modelling?"
            ),
            reflect=(
                "What did the domain layer add over the system layer? "
                "Which concerns does the component layer inherit?"
            ),
        ),
        "frameworks/clear.py",
    ),
    (
        RACEPrompt(
            role="Spec Advisor",
            action="Select the optimal formal specification language for this project layer",
            context=(
                "Multi-region e-commerce platform with eventual consistency and CQRS event sourcing"
            ),
            execute="Return selected_lang, layer, and a one-paragraph justification",
        ),
        "frameworks/race.py",
    ),
    (
        PersonaLayer(
            role="Senior Fintech PM",
            background=(
                "10 years in payments and compliance. Deep expertise in PCI-DSS, ISO 20022, "
                "and real-time settlement protocols."
            ),
            priorities="Regulatory compliance, transaction velocity, and full auditability",
            communication_style=(
                "Direct, precise, risk-aware — always references compliance constraints"
            ),
        ),
        "frameworks/persona.py",
    ),
    (
        ChainOfThought(
            steps=[
                "Identify the primary technical concerns of the project brief "
                "(concurrency, data shape, API surface, safety constraints, consistency model).",
                "For each concern, name one or two candidate specification languages "
                "and briefly evaluate their fit against that specific concern.",
                "Weigh the candidates: which covers the most critical concerns with the "
                "least overhead for this project's complexity level?",
                "Select the best language and determine which spec layer it targets "
                "(system, domain, component, or api).",
                "State confidence (0.0–1.0) based on how unambiguously the language "
                "covers the identified concerns.",
            ]
        ),
        "frameworks/chain_of_thought.py",
    ),
    (
        ReActLoop(
            thought_prompt=(
                "Assess the Spec Specialist's output: does it satisfy the confidence threshold "
                "(≥0.7)? Does it reference at least one concrete technical characteristic of "
                "the brief? Are the reasoning steps grounded in specific concerns?"
            ),
            action_options=["proceed", "retry", "escalate"],
            observation_note=(
                "Record what changed after the revision and whether the quality criteria "
                "are now satisfied. If escalating, state the unresolved concern explicitly."
            ),
        ),
        "frameworks/react.py",
    ),
    (
        ConstitutionalAI(
            principles=[
                "The justification references at least one specific technical characteristic "
                "of the project (e.g. concurrency model, consistency requirements, API surface). "
                "Generic statements that apply to any project are not acceptable.",
                "The reasoning steps include at least one step that names a candidate language "
                "by name and evaluates its fit against a specific project characteristic.",
                "If the project brief provides fewer than two concrete technical signals, "
                "confidence must be < 0.75 and revised must be set to true.",
            ]
        ),
        "frameworks/constitutional_ai.py",
    ),
    (
        FewShot(
            preamble="Examples of formally correct spec outputs in the selected language:",
            examples=[
                (
                    "OpenAPI",
                    "openapi: 3.0.0\ninfo:\n  title: Todo API\n  version: 1.0.0\n"
                    "paths:\n  /todos:\n    get:\n      summary: List all todos\n"
                    "      responses:\n        '200':\n          description: OK",
                ),
                (
                    "TLA+",
                    "---- MODULE Inventory ----\nVARIABLES stock\n"
                    "Init == stock = 100\n"
                    "Next == stock' \\in {stock - 1, stock}\n"
                    "Inv == stock >= 0\n"
                    "====",
                ),
            ],
        ),
        "frameworks/few_shot.py",
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _file_meta(relative_path: str) -> dict:
    path = _M1_DIR / relative_path
    content = path.read_text(encoding="utf-8")
    return {
        "file_path": relative_path,
        "file_hash": hashlib.sha256(content.encode()).hexdigest(),
        "file_size_bytes": path.stat().st_size,
    }


def _token_est(text: str) -> int:
    """GPT-style heuristic: ~4 characters per token."""
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract() -> list[dict]:
    """
    Instantiate each framework, call build(), measure time, capture file metadata.

    Returns FrameworkLayer records as plain dicts.
    No Kuzu dependency — safe to call from any downstream milestone.
    """
    records: list[dict] = []
    for instance, rel_path in _INSTANCES:
        t0 = time.perf_counter()
        build_output = instance.build()
        build_time_ms = round((time.perf_counter() - t0) * 1000, 6)

        records.append(
            {
                "name": type(instance).__name__,
                "dimension": getattr(instance, "_dimension", "Unknown"),
                "build_output": build_output,
                "build_time_ms": build_time_ms,
                "output_char_count": len(build_output),
                "output_token_est": _token_est(build_output),
                **_file_meta(rel_path),
            }
        )
    return records


def seed(conn: kuzu.Connection, run_id: str | None = None, model: str = "local") -> str:
    """
    Create M1 schema and write one subgraph (MilestoneRun + FrameworkLayer nodes).

    Each call creates a new MilestoneRun node and 9 FrameworkLayer nodes scoped to it.
    Multiple calls with different run_ids produce multiple coexisting subgraphs.
    Calling with the same run_id is a no-op (MilestoneRun PK conflict check).

    Returns the run_id used.
    """
    import datetime

    if run_id is None:
        run_id = datetime.datetime.utcnow().strftime("m1-%Y%m%d-%H%M%S")

    ensure_schema(conn)

    # Idempotent: skip if this run already exists
    existing_runs = {
        cast(list, row)[0]
        for row in cast(list, cast(kuzu.QueryResult, conn.execute(
            "MATCH (r:MilestoneRun) RETURN r.run_id"
        )).get_all())
    }
    if run_id in existing_runs:
        return run_id

    conn.execute(
        "CREATE (:MilestoneRun {run_id: $run_id, milestone: 'm1', model: $model, timestamp: $ts})",
        parameters={
            "run_id": run_id,
            "model": model,
            "ts": datetime.datetime.utcnow().isoformat() + "Z",
        },
    )

    for rec in extract():
        node_id = f"{run_id}:{rec['name']}"
        conn.execute(
            "CREATE (:FrameworkLayer {"
            "id: $id, name: $name, run_id: $run_id, "
            "dimension: $dimension, build_output: $build_output, "
            "file_path: $file_path, file_hash: $file_hash, "
            "file_size_bytes: $file_size_bytes, build_time_ms: $build_time_ms, "
            "output_char_count: $output_char_count, output_token_est: $output_token_est"
            "})",
            parameters={"id": node_id, "run_id": run_id, **rec},
        )
        conn.execute(
            "MATCH (f:FrameworkLayer {id: $fid}), (r:MilestoneRun {run_id: $rid}) "
            "CREATE (f)-[:CAPTURED_IN]->(r)",
            parameters={"fid": node_id, "rid": run_id},
        )

    return run_id


def reseed_frameworks(conn: kuzu.Connection, run_ids: list[str]) -> None:
    """
    Create FrameworkLayer nodes + CAPTURED_IN edges for given run_ids.

    Called by the ETL migrate runner when FrameworkLayer is in reseed_tables.
    Unlike seed(), does not create MilestoneRun nodes — assumes they already exist
    (loaded from Parquet). Safe to call on a DB where MilestoneRun rows are present
    but FrameworkLayer rows are absent.
    """
    ensure_schema(conn)
    records = extract()
    for run_id in run_ids:
        for rec in records:
            node_id = f"{run_id}:{rec['name']}"
            conn.execute(
                "CREATE (:FrameworkLayer {"
                "id: $id, name: $name, run_id: $run_id, "
                "dimension: $dimension, build_output: $build_output, "
                "file_path: $file_path, file_hash: $file_hash, "
                "file_size_bytes: $file_size_bytes, build_time_ms: $build_time_ms, "
                "output_char_count: $output_char_count, output_token_est: $output_token_est"
                "})",
                parameters={"id": node_id, "run_id": run_id, **rec},
            )
            conn.execute(
                "MATCH (f:FrameworkLayer {id: $fid}), (r:MilestoneRun {run_id: $rid}) "
                "CREATE (f)-[:CAPTURED_IN]->(r)",
                parameters={"fid": node_id, "rid": run_id},
            )


def dump(conn: kuzu.Connection, output_path: "Path | str", run_id: str | None = None) -> None:
    """
    Export one run's FrameworkLayer data as a JSON artifact.

    If run_id is None, exports the most recent run (by timestamp).
    The artifact is what Claude reads for analysis — no live Kuzu connection needed.
    """
    import datetime
    import json

    if run_id is None:
        _res = cast(kuzu.QueryResult, conn.execute(
            "MATCH (r:MilestoneRun) RETURN r.run_id ORDER BY r.timestamp DESC LIMIT 1"
        ))
        _r = cast(list, _res.get_all())
        if not _r:
            return
        run_id = cast(list, _r[0])[0]

    _res2 = cast(kuzu.QueryResult, conn.execute(
        "MATCH (r:MilestoneRun {run_id: $rid})<-[:CAPTURED_IN]-(f:FrameworkLayer) "
        "RETURN f.name, f.dimension, f.build_output, f.file_path, f.file_hash, "
        "f.file_size_bytes, f.build_time_ms, f.output_char_count, f.output_token_est "
        "ORDER BY f.dimension, f.name",
        parameters={"rid": run_id},
    ))
    rows = cast(list, _res2.get_all())

    nodes = [
        {
            "name": name, "dimension": dim, "build_output": build_output,
            "file_path": file_path, "file_hash": file_hash,
            "file_size_bytes": file_size, "build_time_ms": build_time,
            "output_char_count": char_count, "output_token_est": token_est,
        }
        for name, dim, build_output, file_path, file_hash,
            file_size, build_time, char_count, token_est in rows
    ]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "milestone": "m1",
        "run_id": run_id,
        "schema": "FrameworkLayer",
        "exported": datetime.datetime.utcnow().isoformat() + "Z",
        "node_count": len(nodes),
        "nodes": nodes,
    }, indent=2))

