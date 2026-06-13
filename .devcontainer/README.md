# Dev Container — Faber

## Setup

Open the repo in VS Code → **Reopen in Container** (or `Dev Containers: Rebuild and Reopen in Container`).

`postCreateCommand` runs automatically:
```bash
bash .devcontainer/bootstrap-secrets.sh   # wires /secrets/secrets.env into .bashrc + .profile
python3.10 -m pip install --upgrade pip
python3.10 -m pip install -e '/workspace/.[dev]'
python3.10 -m playwright install chromium --with-deps
```

## What's in the container

| Component | Detail |
|---|---|
| Python 3.10 | Bind-mounted from host — survives rebuilds, no reinstall needed |
| Secrets | `/secrets/secrets.env` from `${HOME}/projects/.secrets` — never in `.env` or git |
| `faber-pip-cache` | Named Docker volume — pip wheels persist across rebuilds (fast `postCreate`) |
| `remoteEnv` | `MODEL_PROVIDER`, `MODEL_NAME`, `KUZU_DB_PATH`, `FABER_LOG_PROMPTS` set in every terminal |
| Ports | 8000 (Streamlit/Chainlit) + 8501 (Streamlit default) forwarded |
| Git | Latest git via `ghcr.io/devcontainers/features/git:1` |

## Port convention

- **8000**: `streamlit run src/ui/dashboard.py --server.port 8000` (current)
- **8000** is also Chainlit's default — at M7, switch one of them to 8501
- Never run Streamlit and Chainlit on the same port simultaneously

## Secrets discipline

- `ANTHROPIC_API_KEY` → `/secrets/secrets.env` **only**. Never `.env`, never version control.
- `.env` is safe to commit — non-sensitive config only (`MODEL_PROVIDER`, `MODEL_NAME`, `KUZU_DB_PATH`, `FABER_LOG_PROMPTS`).
- `remoteEnv` in `devcontainer.json` mirrors `.env` so terminal scripts see variables without sourcing.

## VS Code behaviour

- **Test discovery**: `pytestArgs: ["tests", "src/milestones"]` — both Spec Council and GNN gate tests appear in the Test Explorer
- **Type checking**: `typeCheckingMode: standard` (stricter than default `basic`) — catches Pydantic field mismatches and Kuzu return type errors before runtime
- **Format on save**: ruff formats and organises imports automatically

## Rebuilding

`data/kuzu` is inside the workspace bind mount — the persistent GNN survives container rebuilds.  
`faber-pip-cache` volume preserves pip wheels — rebuild is fast.
