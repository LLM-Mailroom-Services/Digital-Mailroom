# OpenRouter call-site audit — Qwen3-8B hosted sunset (SAND-024)

**External clock:** hosted providers (QwenCloud Model Studio, Novita, OpenRouter
catalog) list **`Qwen/Qwen3-8B` / `qwen/qwen3-8b`-class hosted API ids** for
retirement on **2026-10-10**.

**Not on that clock:** self-hosted weights (`Qwen/Qwen3-8B` on Hub, Apache-2.0)
including Modal+vLLM, local vLLM, Ollama tags remapped from the champion map.

**Audit date:** 2026-09-26 (repo snapshot; regenerate with the grep recipes in
§6). No live OpenRouter calls were made to produce this document.

## Executive summary

| Question | Answer |
| --- | --- |
| Default sandbox path (`SANDBOX_PROFILE=ollama` / `modal-vllm`) hits OpenRouter on 2026-10-10? | **No** — local/OpenAI-compatible endpoints only. |
| Does the sandbox ever send `qwen/qwen3-8b` to OpenRouter? | **No in-tree pin** — champion slug is **`qwen/qwen3.7-flash`**, mapped locally to `Qwen/Qwen3-8B` (`config/models.yaml`). |
| Are there hosted-dependent call sites if an operator opts in? | **Yes** — profile `openrouter`, api-evals, and vendored `--real` scripts (see tables). |
| Does Oct 10 break Modal `Qwen/Qwen3-8B` deploys? | **No** — weights are self-hosted. |
| Maintenance before Oct 10? | **Hosted opt-in paths:** confirm OpenRouter still serves `qwen/qwen3.7-flash` (or migrate champion + `models.yaml` map). Treat **`qwen/qwen3-8b`** as dead on OpenRouter if your runbook still references it. |

Legend for **classification**:

- **local-only** — HTTP client targets non-OpenRouter `base_url` after profile activation (Modal/vLLM/Ollama/generic).
- **hosted-dependent** — live traffic to `https://openrouter.ai/api/v1` (or `OPENROUTER_BASE_URL`) with `OPENROUTER_API_KEY`.
- **dead / fallback-only** — unreachable unless operator explicitly selects OpenRouter provider *and* supplies a key; or test/mock-only.

**Breaks on 2026-10-10?** applies only to rows that are **hosted-dependent** *and* use a hosted id subject to the Qwen3-8B retirement (typically `qwen/qwen3-8b`). Rows using **`qwen/qwen3.7-flash`** depend on OpenRouter continuing to host that slug (separate from the weight retirement; verify in catalog before spend).

---

## 1. Sandbox configuration & overlay (first-party)

| Path | Model id (OpenRouter slug) | Hosted vs remapped-local | Class | Breaks 2026-10-10? |
| --- | --- | --- | --- | --- |
| `config/profiles/openrouter.yaml` | `qwen/qwen3.7-flash` (default) | **hosted** when profile active | hosted-dependent (opt-in) | Only if OpenRouter retires **this** slug; not the HF weight |
| `config/models.yaml` `defaults.openrouter` | `qwen/qwen3.7-flash` | champion → local map | config | N/A |
| `config/models.yaml` `map.qwen/qwen3.7-flash` | OR: `qwen/qwen3.7-flash`; vllm: `Qwen/Qwen3-8B` | remapped-local for non-OR profiles | local-only when not on OR profile | **No** (HF weights) |
| `config/mailroom.taxonomy.base.yaml` (agents `provider: openrouter`) | various OR slugs in base file | **overwritten** at runtime by overlay | dead / fallback-only in default runs | **No** on default path |
| `config/.env.example` (commented OR block) | — | documentation | dead / fallback-only | N/A |
| `src/mailroom_sandbox/runtime.py` `apply_profile_env` | inherits profile | sets `OPENROUTER_*` only for OR profile | local-only unless `openrouter` | **No** unless profile=openrouter |
| `src/mailroom_sandbox/overlay.py` `map_model` / `mailroom_provider` | champion rewrite | remapped-local | local-only for default profiles | **No** |
| `src/mailroom_sandbox/providers.py` | `openrouter` in `KNOWN_PROFILES` | registry | dead / fallback-only | N/A |
| `src/mailroom_sandbox/job/spec.py` `engine.kind: openrouter` | per run YAML | hosted when run | hosted-dependent (opt-in) | Per engine.model |
| `src/mailroom_sandbox/job/metrics.py` `API_PROFILES` | token $ proxy uses champion prices | accounting only | local-only | **No** |
| `src/mailroom_sandbox/eval/scoring.py` `_SANDBOX_API_PROFILES` | — | scoring branch | hosted-dependent when profile=api | Per model |
| `src/mailroom_sandbox/eval/runners.py` `local_vs_api` | fixture + live API path | mock default | dead / fallback-only unless live | Per model |
| `src/mailroom_sandbox/cli.py` (~1695) | comment: sorter without key | mock/offline guard | dead / fallback-only | **No** |

Default job YAMLs under `config/runs/` use **`modal-vllm`** + `Qwen/Qwen3-8B` → **local-only** (unaffected).

---

## 2. api-evals (OpenRouter-only harness)

All tasks pin **`profile: openrouter`**, **`engine.kind: openrouter`**, model
**`qwen/qwen3.7-flash`** (not `qwen/qwen3-8b`).

