-- Transform: m1 baseline
-- source_milestone: null — m1 is the origin; no prior schema to transform from.
-- When migrating FROM m1 to a later milestone, these queries export m1 data.
-- FrameworkLayer is in reseed_tables — no COPY block here; re-seeded from source code
-- by migrate.py via reseed_frameworks(). CAPTURED_IN is also excluded; re-created during reseed.

-- MilestoneRun: identity export (irreplaceable — contains per-run timestamps)
COPY (
  MATCH (n:MilestoneRun)
  RETURN n.run_id AS run_id, n.milestone AS milestone,
         n.model AS model, n.timestamp AS timestamp
) TO '{output_dir}/MilestoneRun.parquet'
