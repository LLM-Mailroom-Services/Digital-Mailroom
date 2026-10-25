<div align="center">

<picture>
  <source media="(max-width: 640px)" srcset="docs/assets/readme/hero-mobile.svg"/>
  <img src="docs/assets/readme/hero.svg" alt="local-mailroom-sandbox: seven provider profiles feed the vendored 13-node llm-mailroom graph, whose runs are scored by the vendored llm-dojo-scoring and traced to Langfuse" width="100%"/>
</picture>

<br/>

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](pyproject.toml)
[![Pipeline](https://img.shields.io/badge/pipeline-llm--mailroom_vendored-2563EB?style=for-the-badge)](vendor/llm-mailroom/VENDOR.md)
[![Scoring](https://img.shields.io/badge/scoring-llm--dojo--scoring_vendored-8B5CF6?style=for-the-badge)](vendor/llm-dojo-scoring/VENDOR.md)
[![Tracing](https://img.shields.io/badge/tracing-Langfuse_v4-F5A623?style=for-the-badge)](docs/tracing.md)

[![Hub](https://img.shields.io/badge/🏛️_hub-Digital--Mailroom-000?style=flat-square)](https://github.com/LLM-Mailroom-Services/Digital-Mailroom)
[![Quickstart](https://img.shields.io/badge/📘_guide-QUICKSTART-555?style=flat-square)](docs/setting-up/QUICKSTART.md)
[![Providers](https://img.shields.io/badge/🔌_providers-seven_profiles-555?style=flat-square)](docs/setting-up/providers.md)

**[Quickstart](#quickstart)** · **[How it works](#how-it-works)** · **[At a glance](#at-a-glance)** · **[CLI](#cli)** · **[Docs](#docs)** · **[Where it fits](#where-it-fits)**

</div>

---

<!-- readme-v2.1 -->
<details>
<summary><b>📑 Contents</b></summary>

- [🧪 What is this?](#what-is-this)
- [🤔 When to reach for it](#when-to-reach-for-it)
- [🚀 Quickstart](#quickstart)
- [🧭 How it works](#how-it-works)
- [📟 At a glance](#at-a-glance)
- [⌨️ CLI](#cli)
- [📚 Docs](#docs)
- [✍️ Specialist extraction rules](#specialist-extraction-rules)
- [🗂️ Layout](#layout)
- [🐳 Offline Docker and notebooks](#offline-docker--notebooks)
- [🌌 Where it fits](#where-it-fits)
- [❓ FAQ](#faq)
- [🙏 Built on](#built-on)
- [🤝 Contributing, security and license](#contributing-security-and-license)

</details>

<a id="what-is-this"></a>

## 🧪 What is this?

A local-first experiment sandbox for the LLM-Mailroom pipeline. It runs the
full classify → extract → report → archive graph on your own machine with
Ollama, vLLM, llama.cpp or LM Studio, or on a rented GPU through Modal. Swap in
OpenRouter when you need an API provider; it is opt-in and never the default.

This repository does **not** fork the pipeline. It ships the family code it
needs as **tracked snapshots under `vendor/`** (DMR-057): the pipeline
(`llm-mailroom`) and the scoring engine (`llm-dojo-scoring`) are self-contained
copies, each pinned to an exact source commit in its `VENDOR.md`, with config,
serving, eval and scoring overlays on top.

<div align="center">
<picture>
  <source media="(max-width: 640px)" srcset="docs/assets/readme/stats-mobile.svg"/>
  <img src="docs/assets/readme/stats.svg" alt="By the numbers: seven provider profiles, two vendored snapshots, a 13-node graph, five document classes, a 3,302-row pinned dataset pull, and a mock mode that needs no LLM" width="100%"/>
</picture>
</div>

<a id="when-to-reach-for-it"></a>

## 🤔 When to reach for it

| ✅ Reach for it when… | ↪️ Look elsewhere when… |
| :--- | :--- |
| You want to run the real mailroom graph against a local or self-hosted model, offline, before you spend anything | You want to change the pipeline itself. Its source is [llm-mailroom](https://github.com/Exios66/llm-mailroom); the copy under `vendor/` is a snapshot |
| You need to compare providers, models and prompt versions on the same documents and score them the same way | You want to change a metric. Scoring lives in [llm-dojo-scoring](https://github.com/Exios66/llm-dojo-scoring) |
| You are bringing up vLLM locally, over an SSH tunnel or on Modal, and want health checks, run specs and a watch view | You want to train a classifier. Training lives in [mailroom-ml](https://github.com/LLM-Mailroom-Services/mailroom-ml) |

<a id="quickstart"></a>
<a id="quick-start"></a>
<a id="one-command-local-path"></a>

## 🚀 Quickstart

<div align="center">
<img src="docs/assets/readme/terminal.svg" alt="Animated terminal: install, copy the env file, bring up Langfuse and Ollama, pull the model, check health, then run the pilot with the mock and with a local model" width="90%"/>
</div>

```bash
pip install -e ".[dev]"
cp config/.env.example .env
# family code is already vendored under vendor/ (self-contained); fetch-deps
# only refreshes the snapshots (workspace packages first; reviewed standalone
# commit/release refs frozen to SHAs otherwise, requiring network). Moved refs are rejected
# before tracked vendor files are replaced:
sandbox fetch-deps                 # mirror workspace packages or refresh SHA-frozen standalone commit/release refs
sandbox up                         # Langfuse + Ollama
sandbox pull-models                # ollama pull qwen3:8b
sandbox health
sandbox pilot --mock               # machinery only, no LLM
sandbox pilot --local              # real local model
```

The one-command local path is the core of it:

1. Install
2. `sandbox up` (compose profiles `langfuse` + `ollama`)
3. `sandbox pull-models`
4. `sandbox pilot --mock`
5. `sandbox pilot --local`

<details>
<summary>CPU-only smoke test</summary>

Pull `llama3.2:3b` and run:

```bash
sandbox cutover --profile ollama --model llama3.2:3b
```

GPU recommended for Qwen 8B.

</details>

<a id="how-it-works"></a>

## 🧭 How it works

<div align="center">
<picture>
  <source media="(max-width: 640px)" srcset="docs/assets/readme/flow-mobile.svg"/>
  <img src="docs/assets/readme/flow.svg" alt="The local path from install to a scored run: install, bring up Langfuse and Ollama, pull the model, probe the provider and trace sinks, run the pilot with the mock and then a local model, and score with the vendored dojo; matrix, run specs, Modal workers, comparisons and the watch TUI branch off it" width="100%"/>
</picture>
</div>

Start with `--mock` to prove the machinery, switch to `--local` for a real
model, then score with `sandbox eval`. When you scale out, `sandbox matrix`
sweeps providers × models × prompts, `sandbox run` drives spec files under
`config/runs/`, `--job-mode modal` hands a run to a Modal GPU worker, and
`sandbox watch` follows it in the mailroom TUI.

Live-or-loud: a vLLM/Modal profile without `--local` warns instead of silently
mocking (DMR-048); live eval errors are recorded per item instead of being
replaced by mock answers (DMR-044), and a task that has no live predictor is
explicitly flagged `offline_fallback`.

<a id="at-a-glance"></a>

## 📟 At a glance

<div align="center">
<img src="docs/assets/readme/tui.svg" alt="Dashboard: the seven provider profiles with what each targets, and a log of a mock pilot run on the default Ollama profile" width="90%"/>
</div>

<div align="center">

| Component | Default | Notes |
| :--- | :--- | :--- |
| **Default provider** | Ollama (`qwen3:8b`) | Fallback `qwen3:7b` |
| **Scoring** | `llm-dojo-scoring` (vendored) | Deterministic, field-type-aware |
| **Pipeline** | `llm-mailroom` (vendored) | 13-node LangGraph state machine |
| **Tracing** | Langfuse 3 / SDK v4 | `document-pipeline` traces |
| **Storage** | SQLite under `./data` | Mailroom default |

</div>

<a id="cli"></a>

## ⌨️ CLI

```
sandbox up | down | health | pull-models | fetch-deps | cutover | profiles | agents
sandbox pipeline watcher | pipeline api
sandbox pilot --mock|--local
sandbox hf-pilot --check|--mock|--local
sandbox legalbench --mock|--local
sandbox eval <agent>|extract|chained|pipeline|legalbench|local_vs_api [--mock|--local]
sandbox eval local_vs_api --from-log   # compare experiment_log local vs API-key runs
sandbox matrix --providers ollama --models qwen3:8b --prompts sorter_local_v0
sandbox datasets pull          # LIVE pinned FULL Hub pull (3302 rows) → data/cache/
sandbox datasets sample --per-class 40  # offline 20/40/100… per live class from that cache
sandbox datasets prepare   # offline clean → data/runtime/prepared/
sandbox run preflight|start|status|resume|cancel|list --config config/runs/<name>.yaml
sandbox watch [--web] [--config config/runs/<name>.yaml]       # mailroom TUI + Modal log tail (see docs/pretty-logging/mailroom-themed-logging.md)
sandbox run start --config <run.yaml> --job-mode modal --watch   # Modal worker
sandbox prompts list | show <agent> [--variant X]
sandbox prompts list-versions [--role R] | show <key> [--diff <other-key> | --memo]   # every eval-environment prompt version
sandbox eval sorter --prompt-version sorter_v4        # run any version: docs/prompts/
sandbox metrics compare --runs local,modal,api | --log
sandbox tunnel --profile vllm-remote plan|up|status|down
sandbox traces export
```

`SANDBOX_DEBUG=1` traces CHTC/Modal scripts (DMR-053). The full reference is in
the [Quickstart guide](docs/setting-up/QUICKSTART.md).

<a id="docs"></a>

## 📚 Docs

| Guide | Description |
| :--- | :--- |
| [Quickstart](docs/setting-up/QUICKSTART.md) | **Start here** — install, full CLI reference, canonical workflows |
| [Providers](docs/setting-up/providers.md) | Ollama, vLLM, Modal, llama.cpp, LM Studio, OpenRouter |
| [Evals](docs/evals.md) | Runners, matrix, scoring, experiment log |
| [Tracing](docs/tracing.md) | Langfuse v4 data model, tags, The-Mailroom |
| [Docker offline](docs/setting-up/docker-offline.md) | Dockerfile, Compose `jupyter` profile, prep notebooks |
| [Sister repos](docs/setting-up/sister-repos.md) | Family map |
| [Layout contract](docs/setting-up/LAYOUT.md) | **Which folder owns what** — the two config trees, frozen surfaces, junk policy |
| [Agent skills](.cursor/skills/README.md) | Langfuse, Phoenix, Braintrust, Ollama, Modal, Hugging Face |

<a id="specialist-extraction-rules"></a>

## ✍️ Specialist extraction rules

- `config/prompts/corporate_records_specialist_simplified.txt`, line 11:
  `subsidiary_list` emits `record_type: other`, the parent as `entity_name`,
  a subsidiary listing in `subject_matter`, and subsidiary names in `keywords`.
  `filing_number` is null unless an official filing or document number is present;
  an exhibit ID never qualifies.
- `config/prompts/correspondence_specialist_simplified.txt`, lines 14 and 33:
  `communication_type` is null when no registered token fits the visible text;
  continue extracting sender, recipient, and date from headers. Do not invent a type.

See [prompt guidance](config/prompts/README.md#extraction-rules-in-the-re-frozen-v1-stems)
for the registered communication types and source links.

<a id="layout"></a>

## 🗂️ Layout

<details>
<summary>Directory map</summary>

```
config/profiles/     provider profiles (local-first defaults)
config/runs/         run specs for `sandbox run` (vllm-local / vllm-remote / modal-vllm)
config/prompts/      frozen prompt stems (referenced by name from run specs)
docs/prompts/        catalog of every eval-environment prompt version: memos, changes, diffs, full text (generated)
config/taxonomy.overlay.yaml
config/models.yaml   OpenRouter champion → local tag map
deploy/              Dockerfile + compose + Modal vLLM (modal_vllm.py) + Modal job worker (modal_job.py) + htcondor/ + conda/
notebooks/           offline env setup + data prep + mock smoke
data/fixtures/       offline samples (see ATTRIBUTION.md)
src/mailroom_sandbox/
vendor/              tracked family snapshots (llm-mailroom + llm-dojo-scoring; exact source commits in each VENDOR.md)
reports/             sandbox experiment log (not a sister-repo mirror)
governance/          SAND-* board (README / PREFIX / TASKS / archive)
api-evals/           OpenRouter API cost harness — its own config/runs/ + reports/ and its own CLI
                     (`python api-evals/run_api_evals.py`), not packaged, not in the Docker image.
                     Run specs here are the real-spend `api-*` tasks; see docs/setting-up/LAYOUT.md.
```

</details>

Full rules — including why the two `config/runs/` trees stay separate and which
paths are frozen by a test — are in [`docs/setting-up/LAYOUT.md`](docs/setting-up/LAYOUT.md).
The exact snapshot commits are in
[`vendor/llm-mailroom/VENDOR.md`](vendor/llm-mailroom/VENDOR.md) and
[`vendor/llm-dojo-scoring/VENDOR.md`](vendor/llm-dojo-scoring/VENDOR.md).

<a id="offline-docker--notebooks"></a>

## 🐳 Offline Docker and notebooks

```bash
pip install -e ".[dev,notebooks]"
sandbox up --compose-profile langfuse --compose-profile ollama --compose-profile jupyter
# Lab → http://127.0.0.1:8888/lab
sandbox datasets prepare
```

See [`docs/setting-up/docker-offline.md`](docs/setting-up/docker-offline.md).

<a id="where-it-fits"></a>

## 🌌 Where it fits

<div align="center">
<picture>
  <source media="(max-width: 640px)" srcset="docs/assets/readme/constellation-mobile.svg"/>
  <img src="docs/assets/readme/constellation.svg" alt="Data-flow map of the Mailroom constellation with local-mailroom-sandbox highlighted: it pulls the pinned dataset, executes the pipeline and scores with llm-dojo-scoring" width="100%"/>
</picture>
</div>

| | Neighbour | Relationship |
| :---: | :--- | :--- |
| 🏛️ | [`Digital-Mailroom`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom) | The integration hub. It imports this repository as a workspace member and regenerates its `vendor/` snapshots |
| 🧠 | [`llm-mailroom`](https://github.com/Exios66/llm-mailroom) | The pipeline this sandbox executes, vendored under `vendor/llm-mailroom/` |
| 🥋 | [`llm-dojo-scoring`](https://github.com/Exios66/llm-dojo-scoring) | The scoring engine behind `sandbox eval`, vendored under `vendor/llm-dojo-scoring/` |
| 🎞️ | [`The-Mailroom`](https://github.com/Exios66/The-Mailroom) | The visualizer that reads the Langfuse traces; `sandbox fetch-deps --visualizer` clones it |
| 🤗 | [`mailroom-dataset`](https://huggingface.co/datasets/Lucius-Morningstar/mailroom-dataset) | The corpus behind `sandbox datasets pull`: a pinned 3,302-row pull |

<a id="faq"></a>

## ❓ FAQ

<details>
<summary><b>Do I need a GPU?</b></summary>

Not on your machine. `sandbox pilot --mock` exercises the machinery with no
model at all, and a small model such as `llama3.2:3b` runs on CPU through Ollama
(see the CPU-only smoke test above). A GPU is recommended for the default Qwen 8B.
`vllm-local` needs a local GPU; `vllm-remote` reaches a GPU box over an SSH
tunnel and `modal-vllm` rents one on Modal.

</details>

<details>
<summary><b>Is the code under <code>vendor/</code> mine to edit?</b></summary>

No. The snapshots are copies of `llm-mailroom` and `llm-dojo-scoring` pinned to
the commits in each `VENDOR.md`. Change the standalone repository; the snapshot
moves when the Digital-Mailroom hub imports that commit and regenerates `vendor/`,
or when the SHA pins that `sandbox fetch-deps` uses are bumped (it rejects a
moved ref rather than following it).

</details>

<details>
<summary><b>What happens when a live provider is unreachable?</b></summary>

It fails loudly instead of quietly mocking. `sandbox run start --job-mode modal`
probes the engine first and stops with `engine_unreachable`, and errors during a
live eval are recorded per item. Run `sandbox health` beforehand to probe the
active provider and the trace sinks.

</details>

<details>
<summary><b>Does anything cost money by default?</b></summary>

No. The default profile is Ollama on your own machine. OpenRouter is opt-in,
Modal runs bill your Modal account, and the `api-evals/` harness is the
real-spend API path, kept outside the package.

</details>

<details>
<summary><b>Where do I see a run?</b></summary>

Traces land in Langfuse under the `document-pipeline` root name; see
[`docs/tracing.md`](docs/tracing.md). The-Mailroom draws them as a conveyor, and
`sandbox watch` shows a run live in the mailroom TUI.

</details>

<a id="built-on"></a>

## 🙏 Built on

The sandbox drives the vendored family code through these open-source projects.

| Project | What it does here |
| :--- | :--- |
| [Ollama](https://github.com/ollama/ollama) | The default local provider (`qwen3:8b`) |
| [vLLM](https://github.com/vllm-project/vllm) | The `vllm-local`, `vllm-remote` and `modal-vllm` serving profiles |
| [Modal](https://modal.com/) | GPU serving and job workers under `deploy/` (the `[deploy]` extra) |
| [LangGraph](https://github.com/langchain-ai/langgraph) | Runs the vendored 13-node pipeline graph (the `[pipeline]` extra) |
| [Langfuse](https://github.com/langfuse/langfuse) | The canonical trace sink (the `[observability]` extra; Phoenix and Braintrust are alternatives) |
| [OpenAI Python SDK](https://github.com/openai/openai-python) | Talks to every OpenAI-compatible endpoint, local or remote |
| [Pydantic](https://github.com/pydantic/pydantic) | Validates run specs (`RunSpec`) |

<a id="contributing-security-and-license"></a>

## 🤝 Contributing, security and license

| | |
| :--- | :--- |
| **Contributing** | Read [`AGENTS.md`](AGENTS.md) and the SAND-* board under [`governance/`](governance/). Pipeline and scoring changes go to their standalone repositories, never into `vendor/`. The hub [contributing guide](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/CONTRIBUTING.md) covers the import into Digital-Mailroom. |
| **Security** | Report vulnerabilities, including leaked tokens, privately as described in the hub [security policy](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/SECURITY.md), which also routes package-code issues to this repository. |
| **License** | No license file is published for the code yet. Fixture attributions are in [`data/fixtures/ATTRIBUTION.md`](data/fixtures/ATTRIBUTION.md). |

---

<div align="center">

**[Digital-Mailroom](https://github.com/LLM-Mailroom-Services/Digital-Mailroom)** ·
**[llm-mailroom](https://github.com/Exios66/llm-mailroom)** ·
**[llm-dojo-scoring](https://github.com/Exios66/llm-dojo-scoring)** ·
**[The-Mailroom](https://github.com/Exios66/The-Mailroom)** ·
**[local-mailroom-sandbox](https://github.com/Exios66/local-mailroom-sandbox)** ·
**[Mailroom-Corpus-EDA](https://github.com/Exios66/Mailroom-Corpus-EDA)** ·
**[mailroom-ml](https://github.com/LLM-Mailroom-Services/mailroom-ml)**

<sub>local-mailroom-sandbox · one of the Mailroom constellation's independent source repositories, with shared interfaces.</sub>
<br/>
<sub>Core packages integrate in Digital-Mailroom; mailroom-ml is a standalone contractor.</sub>
<br/>
<sub>🧪 <i>Mock first, then local, then scored.</i> · Artwork: <a href="docs/assets/readme/README.md">design and regeneration</a></sub>

</div>


### Reviewed dependency refreshes (DMR-111)

The tracked snapshots contain pipeline 0.8.1 and Dojo 0.24.0 from the exact
commits in their `VENDOR.md` files. `sandbox fetch-deps` remains optional: it
uses workspace packages when available and retrieves the reviewed immutable
commit or frozen release tag in standalone checkouts. Ref movement, fetch,
layout and copy failures leave the previous snapshot intact. If installation
and rollback both fail, the command prints the preserved recovery directory.

`--visualizer` retrieves a separately reviewed exact visualizer commit. An
existing checkout with local files or a different HEAD is preserved and rejected;
review it and move it aside before requesting a fresh pinned checkout. Large LFS
assets are not downloaded. CUAD/MAUD row and pooled headline metrics delegate to
Dojo; null ground-truth answers are unlabelled, while genuine zero scores remain
numeric zero. The production and evaluation corporate prompt catalogs stay distinct.
