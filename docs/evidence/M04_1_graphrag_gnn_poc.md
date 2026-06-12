# M04.1 — GraphRAG / GNN PoC: PE Evolution Captured and Queryable

**Layer:** 4.1 — GNN substrate proof (runs in parallel with Spec Council M5+)  
**Milestone:** M4.1 in BACKLOG.md  
**Status:** In progress — M4.1 M0 and M4.1 M1 confirmed; M4.1 M2–M4 pending  
**Date started:** 2026-06-12  
**Date completed:** — (in progress)

---

## Hypothesis

The GNN substrate is not architectural intent — it is a running, queryable graph.
PE evolution from M1–M4 can be encoded as heterogeneous subgraphs in Kuzu,
with cross-schema comparison edges carrying the ML signal.
A topology-based traversal across those edges returns a structurally meaningful result.

---

## Method

Structured as four sub-milestones (M4.1 M0–M4), each seeding one milestone's own subgraph
into the persistent Kuzu DB. No unified schema — each milestone owns its node/edge types.
Claude (not code) decides what signals to persist as `AnalysisNote` nodes after each run.

`analysis_opportunities.md` at the repo root is the cross-session grounding document:
confirmed signals, open hypotheses with `available_when` conditions, and Cypher queries
ready to run when their milestone's data is available.

Each sub-milestone follows the self-contained layout established in M4.1 M0:
`src/milestones/m{N}/` with its own `graph/schema.py`, `graph/runner.py`, `run.py`,
and `tests/test_m{N}_gnn.py` (ephemeral DB gate tests).

See BACKLOG.md [M4.1 section](../../BACKLOG.md#milestone-41--graphrag--gnn-poc-pe-evolution-captured-and-queryable) for full task lists.

---

## Gate Tests

> Each milestone's own subgraph is seeded from live agent calls.
> Cross-schema comparison edges exist between milestone subgraphs with delta properties.
> A topology-based traversal across cross-schema edges returns a structurally similar prior run —
> proving the graph learns by comparison, not by keyword.

---

## Result — M4.1 M0: GNN Grounding ✓

**Hypothesis**: the architectural pattern works — self-contained milestone layout,
`MilestoneRun` subgraph anchor, runner CLI, Claude-in-loop `AnalysisNote` feedback loop,
`analysis_opportunities.md` as cross-session grounding.

Confirmed 2026-06-12. Pattern proven working:
- Gate tests use ephemeral tmp Kuzu DB; never write to persistent `data/kuzu`
- Runner CLI seeds one subgraph per invocation; N invocations = N independent subgraphs
- `AnalysisNote` schema invented on the fly per session — not predetermined
- `analysis_opportunities.md` created with OPP-1–OPP-7 and H1–H5

---

## Result — M4.1 M1: Framework Layer GNN ✓

**Hypothesis**: 9 framework builders captured as `FrameworkLayer` nodes, multiple runs
accumulate as distinct subgraphs, Claude-in-loop analysis surfaces real signals and
writes them back as `AnalysisNote` nodes.

Confirmed 2026-06-12. 11/11 gate tests passing.

**Persistent DB state** (3 runs):
- 3 MilestoneRun + 27 FrameworkLayer + 27 CAPTURED_IN
- 12 AnalysisNote + 108 ANALYZED edges

**Confirmed signals**:

| Framework | Dimension | tokens_est | build_avg | variance_ratio | Signal |
|---|---|---|---|---|---|
| ConstitutionalAI | Verification | 162 | 0.023ms | **8.8×** | timing outlier; anomaly threshold `range > 0.040ms` |
| FewShot | Technique | 102 | 0.006ms | **0.8×** | most consistent builder |
| ChainOfThought | Reasoning | 175 | 0.012ms | 2.0× | highest token density in Reasoning dimension |
| PersonaLayer | Technique | 78 | 0.008ms | 1.6× | lowest expansion ratio (0.265) |

Noise floor: max 0.050ms across 3 runs. M2+ ML signal is LLM latency, not build_time_ms.
Full determinism confirmed: `build_output` and `file_hash` identical across all 3 runs.

---

## Result — M4.1 M2–M4

> TBD — fill after each sub-milestone's gate tests pass.

---

## Lessons

- **The crucial architectural distinction**: `runner.py` captures raw features; Claude analyzes.
  A hardcoded `analyze()` function with predetermined signal names makes the analysis loop as
  rigid as the thing it was replacing. Dynamic analysis (ad-hoc Cypher, `AnalysisNote` on the fly)
  is the right model.
- **Noise floor established early**: M1 proves that `build_time_ms` is noise (<0.050ms max) for
  pure Python builders. This pre-empts a whole class of false signals in M2+ analysis.
- **ConstitutionalAI timing outlier**: 8.8× variance ratio suggests Python list allocation on
  first call — not a performance concern, but a signal to watch in any framework with internal
  state. Anomaly threshold for future detection: `range > 0.040ms`.
- **Git discipline**: M4.1 M0 and M1 work was done across two sessions without a dedicated commit
  per sub-milestone. Going forward, each M4.1 sub-milestone should be on its own branch with a
  clean merge commit — both for traceability and for the git-restoration pattern needed in M4.1 M2+.
- **Frozen composition pattern**: each M4.1 M{N} milestone must freeze the agent composition
  from git (e.g. `git show 05f373d:src/agents/spec_advisor.py`) — not import from `src/agents/`
  which always holds the current (M4) version. Self-contained milestone = frozen snapshot.

---

## Next Layer Can Rely On

- `python3 -m src.milestones.m1.run [run-id]` seeds one `MilestoneRun` subgraph reliably.
  Run it N times to accumulate N subgraphs — no code changes needed between runs.
- Gate tests scoped by `run_id` (`MATCH ... WHERE r.run_id = $rid`) — safe to assert on
  without cross-run pollution.
- `AnalysisNote` + `ANALYZED` pattern: `CREATE NODE TABLE IF NOT EXISTS AnalysisNote (...)`,
  `CREATE REL TABLE IF NOT EXISTS ANALYZED (FROM AnalysisNote TO ...)` — schema on the fly,
  queryable immediately.
- `analysis_opportunities.md` read at session start = full context for what to query and why.
- M1 timing baselines: any new framework with `build_time_ms > 1.0` has unexpected IO.
  ConstitutionalAI variance `range > 0.040ms` is the anomaly threshold.
