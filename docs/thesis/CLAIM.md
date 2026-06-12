# Faber — Central Claim and Thesis Hypotheses

**Author:** Nitin Pawar | **Date:** June 2026  
**Status:** Active — M00–M04 confirmed; M4.1 GNN PoC in progress (M4.1 M0–M1 confirmed)

---

## Central Claim

> Faber is a **meta-prompting system** (Suzgun & Kalai, 2024) in which each agent
> prompt is a **composed chain of orthogonal framework layers** (DSPy, 2023),
> verified by a **critique-revision loop** (Constitutional AI, 2022), with
> the council's decisions made auditable by **explicit reasoning traces**
> (CoT + ReAct). The composition itself — not any individual technique —
> is the architectural contribution.

The claim has three components:
1. **Composition beats monolithic** — a chain of orthogonal layers produces better output than any single framework applied alone. (Empirical: DSPy 25–65% improvement; ACL 2024 chaining > monolithic.)
2. **Verification must close the loop** — every agent gates its output through a critique-revision pass. Without it, composition is just structured concatenation. (Grounded in: Constitutional AI, Anthropic 2022.)
3. **Meta-prompting is the design pattern for dynamic specialisation** — the Spec Advisor generates the Spec Specialist's entire prompt at runtime, enabling adaptive spec language selection across layers. (Grounded in: Suzgun & Kalai 2024.)

---

## Research Foundations

| Paper | Authors | Venue | Core contribution to Faber |
|---|---|---|---|
| [Chain-of-Thought Prompting](https://arxiv.org/abs/2201.11903) | Wei et al., Google Brain | NeurIPS 2022 | Intermediate reasoning steps improve complex task performance — basis for ChainOfThought layer |
| [Constitutional AI](https://arxiv.org/abs/2212.08073) | Bai et al., Anthropic | 2022 | Generate → critique → revise loop as verifiable output gate — basis for ConstitutionalAI layer |
| [ReAct](https://arxiv.org/abs/2210.03629) | Yao et al., Google + Princeton | 2022 | Interleaved reasoning + acting outperforms either alone — basis for ReActLoop layer |
| [DSPy](https://arxiv.org/abs/2310.03714) | Khattab et al., Stanford | NeurIPS 2023 | Composable declarative modules outperform monolithic prompts by 25–65% — foundational design principle |
| [Reflexion](https://proceedings.neurips.cc/paper_files/paper/2023/file/1b44b878bb782e6954cd888628510e90-Paper-Conference.pdf) | Shinn et al. | NeurIPS 2023 | Verbal episodic memory for multi-trial improvement — basis for SME Agent Phase B multi-turn |
| [Meta-Prompting](https://arxiv.org/abs/2401.12954) | Suzgun & Kalai, Stanford + OpenAI | 2024 | Conductor LM generates prompts for specialist LMs — exact architecture of Spec Advisor → Spec Specialist |
| [Prompt Chaining vs Monolithic](https://aclanthology.org/2024.findings-acl.449/) | Sun et al. | ACL Findings 2024 | Empirical proof: chained prompts consistently outperform monolithic prompts |
| [Layered Multi-Prompt Engineering](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12493772) | US Patent 12493772 | 2025 | Industry validation of vector-store-driven layered prompt assembly |

**Synthesis**: DSPy says *make it composable*. Meta-Prompting says *one conductor, many specialists*.
ACL 2024 says *chains beat monoliths empirically*. Constitutional AI says *always close the loop*.
These four constitute the theoretical spine.

---

## Per-Milestone Hypotheses

Each hypothesis is a testable claim. Passing the milestone's gate tests = hypothesis confirmed.
Evidence files in `docs/evidence/` record the result.

| Milestone | Hypothesis | Status |
|---|---|---|
| M00 | A working devcontainer is established by extracting and adapting the Senatus infra layer with minimal changes. | ✓ confirmed |
| M01 | All framework builders produce correctly structured output independently and can be composed in sequence without interference. | ✓ confirmed |
| M02 | A Structure layer (COSTAR alone) is sufficient to ground the Spec Advisor's language selection task — producing coherent, differentiated selections for projects of different complexity. | ✓ confirmed |
| M03 | Adding a Chain of Thought layer makes selection reasoning visible and auditable, and improves or maintains selection quality relative to the M02 baseline. | ✓ confirmed |
| M04 | The Constitutional AI critique-revision loop demonstrably improves low-quality outputs while passing high-quality outputs through unchanged — functioning as a reliable output gate. | ✓ confirmed |
| M4.1 | The GNN substrate is not architectural intent — it is a running, queryable graph. PE evolution is encoded as heterogeneous subgraphs with cross-schema comparison edges as ML signal. | → in progress (M4.1 M0–M1 confirmed) |
| M05 | With all four layers active, the Spec Advisor generates a CRISPE meta-prompt that is sufficient to drive a Spec Specialist to produce a non-empty formal spec mentioning domain terms from the input. | ○ pending |
| M06 | Inter-agent context flows correctly: SME domain vocabulary appears in the Spec Advisor's selection context, and different personas applied to the same domain brief produce measurably different requirement text. | ○ pending |
| M07 | The full meta-prompting chain (SME → Spec Advisor → Spec Specialist) produces a formal spec in the Advisor-selected language, grounded in the SME's domain terminology. | ○ pending |
| M08 | The Coordinator detects low-confidence output and triggers the correct decision (retry/proceed/escalate). The ReAct reasoning is auditable. The loop terminates correctly. | ○ pending |
| M09 | Spec artifacts persist in Kuzu with GROUNDS edges forming a queryable traceability chain from component spec back to requirement. | ○ pending |
| M10 | The Spec Advisor is stateful across visits. Projects of different complexity produce spec stacks of different depths, each layer grounded in the layer above it. | ○ pending |
| M11 | The Test Engineer produces Gherkin scenarios traceable to named spec nodes in the graph. Full traceability path (Requirement → system spec → domain spec → component spec → Gherkin) is queryable end-to-end. | ○ pending |
| M12 | The SME Agent accumulates council responses as episodic memory across turns (Reflexion pattern), producing requirement sequences that visibly react to and build on prior council output. | ○ pending |
| M13 | The system operates reliably with smaller models (Ollama). Confidence scoring is model-derived, not hardcoded. The spec stack rehydrates correctly from Kuzu on session restart. | ○ pending |

---

## What thesis completion looks like

The thesis is complete when:
- All milestone evidence files have non-empty `Result` and `Lessons` sections
- The full traceability path (M11) is verified in a live session
- M12 produces a benchmark dataset across ≥3 personas × ≥2 domains
- This CLAIM.md can be read with the evidence files as supporting chapters

The final document set is:
```
thesis/CLAIM.md              (this file)
decisions/ADR-001.md         (why composition)
decisions/ADR-002.md         (why not VOICE)
evidence/M00–M13.md          (what each PoC proved)
analysis/alternatives.md     (what was considered and rejected)
foundations/composition_framework.md  (the full architecture + research synthesis)
```
