# Git Workflow — Faber

## Core rule

**Never commit to `main` directly.** All work happens on branches. `main` is always clean, green, and provably working.

## Branch naming

| Type | Pattern | When | Lifecycle |
|---|---|---|---|
| Milestone | `m{N}/short-description` | Implementing a milestone task | Merge to main when gate tests pass + evidence file complete |
| Analysis | `analysis/hypothesis-name` | Claude-in-loop GNN analysis | Merge to main when `analysis_opportunities.md` updated + `AnalysisNote` nodes seeded |
| Chore | `chore/description` | Docs, tooling, refactoring | Merge to main when done |
| Fix | `fix/description` | Bug fix or schema correction | Merge to main immediately |
| Experimental | `wip/description` | Exploratory — never PR'd | Delete without merging; insights go into a clean commit on another branch |

## Commit format (Conventional Commits)

```
feat(m4): add RevisionEvent nodes and VERIFICATION_ADDS edges
fix(schema): correct src_id/dst_id convention in REASONING_ADDS rel
chore(docs): add running-with-claude.md
test(m3): extend gate tests for evaluation_depth assertion
```

Scope is the milestone (`m4`), component (`schema`, `docs`, `etl`), or agent name.

## When to commit

**Commit after every meaningful, impactful change.** The rule: if it would hurt to redo it, commit it.

Specifically commit when:
- Gate tests pass for a milestone or sub-milestone
- A schema or migration file is added/updated
- An evidence file is created or completed
- Analysis findings are written to `analysis_opportunities.md`
- An `AnalysisNote` schema is established and seeded
- Any docs that took real thought to write

One logical unit per commit — don't batch unrelated changes. This keeps `git bisect` and revert safe.

## Claude commits — consistency rules

- Always include `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`
- Run `ruff check . && pyright src/` before committing any code change
- Never amend a pushed commit — create a new commit instead
- Never force-push to any branch
- Never commit directly to `main` — always branch, always ask for merge approval

## Merge strategy

- Merge branches via PR or fast-forward merge after review
- Delete branches after merge — keep the branch list clean
- `wip/` branches are never merged — delete them when the exploration is done
- `analysis/` branches are merged only after `analysis_opportunities.md` is updated and `AnalysisNote` nodes are seeded in the persistent DB
