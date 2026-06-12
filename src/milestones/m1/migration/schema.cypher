-- M1 schema snapshot
-- Tables owned by M1: MilestoneRun, FrameworkLayer, CAPTURED_IN

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
