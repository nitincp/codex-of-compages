# Analysis Opportunities

Cross-session grounding document. Each session Claude reads this, picks what's
actionable given the current milestone state, runs ad-hoc Cypher queries or scripts
against the live GNN, and updates this file with new opportunities discovered.

This is NOT a results log. Results are ephemeral (printed, read, discarded).
What persists here is: what to ask, when to ask it, and what the answer would prove.

---

## How to use this file

1. Read this before any ML pass work
2. Check which milestones are currently seeded (run `python3 scripts/graph_stats.py` or
   query `MATCH (n) RETURN labels(n), count(n)`)
3. Pick opportunities whose `available_when` condition is met
4. Write an ad-hoc script or direct Cypher — run it, read the output, update hypotheses here
5. Add new opportunities discovered during the session

---

## M1 — Framework characterization (always available)

**Seeded nodes:** `FrameworkLayer` × 9  
**Persistent DB:** `data/kuzu` — run `python3 -m src.milestones.m1.run` to add a subgraph

### Observed signals (M1, 3-run analysis, 2026-06-12)

**Confirmed across 3 runs** (`python3 -m src.milestones.m1.run` × 3, persistent DB at `data/kuzu`):

| Framework | Dimension | tokens_est | expansion | build_avg | build_range | variance |
|---|---|---|---|---|---|---|
| ChainOfThought | Reasoning | 175 | 0.723 | 0.012ms | 0.007ms | 2.0× |
| ConstitutionalAI | Verification | 162 | 0.560 | 0.023ms | **0.045ms** | **8.8×** |
| CLEARSession | Structure | 142 | 0.597 | 0.012ms | 0.008ms | 1.3× |
| CRISPEPrompt | Structure | 137 | 0.389 | 0.019ms | 0.018ms | 3.0× |
| ReActLoop | Reasoning | 124 | 0.378 | 0.010ms | 0.011ms | 3.4× |
| COSTARPrompt | Structure | 115 | 0.395 | 0.021ms | 0.011ms | 1.7× |
| FewShot | Technique | 102 | 0.424 | 0.006ms | 0.005ms | **0.8×** |
| PersonaLayer | Technique | 78 | 0.265 | 0.008ms | 0.007ms | 1.6× |
| RACEPrompt | Structure | 69 | 0.348 | 0.012ms | 0.015ms | 4.1× |

`build_output` and `file_hash`: **identical across all 3 runs — M1 is fully deterministic.**

Key observations:
- **ConstitutionalAI is the timing outlier** — 8.8× variance, likely Python list allocation on first call. Anomaly threshold for OPP-6 should be `range > 0.04ms`, not `build_time > 1ms`.
- **Noise floor confirmed: max 0.050ms.** M2 API latency (1–5s) makes `build_time_ms` irrelevant from M2 onward. The signal to measure in M2+ is `latency_ms` from the LLM call.
- **Reasoning dimension has highest mean token density** (149.5) vs Structure (115.75). ChainOfThought alone adds ~175 tokens when M3 composes it.
- **PersonaLayer** lowest expansion (0.265) — cheap token footprint despite verbose source.
- **ConstitutionalAI** sole Verification framework — 162 tokens fixed per agent invocation.

---

---

## M2 — Spec Advisor, COSTAR-only (available from 2026-06-12)

