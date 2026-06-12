-- M2 schema snapshot
-- All tables at M2: M1 tables unchanged + M2 additions + ad-hoc AnalysisNote from Claude analysis

-- M1 tables (unchanged)
CREATE NODE TABLE MilestoneRun (
  run_id STRING,
  milestone STRING,
  model STRING,
  timestamp STRING,
  PRIMARY KEY (run_id)
);

CREATE NODE TABLE FrameworkLayer (
  id STRING,
  name STRING,
  run_id STRING,
  dimension STRING,
  build_output STRING,
  file_path STRING,
  file_hash STRING,
  file_size_bytes INT64,
  build_time_ms DOUBLE,
  output_char_count INT64,
  output_token_est INT64,
  PRIMARY KEY (id)
);

CREATE REL TABLE CAPTURED_IN (FROM FrameworkLayer TO MilestoneRun);

-- M2 additions: SpecRun seeded by M2 runner
CREATE NODE TABLE SpecRun (
  id STRING,
  run_id STRING,
  milestone STRING,
  brief_label STRING,
  selected_lang STRING,
  layer STRING,
  confidence DOUBLE,
  justification_char_count INT64,
  latency_ms DOUBLE,
  model STRING,
  timestamp STRING,
  PRIMARY KEY (id)
);

-- M2 uses a distinct rel name to avoid Kuzu 0.11.3 single-FROM-type constraint on CAPTURED_IN
CREATE REL TABLE SPEC_CAPTURED_IN (FROM SpecRun TO MilestoneRun);

-- AnalysisNote: ad-hoc schema created by Claude during M1+M2 analysis sessions.
-- Columns: id, session, by, subject, signal, value, note (introspected 2026-06-12).
-- Future sessions may add columns; migrate.py discovers schema at runtime via CALL table_info().
CREATE NODE TABLE AnalysisNote (
  id STRING,
  session STRING,
  by STRING,
  subject STRING,
  signal STRING,
  value STRING,
  note STRING,
  PRIMARY KEY (id)
);

-- AnalysisNote rel tables created during M1+M2 analysis
CREATE REL TABLE ANALYZED (FROM AnalysisNote TO FrameworkLayer);
CREATE REL TABLE ANALYZED_RUN (FROM AnalysisNote TO MilestoneRun);
CREATE REL TABLE ANALYZED_SPEC (FROM AnalysisNote TO SpecRun);
