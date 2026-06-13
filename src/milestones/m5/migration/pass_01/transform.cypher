-- M5 migration: M4 → M5 structural migration (applies from M4-shaped source)
-- SpecRun gains specialist_crispe_prompt STRING; backfill M0-M4 rows with ''.
-- MetaPromptEvent, META_PROMPT_ADDS, ANALYZED_META are new empty tables — no COPY blocks.
-- FrameworkLayer excluded — in reseed_tables, recreated from source code.

-- MilestoneRun: identity
COPY (
  MATCH (n:MilestoneRun)
  RETURN n.run_id AS run_id, n.milestone AS milestone,
         n.model AS model, n.timestamp AS timestamp
) TO '{output_dir}/MilestoneRun.parquet'

-- SpecRun: M4 columns + backfill new M5 column with neutral default
-- specialist_crispe_prompt='': M0-M4 rows had no CRISPE generation step.
--   Pre-M5 rows default to empty string. Not comparable to M5 rows.
--   Filter by milestone in GNN queries to avoid mixing.
COPY (
  MATCH (n:SpecRun)
  RETURN n.id AS id, n.run_id AS run_id, n.milestone AS milestone,
         n.brief_label AS brief_label, n.selected_lang AS selected_lang,
         n.layer AS layer, n.confidence AS confidence,
         n.justification_char_count AS justification_char_count,
         n.latency_ms AS latency_ms, n.model AS model,
         n.timestamp AS timestamp,
         n.reasoning_step_count AS reasoning_step_count,
         n.evaluation_depth AS evaluation_depth,
         n.revised AS revised,
         n.revision_notes AS revision_notes,
         '' AS specialist_crispe_prompt
) TO '{output_dir}/SpecRun.parquet'

-- AnalysisNote: identity (read all M4 columns directly)
COPY (
  MATCH (n:AnalysisNote)
  RETURN n.id AS id, n.session AS session, n.by AS by,
         n.subject AS subject, n.signal AS signal,
         n.value AS value, n.note AS note,
         n.milestone AS milestone,
         n.hypothesis_id AS hypothesis_id,
         n.direction AS direction,
         n.metric_before AS metric_before,
         n.metric_after AS metric_after
) TO '{output_dir}/AnalysisNote.parquet'

-- RevisionEvent: identity (unchanged in M5)
COPY (
  MATCH (n:RevisionEvent)
  RETURN n.id AS id, n.run_id AS run_id, n.brief_label AS brief_label,
         n.revised AS revised,
         n.cai_principle_triggered AS cai_principle_triggered,
         n.assumption_inventory_added AS assumption_inventory_added
) TO '{output_dir}/RevisionEvent.parquet'

-- SPEC_CAPTURED_IN: identity
COPY (
  MATCH (s:SpecRun)-[:SPEC_CAPTURED_IN]->(r:MilestoneRun)
  RETURN s.id AS src_id, r.run_id AS dst_id
) TO '{output_dir}/SPEC_CAPTURED_IN.parquet'

-- REASONING_ADDS: carry forward cross-schema edges
COPY (
  MATCH (m2:SpecRun)-[e:REASONING_ADDS]->(m3:SpecRun)
  RETURN m2.id AS src_id, m3.id AS dst_id,
         e.confidence_delta AS confidence_delta,
         e.step_count AS step_count,
         e.evaluation_depth AS evaluation_depth,
         e.adds_candidate_rejection AS adds_candidate_rejection
) TO '{output_dir}/REASONING_ADDS.parquet'

-- VERIFICATION_ADDS: carry forward cross-schema edges
COPY (
  MATCH (m3:SpecRun)-[e:VERIFICATION_ADDS]->(m4:SpecRun)
  RETURN m3.id AS src_id, m4.id AS dst_id,
         e.revised AS revised,
         e.confidence_delta AS confidence_delta,
         e.cai_principle_triggered AS cai_principle_triggered,
         e.signal_count_below_threshold AS signal_count_below_threshold,
         e.assumption_inventory_added AS assumption_inventory_added
) TO '{output_dir}/VERIFICATION_ADDS.parquet'

-- ANALYZED: AnalysisNote → FrameworkLayer
COPY (
  MATCH (a:AnalysisNote)-[:ANALYZED]->(f:FrameworkLayer)
  RETURN a.id AS src_id, f.id AS dst_id
) TO '{output_dir}/ANALYZED.parquet'

-- ANALYZED_RUN: AnalysisNote → MilestoneRun
COPY (
  MATCH (a:AnalysisNote)-[:ANALYZED_RUN]->(r:MilestoneRun)
  RETURN a.id AS src_id, r.run_id AS dst_id
) TO '{output_dir}/ANALYZED_RUN.parquet'

-- ANALYZED_SPEC: AnalysisNote → SpecRun
COPY (
  MATCH (a:AnalysisNote)-[:ANALYZED_SPEC]->(s:SpecRun)
  RETURN a.id AS src_id, s.id AS dst_id
) TO '{output_dir}/ANALYZED_SPEC.parquet'

-- MetaPromptEvent: new in M5 — no COPY block (no source data to carry forward)
-- META_PROMPT_ADDS: new in M5 — no COPY block
-- ANALYZED_META: new in M5 — no COPY block
