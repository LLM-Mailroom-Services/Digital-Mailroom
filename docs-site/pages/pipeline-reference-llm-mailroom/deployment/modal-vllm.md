---
description: vLLM on a rented Modal GPU.
icon: microchip
title: Modal + vLLM
---

# Modal + vLLM

Modal runs vLLM on a rented GPU and gives the pipeline an OpenAI-compatible `/v1` endpoint. The Modal app name is **`mailroom-vllm`**. Do not confuse it with the sandbox app `sandbox-vllm`. Source: [`deploy/modal_vllm.py`](https://github.com/Exios66/llm-mailroom/blob/main/deploy/modal_vllm.py).

Everyday production uses OpenRouter. Use Modal only when you want open-weight models on a GPU that you do not own.

| If you want... | Use |
| --- | --- |
| One model for all agents, behind one URL | [Single-tier serve (Mode M)](#single-tier-serve-mode-m) |
| A small model for routing, a large model for extraction, and a vision model, behind the LiteLLM gateway | [Multi-tier serve (Mode G)](#multi-tier-serve-mode-g) |
| A local smoke test on CPU | [Local models](../local-models.md) (Ollama), not Modal |
| Unit tests or `--mock` runs | No LLM server. Do not use Modal for these |

The Docker host that sends calls to these GPUs is on [Docker deployment](docker-deployment.md).

**Cost model.** Modal charges for GPU time while a container runs, not for each token. Each function scales to zero after `SCALEDOWN_SECONDS` of idle time. The first call after that starts a new container (a cold start).

## Single-tier serve (Mode M)

One vLLM OpenAI-compatible `/v1` server behind a Modal `web_server`. SDK pin `modal==1.5.5`, image `vllm/vllm-openai:v0.28.0` (matches the local compose pin).

```bash
pip install -e ".[deploy]"
modal token new
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_API_TOKEN="$(openssl rand -hex 24)"
modal run deploy/modal_vllm.py::download_model   # pre-warm weights (CPU-only)
modal deploy deploy/modal_vllm.py                # prints the URL
```

Smoke without a persistent deploy: `modal serve deploy/modal_vllm.py`. Tear down: `modal app stop mailroom-vllm`.

Debug: `modal run deploy/modal_vllm.py --debug` prints the masked resolved config; `--check` probes `/models` with bearer hints. `download_model` fails loudly on an empty snapshot.

### Cut over the pipeline

```bash
# .env
DEFAULT_PROVIDER=vllm
VLLM_BASE_URL=https://<workspace>--mailroom-vllm-serve.modal.run/v1
VLLM_API_KEY=<same as MODAL_VLLM_API_TOKEN>
```

Every agent still gets its client from `get_llm()`. The pipeline reads a `503` from a `*.modal.run` endpoint as a cold start. For that error, `llm/retry.py` waits longer between attempts, up to a fixed limit (DMR-052). To go back to OpenRouter, set `DEFAULT_PROVIDER=openrouter`.

The sibling `llm-entity-extraction` pipeline can share the **same** server through its `OPENROUTER_BASE_URL` seam, so one Modal workspace can back both pipelines.

Then run the compose `app` (Mode M) from [Docker deployment](docker-deployment.md), or a local `PYTHONPATH=src python -m api.main`.

Bearer auth is enforced by vLLM itself. The pipeline sends `VLLM_API_KEY` as the bearer (`llm/providers.py`). Knobs are baked into a deploy-time `Secret.from_dict` (SDK 1.5.5 removed `Secret.from_local`).

## Deploy-time knobs

Set these **before** `modal deploy`, not in the running pipeline `.env` (except `VLLM_BASE_URL` / `VLLM_API_KEY`).

| Env                                  | Default                             |
| ------------------------------------ | ----------------------------------- |
| `MODAL_VLLM_MODEL`                   | `Qwen/Qwen3-8B`                     |
| `MODAL_VLLM_GPU`                     | `L4`                                |
| `MODAL_VLLM_MAX_MODEL_LEN`           | `32768`                             |
| `MODAL_VLLM_GPU_MEMORY_UTILIZATION`  | engine default                      |
| `MODAL_VLLM_MAX_NUM_SEQS`            | engine default                      |
| `MODAL_VLLM_TP_SIZE`                 | from the GPU `:N` suffix (DMR-051)  |
| `MODAL_VLLM_QUANTIZATION`            | empty                               |
| `MODAL_VLLM_REVISION`                | empty (Hub default)                 |
| `MODAL_VLLM_IMAGE_TAG`               | `v0.28.0`                           |
| `MODAL_VLLM_API_TOKEN`               | required bearer                     |
| `MODAL_VLLM_SCALEDOWN_SECONDS`       | scale-to-zero idle                  |
| `MODAL_VLLM_STARTUP_TIMEOUT_SECONDS` | cold-start budget                   |
| `HF_TOKEN`                           | optional Hub auth for gated weights |

Gated Hub weights: set `HF_TOKEN` at deploy time. See [Configuration](../configuration.md) for `VLLM_BASE_URL` / `VLLM_API_KEY` on the pipeline side.

## Multi-tier serve (Mode G)

`modal deploy deploy/modal_vllm.py` can stand up **one scale-to-zero vLLM function per tier**, grouped by model so each model has at most one warm GPU pool. `MODAL_VLLM_TIERS` selects which tiers deploy (default `fast,extract,vision`).

| Tier    | Alias              | Default model                   | GPU  | Context | Agents                                                     |
| ------- | ------------------ | ------------------------------- | ---- | ------- | ---------------------------------------------------------- |
| fast    | `mailroom-fast`    | Qwen3-8B-FP8                    | L4   | 32k     | sorter, sorter\_reviewer, intake, gmail\_triage, relations |
| extract | `mailroom-extract` | Qwen3-30B-A3B-Instruct-2507-FP8 | L40S | 64k     | specialists, arbiter, boss, judge                          |
| vision  | `mailroom-vision`  | Qwen3-VL-8B-Instruct-FP8        | L4   | 32k     | pdf\_transcriber, image\_extractor                         |

Per-tier knobs: `MODAL_VLLM_<TIER>_<KNOB>` (`MODEL`, `GPU`, `MAX_MODEL_LEN`, `MAX_NUM_SEQS`, `MAX_INPUTS`, `MAX_CONTAINERS`, `MIN_CONTAINERS`, `SCALEDOWN_SECONDS`, …). Unscoped `MODAL_VLLM_<KNOB>` still applies to `fast`.

Put the three printed URLs plus `MODAL_VLLM_API_TOKEN` in `.env` as `MODAL_FAST_URL` / `MODAL_EXTRACT_URL` / `MODAL_VISION_URL`, then bring up [`deploy/docker-compose.full.yml`](https://github.com/Exios66/llm-mailroom/blob/main/deploy/docker-compose.full.yml). The compose `app` uses `DEFAULT_PROVIDER=litellm` and sends every agent through the gateway to the taxonomy `tier:`. Runtime override: `MAILROOM_GATEWAY_TIERS=sorter=api,boss=fast`.

Host compose, LiteLLM image pin, required secrets, and the smoke script: [Docker deployment — Mode G](docker-deployment.md#mode-g-full-stack-litellm--modal-gpu-tiers).

```bash
PYTHONPATH=src python src/scripts/smoke_modal_tiers.py --check
PYTHONPATH=src python src/scripts/smoke_modal_tiers.py --warm
PYTHONPATH=src python src/scripts/smoke_modal_tiers.py --run
```

`--check` is network-free. `--run` sends one document per class and checks each node's traced model against its expected tier.

`vision.exclude` keeps the text-only tier aliases off the vision path. Thinking: vLLM-served calls send `chat_template_kwargs.enable_thinking`, which is off for effort `none` / `minimal`. OpenRouter calls keep `reasoning.effort`.

## Local vLLM (no Modal)

A host vLLM server is still `DEFAULT_PROVIDER=vllm` + `VLLM_BASE_URL=http://localhost:8000/v1`. Confirm `/v1` is on the URL (the OpenAI SDK appends `/chat/completions`). Cutover and troubleshooting: [Local models](../local-models.md).

`taxonomy.yaml: vllm_model_map` changes each OpenRouter model id to the id that the engine serves. `DEFAULT_PROVIDER` overrides the `provider:` of every agent, Gmail triage included. Thus on vLLM, Gmail triage sends `openrouter/free` through the map and gets `Qwen/Qwen3-8B`.

## Related

* [Docker deployment](docker-deployment.md) — Mode M compose + Mode G full stack
* [Deployment](./) — laptop install, Spaces
* [Local models](../local-models.md) — Ollama / local vLLM cutover
* [Configuration](../configuration.md) — `DEFAULT_PROVIDER`, `VLLM_*`, `MODAL_*`
