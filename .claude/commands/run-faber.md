---
name: run-faber
description: Run, test, seed, and verify Faber — gate tests, milestone runners, ETL, Streamlit dashboard. Use when asked to run, test, start, seed, or verify Faber.
---

Driver: `.claude/commands/scripts/smoke.sh`. Run from `/workspace`.

**Gate tests** (no API key, ~13s, ephemeral DB):
```bash
bash .claude/commands/scripts/smoke.sh tests          # all proven milestones: M1 M2 M3 + ETL (67 tests)
bash .claude/commands/scripts/smoke.sh m1             # single milestone
bash .claude/commands/scripts/smoke.sh m3
```

**Seed a subgraph into persistent data/kuzu:**
```bash
bash .claude/commands/scripts/smoke.sh run m1         # M1: no API key needed
bash .claude/commands/scripts/smoke.sh run m2         # M2+: needs ANTHROPIC_API_KEY
bash .claude/commands/scripts/smoke.sh run m3
```

**Streamlit dashboard** (verify it starts):
```bash
bash .claude/commands/scripts/smoke.sh dashboard      # starts on :8000, curl-verifies, kills
```

**Full smoke** (tests + M1 seed + dashboard ping):
```bash
bash .claude/commands/scripts/smoke.sh
```

**Direct pytest / runner** (when you need more control):
```bash
python3 -m pytest src/milestones/m1/tests/ -q --tb=short
python3 -m src.milestones.m3.run my-run-id
```

**ETL:**
```bash
python3 -m src.etl.migrate --to m3 --dry-run
python3 -m src.etl.migrate --to m3
python3 -m src.etl.diff m2 m3
```

**Gotchas:**
- `src` imports only work from `/workspace` root — never `cd` into a subdir first
- M1 runner needs no API key (pure Python). M2+ call Anthropic — `ANTHROPIC_API_KEY` is in `.env`.
- Gate tests never touch `data/kuzu`. Runner always writes to `data/kuzu`.
- `streamlit` binary may not be on PATH — `python3 -m streamlit run ...` always works
- If Kuzu throws `Cannot open DB`, another process has the DB open — kill it first
