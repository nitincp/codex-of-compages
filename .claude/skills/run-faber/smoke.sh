#!/usr/bin/env bash
# Faber smoke driver — run from /workspace
# Usage:
#   bash .claude/skills/run-faber/smoke.sh          # gate tests + M1 runner + dashboard ping
#   bash .claude/skills/run-faber/smoke.sh tests     # gate tests only (all milestones with data)
#   bash .claude/skills/run-faber/smoke.sh mN        # single milestone gate tests  e.g. m1 m2 m3
#   bash .claude/skills/run-faber/smoke.sh run mN    # seed one subgraph via mN runner (no API for m1)
#   bash .claude/skills/run-faber/smoke.sh dashboard # start Streamlit + curl-verify + kill

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

MODE="${1:-all}"
ARG2="${2:-}"

run_tests() {
    local target="${1:-}"
    if [ -z "$target" ]; then
        echo "=== Gate tests: M1 M2 M3 ETL ==="
        python3 -m pytest src/milestones/m1/tests/ \
                          src/milestones/m2/tests/ \
                          src/milestones/m3/tests/ \
                          tests/etl/ -q --tb=short
    else
        echo "=== Gate tests: $target ==="
        python3 -m pytest "src/milestones/${target}/tests/" -q --tb=short
    fi
}

run_milestone() {
    local mn="${1:-m1}"
    local run_id="smoke-$(date +%Y%m%d-%H%M%S)"
    echo "=== Seeding $mn runner (run_id=$run_id) ==="
    python3 -m "src.milestones.${mn}.run" "$run_id"
}

run_dashboard() {
    echo "=== Starting Streamlit on :8000 ==="
    python3 -m streamlit run src/ui/dashboard.py \
        --server.port 8000 --server.headless true &
    local PID=$!
    sleep 5
    if curl -sf http://localhost:8000 | grep -q "Streamlit"; then
        echo "OK — dashboard serving at http://localhost:8000"
    else
        echo "WARN — dashboard started but response unexpected (check manually)"
    fi
    kill $PID 2>/dev/null
    wait $PID 2>/dev/null || true
    echo "Dashboard stopped."
}

case "$MODE" in
    all)
        run_tests
        run_milestone m1
        run_dashboard
        ;;
    tests)
        run_tests "$ARG2"
        ;;
    m[0-9]*)
        # bare milestone arg — run its gate tests
        run_tests "$MODE"
        ;;
    run)
        run_milestone "${ARG2:-m1}"
        ;;
    dashboard)
        run_dashboard
        ;;
    *)
        echo "Unknown mode: $MODE"
        echo "Usage: smoke.sh [all|tests [mN]|mN|run [mN]|dashboard]"
        exit 1
        ;;
esac

echo "=== done ==="
