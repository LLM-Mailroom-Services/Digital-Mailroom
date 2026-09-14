<div align="center">

# 🌐 Provider Profiles

**Serving profiles for the local-mailroom-sandbox package.**

</div>

---

## Files

| File | Purpose |
|:---|:---|
| [`ollama.yaml`](ollama.yaml) | Local Ollama (`:11434/v1`) |
| [`vllm-local.yaml`](vllm-local.yaml) | Local vLLM (`:8000/v1`) |
| [`vllm-remote.yaml`](vllm-remote.yaml) | Remote vLLM (tunneled/SSH) |
| [`modal-vllm.yaml`](modal-vllm.yaml) | Modal-deployed vLLM endpoint |
| [`llamacpp.yaml`](llamacpp.yaml) | llama.cpp server (`:8080/v1`) |
| [`lmstudio.yaml`](lmstudio.yaml) | LM Studio local server |
| [`openrouter.yaml`](openrouter.yaml) | OpenRouter cloud API |

## Usage

Select a profile with the **`SANDBOX_PROFILE`** environment variable:

```bash
SANDBOX_PROFILE=vllm-local sandbox up
sandbox tunnel --profile vllm-remote plan
```

See `docs/SANDBOX-GUIDE.md` (profiles + tunnel sections) for the full flow.

## Related Files

- `../` — Configuration root
- `../../src/` — Source code