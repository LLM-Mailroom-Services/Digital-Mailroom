# Providers

The sandbox never hardcodes a model inside agent code. `runtime.activate(profile)`
rewrites every `taxonomy.yaml` agent to the profile's provider + local tag, then
points mailroom at `data/runtime/taxonomy.yaml`.

| Profile | Mailroom provider | Default base URL | Default model |
| --- | --- | --- | --- |
| `modal-vllm` (default) | `vllm` | Modal `*.modal.run/v1` | `Qwen/Qwen3.5-9B` (online fp8) |
| `ollama` (offline) | `ollama` | `http://localhost:11434/v1` | `qwen3:8b` |
| `vllm-local` | `vllm` | `http://localhost:8000/v1` | `Qwen/Qwen3.5-9B` (compose serves it bf16) |
| `vllm-remote` | `vllm` | `http://localhost:18000/v1` (SSH forward) | `Qwen/Qwen3.5-9B` |
| `llamacpp` | `generic` | `http://localhost:8080/v1` | `qwen3-8b` |
| `lmstudio` | `generic` | `http://localhost:1234/v1` | `qwen3-8b` |
| `openrouter` | `openrouter` | `https://openrouter.ai/api/v1` | `qwen/qwen3.5-9b` (same weights as the Modal default) |

Remote serving — Modal deployment (the **default path**: `sandbox runbook show serve`),
SSH-tunnel workflow (`sandbox tunnel`), CHTC/HTCondor job paths, and the
portable conda env — is documented in
[`remote-serving.md`](remote-serving.md).

OpenRouter is **opt-in**. The default `.env` does not set `OPENROUTER_API_KEY`.
For the 2026-10-10 hosted **Qwen3-8B** catalog sunset vs local weights, see
[`openrouter-sunset-audit.md`](../archive/openrouter-sunset-audit.md) (SAND-024 / issue #30).
Comparable serving metrics (TTFT, throughput, GPU on local only) are scored
with `sandbox eval local_vs_api --mock` via dojo `get_suite("local_vs_api")` —
no API key is required for the fixture path.

**OpenRouter evaluation preference (SAND-077).** `config/models.yaml`
`openrouter_preference` ranks three open-weights models. Each has a Hugging Face
id that Modal+vLLM can serve, so an API run is directly comparable to its Modal
counterpart:

1. `qwen/qwen3.5-9b`: the same weights as the Modal default `Qwen/Qwen3.5-9B`.
   It is also the `openrouter` profile default.
2. `qwen/qwen3.5-35b-a3b`: `Qwen/Qwen3.5-35B-A3B`, the Modal `L4:2` TP=2 row.
3. `qwen/qwen3.5-27b`: `Qwen/Qwen3.5-27B` (dense; the Modal judge tier on
   `L40S`).

OpenRouter serves each id from several hosts at different precisions, from fp4
to bf16 (`GET /api/v1/models/<id>/endpoints`). Outputs can therefore differ from
a Modal run even on the same weights. The `openrouter` profile's judge stays
`deepseek/deepseek-v4-flash`.

**Judge tier on Modal (SAND-078).** On Modal the judge runs a larger, more
capable sibling of the base model: `Qwen/Qwen3.5-27B` at fp8 on its own `L40S`
app, beside the 9B base engine. `config/models.yaml` `critical_tier.judge`
defines the route. `sandbox experiment create --provider modal-vllm --task
pipeline` adds it unless `--agent-route judge=...` or `--agent-model judge=...`
already sets the judge. Plain `sandbox run` configs do not deploy route apps,
so add the judge route there only when its app is already up. The run's
`cost_cap_usd` prices every Modal app the run keeps warm, so the judge's L40S
(and a `mid` specialist app) count toward the cap.

**Specialist tiers (SAND-079).** The five specialists stay on the base model
unless `sandbox experiment create --specialist-tier` moves them:

| Tier | Modal / vLLM | OpenRouter | Extra Modal GPU |
| --- | --- | --- | --- |
| `base` (default) | the run's model (`Qwen/Qwen3.5-9B`) | the run's model | none |
| `mid` | `Qwen/Qwen3.5-35B-A3B` (MoE, fp8, `L4:2`) | `qwen/qwen3.5-35b-a3b` | one `L4:2` app |
| `full` | `Qwen/Qwen3.5-27B`, the judge's own route | `qwen/qwen3.5-27b` | none beyond the judge's `L40S` |

`full` shares the judge's app, so it adds no deployment. An explicit
`--agent-route` or `--agent-model` for one specialist overrides the tier for
that specialist. The tiers apply to `specialists` and `pipeline` experiments,
not the frozen `sand42` study. `config/models.yaml`
`critical_tier.specialists` defines them.

## Why an overlay

`DEFAULT_PROVIDER=vllm` alone still sends the OpenAI-compatible endpoint the
OpenRouter id `qwen/qwen3.7-flash`. `config/models.yaml` maps champion ids onto
served ids (the `vllm` column is the `modal-vllm` default).
`sandbox cutover --agent-model judge=qwen3:14b` is the surgical override
(`--model` still rewrites every agent). Overlay knobs (temperature, max_tokens,
…) live in `config/taxonomy.overlay.yaml` and win after the profile rewrite.

## Health

`sandbox health` GETs `{base}/models` and posts a 1-token `json_object` chat.
If the engine rejects structured output, the probe reports `json_object_ok: false`.

## Compose / Modal

See [`deploy/README.md`](../../deploy/README.md). GPU is required for the `vllm`
compose profile; Ollama can run on CPU for tiny models.
