"""
Schema diff between two milestone migration snapshots.

Usage:
  python3 -m src.etl.diff m1 m2

Compares CREATE NODE TABLE and CREATE REL TABLE statements in the two
schema.cypher files and reports NEW / CHANGED / UNCHANGED per table.
Column-level changes are listed under CHANGED tables.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

_MILESTONES_DIR = Path("src/milestones")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


@dataclass
class NodeTable:
    name: str
    columns: dict[str, str]  # col_name → type
    pk: str


@dataclass
class RelTable:
    name: str
    from_type: str
    to_type: str


def _strip_comments(text: str) -> str:
    return "\n".join(
        line for line in text.split("\n")
        if not line.strip().startswith("--")
    )


def _parse_node_tables(schema_text: str) -> dict[str, NodeTable]:
    text = _strip_comments(schema_text)
    tables: dict[str, NodeTable] = {}
    pattern = re.compile(
        r"CREATE NODE TABLE (\w+)\s*\((.*?)\)\s*;",
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern.finditer(text):
        name = m.group(1)
        body = m.group(2)
        columns: dict[str, str] = {}
        pk = ""
        for part in body.split(","):
            part = part.strip()
            if not part:
                continue
            pk_match = re.match(r"PRIMARY KEY\s*\((\w+)\)", part, re.IGNORECASE)
            if pk_match:
                pk = pk_match.group(1)
                continue
            col_match = re.match(r"(\w+)\s+(\w+)", part)
            if col_match:
                columns[col_match.group(1)] = col_match.group(2).upper()
        tables[name] = NodeTable(name=name, columns=columns, pk=pk)
    return tables


def _parse_rel_tables(schema_text: str) -> dict[str, RelTable]:
    text = _strip_comments(schema_text)
    tables: dict[str, RelTable] = {}
    pattern = re.compile(
        r"CREATE REL TABLE (\w+)\s*\(\s*FROM\s+(\w+)\s+TO\s+(\w+)(?:,.*?)?\)\s*;",
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern.finditer(text):
        name, from_type, to_type = m.group(1), m.group(2), m.group(3)
        tables[name] = RelTable(name=name, from_type=from_type, to_type=to_type)
    return tables


def _load_schema(milestone: str) -> tuple[dict[str, NodeTable], dict[str, RelTable]]:
    import json
    mig_dir = _MILESTONES_DIR / milestone / "migration"
    meta_path = mig_dir / "meta.json"
    declared_passes = json.loads(meta_path.read_text()).get("passes") if meta_path.exists() else None

    if declared_passes is not None:
        path = mig_dir / f"pass_{declared_passes:02d}" / "schema.cypher"
    else:
        path = mig_dir / "schema.cypher"

    if not path.exists():
        raise FileNotFoundError(f"schema.cypher not found for {milestone}: {path}")
    text = path.read_text()
    return _parse_node_tables(text), _parse_rel_tables(text)


# ---------------------------------------------------------------------------
# Diff logic
# ---------------------------------------------------------------------------


def diff(milestone_a: str, milestone_b: str) -> list[str]:
    """
    Return a list of diff lines comparing schema at milestone_a vs milestone_b.
    Suitable for printing or asserting in tests.
    """
    nodes_a, rels_a = _load_schema(milestone_a)
    nodes_b, rels_b = _load_schema(milestone_b)

    lines: list[str] = []

    # Node tables
    all_node_names = sorted(set(nodes_a) | set(nodes_b))
    for name in all_node_names:
        if name not in nodes_a:
            lines.append(f"NEW       NODE {name}")
        elif name not in nodes_b:
            lines.append(f"REMOVED   NODE {name}")
        else:
            ta, tb = nodes_a[name], nodes_b[name]
            col_changes: list[str] = []
            for col, typ in tb.columns.items():
                if col not in ta.columns:
                    col_changes.append(f"  +       {name}.{col} {typ} (NEW)")
                elif ta.columns[col] != typ:
                    col_changes.append(
                        f"  CHANGED {name}.{col} {ta.columns[col]} → {typ}"
                    )
            for col in ta.columns:
                if col not in tb.columns:
                    col_changes.append(f"  -       {name}.{col} {ta.columns[col]} (REMOVED)")
            if col_changes:
                lines.append(f"CHANGED   NODE {name}")
                lines.extend(col_changes)
            else:
                lines.append(f"UNCHANGED NODE {name}")

    # Rel tables
    all_rel_names = sorted(set(rels_a) | set(rels_b))
    for name in all_rel_names:
        if name not in rels_a:
            lines.append(f"NEW       REL {name}")
        elif name not in rels_b:
            lines.append(f"REMOVED   REL {name}")
        else:
            ra, rb = rels_a[name], rels_b[name]
            if ra.from_type != rb.from_type or ra.to_type != rb.to_type:
                lines.append(
                    f"CHANGED   REL {name}  "
                    f"{ra.from_type}→{ra.to_type} → {rb.from_type}→{rb.to_type}"
                )
            else:
                lines.append(f"UNCHANGED REL {name}")

    return lines


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Kuzu schema diff between milestones")
    parser.add_argument("milestone_a", help="Source milestone (e.g. m1)")
    parser.add_argument("milestone_b", help="Target milestone (e.g. m2)")
    args = parser.parse_args()

    a, b = args.milestone_a, args.milestone_b
    lines = diff(a, b)

    print(f"Schema diff: {a} → {b}")
    print("─" * 40)
    for line in lines:
        print(line)


if __name__ == "__main__":
    main()
