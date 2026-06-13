"""
M5 Claude-in-loop: persist AnalysisNote nodes + ANALYZED_META edges.
7 findings from the 3-run analysis (2026-06-13).

Run: python3 scripts/m5_persist_notes.py
"""
import os

import kuzu

KUZU_DB_PATH = os.environ.get("KUZU_DB_PATH", "data/kuzu")
SESSION = "2026-06-13"
BY = "claude-sonnet-4-6"
VALID_RUNS = ["m5-20260613-224118", "m5-20260613-224509", "m5-20260613-224727"]

NOTES = [
    {
        "id": "m5-crispe-structural-invariant",
        "subject": "MetaPromptEvent.crispe_field_count + capacity_matches_lang",
        "signal": "crispe_field_count",
        "value": "6",
        "note": (
            "crispe_field_count=6 and capacity_matches_lang=True for all 3 briefs across "
            "all 3 runs (9/9 MetaPromptEvent nodes). The CRISPE builder is structurally "
            "invariant — no missing sections, no capacity/lang mismatch. Gate test invariant "
            "confirmed under real LLM outputs."
        ),
        "milestone": "m5",
        "hypothesis_id": "",
        "direction": "confirmed",
        "metric_before": 0.0,
        "metric_after": 6.0,
    },
    {
        "id": "m5-confidence-zero-variance",
        "subject": "SpecRun.confidence per brief across 3 runs",
        "signal": "confidence_range",
        "value": "0.000 for all 3 briefs",
        "note": (
            "All 3 briefs show 0.000 confidence range across 3 M5 runs: complex=0.950, "
            "simple=0.950, vague=0.400. This is stronger than M3 (complex=0.000, simple "
            "varied) and M4 (complex=0.000, simple=0.000, vague=0.150). The full COSTAR + "
            "CoT + CAI + CRISPE chain locks confidence tighter than any prior milestone."
        ),
        "milestone": "m5",
        "hypothesis_id": "",
        "direction": "confirmed",
        "metric_before": 0.150,
        "metric_after": 0.0,
    },
    {
        "id": "m5-insight-ordering",
        "subject": "MetaPromptEvent.insight_char_count per brief",
        "signal": "insight_char_count",
        "value": "complex=1222, simple=851, vague=754 (averages)",
        "note": (
            "Insight char ordering: complex (avg 1222, range 149) >> simple (avg 851, range 29) "
            "> vague (avg 754, range 207). Simple is most stable (29-char range, 3.4% variance). "
            "Vague is most variable (207-char range, 27.5% variance) — low-signal briefs produce "
            "unstable justifications. Complex-to-vague ratio: 1.62× on average insight length."
        ),
        "milestone": "m5",
        "hypothesis_id": "H_META_insight",
        "direction": "confirmed",
        "metric_before": 0.0,
        "metric_after": 1.62,
    },
    {
        "id": "m5-statement-uniformity",
        "subject": "MetaPromptEvent.statement_char_count across all briefs",
        "signal": "statement_char_count",
        "value": "194 (identical for all 9 MetaPromptEvent nodes)",
        "note": (
            "Statement section is 194 chars for all 3 briefs across all 3 runs. "
            "It is template-driven ('Produce a formal specification targeting the {layer} "
            "layer...'), not content-driven. Since layer is deterministic per brief, statement "
            "is also deterministic. Capacity section is similarly short: 15 chars for complex, "
            "18 for simple/vague (just '{lang} specialist'). The Insight section is the sole "
            "variable-length field and carries all brief-specific information."
        ),
        "milestone": "m5",
        "hypothesis_id": "",
        "direction": "confirmed",
        "metric_before": 0.0,
        "metric_after": 194.0,
    },
    {
        "id": "m5-vague-revision-lock",
        "subject": "SpecRun.revised for vague brief at M5 vs M4",
        "signal": "revision_rate",
        "value": "100% at both M4 and M5",
        "note": (
            "Vague brief: revised=True for all 3 M5 runs (conf=0.400, 0.000 range). "
            "M4 vague: revised=True, conf range 0.350–0.500. M5 confidence is more stable "
            "than M4 (range 0.000 vs 0.150) — adding the CRISPE generation step appears to "
            "stabilize CAI output for vague briefs. Language selection: OpenAPI/api in all "
            "M4 and M5 runs (mock fixtures used JSON Schema/domain — real behavior differs)."
        ),
        "milestone": "m5",
        "hypothesis_id": "H4",
        "direction": "confirmed",
        "metric_before": 0.150,
        "metric_after": 0.0,
    },
    {
        "id": "m5-crispe-prompt-length-ordering",
        "subject": "META_PROMPT_ADDS.prompt_char_count per brief",
        "signal": "prompt_char_count",
        "value": "complex=1859, simple=1491, vague=1394 (averages)",
        "note": (
            "CRISPE prompt length ordering: complex (avg 1859, 8.0% variance) > simple "
            "(avg 1491, 1.9% variance) > vague (avg 1394, 14.8% variance). Vague has the "
            "shortest prompt AND highest variance — both driven by the variable-length Insight "
            "section (which carries justification text). Simple is most stable (1.9%). Prompt "
            "length correlates with brief complexity: complex Insight (~1222 chars) vs vague "
            "Insight (~754 chars). The CRISPE wrapper adds ~600-700 chars of fixed scaffolding."
        ),
        "milestone": "m5",
        "hypothesis_id": "",
        "direction": "confirmed",
        "metric_before": 0.0,
        "metric_after": 1859.0,
    },
    {
        "id": "m5-3hop-topology-confirmed",
        "subject": "3-hop topology: REASONING_ADDS → VERIFICATION_ADDS → META_PROMPT_ADDS",
        "signal": "path_count",
        "value": "simple + complex reachable; vague absent",
        "note": (
            "3-hop topology confirmed across 3 M5 runs: REASONING_ADDS (M2→M3) → "
            "VERIFICATION_ADDS (M3→M4) → META_PROMPT_ADDS (M4→M5) reaches simple and complex "
            "M5 SpecRuns. Vague is absent because no VERIFICATION_ADDS edge points to the "
            "vague M4 SpecRun (vague was not run at M3). Cumulative confidence delta ≈ 0 "
            "(complex=0.000, simple=-0.010) — the delta signal lives in step_count and "
            "evaluation_depth, established at M3. OPP-8 topology-based retrieval is valid "
            "end-to-end: the 4-layer chain (M2→M3→M4→M5) is traversable by graph query."
        ),
        "milestone": "m5",
        "hypothesis_id": "OPP-8",
        "direction": "confirmed",
        "metric_before": 0.0,
        "metric_after": 1.0,
    },
]


