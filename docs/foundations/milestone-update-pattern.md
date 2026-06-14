# Milestone Update Pattern

Use this doc when asked to update a pre-M4.1 milestone plan.
Example: *"Follow milestone-update-pattern.md to update the M6 milestone."*

The updated plan replaces the milestone's BACKLOG.md task list in-place.
**Reference:** M5's BACKLOG entry is the canonical output of this process.

---

## Step 1 — Extract what stays

From the existing BACKLOG entry, keep unchanged:
- **"What is being proven"** statement
- **Success criteria** (gate to next milestone)
- The agent composition chain (check for dimension conflicts — see Step 4)

Discard the old task list entirely.

---

## Step 2 — Answer the three GNN questions

These determine the schema additions for this milestone.

**Q1: What new node table does this milestone own?**
Named after what the new layer produces.
Examples: `RevisionEvent` (CAI layer), `MetaPromptEvent` (CRISPE generation), `ChainEvent` (first agent chain).

**Q2: What cross-schema edge connects this milestone to the prior one?**
Named `{LAYER}_ADDS`. Properties carry the delta signal — what changed by adding this layer?
Examples: `VERIFICATION_ADDS` (M3→M4), `META_PROMPT_ADDS` (M4→M5).

**Q3: Which briefs get a cross-schema edge?**
Check whether all 3 briefs (simple, complex, vague) exist in the prior milestone's SpecRun nodes.
An edge can only exist where a prior-milestone node exists.
- M2, M3: simple + complex only (vague not introduced yet)
- M4+: all 3 briefs

---

## Step 3 — Write the migration plan

Always use the multi-pass directory layout, even if only pass_01 is planned.

```
src/milestones/m{N}/migration/
  meta.json          ← see below
  pass_01/
    schema.cypher    ← complete DB snapshot at this milestone (ALL tables, not just new ones)
    transform.cypher ← backfill new columns on existing rows; WHY comment on every default
```

`meta.json` format:
```json
{
  "source_milestone": "m{N-1}",
  "target_milestone": "m{N}",
  "reseed_tables": ["FrameworkLayer"],
  "passes": 1
}
```

`reseed_tables: ["FrameworkLayer"]` is always present — FrameworkLayer is deterministic.

`pass_02+` are not planned now. They are added during the Claude-in-loop analytical session
if new schema needs emerge. Never modify an existing pass.

---

## Step 4 — Resolve composition chain conflicts

Check the original milestone's agent chain for the **one-layer-per-dimension rule**:
- Structure: COSTAR, CRISPE, CLEAR, RACE — only one per agent
- Reasoning: ChainOfThought, ReActLoop — only one per agent
- Verification: ConstitutionalAI — only one per agent
- Technique: PersonaLayer, FewShot — only one per agent

If two Structure frameworks appear (e.g. CLEAR + COSTAR), resolve it: keep the one that
fits the agent's role; add a note in the BACKLOG entry explaining the decision.

---

## Step 5 — Decide agent scope

- Agent lives in `src/milestones/m{N}/` — NOT `src/agents/`
- Frameworks are copied from the prior milestone and tagged `[MN-copy | milestones/m{N-1}/frameworks/<name>.py]`
- New agents are tagged `[MN-origin]`
- Agents are only promoted to `src/agents/` at the milestone where they first join a multi-agent chain

---

## Step 6 — Write the full task list

Use this structure (M5's BACKLOG entry is the reference):

```
- [ ] src/milestones/m{N}/migration/  — pass_01 planned (see Step 3)

- [ ] src/milestones/m{N}/frameworks/ — copies from m{N-1} + any new frameworks needed

- [ ] src/milestones/m{N}/schema.py   — [MN-origin] Pydantic output models

- [ ] src/milestones/m{N}/agent.py    — [MN-origin] agent with composition chain;
      any programmatic post-processing (e.g. CRISPE prompt assembly) done here, not as a layer

- [ ] src/milestones/m{N}/[new-agent.py] — if a new stub agent is introduced this milestone

- [ ] src/milestones/m{N}/graph/schema.py — new node table + cross-schema rel + ANALYZED_[TYPE] rel

- [ ] src/milestones/m{N}/graph/runner.py — infer_*() helpers + seed() + dump() dev util

- [ ] src/milestones/m{N}/run.py — CLI: 3 briefs; --m{N-1}-run-id (auto-detects); summary table

- [ ] src/milestones/m{N}/tests/test_m{N}.py — ~30 gate tests (ephemeral DB, mock outputs):
      schema; SpecRun new fields; new node per brief; cross-schema edges + properties;
      topology query (extends prior by one hop); regression (all prior tests green);
      1 @pytest.mark.integration LLM call

- [ ] Claude-in-loop: 3 CLI runs; ad-hoc Cypher analysis of [new node] signals;
      AnalysisNote nodes via ANALYZED_[TYPE] edges;
      add pass_02 to migration if schema needs evolve

- [ ] docs/evidence/M{NN}_name.md — create now (hypothesis + method + gate tests);
      fill Result / Lessons / Next at milestone end
```

---

## Step 7 — Write the topology query test

Every milestone's signature gate test extends the prior milestone's topology query by one edge hop.

Current chain at M4 (two hops):
```cypher
MATCH (m2:SpecRun {milestone:'m2'})-[:REASONING_ADDS]->(m3:SpecRun)
      -[:VERIFICATION_ADDS]->(m4:SpecRun)
WHERE m4.revised = false AND ...
```

M5 adds the third hop (`META_PROMPT_ADDS`). M6 adds the fourth, and so on.
Name the test `test_topology_query_N_hop` in the test file.

---

## What NOT to put in the milestone task list

- OPP entries or hypothesis tracking — these are Claude-in-loop decisions, not tasks
- Specific AnalysisNote schemas — these emerge from the analytical session
- `pass_02+` migration content — added ad-hoc, not planned
- `analysis_opportunities.md` updates — Claude does this during the analytical session

---

## Reference

- Canonical output: [BACKLOG.md — Milestone 5](../../BACKLOG.md#milestone-5--layer-4-poc-full-spec-advisor--meta-prompt-output)
- Layout rules: [dev-guide.md](dev-guide.md#implementing-a-new-milestone-m41-sub-milestone-pattern)
- ETL patterns: [kuzu_etl_strategy.md](kuzu_etl_strategy.md)
