---
description: Seven paths to a first run. Each works without paid keys.
icon: rocket
title: Getting started
---

# Getting started

Pick the path that matches what you came to do. Every path below can run without paid API keys first (mock mode), so you can see the machinery work before spending anything.

| If you want to... | Take path |
| --- | --- |
| Contribute code across several repositories | 1 |
| See a document move through the pipeline | 2 |
| Run without any cloud model | 3 |
| Measure how well one pipeline step performs | 4 |
| Watch runs as they happen | 5 |
| Score extraction output in your own code | 6 |
| Deploy | 7 |

Prerequisites for all paths: Python 3.11+, git, and [uv](https://docs.astral.sh/uv/) (pip works for the standalone repos).

## 1. Work across the whole constellation (recommended for contributors)

Clone the monorepo. One `uv sync` installs every package editable into one virtualenv, so nothing ever imports across separate checkouts.

```bash
git clone https://github.com/LLM-Mailroom-Services/Digital-Mailroom.git
cd Digital-Mailroom
uv sync
```

Run tests one package at a time (several packages ship a top-level `tests` package and collide if batched):

```bash
uv run pytest packages/llm-mailroom/src/tests
uv run pytest packages/llm-dojo-scoring/tests
uv run pytest packages/local-mailroom-sandbox/tests
```

Before changing anything, read the board: `governance/TASKS.md` in the monorepo, or the live [Dispatch Board](https://digital-mailroom-theta.vercel.app). The rules are in [Governance and workflow](../how-it-fits-together/governance.md).

## 2. Run the pipeline and push a document through it

Standalone `llm-mailroom`. Storage is a plain SQLite file, so no database server is needed.

```bash
git clone https://github.com/Exios66/llm-mailroom.git
cd llm-mailroom
cp .env.example .env              # add OPENROUTER_API_KEY for real runs
pip install -e ".[dev]"

# Machinery check with a fake LLM, no key needed
PYTHONPATH=src python src/scripts/run_pilot.py --mock

# Start the API (it embeds the inbox watcher)
PYTHONPATH=src python -m api.main

# In another shell: upload, then follow the document
curl -X POST http://localhost:8000/v1/upload \
  -F "file=@src/tests/fixtures/contract/sample_msa.txt" -F "matter_id=MATTER-001"
curl http://localhost:8000/v1/status/{doc_id}
curl http://localhost:8000/v1/audit/{doc_id}
```

**What each command proves.** The `--mock` pilot uses a deterministic fake model. It confirms that the graph, storage and scoring wiring work. It needs no key and costs nothing. It says nothing about model quality. The upload call returns an `upload_id` and queues the file. The watcher mints the pipeline's `doc_id` when it claims the file. Find the `doc_id` in `GET /v1/queue` or in the watcher logs. Use it in the `status` and `audit` commands. `status` shows how far that document has travelled, and `audit` returns its hash-chained history, one entry per stage. If a command fails with an import error, check that `PYTHONPATH=src` is set. If a real (non-mock) run fails immediately, the usual cause is a missing `OPENROUTER_API_KEY`.

Every route is also mounted **without** the `/v1` prefix for backwards compatibility, but `/v1` is the current interface — see [API](../pipeline-reference-llm-mailroom/api.md).

Next: [Pipeline architecture](../pipeline-reference-llm-mailroom/architecture.md), [Configuration](../pipeline-reference-llm-mailroom/configuration.md), [API](../pipeline-reference-llm-mailroom/api.md).

## 3. Run everything offline on local models

`local-mailroom-sandbox` vendors the pipeline and scoring library and runs them against Ollama (default `qwen3:8b`), vLLM, llama.cpp or LM Studio.

```bash
git clone https://github.com/Exios66/local-mailroom-sandbox.git
cd local-mailroom-sandbox
pip install -e ".[dev]"
cp config/.env.example .env
sandbox up              # Langfuse + Ollama via compose profiles
sandbox pull-models
sandbox pilot --mock    # machinery only
sandbox pilot --local   # real local model
```

Next: [local-mailroom-sandbox guide](../repository-guides/repos/local-mailroom-sandbox/), [run reports](../repository-guides/repos/local-mailroom-sandbox/local-mailroom-sandbox-reports.md), [visuals](../repository-guides/repos/local-mailroom-sandbox/local-mailroom-sandbox-visuals.md).

## 4. Measure a pipeline node

`eval-environment` has one task registry covering every LLM node. Start in mock mode.

```bash
git clone https://github.com/LLM-Mailroom-Services/eval-environment.git
cd eval-environment
uv sync --extra dev     # needs an llm-mailroom checkout beside it (see [tool.uv.sources])
uv run python scripts/run_evals.py --list
uv run python scripts/run_evals.py --task all --mock --n 2
```

Next: [eval-environment guide](../repository-guides/repos/eval-environment.md).

## 5. Watch the pipeline run

`The-Mailroom` draws every pipeline run as envelopes on a conveyor. It reads only Langfuse, so it needs the same Langfuse keys the pipeline writes to.

```bash
git clone https://github.com/Exios66/The-Mailroom.git
cd The-Mailroom
pip install -e ".[dev]"
cp .env.example .env    # LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY
mailroom-web            # http://127.0.0.1:8001
```

For a self-contained alternative with no Langfuse at all, run [agent-mailroom](../repository-guides/repos/agent-mailroom.md): `pip install -e ".[dev]" && python -m agent_mailroom`.

## 6. Score extraction output

```bash
pip install "llm-dojo-scoring @ git+https://github.com/Exios66/llm-dojo-scoring.git@v0.28.1"
```

```python
import llm_dojo_scoring as dojo
suite = dojo.get_suite("insurance_claims_specialist")
result = suite.score(expected_fields, predicted_fields)
```

Next: [llm-dojo-scoring guide](../repository-guides/repos/llm-dojo-scoring.md).

## 7. Deploy with Docker or Modal GPU

The GitBook pipeline reference publishes the full operator manuals (they are listed in `SUMMARY.md`):

* [Docker deployment](../pipeline-reference-llm-mailroom/deployment/docker-deployment.md) — compose matrix (OpenRouter, Ollama, llamafile, Mode G LiteLLM + Modal GPU tiers) and the The-Mailroom producer image
* [Modal + vLLM](../pipeline-reference-llm-mailroom/deployment/modal-vllm.md) — `mailroom-vllm` serve, pipeline cutover, multi-tier GPUs
* [Deployment](../pipeline-reference-llm-mailroom/deployment/) — laptop Python install, Hugging Face Spaces, backup

```bash
cp .env.example .env   # MAILROOM_API_TOKEN is required on every compose app
docker compose -f deploy/docker-compose.yml --env-file .env up -d --build
```

## Keys you will eventually need

| Key                                                             | Used by                                                       | Needed for                                            |
| --------------------------------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------------- |
| `OPENROUTER_API_KEY`                                            | pipeline, entity-extraction, eval-environment, agent-mailroom | Real LLM runs (the primary provider)                  |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` | pipeline, The-Mailroom, sandbox                               | Tracing, and anything The-Mailroom displays           |
| `BRAINTRUST_API_KEY`                                            | entity-extraction, eval-environment                           | Eval datasets and optional experiment logging         |
| `HF_TOKEN`                                                      | corpus repos, mailroom-ml                                     | Publishing datasets or models to `Lucius-Morningstar` |

Most repos have a mock mode for working without keys (`--mock` flags, or agent-mailroom's automatic `mock` fallback). The pipeline itself is stricter: outside mock runs, `get_llm` raises if `OPENROUTER_API_KEY` is missing.
