-- M4 schema snapshot
-- All tables at M4: M3 tables unchanged + SpecRun extended with verification fields
--                  + RevisionEvent node + VERIFICATION_ADDS rel

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

-- SpecRun: M3 columns + M4 additions
-- revised: true if the CAI critique triggered a revision of lang selection or justification
-- revision_notes: the CAI principle that triggered revision (empty string if revised=false)
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
  reasoning_step_count INT64,
  evaluation_depth STRING,
  revised BOOLEAN,
  revision_notes STRING,
  PRIMARY KEY (id)
);

CREATE REL TABLE SPEC_CAPTURED_IN (FROM SpecRun TO MilestoneRun);

-- AnalysisNote: unchanged from M2
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

CREATE REL TABLE ANALYZED (FROM AnalysisNote TO FrameworkLayer);
CREATE REL TABLE ANALYZED_RUN (FROM AnalysisNote TO MilestoneRun);
CREATE REL TABLE ANALYZED_SPEC (FROM AnalysisNote TO SpecRun);

-- M3 cross-schema edge (unchanged)
CREATE REL TABLE REASONING_ADDS (
  FROM SpecRun TO SpecRun,
  confidence_delta DOUBLE,
  step_count INT64,
  evaluation_depth STRING,
  adds_candidate_rejection BOOLEAN
);

-- M4 addition: records each CAI critique-revision cycle outcome per brief per run
CREATE NODE TABLE RevisionEvent (
  id STRING,
  run_id STRING,
  brief_label STRING,
  revised BOOLEAN,
  cai_principle_triggered STRING,
  assumption_inventory_added BOOLEAN,
  PRIMARY KEY (id)
);

-- M4 addition: cross-schema edge M3 SpecRun → M4 SpecRun (same brief_label)
-- Carries the delta produced by adding the ConstitutionalAI verification layer
CREATE REL TABLE VERIFICATION_ADDS (
  FROM SpecRun TO SpecRun,
  revised BOOLEAN,
  confidence_delta DOUBLE,
  cai_principle_triggered STRING,
  signal_count_below_threshold INT64,
  assumption_inventory_added BOOLEAN
);
