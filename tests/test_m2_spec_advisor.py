"""
M2/M3 gate: SpecAdvisorAgent — COSTAR (M2) + ChainOfThought (M3).

M2 success criteria (gate to M3):
  - Selects different languages for projects of different complexity
  - Justification is coherent and non-empty
  - Simple project → JSON Schema or OpenAPI
  - Complex distributed project → TLA+ or CML

M3 success criteria (gate to M4):
  - reasoning_steps is non-empty (≥3 steps)
  - Each step references a specific concern or candidate language
  - Selection quality ≥ M2 baseline (same inputs, justification depth preserved)
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.agents.schemas import SpecAdvisorOutput
from src.agents.spec_advisor import SpecAdvisorAgent

SIMPLE_BRIEF = "CRUD todo app with REST API and a PostgreSQL backend"
COMPLEX_BRIEF = (
    "multi-region e-commerce platform with eventual consistency, "
    "distributed inventory, and CQRS event sourcing"
)

SIMPLE_EXPECTED = {"json schema", "openapi", "pydantic"}
COMPLEX_EXPECTED = {"tla+", "cml", "alloy", "event-b"}

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"


def _save_artifact(name: str, brief: str, output: SpecAdvisorOutput) -> None:
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    artifact = {
        "milestone": "M3",
        "agent": "SpecAdvisorAgent",
        "composition": "COSTARPrompt + ChainOfThought",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input": {"project_brief": brief},
        "output": output.model_dump(),
    }
    path = ARTIFACTS_DIR / f"m3_{name}.json"
    path.write_text(json.dumps(artifact, indent=2))


@pytest.fixture(scope="module")
def advisor():
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")
    return SpecAdvisorAgent()


@pytest.fixture(scope="module")
def simple_output(advisor):
    out = advisor.run(SIMPLE_BRIEF)
    _save_artifact("simple", SIMPLE_BRIEF, out)
    return out


@pytest.fixture(scope="module")
def complex_output(advisor):
    out = advisor.run(COMPLEX_BRIEF)
    _save_artifact("complex", COMPLEX_BRIEF, out)
    return out


class TestSpecAdvisorOutput:
    def test_simple_returns_valid_schema(self, simple_output):
        assert isinstance(simple_output, SpecAdvisorOutput)

    def test_complex_returns_valid_schema(self, complex_output):
        assert isinstance(complex_output, SpecAdvisorOutput)

    def test_simple_selects_lightweight_lang(self, simple_output):
        lang = simple_output.selected_lang
        assert lang.lower() in SIMPLE_EXPECTED, (
            f"Simple project: expected one of {SIMPLE_EXPECTED}, got '{lang}'"
        )

    def test_complex_selects_formal_lang(self, complex_output):
        lang = complex_output.selected_lang
        assert lang.lower() in COMPLEX_EXPECTED, (
            f"Complex project: expected one of {COMPLEX_EXPECTED}, got '{lang}'"
        )

    def test_simple_justification_non_empty(self, simple_output):
        assert simple_output.justification and len(simple_output.justification) > 20

    def test_complex_justification_non_empty(self, complex_output):
        assert complex_output.justification and len(complex_output.justification) > 20

    def test_simple_confidence_in_range(self, simple_output):
        assert 0.0 <= simple_output.confidence <= 1.0

    def test_complex_confidence_in_range(self, complex_output):
        assert 0.0 <= complex_output.confidence <= 1.0

    def test_different_langs_for_different_complexity(self, simple_output, complex_output):
        """Core M2 gate: complexity drives different language selection."""
        assert simple_output.selected_lang.lower() != complex_output.selected_lang.lower(), (
            "Spec Advisor must select different languages for simple vs complex projects"
        )

    def test_layer_field_present(self, simple_output, complex_output):
        valid_layers = {"system", "domain", "component", "api"}
        assert simple_output.layer.lower() in valid_layers, (
            f"Unexpected layer: {simple_output.layer}"
        )
        assert complex_output.layer.lower() in valid_layers, (
            f"Unexpected layer: {complex_output.layer}"
        )


# ── M3 gate ──────────────────────────────────────────────────────────────────

_CONCERN_KEYWORDS = {
    "concurren",
    "consistency",
    "data shape",
    "api surface",
    "safety",
    "distributed",
    "payload",
    "endpoint",
    "model",
    "event",
    "schema",
    "json schema",
    "openapi",
    "pydantic",
    "tla+",
    "cml",
    "alloy",
    "event-b",
    "inventory",
    "cqrs",
    "crud",
    "rest",
    "postgresql",
}


def _step_references_concern_or_candidate(step: str) -> bool:
    lower = step.lower()
    return any(kw in lower for kw in _CONCERN_KEYWORDS)


class TestM3Reasoning:
    def test_simple_has_reasoning_steps(self, simple_output):
        assert simple_output.reasoning_steps, "reasoning_steps must not be empty"
        assert len(simple_output.reasoning_steps) >= 3, (
            f"Expected ≥3 reasoning steps, got {len(simple_output.reasoning_steps)}"
        )

    def test_complex_has_reasoning_steps(self, complex_output):
        assert complex_output.reasoning_steps, "reasoning_steps must not be empty"
        assert len(complex_output.reasoning_steps) >= 3, (
            f"Expected ≥3 reasoning steps, got {len(complex_output.reasoning_steps)}"
        )

    def test_simple_steps_reference_concerns_or_candidates(self, simple_output):
        failing = [
            s for s in simple_output.reasoning_steps if not _step_references_concern_or_candidate(s)
        ]
        assert not failing, (
            "These steps lack a concrete concern or candidate language reference:\n"
            + "\n".join(f"  - {s}" for s in failing)
        )

    def test_complex_steps_reference_concerns_or_candidates(self, complex_output):
        failing = [
            s
            for s in complex_output.reasoning_steps
            if not _step_references_concern_or_candidate(s)
        ]
        assert not failing, (
            "These steps lack a concrete concern or candidate language reference:\n"
            + "\n".join(f"  - {s}" for s in failing)
        )

    def test_selection_quality_preserved_simple(self, simple_output):
        """M3 must not regress M2 baseline: simple project still selects a lightweight lang."""
        lang = simple_output.selected_lang
        assert lang.lower() in SIMPLE_EXPECTED, (
            f"M3 regression: simple project expected one of {SIMPLE_EXPECTED}, got '{lang}'"
        )

    def test_selection_quality_preserved_complex(self, complex_output):
        """M3 must not regress M2 baseline: complex project still selects a formal lang."""
        lang = complex_output.selected_lang
        assert lang.lower() in COMPLEX_EXPECTED, (
            f"M3 regression: complex project expected one of {COMPLEX_EXPECTED}, got '{lang}'"
        )

    def test_justification_depth_simple(self, simple_output):
        """M3 justification should be at least as detailed as M2 (>20 chars)."""
        assert len(simple_output.justification) > 20

    def test_justification_depth_complex(self, complex_output):
        """M3 justification should be at least as detailed as M2 (>20 chars)."""
        assert len(complex_output.justification) > 20
