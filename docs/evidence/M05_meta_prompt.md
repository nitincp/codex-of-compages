# M05 — Layer 4 PoC: Full Spec Advisor — Meta-Prompt Output

## Hypothesis

The Spec Advisor (COSTAR + CoT + CAI — M4 chain, unchanged) can programmatically generate a
CRISPE meta-prompt from its structured output. That prompt, injected into a Spec Specialist stub
as its system prompt, produces a non-empty formal spec. All 6 CRISPE fields are populated and
non-empty for all 3 briefs. The `capacity` field reliably names the selected language. The
`insight` field (filled from the Advisor's justification) provides sufficient grounding for the
Specialist — measurably richer for strong briefs than for vague ones.

Secondary hypothesis: M5 is the first milestone where all 3 briefs have a cross-schema edge
(`META_PROMPT_ADDS`). Vague was excluded from `VERIFICATION_ADDS` (M4) because M3 had no vague
run; M4 seeded a vague `SpecRun`, so M5 can link all 3.

## Method

1. Extend M4 `SpecAdvisorOutput` with `specialist_crispe_prompt: str` (appended in `run()`, not
   from the LLM tool call).
2. `build_crispe_prompt(output)` fills `CRISPEPrompt` with:
   - `capacity = "{selected_lang} specialist"`
   - `role` = fixed council role
   - `insight = output.justification`
   - `statement` = scoped to `output.layer`
   - `personality`, `experiment` = `CRISPEPrompt` defaults
3. `SpecSpecialistAgent` receives the CRISPE string as its system prompt at call time (no
   `ComposedPrompt` chain). Forced tool-use returns `SpecialistOutput`.
4. GNN: `MetaPromptEvent` node per brief captures CRISPE quality signals. `META_PROMPT_ADDS`
   cross-schema edge (M4 `SpecRun` → M5 `SpecRun`) carries structural signals per brief.
5. Run gate tests (ephemeral DB, mocked outputs). Then Claude-in-loop: 3 CLI runs, ad-hoc
   Cypher analysis of `MetaPromptEvent` nodes, `AnalysisNote` written via `ANALYZED_META` edges.

## Gate Tests

- Schema: `MetaPromptEvent`, `META_PROMPT_ADDS`, `ANALYZED_META` tables created correctly.
- `SpecRun.specialist_crispe_prompt` non-empty for all 3 briefs.
- CRISPE prompt contains all 6 section headers (`**Capacity**` … `**Experiment**`).
- `crispe_field_count == 6` for all 3 briefs.
- `capacity_matches_lang=True` for all 3 briefs.
- `insight_char_count > 50` for simple + complex.
- Vague `insight_char_count` < complex `insight_char_count`.
- `META_PROMPT_ADDS` edge present for all 3 briefs (first full cross-schema coverage).
- Edge `crispe_field_count` and `capacity_matches_lang` match node values.
- 3-hop topology query (`REASONING_ADDS → VERIFICATION_ADDS → META_PROMPT_ADDS`):
  - Strong briefs (simple, complex) in results.
  - Vague absent — no `VERIFICATION_ADDS` path reaches the vague `SpecRun`.
- Integration (1 `@pytest.mark.integration`): `SpecSpecialistAgent` called with complex CRISPE
  → `spec_content` non-empty, `spec_lang` matches `selected_lang`.
- Regression: 74 prior tests (M1+M2+M3+ETL+M4) green.

## Result

_To be filled at milestone end._

## Lessons

_To be filled at milestone end._

## Next Layer Can Rely On

_To be filled at milestone end._
