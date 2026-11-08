---
description: 'Run on Ollama, vLLM or llama.cpp.'
icon: laptop-code
title: Local models
---

# Local models

Mailroom does not depend on one LLM provider. OpenRouter is the default provider. A change to local models (Ollama, llamafile, vLLM) is a configuration change, not a code change.

## Should you use local models?

| Reason | Local models help? |
| --- | --- |
| Documents must not leave your infrastructure | Yes. This is the main reason to use them. |
| You need to run with no internet connection | Yes. |
| You want to reduce cost | Sometimes. The measured OpenRouter cost is about $0.01 to $0.18 per document, so the saving is small at pilot volume. A GPU has its own cost. |
| You want better accuracy | Usually no. A 7B or 8B local model is smaller than the default champion. Measure it with a pilot before you depend on it. |

Three rules apply to every change on this page:

1. **Change one agent at a time, then measure.** The unit tests check the configuration, not the model quality. Only a `--real` pilot measures quality.
2. **Keep the Lane A reviewer different from the Sorter.** The reviewer gives a second opinion. If the Sorter and the `sorter_reviewer` use the same local model, the two opinions are not independent, and Lane A gives less protection.
3. **Record the previous value before each change.** Run `cutover.py --list` first, so you can go back to the exact model.

Compose sidecars (Ollama / llamafile) and the Mode G host stack: [Docker deployment](deployment/docker-deployment.md). Remote GPU OpenAI `/v1` (`mailroom-vllm`): [Modal + vLLM](deployment/modal-vllm.md).

***

## Architecture

The LLM layer is abstracted in two files:

```
llm/
├── client.py       # get_llm(agent_name) → OpenAI client
└── providers.py    # Provider configs: base URLs, models, auth
```

And one config file:

```
config/
└── taxonomy.yaml   # agents: section — per-agent provider + model
```

Provider selection flow:

```
taxonomy.yaml (agent config)
    → llm/client.py (resolve agent name)
        → llm/providers.py (resolve provider config)
            → openai.OpenAI(base_url=..., api_key=...)
```

***

## Available Local Models

### Recommended Primary Local Model: Qwen 3

**Qwen 3 7B** (`qwen3:7b`) is the recommended primary local model for Mailroom:

* Strong structured JSON output. Every specialist must return JSON that matches a Pydantic schema, so this is the most important property.
* Good legal text understanding.
* A 14B variant (`qwen3:14b`) is available for higher accuracy.
* It is in the same family as the default champion `qwen/qwen3.7-flash`, so the prompts need fewer changes.

### Full Local Model Catalog (Ollama)

| Model Family     | Available Sizes | Strengths                       | Weaknesses                  |
| ---------------- | --------------- | ------------------------------- | --------------------------- |
| **Qwen 3**       | 7b, 14b         | Structured output, legal text   | Medium resource usage       |
| **Qwen 2.5**     | 14b, 32b        | Multilingual, strong extraction | Larger size                 |
| **Llama 3.1**    | 8b, 70b         | Reliable all-around             | Weaker structured output    |
| **Llama 3.2**    | 3b              | Very fast, lightweight          | Limited complex extraction  |
| **Mistral**      | 7b              | Fast, good instructions         | Less legal domain knowledge |
| **Mistral Nemo** | 12b             | Good speed/quality balance      | —                           |
| **Mixtral**      | 8x7b            | MoE — strong extraction         | Higher memory usage         |
| **DeepSeek-R1**  | 8b, 14b         | Legal reasoning, analysis       | Slower inference            |
| **Phi-4**        | 14b             | Document understanding          | —                           |
| **Gemma 2**      | 9b, 27b         | Instruction following           | —                           |
| **Command R**    | 35b, 104b       | RAG, extraction                 | Very high resource usage    |

***

## Phase 1: Global Cutover (Fastest)

Set a single environment variable to switch ALL agents to local:

```bash
export DEFAULT_PROVIDER=ollama
```

All agents now use Ollama. The pipeline changes each agent's OpenRouter model name to an Ollama tag with `ollama_model_map` in `src/config/taxonomy.yaml` (`llm/client.py: _self_hosted_model`). The current map:

