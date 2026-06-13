-- M4 migration: M3 → M4 structural migration (applies from M3-shaped source)
-- SpecRun gains revised and revision_notes; backfill M3 rows with neutral defaults.
-- RevisionEvent and VERIFICATION_ADDS are new empty tables — not exported (skipped in loader).
-- FrameworkLayer excluded — in reseed_tables, recreated from source code.

-- MilestoneRun: identity
COPY (
  MATCH (n:MilestoneRun)
  RETURN n.run_id AS run_id, n.milestone AS milestone,
         n.model AS model, n.timestamp AS timestamp
) TO '{output_dir}/MilestoneRun.parquet'

-- SpecRun: M3 columns + backfill new M4 columns with neutral defaults
-- revised=false: M3 used COSTAR+CoT only — no CAI verification layer existed
-- revision_notes='': no CAI critique occurred for pre-M4 rows
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

-- AnalysisNote: identity (read all M3 columns directly)
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
