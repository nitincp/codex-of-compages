# Dev Container — Faber

## Setup

Open the repo in VS Code → **Reopen in Container** (or `Dev Containers: Rebuild and Reopen in Container`).

`postCreateCommand` runs automatically:
```bash
python3 -m pip install --upgrade pip
python3 -m pip install -e '/workspace/.[dev]'
```

## What's in the container

| Component | Detail |
|---|---|
| Python 3.10 | Installed in the container via devcontainer features |
| Secrets | loaded from `.env` in workspace root |
| `faber-pip-cache` | Named Docker volume — pip wheels persist across rebuilds (fast `postCreate`) |
| `remoteEnv` | `MODEL_PROVIDER`, `MODEL_NAME`, `KUZU_DB_PATH`, `FABER_LOG_PROMPTS` set in every terminal |
| Ports | 8000 (Streamlit/Chainlit) + 8501 (Streamlit default) forwarded |
| Git | Latest git via `ghcr.io/devcontainers/features/git:1` |

## Port convention

- **8000**: `streamlit run src/ui/dashboard.py --server.port 8000` (current)
- **8000** is also Chainlit's default — at M7, switch one of them to 8501
- Never run Streamlit and Chainlit on the same port simultaneously

## Secrets discipline

- `ANTHROPIC_API_KEY` → `.env` or shell environment in the workspace. Do not commit sensitive values to git.
- `remoteEnv` in `devcontainer.json` mirrors non-sensitive defaults so terminal scripts see variables without sourcing.

## VS Code behaviour

- **Test discovery**: `pytestArgs: ["tests", "src/milestones"]` — both Spec Council and GNN gate tests appear in the Test Explorer
- **Type checking**: `typeCheckingMode: standard` (stricter than default `basic`) — catches Pydantic field mismatches and Kuzu return type errors before runtime
- **Format on save**: ruff formats and organises imports automatically

## Rebuilding

`data/kuzu` is inside the workspace bind mount — the persistent GNN survives container rebuilds.
`faber-pip-cache` volume preserves pip wheels — rebuild is fast.
