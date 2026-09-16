# Docker offline sandbox

This repo ships **two** Docker surfaces:

| Artifact | Role |
| --- | --- |
| [`deploy/docker-compose.yml`](../deploy/docker-compose.yml) | Sidecar stack: Langfuse 3, Ollama, optional Phoenix / vLLM / llama.cpp, and **Jupyter Lab** |
| [`deploy/Dockerfile`](../deploy/Dockerfile) | Offline sandbox image (`mailroom-sandbox:offline`) with the Python harness + notebooks |

There is no second mailroom pipeline inside the image — only the sandbox overlay, fixtures, and Jupyter.

## Quick start (Jupyter + Ollama + Langfuse)

```bash
pip install -e ".[dev,notebooks]"
cp -n config/.env.example .env
sandbox up --compose-profile langfuse --compose-profile ollama --compose-profile jupyter
# Lab: http://127.0.0.1:8888/lab
# Langfuse: http://127.0.0.1:3000  (pk-lf-sandbox / sk-lf-sandbox)
sandbox pull-models
```

Or build the image alone:

```bash
docker build -f deploy/Dockerfile -t mailroom-sandbox:offline .
docker run --rm -p 8888:8888 -v "$PWD":/workspace mailroom-sandbox:offline
```

Image hardening (HUB-015): the sandbox image runs as a **non-root user**
(`sandbox`, uid 1000) and carries a **HEALTHCHECK** (`curl /lab`). On hosts
whose first user is not uid 1000, pass `--user "$(id -u):$(id -g)"`. All
compose images are **version-pinned** (ollama `0.33.2`, vllm `v0.29.0`,
phoenix `version-20.4.0`, llama.cpp `full-e95b6554b493e71a0275764342e09bd5784a7026`,
minio `RELEASE.2025-09-07…`, langfuse `3`,
redis `7`, clickhouse `24-alpine`, pgvector `pg16`) for offline
reproducibility — bump pins deliberately.

## Notebooks (dedicated prep path)

| Notebook | Purpose |
| --- | --- |
| [`notebooks/01_offline_environment_setup.ipynb`](../notebooks/01_offline_environment_setup.ipynb) | Copy `.env`, activate profile, verify Dockerfile/compose/fixtures |
| [`notebooks/02_load_clean_prepare_data.ipynb`](../notebooks/02_load_clean_prepare_data.ipynb) | Load catalog + HF + LegalBench + agent gold; clean; write `data/runtime/prepared/` |
| [`notebooks/03_offline_sandbox_smoke.ipynb`](../notebooks/03_offline_sandbox_smoke.ipynb) | Mock pilot / sorter smoke against prepared JSONL (no live LLM) |

Helpers live in `mailroom_sandbox.prep` (`prepare_offline_datasets`, `environment_checklist`).

## Compose profiles

| Profile | Services |
| --- | --- |
| `langfuse` | postgres, clickhouse, redis, minio, langfuse-web, langfuse-worker |
| `ollama` | `sandbox-ollama` on `:11434` |
| `jupyter` | builds `deploy/Dockerfile`, Lab on `:8888` |
| `phoenix` / `vllm` / `llamacpp` | optional sidecars |

`sandbox up` (default ollama profile) starts `langfuse` + `ollama`. Add Jupyter explicitly:

```bash
sandbox up --compose-profile jupyter
sandbox down --compose-profile jupyter
```

Inside the Jupyter container, provider URLs point at compose DNS names (`http://ollama:11434/v1`, `http://langfuse-web:3000`). On the host, keep using `localhost` URLs from `config/.env.example`.

## Offline data prep without Docker

```bash
pip install -e ".[dev,notebooks]"
python -c "from mailroom_sandbox.prep import prepare_offline_datasets; print(prepare_offline_datasets())"
jupyter lab notebooks/
```

Prepared artifacts are written under `data/runtime/prepared/` (gitignored with the rest of `data/runtime/`).
