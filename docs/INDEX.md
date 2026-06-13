# Faber — Docs Navigator

> *"The composition of layers is the architecture."*

Entry point to all project documentation. Start here when you need to find something.
For new session orientation, start with `README.md` in the repo root.

---

## Quick orientation (new session)

| Question | Go to |
|---|---|
| Where are we? What's next? | `README.md` |
| How do I work with Claude on this project? | `docs/running-with-claude.md` |
| What are the implementation rules? | `CLAUDE.md` |
| What's the active task list? | `BACKLOG.md` |
| What's been proven? | `COMPLETED.md` |
| What GNN signals are confirmed? What's open? | `analysis_opportunities.md` |

---

## Foundations (stable reference)

| Document | What it covers |
|---|---|
| [docs/foundations/composition_framework.md](foundations/composition_framework.md) | **Central architectural doc.** Research grounding (8 papers), framework taxonomy, full agent chains, one-shot examples for every layer. Read this before implementing anything. |
| [docs/foundations/prompt_frameworks.md](foundations/prompt_frameworks.md) | Per-framework field reference (COSTAR, CRISPE, CLEAR, RACE, PersonaLayer, etc.) |
| [docs/foundations/kuzu_etl_strategy.md](foundations/kuzu_etl_strategy.md) | Kuzu schema migration strategy — blue-green rotation, transform.cypher patterns, multi-pass layout |
| [docs/foundations/dev-guide.md](foundations/dev-guide.md) | How to implement a new agent, framework layer, or milestone; Python+Claude techniques |
| [docs/git-workflow.md](git-workflow.md) | Branch naming, commit conventions, merge strategy |
| [.devcontainer/README.md](../.devcontainer/README.md) | Dev container setup, ports, secrets, rebuild behaviour |

---

## Architecture decisions (ADRs)

The *why* behind design choices. Read when you want rationale, not just behaviour.

| ADR | Decision | Status |
|---|---|---|
| [ADR-001](decisions/ADR-001_layered-composition-over-monolithic.md) | Layered composition over monolithic agent prompts | Active |
| [ADR-002](decisions/ADR-002_voice-retired.md) | VOICE framework retired; replaced by composed layers | Retired |
| [ADR-003](decisions/ADR-003_constitutional-ai-as-verification-layer.md) | Constitutional AI as the universal verification gate | Active |
| [ADR-004](decisions/ADR-004_forced-tool-use-for-structured-output.md) | Forced tool-use (`tool_choice=any`) for all structured output | Active |

---

## Evidence — PoC results

One file per milestone. Created at milestone start (hypothesis + method + gates). Completed at milestone finish (result + lessons + what next layer can rely on).

| Milestone | Layer | File | Status |
|---|---|---|---|
| M00 | Infrastructure | [M00_infrastructure.md](evidence/M00_infrastructure.md) | Complete |
| M01 | Layer 0: Framework builders | [M01_framework_builders.md](evidence/M01_framework_builders.md) | Complete |
| M02 | Layer 1: Single agent, structure only | [M02_spec_advisor_structure.md](evidence/M02_spec_advisor_structure.md) | Complete |
| M03 | Layer 2: Add Reasoning (CoT) | [M03_reasoning_layer.md](evidence/M03_reasoning_layer.md) | Complete |
| M04 | Layer 3: Add Verification (CAI) | [M04_verification_layer.md](evidence/M04_verification_layer.md) | Complete |
| M4.1 | GNN PoC: PE evolution captured and queryable | [M04_1_graphrag_gnn_poc.md](evidence/M04_1_graphrag_gnn_poc.md) | In progress — M4.1 M0–M3 proven; M4.1 M4 next |
| M05–M13 | Subsequent Spec Council layers | Create from [TEMPLATE.md](evidence/TEMPLATE.md) when milestone starts | — |

---

## Analysis

Subjective assessments, debates, and alternatives considered.

| Document | What it covers |
|---|---|
| [docs/analysis/alternatives_considered.md](analysis/alternatives_considered.md) | Frameworks, patterns, and approaches considered and rejected; tensions in the current design |

---

## Archive

Predecessor and founding documents, kept for lineage.

| Document | What it is |
|---|---|
| [docs/archive/original-thesis.md](archive/original-thesis.md) | Original Greenfield Development Agent Council design doc (predecessor to Faber) |
| [docs/archive/compages-codex.md](archive/compages-codex.md) | Creative architectural framing from early project ideation |

---

## Thesis arc

| Document | What it covers |
|---|---|
| [docs/thesis/CLAIM.md](thesis/CLAIM.md) | Central claim + per-milestone hypotheses (the thesis arc) |

---

## How this project generates docs

```
Before milestone starts  →  create docs/evidence/Mxx_name.md (hypothesis + method + gates)
After milestone passes   →  fill in Result + Lessons + "Next Layer Can Rely On"
If a decision is made    →  create docs/decisions/ADR-xxx_name.md
If analysis is needed    →  add to docs/analysis/ or a new file there
After analysis session   →  update analysis_opportunities.md (confirmed signals + new hypotheses)
```