| Taxonomy model (OpenRouter) | Ollama tag | llamafile alias | vLLM model id |
| --- | --- | --- | --- |
| `qwen/qwen3.7-flash` | `qwen3:7b` | `qwen3:7b` | `Qwen/Qwen3-8B` |
| `deepseek/deepseek-v4-flash` | `deepseek-r1:8b` | `qwen3:7b` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` |
| `deepseek/deepseek-v4-pro` | `deepseek-r1:14b` | `qwen3:14b` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B` |
| `openrouter/free` | `qwen3:7b` | `qwen3:7b` | `Qwen/Qwen3-8B` |

Pull each tag in the map before you start (`ollama pull qwen3:7b`). If the Ollama library has no `qwen3:7b` tag, pull `qwen3:8b` and change the mapped tag in `taxonomy.yaml` to match. If a model has no entry in the map, the pipeline sends the name unchanged, and Ollama returns "model not found". Self-hosted providers are exempt from the `MAILROOM_LLM_FREE_ONLY` guard because they have no per-token price.

***

## Phase 2: Agent-by-Agent Cutover (Recommended)

Move one agent, measure it, then move the next agent. If quality drops, you know which agent caused it.

### Recommended Cutover Order

Start with the agents whose errors a later check catches. Move the agents whose errors reach the archive last.

| Order | Agent (taxonomy key) | Why this position |
| ----- | -------------------- | ----------------- |
| 1 | `sorter` | The confidence gates, the retry and the Lane A reviewer catch a wrong class. Keep `sorter_reviewer` on a different model. |
| 2 | `correspondence_specialist` | It has the lowest thresholds and the smallest cost of an error. |
| 3 | `corporate_records_specialist` | Its records have a regular structure. |
| 4 | `insurance_claims_specialist` | Its thresholds are high (0.98 / 0.90), so weak output goes to review more often. |
| 5 | `contracts_specialist`, `merger_agreement_specialist` | Long documents (up to 100,000 characters) and precise legal fields. |
| 6 | `judge`, `arbiter`, `boss` | They check the other agents. Move them last, and keep them on a different model from the specialists if you can. |