**Seeded nodes:** `SpecRun` × 6 (3 runs × 2 briefs)  
**Persistent DB:** `data/kuzu` — run `python3 -m src.milestones.m2.run` to add a subgraph  
**Rel table:** `SPEC_CAPTURED_IN (FROM SpecRun TO MilestoneRun)` — M2-owned (distinct from M1's CAPTURED_IN)

### Observed signals (M2, 3-run analysis, 2026-06-12)

**Confirmed across 3 runs** (`python3 -m src.milestones.m2.run` × 3, model: claude-sonnet-4-6):

| Brief | Lang | Layer | Conf mean | Conf range | Lat mean (warm) | Lat range | Just chars mean |
|---|---|---|---|---|---|---|---|
| simple | OpenAPI | api | 0.977 | 0.010 | 11,476ms | 271ms | 761 |
| complex | TLA+ | system | 0.957 | 0.040 | 8,566ms | 1,170ms | 1,326 |

_Warm latency excludes run-1 cold-start (27,567ms for simple; 9,272ms for complex)._

Key observations:
- **Lang/layer selection fully deterministic**: OpenAPI/api for simple, TLA+/system for complex — 0 variance. COSTAR alone drives unambiguous choices for clear-cut briefs.
- **Confidence ceiling is high**: simple 0.977 (tight), complex 0.957 (looser). Complex is 2% lower and 4× more variable — complexity → uncertainty confirmed.
- **Cold-start penalty**: run-1 simple = 2.40× slower than warm state; complex barely affected (1.08×). Filter run-1 in latency analysis; warm state is the signal.
- **Complexity-latency inversion**: complex briefs are ~2.6s _faster_ than simple at warm state despite 1.74× longer justification text. Unambiguous signals → fast token selection even for long output.
- **Justification density**: complex = 1,326 chars (11% variance), simple = 761 chars (28% variance). Shorter outputs are proportionally less stable.

AnalysisNote nodes written: `m2-lang-determinism`, `m2-confidence-baseline`, `m2-latency-cold-start`, `m2-latency-warm-baseline`, `m2-justification-density`  
Rel tables added: `ANALYZED_SPEC (FROM AnalysisNote TO SpecRun)`, `ANALYZED_RUN (FROM AnalysisNote TO MilestoneRun)`

OPP-3 `available_when` condition **partially met** — M2 baseline seeded but the A/B variant (CLEARSession substitution) still requires a separate run. See updated OPP-3 below.

---

## M3 — Spec Advisor, COSTAR+CoT (available from 2026-06-12)

**Seeded nodes:** `SpecRun` × 6 (3 runs × 2 briefs), `REASONING_ADDS` × 6 cross-schema edges  
**Persistent DB:** `data/kuzu` — run `python3 -m src.milestones.m3.run` to add a subgraph  
**AnalysisNote schema evolved at M3:** added `milestone`, `hypothesis_id`, `direction`, `metric_before`, `metric_after`

### Observed signals (M3, 3-run analysis, 2026-06-12)

**Confirmed across 3 runs** (`python3 -m src.milestones.m3.run` × 3, model: claude-sonnet-4-6):

| Brief | Lang | Layer | Conf mean | Conf range | Lat mean | Steps mean | Just chars mean |
|---|---|---|---|---|---|---|---|
| simple | OpenAPI | api | 0.977 | 0.010 | 22,814ms | 6.67 | 889 |
| complex | TLA+ | system | 0.970 | **0.000** | 25,401ms | 8.67 | 1,310 |

Note: all runs linked to `m2-20260612-130704` for REASONING_ADDS delta computation.

**Hypothesis resolutions:**

| ID | Hypothesis | Result | Evidence |
|---|---|---|---|
| H1 | CoT token density (175) → reasoning depth | **confirmed** | 6/6 runs: `evaluation_depth=per_concern`, ≥5 steps naming candidate langs |
| H5 | M2→M3 delta dominated by CoT (≈175 tokens) | **confirmed** | M2 budget 115 → M3 budget 290 (+175, exactly CoT; zero COSTAR change) |
| H6 | CoT narrows complex conf_range (0.040 → <0.020) | **confirmed (exceeded)** | Complex range collapsed to **0.000** — all 3 runs: 0.970 exact |
| H7 | Complexity-latency inversion persists at M3 | **refuted** | M3 complex(25,401ms) > simple(22,814ms) — reversed; CoT output volume dominates |
| H8 | M3 just_char > M2 for complex, not simple | **refuted** | simple +16.8% (761→889), complex −1.2% (1326→1310) — CoT front-loads complex reasoning into steps |

**New signal (m3-candidate-rejection-asymmetry):**  
`adds_candidate_rejection=True`: simple 3/3, complex 1/3.  
Simple briefs always explicitly dismiss TLA+/Alloy/Event-B. Complex: TLA+ dominance is obvious — dismissal is often implicit rather than stated.

**REASONING_ADDS edge deltas** (M2 run `m2-20260612-130704` → M3 runs):  
- Both briefs: `confidence_delta ≈ 0.000` — M2 confidence for this specific run already matched M3.  
- The delta signal lives in `step_count` (0→5–9) and `evaluation_depth` (unknown→per_concern), not confidence.

AnalysisNote nodes written: `m3-cot-reasoning-depth`, `m3-prompt-budget-delta`, `m3-complex-confidence-lock`, `m3-latency-inversion-reversed`, `m3-justification-delta`, `m3-candidate-rejection-asymmetry`  
New schema fields: `milestone`, `hypothesis_id`, `direction`, `metric_before`, `metric_after` — backfilled with neutral defaults on all pre-M3 notes.

---

## Opportunities

### OPP-1: Reasoning-layer token delta (M1 → M3)
**Available when:** M3 seeded  
**Query:**
```cypher
-- Compare SpecAdvisor output sizes: M2 (COSTAR only) vs M3 (COSTAR+CoT)
MATCH (r:SpecRun) WHERE r.milestone IN ['m2', 'm3']
RETURN r.milestone, avg(r.output_token_count), avg(r.latency_ms)
ORDER BY r.milestone
```
**What it proves:** If M3 mean output tokens >> M2, ChainOfThought's 175-token weight
translates to richer agent output, not just longer prompts.

---

### OPP-2: ConstitutionalAI revision rate (M4)
**Available when:** M4 seeded  
**Query:**
```cypher
MATCH (r:SpecRun {milestone: 'm4'})
RETURN r.revised, count(r), avg(r.confidence)
ORDER BY r.revised
```
**What it proves:** What fraction of M4 outputs trigger the CAI revision loop?
If revision rate is high with low pre-revision confidence, CAI is doing real work.
If revision rate is near zero, CAI may be too permissive (principles too weak).

---

### OPP-3: Structure framework A/B — COSTAR vs CLEARSession
**Available when:** M2 seeded ✓ + an M2-variant run with CLEARSession substituted (not yet done)  
**M2 baseline established:** OpenAPI/0.977 conf / 11,476ms warm latency (simple); TLA+/0.957 / 8,566ms (complex)  
**Query (once variant run exists):**
```cypher
MATCH (s:SpecRun)
WHERE s.milestone IN ['m2', 'm2-clear-variant']
RETURN s.milestone, s.brief_label, s.selected_lang, avg(s.confidence), avg(s.justification_char_count)
ORDER BY s.brief_label, s.milestone
```
**What it proves:** Does CLEARSession's extra 27 tokens (142 vs 115) translate to
higher confidence or longer spec output? Tests whether token density ≈ output quality.  
**New question from M2 data:** Given that M2 lang selection is fully deterministic (0 variance),
does CLEARSession change the selection at all, or does it only affect justification length/confidence?

---

### OPP-4: PersonaLayer impact on SME output
**Available when:** M5 seeded (SME Agent active)  
**Query:**
```cypher
MATCH (r:SpecRun {milestone: 'm5'})
RETURN r.sme_domain, avg(r.confidence), avg(r.output_token_count)
ORDER BY r.sme_domain
```
**What it proves:** PersonaLayer has low expansion ratio (0.265) — does it still
drive meaningful variation in SME output across domains? If confidence is uniform
across domains, PersonaLayer may not be discriminating enough.

---

### OPP-5: Cross-milestone token composition stack
**Available when:** M2, M3, M4 all seeded  
**Query:**
```cypher
-- M1 framework token budget per milestone composition
-- Read from FrameworkLayer nodes, sum per milestone's framework set
MATCH (f:FrameworkLayer)
WHERE f.name IN ['COSTARPrompt', 'ConstitutionalAI']
RETURN f.name, f.output_token_est  -- M2 budget

MATCH (f:FrameworkLayer)
WHERE f.name IN ['COSTARPrompt', 'ChainOfThought', 'ConstitutionalAI']
RETURN f.name, f.output_token_est  -- M3 budget
```
**What it proves:** The cumulative framework token cost per milestone. Compare against
actual `input_token_count` from SpecRun nodes — the delta is the brief + context overhead.

---

### OPP-6: Build time baseline violation detection (ongoing)
**Available when:** Any new framework added to any milestone  
**Query:**
```cypher
MATCH (f:FrameworkLayer) RETURN f.name, f.build_time_ms ORDER BY f.build_time_ms DESC
```
**What it proves:** M1 baselines are all <0.1ms (pure Python, no IO).
Any new framework with build_time_ms > 1ms has unexpected IO or computation.
This is the anomaly detection baseline.

---

### OPP-7: File hash drift detection (A/B runs)
**Available when:** Any A/B run (same milestone, different model)  
**Query:**
```cypher
-- If a framework file changes between runs, hash won't match
-- Run this after seeding a second A/B variant
MATCH (f:FrameworkLayer)
RETURN f.name, f.file_hash, f.milestone_run
ORDER BY f.name, f.milestone_run
```
**What it proves:** If hashes differ across A/B runs for the same framework name,
the framework file changed between runs — the A/B comparison is not clean.

---

## Hypotheses to resolve

| ID | Hypothesis | Testable at | Status |
|---|---|---|---|
| H1 | ChainOfThought token density (175) correlates with reasoning depth in M3 output | M3 | **confirmed** — 6/6 per_concern, ≥5 named-candidate steps |
| H2 | PersonaLayer low expansion (0.265) → low impact on SME output variance | M5 | open |
| H3 | COSTAR vs CLEARSession in Structure slot produces measurable spec quality delta | M2-variant | open |
| H4 | ConstitutionalAI revision rate < 30% when confidence threshold ≥ 0.7 | M4 | open |
| H5 | M2→M3 token delta is dominated by ChainOfThought contribution (≈175 tokens) | M3 | **confirmed** — +175 exactly CoT; COSTAR unchanged |
| H6 | M3 CoT will narrow complex confidence range (0.040 → <0.020) via deliberate reasoning | M3 | **confirmed (exceeded)** — range = 0.000 |
| H7 | Complexity-latency inversion (complex faster than simple) persists at M3 | M3 | **refuted** — reversed; complex 2.6s slower due to more output tokens |
| H8 | M3 justification > M2 for complex, not simple | M3 | **refuted** — simple +16.8%, complex −1.2%; CoT front-loads complex into steps |
