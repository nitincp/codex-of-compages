-- M3 schema snapshot
-- All tables at M3: SpecRun extended with reasoning fields + AnalysisNote extended with
-- hypothesis tracking fields + REASONING_ADDS cross-schema edge

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

-- SpecRun: M2 columns + M3 additions
-- reasoning_step_count: number of CoT steps the agent produced (M3 adds ChainOfThought)
-- evaluation_depth: 'per_concern' | 'aggregate' — granularity of CoT reasoning steps
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
  PRIMARY KEY (id)
);

CREATE REL TABLE SPEC_CAPTURED_IN (FROM SpecRun TO MilestoneRun);

-- AnalysisNote: M2 columns + M3 additions
-- milestone:       which milestone this analysis pertains to ('m1', 'm2', 'm3', ...)
-- hypothesis_id:   hypothesis being tested ('H1', 'H5', ...) or '' for new signals
-- direction:       'confirmed' | 'refuted' | 'new' | '' — outcome of hypothesis test
-- metric_before:   numeric value before the milestone layer was added (e.g. M2 conf_range)
-- metric_after:    numeric value after the milestone layer was added (e.g. M3 conf_range)
CREATE NODE TABLE AnalysisNote (
  id STRING,
  session STRING,
  by STRING,
  subject STRING,
  signal STRING,
  value STRING,
  note STRING,
  milestone STRING,
  hypothesis_id STRING,
  direction STRING,
  metric_before DOUBLE,
  metric_after DOUBLE,
  PRIMARY KEY (id)
);

CREATE REL TABLE ANALYZED (FROM AnalysisNote TO FrameworkLayer);
CREATE REL TABLE ANALYZED_RUN (FROM AnalysisNote TO MilestoneRun);
CREATE REL TABLE ANALYZED_SPEC (FROM AnalysisNote TO SpecRun);

-- M3 addition: cross-schema edge M2 SpecRun → M3 SpecRun (same brief_label)
-- Carries the delta signal produced by adding the ChainOfThought reasoning layer
CREATE REL TABLE REASONING_ADDS (
  FROM SpecRun TO SpecRun,
  confidence_delta DOUBLE,
  step_count INT64,
  evaluation_depth STRING,
  adds_candidate_rejection BOOLEAN
);
