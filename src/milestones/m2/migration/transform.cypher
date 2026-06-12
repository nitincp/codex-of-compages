-- Transform: m1 → m2
-- M1 tables: MilestoneRun (identity), FrameworkLayer (in reseed_tables — excluded here)
-- M2 additions: SpecRun, AnalysisNote exported as-is (new tables, no structural change)
-- Rel tables: SPEC_CAPTURED_IN, ANALYZED, ANALYZED_RUN, ANALYZED_SPEC
-- CAPTURED_IN is excluded — re-created by reseed_frameworks() for FrameworkLayer nodes.

-- MilestoneRun: identity (irreplaceable — timestamps and run provenance)
COPY (
  MATCH (n:MilestoneRun)
  RETURN n.run_id AS run_id, n.milestone AS milestone,
         n.model AS model, n.timestamp AS timestamp
) TO '{output_dir}/MilestoneRun.parquet'

-- SpecRun: new in m2 — identity export
COPY (
  MATCH (n:SpecRun)
  RETURN n.id AS id, n.run_id AS run_id, n.milestone AS milestone,
         n.brief_label AS brief_label, n.selected_lang AS selected_lang,
         n.layer AS layer, n.confidence AS confidence,
         n.justification_char_count AS justification_char_count,
         n.latency_ms AS latency_ms, n.model AS model, n.timestamp AS timestamp
) TO '{output_dir}/SpecRun.parquet'

-- AnalysisNote: ad-hoc schema (id, session, by, subject, signal, value, note at m2).
-- Column list matches schema introspected 2026-06-12. Future columns added in new sessions
-- require updating this file before running the next migration.
COPY (
  MATCH (n:AnalysisNote)
  RETURN n.id AS id, n.session AS session, n.by AS by,
         n.subject AS subject, n.signal AS signal,
         n.value AS value, n.note AS note
) TO '{output_dir}/AnalysisNote.parquet'

-- SPEC_CAPTURED_IN: SpecRun → MilestoneRun anchoring edges
COPY (
  MATCH (s:SpecRun)-[:SPEC_CAPTURED_IN]->(r:MilestoneRun)
  RETURN s.id AS src_id, r.run_id AS dst_id
) TO '{output_dir}/SPEC_CAPTURED_IN.parquet'

-- ANALYZED: AnalysisNote → FrameworkLayer (M1 analysis signal edges — 108 edges at m2)
COPY (
  MATCH (a:AnalysisNote)-[:ANALYZED]->(f:FrameworkLayer)
  RETURN a.id AS src_id, f.id AS dst_id
) TO '{output_dir}/ANALYZED.parquet'

-- ANALYZED_RUN: AnalysisNote → MilestoneRun (M2 analysis cross-run signal — 20 edges at m2)
COPY (
  MATCH (a:AnalysisNote)-[:ANALYZED_RUN]->(r:MilestoneRun)
  RETURN a.id AS src_id, r.run_id AS dst_id
) TO '{output_dir}/ANALYZED_RUN.parquet'

-- ANALYZED_SPEC: AnalysisNote → SpecRun (M2 analysis spec signal — 30 edges at m2)
COPY (
  MATCH (a:AnalysisNote)-[:ANALYZED_SPEC]->(s:SpecRun)
  RETURN a.id AS src_id, s.id AS dst_id
) TO '{output_dir}/ANALYZED_SPEC.parquet'
