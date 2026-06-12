"""
Kuzu graph schema for Faber.

Node types: Session, Requirement, Specification
Edge types: GROUNDS, DERIVED_FROM, REFINES

GROUNDS: a lower-layer Specification is grounded in an upper-layer one
         (component → domain → system)
DERIVED_FROM: a Specification was derived from a Requirement
REFINES: a Specification refines an earlier version of itself
"""

from enum import Enum


class NodeType(str, Enum):
    SESSION = "Session"
    REQUIREMENT = "Requirement"
    SPECIFICATION = "Specification"


class EdgeType(str, Enum):
    GROUNDS = "GROUNDS"
    DERIVED_FROM = "DERIVED_FROM"
    REFINES = "REFINES"


# Property definitions used by GraphStore to create tables.
# Each value is a list of (column_name, kuzu_type) tuples.
NODE_PROPS: dict[NodeType, list[tuple[str, str]]] = {
    NodeType.SESSION: [
        ("session_id", "STRING"),
        ("created_at", "STRING"),
        ("project_brief", "STRING"),
    ],
    NodeType.REQUIREMENT: [
        ("req_id", "STRING"),
        ("session_id", "STRING"),
        ("requirement_text", "STRING"),
        ("scenario_type", "STRING"),
        ("domain_terms", "STRING"),  # JSON-serialised list
        ("confidence", "DOUBLE"),
        ("persona_used", "STRING"),
        ("created_at", "STRING"),
    ],
    NodeType.SPECIFICATION: [
        ("spec_id", "STRING"),
        ("session_id", "STRING"),
        ("spec_lang", "STRING"),
        ("layer", "STRING"),
        ("spec_content", "STRING"),
        ("confidence", "DOUBLE"),
        ("well_formedness_notes", "STRING"),
        ("created_at", "STRING"),
    ],
}

EDGE_PROPS: dict[EdgeType, list[tuple[str, str]]] = {
    EdgeType.GROUNDS: [
        ("created_at", "STRING"),
    ],
    EdgeType.DERIVED_FROM: [
        ("created_at", "STRING"),
    ],
    EdgeType.REFINES: [
        ("created_at", "STRING"),
        ("revision_notes", "STRING"),
    ],
}
