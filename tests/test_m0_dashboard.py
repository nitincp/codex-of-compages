"""
M0 playwright smoke test — verifies the Streamlit dashboard loads correctly.

The test suite starts and stops the Streamlit server itself — no manual setup needed.
Run with: pytest tests/test_m0_dashboard.py -v
"""

import subprocess
import time
from pathlib import Path

import pytest
import requests
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8000"
SCREENSHOTS_DIR = Path("tests/screenshots")


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


@pytest.fixture(autouse=True)
def ensure_screenshots_dir():
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Smoke tests ───────────────────────────────────────────────────────────────


def test_dashboard_loads(page: Page):
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle", timeout=20_000)
    expect(page.get_by_role("heading", name="⚙ Faber")).to_be_visible()


def test_milestone_selector_present(page: Page):
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle", timeout=20_000)
    locator = page.get_by_test_id("stSelectbox").get_by_text("M1 — Framework Builders")
    expect(locator).to_be_visible()


def test_run_button_present(page: Page):
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle", timeout=20_000)
    expect(page.get_by_role("button", name="Run")).to_be_visible()


def test_agent_cards_idle(page: Page):
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle", timeout=20_000)
    expect(page.get_by_text("Framework Tests")).to_be_visible()
    expect(page.get_by_text("idle").first).to_be_visible()


def test_screenshot_after_run(page: Page):
    """Click Run on M1, wait for completion, capture the result state."""
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle", timeout=20_000)

    page.get_by_role("button", name="Run").click()

    # Wait for the run to finish — status changes to done or failed
    _done = "() => document.body.innerText.includes('done')"
    _fail = "() => document.body.innerText.includes('failed')"
    page.wait_for_function(f"() => ({_done})() || ({_fail})()", timeout=60_000)
    page.wait_for_load_state("networkidle", timeout=10_000)

    page.screenshot(
        path=str(SCREENSHOTS_DIR / "m0_run_result.png"),
        full_page=True,
    )
