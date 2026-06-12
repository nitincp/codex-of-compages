"""
GraphStore — Kuzu-backed persistence for Faber spec artifacts.

Usage:
    store = GraphStore(db_path="data/kuzu")
    store.ensure_schema()
    store.write_node(NodeType.SPECIFICATION, props)
    store.write_edge(EdgeType.GROUNDS, from_id, to_id, from_type, to_type, props)
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import kuzu

from src.graph.schema import EDGE_PROPS, NODE_PROPS, EdgeType, NodeType


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GraphStore:
    def __init__(self, db_path: str | None = None) -> None:
        path = db_path or os.getenv("KUZU_DB_PATH", "data/kuzu")
        self._db = kuzu.Database(path)
        self._conn = kuzu.Connection(self._db)

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    def ensure_schema(self) -> None:
        """Create node/edge tables if they don't already exist."""
        for node_type, props in NODE_PROPS.items():
            cols = ", ".join(f"{name} {ktype}" for name, ktype in props)
            pk = props[0][0]  # first column is always the primary key
            self._conn.execute(
                f"CREATE NODE TABLE IF NOT EXISTS {node_type.value} ({cols}, PRIMARY KEY ({pk}))"
            )

        for edge_type, props in EDGE_PROPS.items():
            # Edges are created between all node table pairs that make sense;
            # Kuzu requires explicit FROM/TO declarations — we use ANY for flexibility.
            col_part = (", " + ", ".join(f"{n} {t}" for n, t in props)) if props else ""
            # Determine valid source/dest combinations from the edge semantics.
            src_dst = _edge_endpoints(edge_type)
            for src, dst in src_dst:
                table_name = f"{edge_type.value}_{src.value}_{dst.value}"
                self._conn.execute(
                    f"CREATE REL TABLE IF NOT EXISTS {table_name} "
                    f"(FROM {src.value} TO {dst.value}{col_part})"
                )

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def write_node(self, node_type: NodeType, props: dict) -> None:
        """Insert a node (caller must ensure uniqueness via primary key)."""
        if "created_at" not in props:
            props = {**props, "created_at": _now()}
        allowed = {name for name, _ in NODE_PROPS[node_type]}
        filtered = {k: v for k, v in props.items() if k in allowed}
        cols = ", ".join(f"{k}: ${k}" for k in filtered.keys())
        self._conn.execute(
            f"CREATE (:{node_type.value} {{{cols}}})",
            parameters=filtered,
        )

    def write_edge(
        self,
        edge_type: EdgeType,
        from_id: str,
        to_id: str,
        from_type: NodeType,
        to_type: NodeType,
        props: dict | None = None,
    ) -> None:
        """Create a directed edge between two nodes identified by their primary keys."""
        edge_props = dict(props or {})
        if "created_at" not in edge_props:
            edge_props["created_at"] = _now()

        pk_from = NODE_PROPS[from_type][0][0]
        pk_to = NODE_PROPS[to_type][0][0]
        table_name = f"{edge_type.value}_{from_type.value}_{to_type.value}"

        allowed = {name for name, _ in EDGE_PROPS[edge_type]}
        filtered = {k: v for k, v in edge_props.items() if k in allowed}
        prop_str = (
            (" {" + ", ".join(f"{k}: ${k}" for k in filtered.keys()) + "}") if filtered else ""
        )

        self._conn.execute(
            f"MATCH (a:{from_type.value}), (b:{to_type.value}) "
            f"WHERE a.{pk_from} = $from_id AND b.{pk_to} = $to_id "
            f"CREATE (a)-[:{table_name}{prop_str}]->(b)",
            parameters={"from_id": from_id, "to_id": to_id, **filtered},
        )

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def query(self, cypher: str, parameters: dict | None = None) -> list:
        """Execute a raw Cypher query and return results as a list of rows."""
        result = self._conn.execute(cypher, parameters=parameters or {})
        if isinstance(result, list):
            rows: list = []
            for r in result:
                rows.extend(r.get_all())
            return rows
        return result.get_all()

    def close(self) -> None:
        self._conn.close()
        self._db.close()


# ------------------------------------------------------------------
# Edge endpoint mapping
# ------------------------------------------------------------------


def _edge_endpoints(edge_type: EdgeType) -> list[tuple[NodeType, NodeType]]:
    return {
        EdgeType.GROUNDS: [
            (NodeType.SPECIFICATION, NodeType.SPECIFICATION),
        ],
        EdgeType.DERIVED_FROM: [
            (NodeType.SPECIFICATION, NodeType.REQUIREMENT),
        ],
        EdgeType.REFINES: [
            (NodeType.SPECIFICATION, NodeType.SPECIFICATION),
        ],
    }[edge_type]
