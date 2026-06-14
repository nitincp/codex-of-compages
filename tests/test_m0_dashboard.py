"""
M0 dashboard smoke test — verifies the Streamlit dashboard loads correctly.

The test suite starts and stops the Streamlit server itself — no manual setup needed.
Run with: pytest tests/test_m0_dashboard.py -v
"""

import subprocess
import time

import pytest
import requests

BASE_URL = "http://localhost:8000"


# ── Server lifecycle ──────────────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def streamlit_server():
    """Start Streamlit for the test session; shut it down cleanly on exit."""
    proc = subprocess.Popen(
        [
            "streamlit",
            "run",
            "src/ui/dashboard.py",
            "--server.port",
            "8000",
            "--server.headless",
            "true",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd="/workspace",
    )
    # Wait until the server is accepting connections (up to 15 s)
    for _ in range(30):
        try:
            if requests.get(BASE_URL, timeout=1).status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        proc.terminate()
        pytest.fail("Streamlit did not start within 15 s")

    yield

    proc.terminate()
    proc.wait(timeout=10)


# ── Smoke tests ───────────────────────────────────────────────────────────────


def test_dashboard_loads():
    response = requests.get(BASE_URL, timeout=10)
    assert response.status_code == 200
    assert "⚙ Faber" in response.text


def test_milestone_selector_present():
    response = requests.get(BASE_URL, timeout=10)
    assert response.status_code == 200
    assert "M1 — Framework Builders" in response.text


def test_run_button_present():
    response = requests.get(BASE_URL, timeout=10)
    assert response.status_code == 200
    assert "Run" in response.text


def test_agent_cards_idle():
    response = requests.get(BASE_URL, timeout=10)
    assert response.status_code == 200
    assert "Framework Tests" in response.text
    assert "idle" in response.text
