# Offline sandbox

`packages/local-mailroom-sandbox` is a **local-first experiment harness**
around the governed LLM-Mailroom family. It does not reimplement the
13-node graph — it activates profiles, patches config paths, and evals
against the real pipeline (in the monorepo via `[tool.uv.sources]`; see
[[Sub-Package-Sync]]).

## Provider profiles

`config/profiles/*.yaml` — **ollama is the sandbox default**; all offline
first:

| Profile | Provider | Default model |
| --- | --- | --- |
| `ollama` | Ollama (OpenAI-compatible, :11434) | qwen3:8b |
| `vllm-local` | vLLM server (:8000) | — |
| `llamacpp` | llama.cpp server (:8080) | — |
| `lmstudio` | LM Studio (:1234) | — |
| `modal-vllm` | Remote GPU vLLM (`sandbox-vllm` on Modal) | Qwen/Qwen3-8B |
| `openrouter` | Opt-in cloud (never the default) | — |

OpenRouter model ids are rewritten to local serving tags via the overlay —
`DEFAULT_PROVIDER` alone is not enough.

## Reduced agent profile (HUB-015)

- The **reporter agent is retired**: `components.yaml` lists it under
  `retired_agents`. The compile stage is the **computational procedural
  reporter** — the graph's `compile_report` node backed by llm-mailroom
  v0.6.0's `compile_matter_record`: deterministic matter-record assembly,
  **no LLM call**; the sandbox eval never acquires an LLM client for it.
- **Reviewers stay enabled** (`sorter_reviewer` +
  `sorter_reviewer_local_v0` prompt) — the reduced profile removes the
  reporter, not the reviewers.
- Per-agent gates live in `config/components.yaml` (eval skip + routing
  overlay; they do not fork the graph).

## HF targets aligned to the corpus

`data/fixtures/hf/docclass_mini.jsonl` covers all 5 doc types with full
mailroom-corpus ground-truth targets: `expected_subclass` from the corpus
strata vocabulary + `expected_fields` from the 27-key GT schema
(correspondence intent + provenance; insurance claim entities). See
[[HF-Corpus]].

## Docker (offline)

```bash
sandbox up --compose-profile langfuse --compose-profile ollama --compose-profile jupyter
```

- Images are **version-pinned** (ollama `0.33.2`, vllm `v0.28.0`, phoenix
  `version-20.4.0`, minio `RELEASE.2025-09-07…`, langfuse `3`, redis `7`,
  clickhouse `24-alpine`, pgvector `pg16`).
- The sandbox image (`mailroom-sandbox:offline`) runs as a **non-root
  user** (uid 1000; override with `--user "$(id -u):$(id -g)"`) with a
  **HEALTHCHECK** on Jupyter Lab (:8888).
- Stateful services carry healthchecks; Langfuse 3 init keys come from the
  environment (headless, no web wizard).
- Full guide: [`docs/docker-offline.md`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/packages/local-mailroom-sandbox/docs/docker-offline.md).

## Commands

```bash
sandbox profiles / agents list / cutover --profile ollama --agent-model judge=qwen3:14b
sandbox up / pull-models / health / fetch-deps     # fetch-deps clones llm-mailroom @ v0.6.0
sandbox pilot --mock                               # no LLM
sandbox eval sorter --mock                         # isolated agent evals
sandbox eval pipeline --mock                       # connected graph scores
sandbox eval local_vs_api --mock                   # offline vs API serving comparison
sandbox matrix --providers ollama --models qwen3:8b --prompts sorter_local_v0 --mock --dry-run
pytest -v                                          # network-free; live tests need SANDBOX_LOCAL_LLM=1
sandbox datasets prepare                           # offline JSONL under data/runtime/prepared/
```

Tracing default: Langfuse 3 / SDK v4 (`OBSERVABILITY_PROVIDER=langfuse`).
Phoenix is an optional sidecar; Braintrust opt-in; OpenRouter only when
explicitly chosen.
