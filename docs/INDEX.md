# Faber — Thesis Navigator

> *"The composition of layers is the architecture."*

Faber is a **prompt engineering project** running as an empirical thesis:
each milestone is a controlled PoC that proves one layer before the next is built on top of it.
This document is the spine — it links everything and tells you where to look.

---

## First read (in order)

| Step | Document | Purpose |
|---|---|---|
| 1 | [ARCHITECTURE.md](../ARCHITECTURE.md) | Vision, agents, graph schema, infra, PoC scope |
| 2 | [docs/thesis/CLAIM.md](thesis/CLAIM.md) | Central claim + per-milestone hypotheses (the thesis arc) |
| 3 | [docs/foundations/composition_framework.md](foundations/composition_framework.md) | Research grounding, framework taxonomy, full agent chains, one-shot examples, debate |

---

## Architecture decisions (ADRs)

Why the system is designed the way it is. Read when you want the *why*, not just the *what*.

| ADR | Decision | Status |
|---|---|---|
| [ADR-001](decisions/ADR-001_layered-composition-over-monolithic.md) | Layered composition over monolithic agent prompts | Active |
| [ADR-002](decisions/ADR-002_voice-retired.md) | VOICE framework retired; replaced by composed layers | Retired |
| [ADR-003](decisions/ADR-003_constitutional-ai-as-verification-layer.md) | Constitutional AI as the universal verification gate for all agents | Active |
| [ADR-004](decisions/ADR-004_forced-tool-use-for-structured-output.md) | Forced tool-use (`tool_choice=any`) for all structured agent output | Active |

---

## Evidence — PoC results

One file per milestone. **Created at milestone start** (hypothesis + method + gates prefilled).
**Completed at milestone finish** (result + lessons + what next layer can rely on).

| Milestone | Layer | File | Status |
|---|---|---|---|
| M00 | Infrastructure | [M00_infrastructure.md](evidence/M00_infrastructure.md) | Complete |
| M01 | Layer 0: Framework builders | [M01_framework_builders.md](evidence/M01_framework_builders.md) | Complete |
| M02 | Layer 1: Single agent, structure only | [M02_spec_advisor_structure.md](evidence/M02_spec_advisor_structure.md) | Complete |
| M03–M13 | Subsequent layers | Create from [TEMPLATE.md](evidence/TEMPLATE.md) when milestone starts | — |

---

## Analysis

Subjective assessments, debates, and alternatives considered. Not the architecture itself —
the thinking behind it.

| Document | What it covers |
|---|---|
| [docs/analysis/alternatives_considered.md](analysis/alternatives_considered.md) | Frameworks, patterns, and approaches considered and rejected; tensions in the current design |

---

## Reference

Stable lookup material. Updated, not debated.

| Document | What it covers |
|---|---|
| [docs/foundations/composition_framework.md](foundations/composition_framework.md) | Central analysis — research grounding, composition model, agent chains, one-shot examples |
| [docs/foundations/prompt_frameworks.md](foundations/prompt_frameworks.md) | Per-framework field reference (COSTAR, CRISPE, CLEAR, RACE, PersonaLayer, etc.) |
| [BACKLOG.md](../BACKLOG.md) | Milestone task lists and success criteria gates |
| [CLAUDE.md](../CLAUDE.md) | Implementation guidance for Claude Code |

---

## How this project generates docs

As milestones are executed, the docs system accretes evidence:

```
Before milestone starts  →  create docs/evidence/Mxx_name.md (hypothesis + method + gates)
After milestone passes   →  fill in Result + Lessons + "Next Layer Can Rely On"
If a decision is made    →  create docs/decisions/ADR-xxx_name.md
If analysis is needed    →  add to docs/analysis/ or a new file in docs/analysis/
```

The final thesis is: `thesis/CLAIM.md` + `decisions/` + all completed `evidence/` files in sequence.
