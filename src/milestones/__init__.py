# Milestone snapshots — each subdirectory is a self-contained, frozen milestone.
# The files within are the thesis: the prompt structures, compositions, and agent
# behaviours that produced the GNN training signal at each proven layer.
#
# Directory convention:
#   m{N}/frameworks/   — prompt framework builders active at this milestone
#   m{N}/agents/       — agent code at this milestone's composition level
#   m{N}/graph/        — this milestone's Kuzu schema contribution + runner
#   m{N}/artifacts/    — raw JSON outputs from live execution at this milestone
#
# Snapshot tags in file headers:
#   [M1-origin | src/frameworks/foo.py]       — first appearance in M1
#   [M2-copy | identical to milestones/m1/frameworks/foo.py]  — unchanged copy
