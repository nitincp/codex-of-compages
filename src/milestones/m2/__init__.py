# M2 — Layer 1 PoC: Spec Advisor, COSTAR-only composition
#
# What this milestone proves: the M2 Spec Advisor (COSTAR structure layer only)
# produces SpecRun nodes in the GNN. Multiple runs accumulate distinct subgraphs.
# OPP-3 (COSTAR baseline confidence distribution) becomes queryable.
#
# GNN contribution: SpecRun nodes — one per agent call.
# Node features: selected_lang, layer, confidence, justification_char_count, latency_ms.
# SPEC_CAPTURED_IN edges anchor each SpecRun to its MilestoneRun.
