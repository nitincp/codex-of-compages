-- M3 → M4 transform
-- SpecRun gains revised and revision_notes; backfill M3 rows with neutral values.
-- FrameworkLayer excluded — in reseed_tables, recreated from source code by reseed_frameworks.
-- CAPTURED_IN excluded — recreated by reseed_frameworks alongside FrameworkLayer nodes.
-- RevisionEvent excluded — new table; no M3 rows to carry forward.
-- VERIFICATION_ADDS excluded — new table; no M3 rows to carry forward.
-- REASONING_ADDS included — has data from M3 runs; must be carried forward.

-- MilestoneRun: identity
COPY (
  MATCH (n:MilestoneRun)
  RETURN n.run_id AS run_id, n.milestone AS milestone,
         n.model AS model, n.timestamp AS timestamp
) TO '{output_dir}/MilestoneRun.parquet'

-- SpecRun: M3 columns + backfill new M4 columns
-- revised=false: no CAI layer in M3 (COSTAR+CoT only) — revision not possible
-- revision_notes='': no CAI principle triggered in M3 runs — not applicable
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
         false AS revised,
         '' AS revision_notes
) TO '{output_dir}/SpecRun.parquet'

-- AnalysisNote: identity
COPY (
  MATCH (n:AnalysisNote)
  RETURN n.id AS id, n.session AS session, n.by AS by,
         n.subject AS subject, n.signal AS signal,
         n.value AS value, n.note AS note
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

-- REASONING_ADDS: carry forward M3 cross-schema edges with all properties
COPY (
  MATCH (s1:SpecRun)-[r:REASONING_ADDS]->(s2:SpecRun)
  RETURN s1.id AS src_id, s2.id AS dst_id,
         r.confidence_delta AS confidence_delta,
         r.step_count AS step_count,
         r.evaluation_depth AS evaluation_depth,
         r.adds_candidate_rejection AS adds_candidate_rejection
) TO '{output_dir}/REASONING_ADDS.parquet'
