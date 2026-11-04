---
name: ollama
description: Offline/CPU fallback Ollama provider for local-mailroom-sandbox (compose sandbox-ollama, pull-models, health, cutover). Use for offline/local inference, qwen3:8b / llama3.2:3b smoke, and any SANDBOX_PROFILE=ollama work — not the default (modal-vllm is); prefer it over OpenRouter and Modal only when offline, CPU-only or without a Modal account.
---

# Ollama (offline/CPU fallback provider)

**When:** Offline or CPU-only inference, `--profile ollama`, CPU smoke, mock→local pilots without a Modal endpoint.  
**Prefer over:** OpenRouter (opt-in API) and Modal/vLLM when offline or CPU-only; the default profile is `modal-vllm`.

## Profile

`config/profiles/ollama.yaml`:

| Field | Value |
| --- | --- |
| Provider | `ollama` |
| Base URL | `http://localhost:11434/v1` (`OLLAMA_BASE_URL`) |
| Default model | `qwen3:8b` (fallback `qwen3:7b`) |
| Compose | `langfuse` + `ollama` |

## Commands

```bash
sandbox up -d --compose-profile langfuse --compose-profile ollama   # the default modal-vllm profile starts langfuse only
sandbox pull-models --profile ollama                     # ollama pull qwen3:8b (container or host)
sandbox pull-models llama3.2:3b --profile ollama         # CPU smoke
sandbox cutover --profile ollama --model llama3.2:3b
sandbox cutover --profile ollama --agent-model judge=qwen3:14b
sandbox health --profile ollama
sandbox pilot --mock
sandbox pilot --local --profile ollama
```

Pull prefers `docker exec sandbox-ollama ollama pull …`, else host `ollama`.

## Overlay rules

1. `runtime.activate("ollama")` before mailroom imports.  
2. `config/models.yaml` maps OpenRouter champion ids → local tags — never send `qwen/qwen3.7-flash` to Ollama.  
3. `--model` rewrites every agent; `--agent-model NAME=tag` wins last.  
4. Inside Jupyter compose: `OLLAMA_BASE_URL=http://ollama:11434/v1`.

## When to switch away

| Need | Switch to |
| --- | --- |
| Host NVIDIA, OpenAI `/v1` locally | profile `vllm-local` + compose `vllm` → see [modal](../modal/SKILL.md) only for remote |
| Remote GPU without local cards | [modal](../modal/SKILL.md) (`modal-vllm`) |
| GGUF / LM Studio | profiles `llamacpp` / `lmstudio` |
| Cloud API comparison | `openrouter` (opt-in key only) |

## Related

- Router: [sandbox-tool-router](../sandbox-tool-router/SKILL.md)  
- Providers doc: `docs/setting-up/providers.md`
