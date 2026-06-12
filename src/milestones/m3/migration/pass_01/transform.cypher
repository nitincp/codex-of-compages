-- M3 pass 1: M2 → M3 structural migration (applies from M2-shaped source)
-- SpecRun gains reasoning_step_count and evaluation_depth; backfill M2 rows with neutral defaults.
-- AnalysisNote: identity — hypothesis-tracking columns not yet added.
-- REASONING_ADDS: new table in M3; no prior rows to carry forward.
-- FrameworkLayer/CAPTURED_IN excluded — in reseed_tables, recreated from source code.

-- MilestoneRun: identity
COPY (
  MATCH (n:MilestoneRun)
  RETURN n.run_id AS run_id, n.milestone AS milestone,
         n.model AS model, n.timestamp AS timestamp
) TO '{output_dir}/MilestoneRun.parquet'

-- SpecRun: M2 columns + backfill new M3 columns with neutral defaults
-- reasoning_step_count=0: M2 used COSTAR only — no CoT steps existed
-- evaluation_depth='unknown': CoT not present in M2; not applicable to those rows
COPY (
  MATCH (n:SpecRun)
  RETURN n.id AS id, n.run_id AS run_id, n.milestone AS milestone,
         n.brief_label AS brief_label, n.selected_lang AS selected_lang,
         n.layer AS layer, n.confidence AS confidence,
         n.justification_char_count AS justification_char_count,
         n.latency_ms AS latency_ms, n.model AS model,
         n.timestamp AS timestamp,
         0 AS reasoning_step_count,
         'unknown' AS evaluation_depth
) TO '{output_dir}/SpecRun.parquet'

-- AnalysisNote: identity (hypothesis-tracking columns added in pass 2)
COPY (
  MATCH (n:AnalysisNote)
  RETURN n.id AS id, n.session AS session, n.by AS by,
         n.subject AS subject, n.signal AS signal,
         n.value AS value, n.note AS note,
         'pre-m3' AS milestone,
         '' AS hypothesis_id,
         '' AS direction,
         0.0 AS metric_before,
         0.0 AS metric_after
) TO '{output_dir}/AnalysisNote.parquet'

-- SPEC_CAPTURED_IN: identity
COPY (
  MATCH (s:SpecRun)-[:SPEC_CAPTURED_IN]->(r:MilestoneRun)
  RETURN s.id AS src_id, r.run_id AS dst_id
) TO '{output_dir}/SPEC_CAPTURED_IN.parquet'

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
