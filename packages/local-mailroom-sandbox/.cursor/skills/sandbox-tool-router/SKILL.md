---
name: sandbox-tool-router
description: Choose the correct local-mailroom-sandbox tool for serving, tracing, datasets, and deploy. Use at the start of any sandbox, eval, observability, Ollama, Modal, Langfuse, Braintrust, Phoenix, Hugging Face, or provider task so only the most appropriate skill/stack is used.
---

# Sandbox tool router

Read this skill **first** when the task touches providers, tracing, datasets, Docker, or deploys. Then open exactly one specialty skill below. Do not invent a second tracing backend or cloud LLM path when the local-first default already fits.

## Decision table

| Job | Use | Skill | Do **not** use |
| --- | --- | --- | --- |
| Default local LLM inference | Ollama (`SANDBOX_PROFILE=ollama`) | [ollama](../ollama/SKILL.md) | OpenRouter, Modal, vLLM (unless GPU/Modal requested) |
| GPU / remote OpenAI-compatible serve | Modal vLLM (`modal-vllm`) or compose `vllm` | [modal](../modal/SKILL.md) | Ollama for 70B-class / long-context GPU work |
| Default tracing + The-Mailroom | Langfuse 3 / SDK v4 | [langfuse](../langfuse/SKILL.md) | Phoenix as the only sink if The-Mailroom is required |
| Optional OTEL / Arize UI sidecar | Apache Phoenix compose profile | [apache-phoenix](../apache-phoenix/SKILL.md) | Phoenix as The-Mailroom input |
| Hosted eval / experiment logs (opt-in) | Braintrust | [braintrust](../braintrust/SKILL.md) | Braintrust as the default offline sink |
| Hub datasets / model cards / HF cache | Hugging Face Hub + `sandbox datasets pull` | [huggingface](../huggingface/SKILL.md) | Live Hub pulls in default pytest |
| Offline fixture prep | `sandbox datasets prepare` + notebooks | (prep helpers; no cloud) | Hub network in CI |

## Observability precedence (`OBSERVABILITY_PROVIDER`)

Canonical default in `.env`: **`langfuse`**.

When `auto`:

1. Langfuse if `LANGFUSE_SECRET_KEY` is set  
2. else Braintrust if `BRAINTRUST_API_KEY` is set  
3. else Phoenix if `PHOENIX_TRACING` ≠ `disabled`  
4. else `none`

Sandbox evals implement the Langfuse v4 `document-pipeline` contract in `mailroom_sandbox.eval.tracing`. Phoenix/Braintrust are alternate sinks — they do **not** replace that family schema for The-Mailroom.

## Serving precedence

1. **`--mock` / offline prep** — no live LLM  
2. **Ollama** — default local path (`sandbox up`, `sandbox pull-models`)  
3. **vLLM local** — NVIDIA host + compose profile `vllm`  
4. **Modal vLLM** — remote GPU; `pip install -e ".[deploy]"` + pre-warm + `modal deploy` (see [modal](../modal/SKILL.md))
5. **llama.cpp / LM Studio** — generic OpenAI base URL profiles  
6. **OpenRouter** — opt-in only (`OPENROUTER_API_KEY`); never the sandbox default  

Always `mailroom_sandbox.runtime.activate(profile)` before importing mailroom graph/agents. Rewrite models via overlay / `--agent-model`; do not hardcode OpenRouter ids into Ollama.

## Repo anchors

| Concern | Path |
| --- | --- |
| Profiles | `config/profiles/*.yaml` |
| Env template | `config/.env.example` |
| Compose + Dockerfile | `deploy/docker-compose.yml`, `deploy/Dockerfile` |
| Modal app | `deploy/modal_vllm.py` |
| Tracing | `docs/tracing.md`, `src/mailroom_sandbox/eval/tracing.py` |
| Providers | `docs/providers.md` |
| Offline Docker + notebooks | `docs/docker-offline.md` |
| Project skills (this tree) | `.cursor/skills/*/SKILL.md` |

## Quick commands

```bash
sandbox profiles
sandbox cutover --profile ollama
sandbox up                                          # langfuse + ollama
sandbox up --compose-profile phoenix                # optional sidecar
sandbox health
sandbox datasets prepare                            # offline
sandbox datasets pull                               # Hub (network)
```
