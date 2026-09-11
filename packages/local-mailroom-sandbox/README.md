<div align="center">

# 🧪 local-mailroom-sandbox

**A local-first experiment sandbox for the LLM-Mailroom pipeline — run the full classify → extract → report → archive graph offline on Ollama, vLLM, llama.cpp, or LM Studio.**

Swap in OpenRouter when you need an API provider. This repo does **not** fork the pipeline — it ships the family code it needs as **tracked snapshots under `vendor/`** (DMR-057): the pipeline (`llm-mailroom` v0.6.0) and scoring (`llm-dojo-scoring` v0.12.2) are self-contained, with config, serving, eval, and scoring overlays on top.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Pipeline](https://img.shields.io/badge/pipeline-llm--mailroom%20v0.6.0-blue)](https://github.com/Exios66/llm-mailroom)
[![Scoring](https://img.shields.io/badge/scoring-llm--dojo--scoring%20v0.12.2-purple)](https://github.com/Exios66/llm-dojo-scoring)
[![Tracing](https://img.shields.io/badge/tracing-Langfuse%20v4-F5A623)](#tracing)

</div>

---

## At a Glance

<div align="center">

| Component | Default | Notes |
|:---|:---|:---|
| **Default provider** | Ollama (`qwen3:8b`) | Fallback `qwen3:7b` |
| **Scoring** | `llm-dojo-scoring` @ v0.12.2 (vendored) | Deterministic, field-type-aware |
| **Pipeline** | `llm-mailroom` v0.6.0 (vendored) | 13-node LangGraph state machine |
| **Tracing** | Langfuse 3 / SDK v4 | `document-pipeline` traces |
| **Storage** | SQLite under `./data` | Mailroom default |

</div>

## Quick Start

```bash
pip install -e ".[dev]"
cp config/.env.example .env
# family code is already vendored under vendor/ (self-contained); fetch-deps
# only refreshes the pinned snapshots (network, optional):
sandbox fetch-deps                 # refresh vendor/llm-mailroom @ v0.6.0 + vendor/llm-dojo-scoring @ v0.12.2
sandbox up                         # Langfuse + Ollama
sandbox pull-models                # ollama pull qwen3:8b
sandbox health
sandbox pilot --mock               # machinery only, no LLM
sandbox pilot --local              # real local model
```

## One-Command Local Path

1. Install
2. `sandbox up` (compose profiles `langfuse` + `ollama`)
3. `sandbox pull-models`
4. `sandbox pilot --mock`
5. `sandbox pilot --local`

## CLI

<div align="center">

```
sandbox up | down | health | pull-models | fetch-deps | cutover | profiles | agents
sandbox pipeline watcher | pipeline api
sandbox pilot --mock|--local
sandbox hf-pilot --check|--mock|--local
sandbox legalbench --mock|--local
sandbox eval <agent>|extract|chained|pipeline|legalbench|local_vs_api [--mock|--local]
sandbox eval local_vs_api --from-log   # compare experiment_log local vs API-key runs
sandbox matrix --providers ollama --models qwen3:8b --prompts sorter_local_v0
sandbox datasets pull          # LIVE pinned Hub pull into data/cache/ (network; exit 1 on failure)
sandbox datasets prepare   # offline clean → data/runtime/prepared/
sandbox run preflight|start|status|resume|cancel|list --config config/runs/<name>.yaml
sandbox run start --config <run.yaml> --job-mode modal --watch   # Modal worker
sandbox prompts list | show <agent> [--variant X]
sandbox metrics compare --runs local,modal,api | --log
sandbox tunnel --profile vllm-remote plan|up|status|down
sandbox traces export
```

Live-or-loud: a vLLM/Modal profile without `--local` warns instead of silently
mocking (DMR-048); `SANDBOX_DEBUG=1` traces CHTC/Modal scripts (DMR-053).

</div>

<details>
<summary>CPU-only smoke test</summary>

Pull `llama3.2:3b` and run:

```bash
sandbox cutover --profile ollama --model llama3.2:3b
```

GPU recommended for Qwen 8B.

</details>

## Docs

| Guide | Description |
|:---|:---|
| [Quickstart](docs/QUICKSTART.md) | **Start here** — install, full CLI reference, canonical workflows |
| [Providers](docs/providers.md) | Ollama, vLLM, Modal, llama.cpp, LM Studio, OpenRouter |
| [Evals](docs/evals.md) | Runners, matrix, scoring, experiment log |
| [Tracing](docs/tracing.md) | Langfuse v4 data model, tags, The-Mailroom |
| [Docker offline](docs/docker-offline.md) | Dockerfile, Compose `jupyter` profile, prep notebooks |
| [Sister repos](docs/sister-repos.md) | Family map |
| [Agent skills](.cursor/skills/README.md) | Langfuse, Phoenix, Braintrust, Ollama, Modal, Hugging Face |

## Layout

```
config/profiles/     provider profiles (local-first defaults)
config/taxonomy.overlay.yaml
config/models.yaml   OpenRouter champion → local tag map
deploy/              Dockerfile + compose + Modal vLLM (modal_vllm.py) + Modal job worker (modal_job.py) + htcondor/ + conda/
notebooks/           offline env setup + data prep + mock smoke
data/fixtures/       offline samples (see ATTRIBUTION.md)
src/mailroom_sandbox/
vendor/              tracked family snapshots (llm-mailroom v0.6.0 + llm-dojo-scoring v0.12.2; see VENDOR.md)
reports/             sandbox experiment log (not a sister-repo mirror)
```

## Offline Docker + Notebooks

```bash
pip install -e ".[dev,notebooks]"
sandbox up --compose-profile langfuse --compose-profile ollama --compose-profile jupyter
# Lab → http://127.0.0.1:8888/lab
sandbox datasets prepare
```

See [`docs/docker-offline.md`](docs/docker-offline.md).

---

<div align="center">

**[llm-mailroom](https://github.com/Exios66/llm-mailroom)** ·
**[llm-entity-extraction](https://github.com/Exios66/llm-entity-extraction)** ·
**[llm-dojo-scoring](https://github.com/Exios66/llm-dojo-scoring)** ·
**[The-Mailroom](https://github.com/Exios66/The-Mailroom)**

<sub>Built by the governed evaluation family under <a href="https://github.com/Exios66">@Exios66</a> · 2026</sub>

</div>