def main():
    db = kuzu.Database(KUZU_DB_PATH)
    conn = kuzu.Connection(db)

    # Ensure AnalysisNote table exists (M3 schema, already migrated)
    conn.execute(
        "CREATE NODE TABLE IF NOT EXISTS AnalysisNote ("
        "id STRING, session STRING, by STRING, subject STRING, "
        "signal STRING, value STRING, note STRING, milestone STRING, "
        "hypothesis_id STRING, direction STRING, "
        "metric_before DOUBLE, metric_after DOUBLE, "
        "PRIMARY KEY (id))"
    )
    conn.execute(
        "CREATE REL TABLE IF NOT EXISTS ANALYZED_META (FROM AnalysisNote TO MetaPromptEvent)"
    )

    created = 0
    skipped = 0
    for note_data in NOTES:
        # Idempotent — skip if already exists
        existing = conn.execute(
            "MATCH (n:AnalysisNote {id: $id}) RETURN count(n)",
            parameters={"id": note_data["id"]},
        ).get_all()
        if existing and existing[0][0] > 0:
            print(f"  skip (exists): {note_data['id']}")
            skipped += 1
            continue

        conn.execute(
            "CREATE (:AnalysisNote {"
            "id: $id, session: $session, by: $by, subject: $subject, "
            "signal: $signal, value: $value, note: $note, milestone: $milestone, "
            "hypothesis_id: $hypothesis_id, direction: $direction, "
            "metric_before: $metric_before, metric_after: $metric_after})",
            parameters={**note_data, "session": SESSION, "by": BY},
        )
        print(f"  created: {note_data['id']}")
        created += 1

        # Link to MetaPromptEvent nodes for the 3 valid runs
        for run_id in VALID_RUNS:
            for brief in ["simple", "complex", "vague"]:
                meta_id = f"{run_id}:{brief}"
                res = conn.execute(
                    "MATCH (e:MetaPromptEvent {id: $mid}) RETURN count(e)",
                    parameters={"mid": meta_id},
                )
                if res.get_all()[0][0] > 0:
                    conn.execute(
                        "MATCH (a:AnalysisNote {id: $aid}), (e:MetaPromptEvent {id: $mid}) "
                        "CREATE (a)-[:ANALYZED_META]->(e)",
                        parameters={"aid": note_data["id"], "mid": meta_id},
                    )

    print(f"\nDone: {created} created, {skipped} skipped")

    # Verify
    res = conn.execute(
        "MATCH (a:AnalysisNote {milestone: 'm5'}) RETURN a.id, a.direction ORDER BY a.id"
    )
    rows = res.get_all()
    print(f"\nM5 AnalysisNote nodes ({len(rows)} total):")
    for row in rows:
        print(f"  {row[0]}  [{row[1]}]")

    res2 = conn.execute(
        "MATCH (a:AnalysisNote)-[:ANALYZED_META]->(e:MetaPromptEvent) "
        "RETURN count(*)"
    )
    edge_count = res2.get_all()[0][0]
    print(f"\nANALYZED_META edges written: {edge_count}")

    conn.close()
    db.close()


if __name__ == "__main__":
    main()
