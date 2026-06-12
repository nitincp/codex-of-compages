-- M3 pass 2: AnalysisNote schema evolution (applies from M3-shaped source — after pass 1)
-- SpecRun: reads existing M3 values directly (reasoning_step_count, evaluation_depth present).
-- AnalysisNote: backfills new hypothesis-tracking columns (milestone, hypothesis_id, direction,
--   metric_before, metric_after) for pre-M3 notes.
-- REASONING_ADDS: carries forward live cross-schema edges (present in M3 source).

-- MilestoneRun: identity
COPY (
  MATCH (n:MilestoneRun)
  RETURN n.run_id AS run_id, n.milestone AS milestone,
         n.model AS model, n.timestamp AS timestamp
) TO '{output_dir}/MilestoneRun.parquet'

-- SpecRun: read all M3 columns directly — no hardcoded backfill.
-- Source is M3-shaped: reasoning_step_count and evaluation_depth already exist.
COPY (
  MATCH (n:SpecRun)
  RETURN n.id AS id, n.run_id AS run_id, n.milestone AS milestone,
         n.brief_label AS brief_label, n.selected_lang AS selected_lang,
         n.layer AS layer, n.confidence AS confidence,
         n.justification_char_count AS justification_char_count,
         n.latency_ms AS latency_ms, n.model AS model,
         n.timestamp AS timestamp,
         n.reasoning_step_count AS reasoning_step_count,
         n.evaluation_depth AS evaluation_depth
) TO '{output_dir}/SpecRun.parquet'

-- AnalysisNote: carry existing columns + backfill new hypothesis-tracking columns.
-- Pre-M3 notes already in the DB at pass-2 time get neutral backfill values.
-- milestone='pre-m3': cannot infer milestone from pre-M3 note id prefix
-- hypothesis_id='': pre-M3 notes were not written against a named hypothesis
-- direction='': not applicable to pre-M3 ad-hoc notes
-- metric_before/after=0.0: pre-M3 notes did not capture numeric deltas
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

-- REASONING_ADDS: carry forward live cross-schema edges (exist in M3 source)
COPY (
  MATCH (m2:SpecRun)-[e:REASONING_ADDS]->(m3:SpecRun)
  RETURN m2.id AS src_id, m3.id AS dst_id,
         e.confidence_delta AS confidence_delta,
         e.step_count AS step_count,
         e.evaluation_depth AS evaluation_depth,
         e.adds_candidate_rejection AS adds_candidate_rejection
) TO '{output_dir}/REASONING_ADDS.parquet'

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
