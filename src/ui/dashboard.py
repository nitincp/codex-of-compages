"""
Faber Dashboard — Streamlit process runner and artifact viewer.

Layout:
  Sidebar  — milestone selector + run button
  Main     — agent cards (streaming CLI output) + artifact panels
  Footer   — session token usage

Agents and test runners are wired in as milestones are proven.
At M0 this is the scaffold; cards populate from M1 onward.
"""

import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Faber",
    page_icon="⚙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    /* dark base */
    [data-testid="stAppViewContainer"] { background: #0e0e0e; }
    [data-testid="stSidebar"]          { background: #141414; border-right: 1px solid #2a2a2a; }

    /* cards */
    .agent-card {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 6px;
        padding: 14px 16px;
        margin-bottom: 12px;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 12px;
    }
    .card-header {
        color: #888;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-bottom: 8px;
    }
    .card-title {
        color: #e0e0e0;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 10px;
    }

    /* status chips */
    .status-idle    { color: #555; }
    .status-running { color: #f0a500; }
    .status-done    { color: #4caf50; }
    .status-failed  { color: #e53935; }

    /* cli output box */
    .cli-box {
        background: #0a0a0a;
        border: 1px solid #222;
        border-radius: 4px;
        padding: 10px 12px;
        color: #9e9e9e;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 11px;
        line-height: 1.6;
        white-space: pre-wrap;
        max-height: 260px;
        overflow-y: auto;
    }

    /* artifact panel */
    .artifact-label {
        color: #666;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    .artifact-value {
        color: #c5c5c5;
        font-size: 12px;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        margin-top: 2px;
    }

    /* hide Streamlit chrome */
    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
    header     { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Domain types ───────────────────────────────────────────────────────────────


class RunStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


STATUS_ICON = {
    RunStatus.IDLE: "○",
    RunStatus.RUNNING: "◉",
    RunStatus.DONE: "✓",
    RunStatus.FAILED: "✗",
}
STATUS_CLASS = {
    RunStatus.IDLE: "status-idle",
    RunStatus.RUNNING: "status-running",
    RunStatus.DONE: "status-done",
    RunStatus.FAILED: "status-failed",
}


@dataclass
class AgentRun:
    name: str
    status: RunStatus = RunStatus.IDLE
    log_lines: list[str] = field(default_factory=list)
    artifacts: dict = field(default_factory=dict)
    duration_s: float = 0.0


@dataclass
class MilestoneRun:
    label: str
    test_cmd: str
    agent_runs: list[AgentRun] = field(default_factory=list)
    status: RunStatus = RunStatus.IDLE
    started_at: str = ""
    duration_s: float = 0.0


# ── Milestone registry ─────────────────────────────────────────────────────────

MILESTONES: dict[str, MilestoneRun] = {
    "M1": MilestoneRun(
        label="M1 — Framework Builders",
        test_cmd="pytest tests/test_frameworks.py -v",
        agent_runs=[AgentRun("Framework Tests")],
    ),
    "M2": MilestoneRun(
        label="M2 — Structure Only (Spec Advisor)",
        test_cmd="pytest tests/test_spec_advisor.py -v -k m2",
        agent_runs=[AgentRun("Spec Advisor"), AgentRun("Test Suite")],
    ),
    "M3": MilestoneRun(
        label="M3 — Add Reasoning (CoT)",
        test_cmd="pytest tests/test_spec_advisor.py -v -k m3",
        agent_runs=[AgentRun("Spec Advisor + CoT"), AgentRun("Test Suite")],
    ),
    "M4": MilestoneRun(
        label="M4 — Add Verification (CAI)",
        test_cmd="pytest tests/test_spec_advisor.py -v -k m4",
        agent_runs=[
            AgentRun("Spec Advisor + CAI"),
            AgentRun("CAI Critique"),
            AgentRun("Test Suite"),
        ],
    ),
    "M5": MilestoneRun(
        label="M5 — Full Spec Advisor + Meta-Prompt",
        test_cmd="pytest tests/test_spec_advisor.py tests/test_meta_prompt.py -v",
        agent_runs=[
            AgentRun("Spec Advisor"),
            AgentRun("Meta-Prompt Output"),
            AgentRun("Test Suite"),
        ],
    ),
    "M6": MilestoneRun(
        label="M6 — First Agent Chain (SME → Advisor)",
        test_cmd="pytest tests/test_sme_chain.py -v",
        agent_runs=[AgentRun("SME Agent"), AgentRun("Spec Advisor"), AgentRun("Test Suite")],
    ),
    "M7": MilestoneRun(
        label="M7 — Meta-Prompting Chain",
        test_cmd="pytest tests/test_meta_chain.py -v",
        agent_runs=[
            AgentRun("SME Agent"),
            AgentRun("Spec Advisor"),
            AgentRun("Spec Specialist"),
            AgentRun("Test Suite"),
        ],
    ),
    "M8": MilestoneRun(
        label="M8 — Coordinator + ReAct Loop",
        test_cmd="pytest tests/test_coordinator.py -v",
        agent_runs=[
            AgentRun("SME Agent"),
            AgentRun("Spec Advisor"),
            AgentRun("Spec Specialist"),
            AgentRun("Coordinator"),
            AgentRun("Test Suite"),
        ],
    ),
    "M9": MilestoneRun(
        label="M9 — Kuzu Graph Integration",
        test_cmd="pytest tests/test_graph_store.py -v",
        agent_runs=[AgentRun("Graph Store"), AgentRun("Test Suite")],
    ),
}


# ── Session state ──────────────────────────────────────────────────────────────


def _init_state() -> None:
    if "selected_milestone" not in st.session_state:
        st.session_state.selected_milestone = "M1"
    if "runs" not in st.session_state:
        st.session_state["runs"] = {}


_init_state()


# ── Sidebar ────────────────────────────────────────────────────────────────────


with st.sidebar:
    st.markdown("### ⚙ Faber")
    st.markdown(
        "<span style='color:#555;font-size:11px'>Layered Formal Specification Council</span>",
        unsafe_allow_html=True,
    )
    st.divider()

    selected = st.selectbox(
        "Milestone",
        options=list(MILESTONES.keys()),
        format_func=lambda k: MILESTONES[k].label,
        index=list(MILESTONES.keys()).index(st.session_state.selected_milestone),
    )
    st.session_state.selected_milestone = selected

    ms = MILESTONES[selected]
    st.markdown(
        f"<span class='artifact-label'>Test command</span><br>"
        f"<span class='artifact-value'>{ms.test_cmd}</span>",
        unsafe_allow_html=True,
    )
    st.markdown("")

    run_clicked = st.button("▶  Run", use_container_width=True, type="primary")

    st.divider()
    st.markdown(
        "<span style='color:#444;font-size:10px'>Chainlit shell available on port 8001 "
        "when started manually.</span>",
        unsafe_allow_html=True,
    )


# ── Main header ────────────────────────────────────────────────────────────────

st.markdown(
    f"<h2 style='color:#e0e0e0;margin-bottom:2px'>{ms.label}</h2>"
    f"<span style='color:#555;font-size:12px'>{datetime.now().strftime('%Y-%m-%d')}</span>",
    unsafe_allow_html=True,
)
st.divider()


# ── Run handler ────────────────────────────────────────────────────────────────


def _run_milestone(key: str) -> None:
    ms_def = MILESTONES[key]
    run = MilestoneRun(
        label=ms_def.label,
        test_cmd=ms_def.test_cmd,
        agent_runs=[AgentRun(a.name) for a in ms_def.agent_runs],
        status=RunStatus.RUNNING,
        started_at=datetime.now().isoformat(timespec="seconds"),
    )
    st.session_state.runs[key] = run

    t0 = time.time()
    test_agent = run.agent_runs[-1]  # last card is always the test suite
    test_agent.status = RunStatus.RUNNING

    proc = subprocess.Popen(
        ms_def.test_cmd.split(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd="/workspace",
    )

    output_placeholder = st.empty()

    for line in proc.stdout:  # type: ignore[union-attr]
        test_agent.log_lines.append(line.rstrip())
        output_placeholder.empty()

    proc.wait()
    run.duration_s = time.time() - t0

    if proc.returncode == 0:
        test_agent.status = RunStatus.DONE
        run.status = RunStatus.DONE
    else:
        test_agent.status = RunStatus.FAILED
        run.status = RunStatus.FAILED


if run_clicked:
    _run_milestone(selected)
    st.rerun()


# ── Agent cards ────────────────────────────────────────────────────────────────

current_run = st.session_state.runs.get(selected)

if current_run is None:
    # No run yet — show placeholder cards
    cols = st.columns(min(len(ms.agent_runs), 3))
    for i, agent in enumerate(ms.agent_runs):
        with cols[i % len(cols)]:
            st.markdown(
                f"""
                <div class="agent-card">
                  <div class="card-header">Agent</div>
                  <div class="card-title">{agent.name}</div>
                  <span class="{STATUS_CLASS[RunStatus.IDLE]}">
                    {STATUS_ICON[RunStatus.IDLE]} idle
                  </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
else:
    cols = st.columns(min(len(current_run.agent_runs), 3))
    for i, agent in enumerate(current_run.agent_runs):
        with cols[i % len(cols)]:
            log_text = "\n".join(agent.log_lines[-40:]) if agent.log_lines else "—"
            st.markdown(
                f"""
                <div class="agent-card">
                  <div class="card-header">Agent</div>
                  <div class="card-title">{agent.name}</div>
                  <span class="{STATUS_CLASS[agent.status]}">
                    {STATUS_ICON[agent.status]} {agent.status.value}
                  </span>
                  <div class="cli-box" style="margin-top:10px">{log_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Artifacts panel
    if any(a.artifacts for a in current_run.agent_runs):
        st.divider()
        st.markdown(
            "<span style='color:#888;font-size:11px;text-transform:uppercase;"
            "letter-spacing:0.1em'>Artifacts</span>",
            unsafe_allow_html=True,
        )
        for agent in current_run.agent_runs:
            if agent.artifacts:
                with st.expander(agent.name, expanded=True):
                    for k, v in agent.artifacts.items():
                        st.markdown(
                            f"<span class='artifact-label'>{k}</span>"
                            f"<div class='artifact-value'>{v}</div>",
                            unsafe_allow_html=True,
                        )

    # Run summary
    st.divider()
    status_icon = STATUS_ICON[current_run.status]
    status_cls = STATUS_CLASS[current_run.status]
    st.markdown(
        f"<span class='{status_cls}'>{status_icon} {current_run.status.value}</span>"
        f"<span style='color:#444;font-size:11px;margin-left:16px'>"
        f"started {current_run.started_at} · {current_run.duration_s:.1f}s</span>",
        unsafe_allow_html=True,
    )
