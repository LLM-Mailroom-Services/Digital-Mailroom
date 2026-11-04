# Docker offline sandbox

This repo ships **two** Docker surfaces:

| Artifact | Role |
| --- | --- |
| [`deploy/docker-compose.yml`](../../deploy/docker-compose.yml) | Sidecar stack: Langfuse 3, Ollama, optional Phoenix / vLLM / llama.cpp, and **Jupyter Lab** |
| [`deploy/Dockerfile`](../../deploy/Dockerfile) | Offline sandbox image (`mailroom-sandbox:offline`) with the Python harness + notebooks |

There is no second mailroom pipeline inside the image — only the sandbox overlay, fixtures, and Jupyter.

## Quick start (Jupyter + Ollama + Langfuse)

```bash
pip install -e ".[dev,notebooks]"
cp -n config/.env.example .env
sandbox up -d --compose-profile langfuse --compose-profile ollama --compose-profile jupyter
# Lab: http://127.0.0.1:8888/lab
# Langfuse: http://127.0.0.1:3000  (pk-lf-sandbox / sk-lf-sandbox; sign-in email LANGFUSE_INIT_USER_EMAIL, default sandbox@example.com)
sandbox pull-models --profile ollama
```

Or build the image alone:

```bash
docker build -f deploy/Dockerfile -t mailroom-sandbox:offline .
docker run --rm -p 127.0.0.1:8888:8888 -v "$PWD":/workspace mailroom-sandbox:offline
```

Image hardening (HUB-015): the sandbox image runs as a **non-root user**
(`sandbox`, uid 1000) and carries a **HEALTHCHECK** (`curl /lab`). On hosts
whose first user is not uid 1000, pass `--user "$(id -u):$(id -g)"`. All
compose images are **version-pinned** (ollama `0.33.2`, vllm `v0.29.0`,
phoenix `version-20.4.0`, llama.cpp `full-e95b6554b493e71a0275764342e09bd5784a7026`,
minio `cgr.dev/chainguard/minio@sha256:3b6e40c3…`, langfuse web and worker
`3.225.15`, redis `7`, clickhouse `24-alpine`, pgvector `pg16`) for offline
reproducibility — bump pins deliberately. Every published Compose port binds
`127.0.0.1`, so the services are reachable from the host only.

Upgrading from the old `minio/minio` image: the Chainguard image runs as UID
65532, but a `minio_data` volume created by the old image is root-owned, so
MinIO cannot create `/data/langfuse` and Langfuse loses its event and media
store. Change the volume's owner once:

```bash
docker compose -f deploy/docker-compose.yml --profile langfuse stop minio
volume=$(docker volume ls -q --filter label=com.docker.compose.volume=minio_data)   # e.g. mailroom-sandbox_minio_data
if [ "$(printf '%s\n' "$volume" | grep -c .)" -eq 1 ]; then
  docker run --rm -v "$volume":/data alpine chown -R 65532:65532 /data &&
    docker compose -f deploy/docker-compose.yml --profile langfuse up -d minio
else
  echo "expected exactly one minio_data volume, found: ${volume:-none}; MinIO left stopped"   # chown it by name
fi
```

## Notebooks (dedicated prep path)

| Notebook | Purpose |
| --- | --- |
| [`notebooks/01_offline_environment_setup.ipynb`](../../notebooks/01_offline_environment_setup.ipynb) | Copy `.env`, activate profile, verify Dockerfile/compose/fixtures |
| [`notebooks/02_load_clean_prepare_data.ipynb`](../../notebooks/02_load_clean_prepare_data.ipynb) | Load catalog + HF + agent gold; clean; write `data/runtime/prepared/` |
| [`notebooks/03_offline_sandbox_smoke.ipynb`](../../notebooks/03_offline_sandbox_smoke.ipynb) | Mock pilot / sorter smoke against prepared JSONL (no live LLM) |

Helpers live in `mailroom_sandbox.prep` (`prepare_offline_datasets`, `environment_checklist`).

## Compose profiles

| Profile | Services |
| --- | --- |
| `langfuse` | postgres, clickhouse, redis, minio, langfuse-web, langfuse-worker |
| `ollama` | `sandbox-ollama` on `:11434` |
| `jupyter` | builds `deploy/Dockerfile`, Lab on `:8888` |
| `phoenix` / `vllm` / `llamacpp` | optional sidecars |

`sandbox up` (default `modal-vllm` profile) starts `langfuse` only: the GPU
endpoint lives on Modal, not in compose. For the offline Ollama stack use
`sandbox up --compose-profile ollama`. Explicit compose profiles replace the profile defaults;
select each service you need. To start Jupyter alone:

```bash
sandbox up -d --compose-profile jupyter
sandbox down --compose-profile jupyter
```

The Jupyter service defaults to the `ollama` profile (`SANDBOX_PROFILE` in `deploy/docker-compose.yml`); export `SANDBOX_PROFILE` in the shell that runs `sandbox up` to change it. Inside the Jupyter container, provider URLs point at compose DNS names (`http://ollama:11434/v1`, `http://langfuse-web:3000`). On the host, keep using `localhost` URLs from `config/.env.example`.

## Offline data prep without Docker

```bash
pip install -e ".[dev,notebooks]"
python -c "from mailroom_sandbox.prep import prepare_offline_datasets; print(prepare_offline_datasets())"
jupyter lab notebooks/
```

Prepared artifacts are written under `data/runtime/prepared/` (gitignored with the rest of `data/runtime/`).
