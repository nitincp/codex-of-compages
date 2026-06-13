"""
M5 ad-hoc analysis — CRISPE quality signals across 3 valid runs.
Valid runs: m5-20260613-224118, m5-20260613-224509, m5-20260613-224727

Run: python3 scripts/m5_analysis.py
"""
import os

import kuzu

KUZU_DB_PATH = os.environ.get("KUZU_DB_PATH", "data/kuzu")
VALID_RUNS = ["m5-20260613-224118", "m5-20260613-224509", "m5-20260613-224727"]


def q(conn, cypher, params=None):
    res = conn.execute(cypher, parameters=params or {})
    if isinstance(res, list):
        rows = []
        for r in res:
            rows.extend(r.get_all())
        return rows
    return res.get_all()


def main():
    db = kuzu.Database(KUZU_DB_PATH)
    conn = kuzu.Connection(db)

    print("=" * 70)
    print("=== 1. SpecRun signals per brief across 3 valid runs ===")
    rows = q(
        conn,
        "MATCH (s:SpecRun) WHERE s.milestone = 'm5' AND s.run_id IN $runs "
        "RETURN s.brief_label, s.selected_lang, s.layer, s.confidence, "
        "s.reasoning_step_count, s.revised, s.latency_ms "
        "ORDER BY s.brief_label, s.run_id",
        {"runs": VALID_RUNS},
    )
    print(
        f"{'brief':<10} {'lang':<14} {'layer':<12} {'conf':>5} "
        f"{'steps':>6} {'revised':>8} {'ms':>8}"
    )
    print("-" * 70)
    for brief, lang, layer, conf, steps, revised, ms in rows:
        print(
            f"{brief:<10} {lang:<14} {layer:<12} {conf:>5.2f} "
            f"{steps:>6} {str(revised):>8} {ms:>8.0f}"
        )

    print()
    print("=== 2. Aggregated SpecRun stats per brief ===")
    rows2 = q(
        conn,
        "MATCH (s:SpecRun) WHERE s.milestone = 'm5' AND s.run_id IN $runs "
        "RETURN s.brief_label, "
        "avg(s.confidence) AS avg_conf, min(s.confidence) AS min_conf, "
        "max(s.confidence) AS max_conf, "
        "avg(s.latency_ms) AS avg_ms, min(s.latency_ms) AS min_ms, max(s.latency_ms) AS max_ms "
        "ORDER BY s.brief_label",
        {"runs": VALID_RUNS},
    )
    print(f"{'brief':<10} {'avg_conf':>9} {'conf_rng':>9} {'avg_ms':>8} {'ms_range':>10}")
    print("-" * 55)
    for brief, avg_c, min_c, max_c, avg_ms, min_ms, max_ms in rows2:
        print(
            f"{brief:<10} {avg_c:>9.3f} {max_c - min_c:>9.3f} "
            f"{avg_ms:>8.0f} {max_ms - min_ms:>10.0f}"
        )

    print()
    print("=== 3. MetaPromptEvent insight_char per brief (ordered by run) ===")
    rows3 = q(
        conn,
        "MATCH (e:MetaPromptEvent) WHERE e.run_id IN $runs "
        "RETURN e.brief_label, e.run_id, e.insight_char_count, "
        "e.capacity_char_count, e.statement_char_count, e.capacity_matches_lang "
        "ORDER BY e.brief_label, e.run_id",
        {"runs": VALID_RUNS},
    )
    print(
        f"{'brief':<10} {'run_suffix':<12} {'ins_chars':>9} "
        f"{'cap_chars':>9} {'stmt_chars':>10} {'cap_match':>9}"
    )
    print("-" * 65)
    for brief, run_id, ins, cap, stmt, cm in rows3:
        short = run_id[-6:]
        print(
            f"{brief:<10} ...{short:<9} {ins:>9} {cap:>9} {stmt:>10} {str(cm):>9}"
        )

    print()
    print("=== 4. Aggregated MetaPromptEvent stats per brief ===")
    rows4 = q(
        conn,
        "MATCH (e:MetaPromptEvent) WHERE e.run_id IN $runs "
        "RETURN e.brief_label, "
        "avg(e.insight_char_count) AS avg_ins, min(e.insight_char_count) AS min_ins, "
        "max(e.insight_char_count) AS max_ins, "
        "avg(e.capacity_char_count) AS avg_cap, "
        "avg(e.statement_char_count) AS avg_stmt "
        "ORDER BY e.brief_label",
        {"runs": VALID_RUNS},
    )
    print(
        f"{'brief':<10} {'avg_ins':>8} {'ins_min':>8} {'ins_max':>8} "
        f"{'ins_range':>10} {'avg_cap':>8} {'avg_stmt':>9}"
    )
    print("-" * 70)
    for brief, avg_ins, min_ins, max_ins, avg_cap, avg_stmt in rows4:
        print(
            f"{brief:<10} {avg_ins:>8.0f} {min_ins:>8} {max_ins:>8} "
            f"{max_ins - min_ins:>10} {avg_cap:>8.0f} {avg_stmt:>9.0f}"
        )

    print()
    print("=== 5. CRISPE prompt length via META_PROMPT_ADDS edge ===")
    rows5 = q(
        conn,
        "MATCH (m4:SpecRun)-[e:META_PROMPT_ADDS]->(m5:SpecRun) "
        "WHERE m5.run_id IN $runs "
        "RETURN m5.brief_label, "
        "avg(e.prompt_char_count) AS avg_len, "
        "min(e.prompt_char_count) AS min_len, "
        "max(e.prompt_char_count) AS max_len "
        "ORDER BY m5.brief_label",
        {"runs": VALID_RUNS},
    )
    print(
        f"{'brief':<10} {'avg_len':>8} {'min':>6} {'max':>6} {'range':>7} {'range%':>8}"
    )
    print("-" * 55)
    for brief, avg, mn, mx in rows5:
        rng_pct = (mx - mn) / avg * 100 if avg > 0 else 0
        print(
            f"{brief:<10} {avg:>8.0f} {mn:>6} {mx:>6} {mx - mn:>7} {rng_pct:>7.1f}%"
        )

    print()
    print("=== 6. 3-hop topology: REASONING_ADDS → VERIFICATION_ADDS → META_PROMPT_ADDS ===")
    rows6 = q(
        conn,
        "MATCH (m2:SpecRun)-[r1:REASONING_ADDS]->(m3:SpecRun)"
        "-[r2:VERIFICATION_ADDS]->(m4:SpecRun)"
        "-[r3:META_PROMPT_ADDS]->(m5:SpecRun) "
        "WHERE m5.run_id IN $runs "
        "RETURN DISTINCT m5.brief_label, r1.step_count, r1.evaluation_depth, "
        "r2.revised, r3.crispe_field_count, r3.capacity_matches_lang, "
        "(r1.confidence_delta + r2.confidence_delta) AS cumulative_delta "
        "ORDER BY m5.brief_label",
        {"runs": VALID_RUNS},
    )
    print(
        f"{'brief':<10} {'cot_steps':>10} {'eval_depth':<15} "
        f"{'cai_rev':>8} {'fc':>3} {'cap_match':>9} {'cum_delta':>10}"
    )
    print("-" * 72)
    for brief, steps, depth, rev, fc, cm, delta in rows6:
        print(
            f"{brief:<10} {steps:>10} {depth:<15} "
            f"{str(rev):>8} {fc:>3} {str(cm):>9} {delta:>10.3f}"
        )
    if not rows6:
        print("  (no 3-hop paths found — checking M5 valid run IDs vs linked M4 run IDs)")
        # Check what M4 runs are linked
        rows6b = q(
            conn,
            "MATCH (m4:SpecRun)-[r3:META_PROMPT_ADDS]->(m5:SpecRun) "
            "WHERE m5.run_id IN $runs "
            "RETURN DISTINCT m4.run_id, m5.brief_label LIMIT 5",
            {"runs": VALID_RUNS},
        )
        print("  META_PROMPT_ADDS m4 run_ids found:", rows6b)
        rows6c = q(
            conn,
            "MATCH (m3:SpecRun)-[:VERIFICATION_ADDS]->(m4:SpecRun) "
            "RETURN DISTINCT m4.run_id, m3.brief_label LIMIT 5",
        )
        print("  VERIFICATION_ADDS m4 run_ids:", rows6c)

    print()
    print("=== 7. Revision rates at M5 vs M4 ===")
    rows7 = q(
        conn,
        "MATCH (s:SpecRun) WHERE s.milestone IN ['m4', 'm5'] "
        "AND (s.milestone = 'm4' OR s.run_id IN $m5runs) "
        "RETURN s.milestone, s.brief_label, s.revised, s.confidence "
        "ORDER BY s.milestone, s.brief_label",
        {"m5runs": VALID_RUNS},
    )
    print(f"{'milestone':<10} {'brief':<10} {'revised':>8} {'conf':>6}")
    print("-" * 40)
    for ms, brief, rev, conf in rows7:
        print(f"{ms:<10} {brief:<10} {str(rev):>8} {conf:>6.2f}")

    conn.close()
    db.close()


if __name__ == "__main__":
    main()
