"""
M1 gate: Framework builders.

Tests that every builder produces correctly structured strings, omits empty optional
fields, and that ComposedPrompt assembles layers in declared order with dimension labels.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from src.frameworks import (
    ChainOfThought,
    CLEARSession,
    ComposedPrompt,
    ConstitutionalAI,
    COSTARPrompt,
    CRISPEPrompt,
    FewShot,
    PersonaLayer,
    RACEPrompt,
    ReActLoop,
)

# ---------------------------------------------------------------------------
# COSTARPrompt
# ---------------------------------------------------------------------------


def test_costar_all_fields_present_in_order():
    p = COSTARPrompt(
        context="ctx",
        objective="obj",
        style="formal",
        tone="rigorous",
        audience="aud",
        response_format="JSON",
    )
    result = p.build()
    headers = [
        "**Context**",
        "**Objective**",
        "**Style**",
        "**Tone**",
        "**Audience**",
        "**Response Format**",
    ]
    for h in headers:
        assert h in result, f"Missing header: {h}"
    positions = [result.index(h) for h in headers]
    assert positions == sorted(positions), "Headers out of order"


def test_costar_empty_field_omitted():
    p = COSTARPrompt(
        context="ctx", objective="obj", style="", tone="", audience="", response_format=""
    )
    result = p.build()
    assert "**Context**" in result
    assert "**Objective**" in result
    assert "**Style**" not in result
    assert "**Tone**" not in result
    assert "**Audience**" not in result
    assert "**Response Format**" not in result


# ---------------------------------------------------------------------------
# CRISPEPrompt
# ---------------------------------------------------------------------------


def test_crispe_all_fields_present_in_order():
    p = CRISPEPrompt(
        capacity="TLA+ specialist",
        role="Spec Specialist",
        insight="domain context",
        statement="generate spec",
        personality="Precise",
        experiment="self-check",
    )
    result = p.build()
    headers = [
        "**Capacity**",
        "**Role**",
        "**Insight**",
        "**Statement**",
        "**Personality**",
        "**Experiment**",
    ]
    for h in headers:
        assert h in result, f"Missing header: {h}"
    positions = [result.index(h) for h in headers]
    assert positions == sorted(positions)


def test_crispe_empty_insight_omitted():
    p = CRISPEPrompt(capacity="cap", role="role", statement="stmt", insight="")
    result = p.build()
    assert "**Insight**" not in result
    assert "**Capacity**" in result
    assert "**Role**" in result


# ---------------------------------------------------------------------------
# CLEARSession
# ---------------------------------------------------------------------------


def test_clear_all_fields_present_in_order():
    p = CLEARSession(
        context="ctx",
        layering="layer1",
        execute="do this",
        assess="check",
        reflect="what changed",
    )
    result = p.build()
    headers = ["**Context**", "**Layering**", "**Execute**", "**Assess**", "**Reflect**"]
    for h in headers:
        assert h in result, f"Missing header: {h}"
    positions = [result.index(h) for h in headers]
    assert positions == sorted(positions)


def test_clear_empty_fields_omitted():
    p = CLEARSession(context="ctx", execute="do this")
    result = p.build()
    assert "**Layering**" not in result
    assert "**Assess**" not in result
    assert "**Reflect**" not in result


# ---------------------------------------------------------------------------
# RACEPrompt
# ---------------------------------------------------------------------------


def test_race_all_fields_present_in_order():
    p = RACEPrompt(
        role="code gen",
        action="generate stub",
        context="project context",
        execute="return JSON",
    )
    result = p.build()
    headers = ["**Role**", "**Action**", "**Context**", "**Execute**"]
    for h in headers:
        assert h in result, f"Missing header: {h}"
    positions = [result.index(h) for h in headers]
    assert positions == sorted(positions)


def test_race_empty_fields_omitted():
    p = RACEPrompt(role="r", action="a")
    result = p.build()
    assert "**Context**" not in result
    assert "**Execute**" not in result


# ---------------------------------------------------------------------------
# PersonaLayer
# ---------------------------------------------------------------------------


def test_persona_all_fields_present():
    p = PersonaLayer(
        role="Senior Fintech PM",
        background="10 years in payments",
        priorities="compliance and velocity",
        communication_style="direct and precise",
    )
    result = p.build()
    assert "Senior Fintech PM" in result
    assert "10 years in payments" in result
    assert "compliance and velocity" in result
    assert "direct and precise" in result


def test_persona_empty_fields_omitted():
    p = PersonaLayer(role="PM")
    result = p.build()
    assert "PM" in result
    assert "Your priorities" not in result
    assert "Communication style" not in result


# ---------------------------------------------------------------------------
# ChainOfThought
# ---------------------------------------------------------------------------


def test_cot_steps_in_order():
    p = ChainOfThought(
        steps=["identify concerns", "evaluate candidates", "select and justify"],
        preamble="Think step by step.",
    )
    result = p.build()
    assert "Think step by step." in result
    assert "Step 1: identify concerns" in result
    assert "Step 2: evaluate candidates" in result
    assert "Step 3: select and justify" in result
    assert result.index("Step 1") < result.index("Step 2") < result.index("Step 3")


def test_cot_default_preamble_when_no_steps():
    p = ChainOfThought()
    result = p.build()
    assert "Think through this step by step" in result


# ---------------------------------------------------------------------------
# ReActLoop
# ---------------------------------------------------------------------------


def test_react_all_fields_in_order():
    p = ReActLoop(
        thought_prompt="Assess output quality.",
        action_options=["proceed", "retry", "escalate"],
        observation_note="Record what changed.",
    )
    result = p.build()
    for h in ["**Thought**", "**Action**", "**Observation**"]:
        assert h in result, f"Missing header: {h}"
    assert "proceed" in result
    assert "retry" in result
    assert "escalate" in result
    t = result.index("**Thought**")
    a = result.index("**Action**")
    o = result.index("**Observation**")
    assert t < a < o


def test_react_empty_observation_omitted():
    p = ReActLoop(thought_prompt="Think.", action_options=["go", "stop"])
    result = p.build()
    assert "**Observation**" not in result


# ---------------------------------------------------------------------------
# ConstitutionalAI
# ---------------------------------------------------------------------------


def test_cai_principles_numbered():
    p = ConstitutionalAI(
        principles=["justification is non-empty", "confidence >= 0.7", "candidates evaluated"],
        revise_note="Revise if violated.",
    )
    result = p.build()
    assert "justification is non-empty" in result
    assert "confidence >= 0.7" in result
    assert "candidates evaluated" in result
    assert "Revise if violated." in result
    assert "1." in result and "2." in result and "3." in result


def test_cai_no_principles_returns_revise_note():
    p = ConstitutionalAI()
    result = p.build()
    assert "revise" in result.lower()


# ---------------------------------------------------------------------------
# FewShot
# ---------------------------------------------------------------------------


def test_few_shot_examples_present():
    p = FewShot(
        examples=[
            ("OpenAPI", "openapi: 3.0\ninfo:\n  title: Test"),
            ("TLA+", "---- MODULE Test ----"),
        ],
        preamble="Examples follow.",
    )
    result = p.build()
    assert "Examples follow." in result
    assert "OpenAPI" in result
    assert "TLA+" in result
    assert "openapi: 3.0" in result


def test_few_shot_no_examples_returns_empty():
    assert FewShot(examples=[]).build() == ""


# ---------------------------------------------------------------------------
# ComposedPrompt
# ---------------------------------------------------------------------------


def test_composed_sections_in_declared_order():
    costar = COSTARPrompt(context="ctx", objective="obj")
    persona = PersonaLayer(role="Spec Advisor", background="expert in specs")
    cai = ConstitutionalAI(principles=["coherent output"])

    result = ComposedPrompt([costar, persona, cai]).build()

    costar_pos = result.index("**Context**")
    persona_pos = result.index("Spec Advisor")
    cai_pos = result.index("coherent output")
    assert costar_pos < persona_pos < cai_pos


def test_composed_skips_empty_layer():
    costar = COSTARPrompt(context="ctx", objective="obj")
    few_shot = FewShot(examples=[])  # empty → build() returns ""
    cai = ConstitutionalAI(principles=["p1"])

    result = ComposedPrompt([costar, few_shot, cai]).build()

    # Only one divider between costar and cai — few_shot was skipped
    assert result.count("\n\n---\n\n") == 1


def test_composed_dimension_labels_present():
    costar = COSTARPrompt(context="ctx", objective="obj")
    persona = PersonaLayer(role="PM")
    cai = ConstitutionalAI(principles=["p1"])

    result = ComposedPrompt([costar, persona, cai]).build()

    assert "# [Structure: COSTARPrompt]" in result
    assert "# [Technique: PersonaLayer]" in result
    assert "# [Verification: ConstitutionalAI]" in result


def test_composed_single_layer_no_divider():
    costar = COSTARPrompt(context="ctx", objective="obj")
    result = ComposedPrompt([costar]).build()
    assert "---" not in result
    assert "**Context**" in result


# ---------------------------------------------------------------------------
# Artifact — sample build() outputs for every framework (always passes)
# ---------------------------------------------------------------------------


def test_save_m1_artifact():
    """Save a JSON artifact recording sample build() output for every framework layer."""
    artifacts_dir = Path(__file__).parent / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    samples = {
        "COSTARPrompt": COSTARPrompt(
            context="REST API for a todo app",
            objective="Select the best spec language",
            style="Formal",
            tone="Rigorous",
            audience="Spec Specialist",
            response_format="JSON",
        ).build(),
        "CRISPEPrompt": CRISPEPrompt(
            capacity="TLA+ specialist",
            role="Spec Specialist",
            insight="Distributed system with eventual consistency",
            statement="Generate a TLA+ spec for the inventory module",
            personality="Precise and thorough",
            experiment="Review your spec for completeness",
        ).build(),
        "CLEARSession": CLEARSession(
            context="Spec Advisor council session",
            layering="Domain → Component",
            execute="Select language and justify",
            assess="Is the selection appropriate for complexity?",
            reflect="What changed from the prior layer?",
        ).build(),
        "RACEPrompt": RACEPrompt(
            role="Spec Advisor",
            action="Select formal specification language",
            context="Multi-region e-commerce platform",
            execute="Return selected_lang and justification",
        ).build(),
        "PersonaLayer": PersonaLayer(
            role="Senior Fintech PM",
            background="10 years in payments and compliance",
            priorities="Regulatory compliance and transaction velocity",
            communication_style="Direct, precise, risk-aware",
        ).build(),
        "ChainOfThought": ChainOfThought(
            steps=[
                "Identify the layer concerns (concurrency, data shape, API surface)",
                "Evaluate candidate languages against those concerns",
                "Select the best fit and state confidence",
            ],
            preamble="Think step by step before selecting.",
        ).build(),
        "ReActLoop": ReActLoop(
            thought_prompt="Assess output quality against confidence threshold.",
            action_options=["proceed", "retry", "escalate"],
            observation_note="Record what changed after the revision.",
        ).build(),
        "ConstitutionalAI": ConstitutionalAI(
            principles=[
                "Justification references specific project characteristics",
                "Confidence is >= 0.7 for a non-trivial project",
                "All candidate languages are evaluated before selecting",
            ],
            revise_note="If any principle is violated, revise the output before returning.",
        ).build(),
        "FewShot": FewShot(
            examples=[
                ("OpenAPI", "openapi: 3.0.0\ninfo:\n  title: Todo API\n  version: 1.0.0"),
                ("TLA+", "---- MODULE Inventory ----\nVARIABLES stock\n===================="),
            ],
            preamble="Examples of valid formal spec outputs:",
        ).build(),
        "ComposedPrompt (COSTAR + Persona + CAI)": ComposedPrompt(
            [
                COSTARPrompt(context="spec selection task", objective="pick best language"),
                PersonaLayer(role="Spec Advisor"),
                ConstitutionalAI(principles=["justification is non-empty"]),
            ]
        ).build(),
    }

    artifact = {
        "milestone": "M1",
        "description": "Framework builder sample outputs — baseline for composition layer tests",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "frameworks_tested": list(samples.keys()),
        "samples": samples,
    }
    (artifacts_dir / "m1_frameworks.json").write_text(json.dumps(artifact, indent=2))
    assert (artifacts_dir / "m1_frameworks.json").exists()