The `reporter` key exists in the taxonomy, but report compilation is procedural, so no LLM call uses it. The due-diligence and court-opinion specialists were retired in v0.5.0. `pdf_transcriber` and `image_extractor` need a vision model. See [Vision pages not being sent](#vision-pages-not-being-sent).

### Using the Cutover Utility

```bash
# 1. See current assignments
PYTHONPATH=src python src/scripts/cutover.py --list

# 2. Move one agent to local
PYTHONPATH=src python src/scripts/cutover.py --agent sorter --provider ollama --model qwen3:7b

# 3. Validate with tests
PYTHONPATH=src python src/scripts/cutover.py --validate --agent sorter

# 4. If validation passes, move to the next agent
PYTHONPATH=src python src/scripts/cutover.py --agent contracts_specialist --provider ollama --model qwen3:7b
PYTHONPATH=src python src/scripts/cutover.py --validate --agent contracts_specialist

# 5. If validation or the pilot fails, restore the provider and model that step 1 showed
#    (the values below are the shipped defaults; use your own recorded values if they differ)
PYTHONPATH=src python src/scripts/cutover.py --agent sorter --provider openrouter --model qwen/qwen3.7-flash
```

### Manual Cutover (Direct YAML Edit)

Edit `config/taxonomy.yaml`:

```yaml
agents:
  sorter:
    provider: ollama            # ← changed from openrouter
    model: qwen3:7b             # ← changed from qwen/qwen3.7-flash
    temperature: 0.1
```

***

## Phase 3: Full Validation

After all agents are cut over, run two checks. They answer different questions.

```bash
# 1. Configuration: the tests use a mock LLM, so they prove the plumbing, not the model
pytest -v

# 2. Quality: run the same pilot on the local models and compare with a cloud baseline
PYTHONPATH=src python src/scripts/run_pilot.py --real --baseline data/pilot_report_baseline_real_<stamp>.json
```

Make the baseline with a `--real` pilot on the cloud configuration before the cutover. Each `--real` run writes a dated copy, `pilot_report_baseline_real_<stamp>.json`, next to its report. The `--baseline` flag prints the overall and per-class difference. Look at classification accuracy, the field scores, and the share of documents that go to review. A local model that sends twice as many documents to review costs operator time, even if its accepted results are correct.

***

## Provider Comparison Table

| Capability             | OpenRouter (GPT-4o)   | Ollama (Qwen 3 7B)   | Ollama (Llama 3.1 8B) |
| ---------------------- | --------------------- | -------------------- | --------------------- |
| Structured JSON output | Excellent             | Very Good            | Good                  |
| Legal terminology      | Excellent             | Good                 | Fair                  |
| Instruction following  | Excellent             | Good                 | Very Good             |
| Inference speed        | Depends on provider   | Fast (local GPU)     | Fast (local GPU)      |
| Cost per document      | \~$0.012–0.18 measured | $0 (local)           | $0 (local)            |
| Data privacy           | Documents leave infra | Documents stay local | Documents stay local  |
| Availability           | Requires internet     | Fully offline        | Fully offline         |

The OpenRouter cost is the **measured** range across the 20-document pilot runs in [Scoring and performance](../the-pipeline-in-depth/scoring-and-metrics.md) ($0.012063 to $0.177431), not an estimate. It changes with the specialist, the document length, and the number of retry or arbiter passes. The other ratings are a qualitative assessment, not a benchmark (see [Sources](#sources)).

***

## Hybrid Mode

You can run a mix of providers simultaneously. For example:

```yaml
agents:
  sorter:
    provider: ollama              # Fast local classification
    model: qwen3:7b

  contracts_specialist:
    provider: openrouter          # Cloud for complex contracts
    model: openai/gpt-4o

  insurance_claims_specialist:
    provider: openrouter          # Cloud for claim documentation
    model: openai/gpt-4o
```

This gives you cost savings on simpler tasks while retaining accuracy on complex ones.

***

## Hardware Requirements

| Model Size | Min RAM | Recommended RAM | Min VRAM (GPU) |
| ---------- | ------- | --------------- | -------------- |
| 7B/8B      | 8 GB    | 16 GB           | 6 GB           |
| 12B-14B    | 16 GB   | 32 GB           | 10 GB          |
| 32B-35B    | 32 GB   | 64 GB           | 24 GB          |
| 70B+       | 64 GB   | 128 GB          | 48 GB          |

For pilot scale (dozens of documents/day), a machine with 16GB RAM and a GPU with 8GB+ VRAM running qwen3:7b is sufficient.

***

## Troubleshooting Local Models

### Model not found

```bash
# List available models
docker exec mailroom-ollama ollama list

# Pull a model
docker exec mailroom-ollama ollama pull qwen3:7b
```

### Connection refused / provider not reachable

If the pipeline logs `APIConnectionError` or `ConnectError`:

1.  Verify the service is running:

    ```bash
    # Ollama (Docker)
    docker compose -f src/config/docker/docker-compose.yml --profile local-llm ps
    curl http://localhost:11434/v1/models

    # vLLM
    curl http://localhost:8000/v1/models
    ```
2. Confirm `OLLAMA_BASE_URL` / `VLLM_BASE_URL` matches the service (defaults: `http://localhost:11434/v1`, `http://localhost:8000/v1`). Note the **`/v1` suffix is required** — the OpenAI SDK appends `/chat/completions`, so omitting it produces a 404/connection error.
3. If running Ollama **on the host** (not Docker), make sure it exposes the OpenAI-compatible endpoint: `OLLAMA_HOST=0.0.0.0 ollama serve`.
4. If agents still resolve to OpenRouter, make sure `DEFAULT_PROVIDER` does not override them: `PYTHONPATH=src python src/scripts/cutover.py --list` shows the effective provider per agent.

### HTTP 404 on `/models` or `/chat/completions`

The OpenAI SDK needs the OpenAI-compatible base URL. For Ollama that is `http://<host>:11434/v1` (the raw `:11434` root is not OpenAI-compatible). For vLLM it is `http://<host>:8000/v1`. Double-check there is no trailing slash and no extra path.

### Structured output failures

Some local models struggle with strict JSON schema mode. If you see `_parse_error: true` in extraction results:

1. Try a larger model (14B instead of 7B)
2. Try Llama 3.1 or DeepSeek-R1 for better instruction following
3. Fall back to OpenRouter for that specific agent

### JSON `json_object` mode rejected (HTTP 400)

`agents/base.py:_call_structured` deliberately embeds the literal token `json` in both the system and user messages (some providers gate `response_format: json_object` on that word). If a **local** provider still rejects the request:

1. Check whether the provider supports `response_format` at all — some local serving stacks only accept it for specific models.
2. If your local model does not support `json_object`, use a model that does (Qwen family), or route the offending agent back to OpenRouter.
3. vLLM: use an engine version that supports `guided_json`/structured output and confirm the model is served with a compatible chat template.

### Vision pages not being sent

Page images are only attached when the agent's model matches a `vision.models` substring in `taxonomy.yaml`. If your local model accepts images but pages never appear:

1. Add the model substring to `vision.models` (e.g. `"qwen"`, `"llava"`).
2. Confirm that `MAILROOM_VISION_ENABLED` does not force vision off.
3. Confirm `pymupdf` (fitz) is installed. PDF→image rendering requires it (`llm/vision.py`). Without it, `_render_doc_pages` is skipped regardless of config.

### Slow inference

* Use quantized models (`qwen3:7b-q4_K_M` for GGUF quants)
* Enable GPU passthrough in Docker Compose
* Reduce context window (per-agent `max_input_chars` overrides run from **12,000** chars for the sorter/reviewer up to **100,000** for the contracts specialist; the global fallback when an agent sets none is **25,000** — see [Configuration](configuration.md). Set yours accordingly)
* Check the model actually runs on GPU: `docker exec mailroom-ollama ollama ps` (a CPU-only model shows no GPU line)

### OOM / out-of-memory

* Drop to a smaller quant (e.g. `qwen3:7b-q4_K_M` instead of `qwen3:7b` fp16)
* Reduce `num_ctx`/`num_gpu` in the Ollama model config (`ollama run --keepalive` or Modelfile)
* For vLLM, lower `--max-model-len` and `--gpu-memory-utilization` to free VRAM

### Cutover validation fails

`PYTHONPATH=src python src/scripts/cutover.py --validate --agent <name>` runs the unit tests against the new provider/model. If it fails:

1. Check the agent's `provider` and `model` values resolved correctly: `PYTHONPATH=src python src/scripts/cutover.py --list`
2. Confirm the model is pulled: `docker exec mailroom-ollama ollama list`
3. The tests never hit the real LLM — they validate the config plumbing, not the model's accuracy. For accuracy, run a pilot: `PYTHONPATH=src python src/scripts/run_pilot.py --real --source <corpus>`

### Consistent low confidence / routes to review

Smaller local models are often over-confident or under-confident. If everything lands in `review`:

1. Verify the agent model actually serves the taxonomy classes (a model not fine-tuned for legal text may classify poorly).
2. Compare against OpenRouter with `PYTHONPATH=src python src/scripts/run_vision_sweep.py --real` or a pilot diff: `PYTHONPATH=src python src/scripts/run_pilot.py --real --baseline data/pilot_report_baseline.json`.
3. Adjust `confidence.high` / `confidence.low` in `taxonomy.yaml` — thresholds are config, not code.

## Sources

| Claim on this page | Source of record |
| ------------------ | ---------------- |
| Cost per document (~$0.012–0.18) | Measured — the 20-document pilot runs in [Scoring and performance](../the-pipeline-in-depth/scoring-and-metrics.md), per-run reports under eval-environment `reports/api-comparisons/` |
| Capability comparison (GPT-4o vs Qwen 3 7B vs Llama 3.1 8B) | **Qualitative operator assessment, not a benchmark.** There is no head-to-head run recorded on this page; treat the Excellent/Good/Fair ratings as judgement, and use the pilot/eval reports for measured quality. |
| Hardware and VRAM requirements | **Vendor-documented model sizes plus operator experience**, not a measured sweep. Sizes come from the models' own cards (Qwen 3 7B, Llama 3.1 8B); the VRAM figures assume 4-bit quantization and leave no headroom for a second loaded model. |
| `max_input_chars` budgets (12,000 / 25,000 / 100,000) | [`src/config/taxonomy.yaml`](https://github.com/Exios66/llm-mailroom/blob/main/src/config/taxonomy.yaml) — per-agent overrides with a global fallback; documented in [Configuration](configuration.md) |