| Path | Model id | Class | Breaks 2026-10-10? |
| --- | --- | --- | --- |
| `api-evals/run_api_evals.py` | CLI entry | hosted-dependent when `run` / `run-all` | Per model slug |
| `api-evals/api_evals/invoke.py` | sets `OPENROUTER_API_KEY`; sandbox job runner | hosted-dependent | Per model slug |
| `api-evals/api_evals/cost.py` | `GET …/api/v1/models` (pricing only) | hosted-dependent (metadata) | **No** for inference; catalog drift risk |
| `api-evals/api_evals/registry.py` | `DEFAULT_API_MODEL = qwen/qwen3.7-flash` | config | Verify slug at cutover |
| `api-evals/config/runs/api-*.yaml` (6 files) | `qwen/qwen3.7-flash` | hosted-dependent | Verify slug at cutover |

Replacement champion: update `config/models.yaml` + api-evals YAMLs + `DEFAULT_API_MODEL` together; **Modal `modal_models` row is independent** (HF id swap does not fix hosted slugs).

---

## 3. Vendored llm-mailroom (family snapshot under `vendor/`)

These execute when `DEFAULT_PROVIDER=openrouter` (sandbox sets this only for the
`openrouter` profile). Default sandbox activation uses `ollama` / `vllm`.

| Path | Notes | Class | Breaks 2026-10-10? |
| --- | --- | --- | --- |
| `vendor/llm-mailroom/src/llm/providers.py` | `ProviderConfig` base `https://openrouter.ai/api/v1` | hosted-dependent | Per resolved model |
| `vendor/llm-mailroom/src/llm/client.py` | `get_llm()` OpenAI client to provider `base_url` | hosted-dependent | Per model |
| `vendor/llm-mailroom/src/langchain_agents/openrouter_utils.py` | `OPENROUTER_BASE_URL` / chat URL | hosted-dependent | Per model |
| `vendor/llm-mailroom/src/langchain_agents/classifier.py` | direct `requests.post(OPENROUTER_API_URL, …)` | hosted-dependent | Per model |
| `vendor/llm-mailroom/src/langchain_agents/base_agent.py` | `OPENROUTER_API_KEY`, `base_url` | hosted-dependent | Per model |
| `vendor/llm-mailroom/src/scripts/run_pilot.py` | `--real` + `_fetch_openrouter_prices()` | hosted-dependent | Per model |
| `vendor/llm-mailroom/src/scripts/run_quality_judges.py` | `--real` key check | hosted-dependent | Per model |
| `vendor/llm-mailroom/src/scripts/sync_evaluators.py` | Langfuse OpenRouter connection | hosted-dependent | Per model |
| `vendor/llm-mailroom/src/scripts/cutover.py` | `--provider openrouter` | hosted-dependent | Per `--model` |
| `vendor/llm-mailroom/src/scripts/gmail_smoke_test.py` | `--llm real` | hosted-dependent | Per model |
| `vendor/llm-mailroom/src/scripts/validate_pipeline.py` | sets mock `OPENROUTER_API_KEY` | test-only | **No** |
| `vendor/llm-mailroom/src/config/taxonomy.yaml` | `openrouter/free`, champion map to `Qwen/Qwen3-8B` | remapped-local in sandbox overlay | **No** on default path |

Family changes belong in upstream llm-mailroom + `sandbox fetch-deps`; this audit is the sandbox inventory.

---

## 4. Vendored llm-dojo-scoring

| Path | Notes | Class |
| --- | --- | --- |
| `vendor/llm-dojo-scoring/src/llm_dojo_scoring/field_scoring.py` | optional OR client for judge path | hosted-dependent if enabled |
| `vendor/llm-dojo-scoring/src/llm_dojo_scoring/serving.py` | OpenRouter-like **price table** for comparisons | accounting only (**local-only**) |

---

## 5. Hosted-dependent sites using Qwen3-8B **weights** vs **slugs**

| Serving kind | Identifier | Oct 10 exposure |
| --- | --- | --- |
| Modal / vLLM / Ollama (default matrix) | `Qwen/Qwen3-8B`, `qwen3:8b`, AWQ variants | **None** — self-hosted |
| OpenRouter champion (sandbox pin) | `qwen/qwen3.7-flash` | **Hosted API** — verify catalog; not the same string as `qwen/qwen3-8b` |
| OpenRouter legacy slug (not pinned in this repo) | `qwen/qwen3-8b` | **Would break** if used |

The entanglement called out in SAND-024: comparability uses **one champion OR slug**
mapped to **one local HF row** — retiring hosted `qwen/qwen3-8b` does **not**
automatically retire local `Qwen/Qwen3-8B` or the `qwen/qwen3.7-flash` champion.

---

## 6. Regenerating this audit

From repo root (offline-safe):

```bash
rg -n -i 'openrouter|OPENROUTER_API_KEY|OPENROUTER_BASE_URL' --glob '!vendor/**' .
rg -n -i 'openrouter|OPENROUTER' vendor/llm-mailroom/src vendor/llm-dojo-scoring/src
rg -n 'profile: openrouter|kind: openrouter' config api-evals
```

Review any new hits against the classification legend and update this file.

---

## 7. Recommended follow-ups (not blocking local-first work)

1. Before any OpenRouter spend: confirm `qwen/qwen3.7-flash` still listed (or pick a successor and update `config/models.yaml` + api-evals pins).
2. Do **not** point hosted runs at `qwen/qwen3-8b` after 2026-10-10.
3. Keep default profiles on `ollama` / `modal-vllm` for cost-eval; OpenRouter remains opt-in (`docs/providers.md`).
