<div align="center">

<picture>
  <source media="(max-width: 640px)" srcset="docs/assets/readme/hero-mobile.svg"/>
  <img src="docs/assets/readme/hero.svg" alt="The-Mailroom: a retro CRT shows the pixel-art mailroom floor, with envelopes riding a conveyor past the SORTER, EXTRACT, JUDGE, BOSS, REPORT and ARCHIVE stations and a flagged one parked on the REVIEW siding" width="100%"/>
</picture>

<br/>

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](pyproject.toml)
[![Langfuse only](https://img.shields.io/badge/source-Langfuse_only-6C5CE7?style=for-the-badge)](docs/architecture.md)
[![Four surfaces](https://img.shields.io/badge/surfaces-console_·_Observatory_·_TUI_·_site-22C55E?style=for-the-badge)](#quick-start)
[![Observatory](https://img.shields.io/badge/🤗_live-Observatory-FFD21E?style=for-the-badge)](https://lucius-morningstar-mailroom-observatory.hf.space/)

![version](https://img.shields.io/badge/version-0.5.1-blue)
[![release](https://img.shields.io/badge/release-v0.5.1-blue)](https://github.com/Exios66/The-Mailroom/releases/tag/v0.5.1)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![data source](https://img.shields.io/badge/data%20source-Langfuse%20only-6C5CE7)
[![Hub](https://img.shields.io/badge/🏛️_hub-Digital--Mailroom-000?style=flat-square)](https://github.com/LLM-Mailroom-Services/Digital-Mailroom)
[![Demos](https://img.shields.io/badge/🎬_demos-gallery-555?style=flat-square)](docs/demos.md)

**[Quick start](#quick-start)** · **[How it works](#how-it-works)** · **[Screenshots](#screenshots)** · **[Mailroom Reloaded](#mailroom-reloaded)** · **[Where it fits](#where-it-fits)** · **[Docs](docs/README.md)**

</div>

---

<!-- readme-v2.1 -->
<details>
<summary><b>📑 Contents</b></summary>

- [🏤 What is this?](#what-this-does)
- [🤔 When to reach for it](#when-to-reach-for-it)
- [👀 See it run](#see-it-run)
- [🧭 How it works](#how-it-works)
- [📟 At a glance](#at-a-glance)
- [🚀 Quick start](#quick-start)
- [🖼️ Screenshots](#screenshots)
- [🔁 Mailroom Reloaded](#mailroom-reloaded)
- [🌌 Where it fits](#where-it-fits)
- [❓ FAQ](#faq)
- [🙏 Built on](#built-on)
- [🤝 Contributing, security and license](#contributing-security-and-license)

</details>

<a id="what-this-does"></a>

## 🏤 What is this?

**Pixel-art visual engine for the [`llm-mailroom`](https://github.com/Exios66/llm-mailroom)
multi-agent legal-document pipeline.** The Mailroom renders every pipeline run as an
animated conveyor of document envelopes — sorter, specialist bays, the boss's desk,
the reporter, the archive — driven entirely by **Langfuse traces**.

Four surfaces share one display API (`/api/*` + `/ws`):

| Surface | Command / URL | Notes |
| --- | --- | --- |
| Pixel-art console | `mailroom-web` → `http://127.0.0.1:8001/` | the CRT conveyor floor |
| Hosted Observatory | `mailroom-hosted` (also `/live` on the same server) | public operations desk |
| TUI | `mailroom-tui` | typed-command REPL (`MAILROOM_API_URL`) |
| Terminal site | `…/terminal/` on GH Pages | owlcot-style TTY: `ls`/`cat`/`cd`, `corpus ls | show`,`repos` |

The terminal site and the TUI both add a **dataset viewer** (`corpus …`
commands over `Lucius-Morningstar/mailroom-dataset` — slim windowed
listing, live per-row `doc_text` + ground truth) and a **constellation
repo browser** (`repos …` — every mirror package plus the hub copies and
derived graph sites).

When the configured producer health response includes a valid `dojo_update`,
the live Observatory, pixel console, and existing TUI ops header show a
nonblocking **Dojo update available for pipeline** notice. Installed/available
versions describe the engine loaded by that producer, independently of this
visualizer's optional local `[eval]` engine. The notice labels the cached
check time and stale results; its fixed
[Dojo release link](https://github.com/Exios66/llm-dojo-scoring/releases/latest)
does not certify the current release page against cached knowledge.

This uses the existing `/api/pipeline` and `/ws` pipeline payloads, with no
release checks in the viewer. Absent, unknown, unavailable, disabled, current,
or malformed metadata shows no upgrade notice; a missing producer snapshot
or disconnected transport clears the old notice. Versions use a bounded
canonical PEP 440 subset (64 characters; numeric releases, optional installed
prerelease/dev/local suffixes, stable post releases). Other shapes fail soft.
The static terminal site and optional React desk do not consume this producer
ops payload and have no advisory. No upgrades or pin changes are automatic.

Agent skills (Langfuse / Phoenix / Braintrust / Ollama / Modal / Hugging Face
plus pixel, Observatory, live floor, schema sync, Pages, TUI, operator desk):
[`.cursor/skills/README.md`](.cursor/skills/README.md).

<div align="center">
<picture>
  <source media="(max-width: 640px)" srcset="docs/assets/readme/stats-mobile.svg"/>
  <img src="docs/assets/readme/stats.svg" alt="By the numbers: four surfaces on one display API, seven floor stations including the review siding, six pixel-console desks, Langfuse as the only display source, version 0.5.1 and Python 3.11 or newer" width="100%"/>
</picture>
</div>

<a id="when-to-reach-for-it"></a>

## 🤔 When to reach for it

| ✅ Reach for it when… | ↪️ Look elsewhere when… |
| :--- | :--- |
| You want to watch llm-mailroom runs move through the stations, live or replayed from stored traces | You want to process documents. The pipeline is [llm-mailroom](https://github.com/Exios66/llm-mailroom); this repository only displays it |
| A person needs to approve, reject or requeue documents parked for human review | You want static accuracy reports. Use [llm-dojo-scoring](https://github.com/Exios66/llm-dojo-scoring) (`dojo-analyze`, `dojo-export`) |
| You need a public operations desk (the Observatory) or a terminal view over the same traces | You need live runs on GitHub Pages. The Observatory needs a real host; Pages carries a static edition and the terminal site |

<a id="see-it-run"></a>

## 👀 See it run

<table>
<tr>
<td width="33%"><a href="docs/screenshots/floor.png"><img src="docs/screenshots/floor.png" alt="The pixel-art console floor: stations along a conveyor, envelopes and the review siding" width="100%"/></a><br/><sub><b>Pixel console</b> · the FLOOR: stations, envelopes and the review siding</sub></td>
<td width="33%"><a href="docs/screenshots/observatory-review.png"><img src="docs/screenshots/observatory-review.png" alt="The Observatory review queue with inline Approve, Reject and Requeue" width="100%"/></a><br/><sub><b>Observatory</b> · the human-review queue with inline resolve</sub></td>
<td width="33%"><a href="docs/screenshots/tui-console.png"><img src="docs/screenshots/tui-console.png" alt="The terminal UI: per-document table, verdicts, station banners and live log" width="100%"/></a><br/><sub><b>Terminal UI</b> · per-doc table, verdicts and station banners</sub></td>
</tr>
</table>

<div align="center"><sub>Every still, the walkthrough videos and the PR recording are in <a href="#screenshots">Screenshots</a> below and in the <a href="docs/demos/The-Mailroom-Demos.ipynb">demos notebook</a>.</sub></div>

<a id="how-it-works"></a>

## 🧭 How it works

<div align="center">
<picture>
  <source media="(max-width: 640px)" srcset="docs/assets/readme/flow-mobile.svg"/>
  <img src="docs/assets/readme/flow.svg" alt="A trace from Langfuse or Phoenix is interpreted into stations, served over one display API and rendered by four surfaces; review decisions go back to the producer. It reads llm-mailroom and mailroom-reloaded and runs on a Hugging Face Space or GitHub Pages" width="100%"/>
</picture>
</div>

<a id="at-a-glance"></a>

## 📟 At a glance

<div align="center">
<img src="docs/assets/readme/tui.svg" alt="Terminal dashboard: the four surfaces and the Langfuse-only source, and a sample of what the terminal UI prints as runs advance" width="90%"/>
</div>

<a id="quick-start"></a>
<a id="quickstart"></a>

## 🚀 Quick start

<div align="center">
<img src="docs/assets/readme/terminal.svg" alt="Animated terminal: clone, install, add Langfuse keys, start the pixel console, print one terminal frame and seed demo runs" width="90%"/>
</div>

```bash
pip install -e ".[dev]"
pip install -e ".[pipeline]"  # producer adapter; omit for a display-only install
cp .env.example .env      # add LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY
mailroom-web              # → http://127.0.0.1:8001  (pixel-art console)
                          #    Observatory is also at /live on the same server
mailroom-hosted           # → public Observatory on 0.0.0.0 (container-ready)
mailroom-tui              # typed-command REPL (floor/corpus/repos/inspect)
pip install -e ".[operator]"  # optional: operator desk (auth / archive / observer)
pip install -e ".[ui]"        # marker only; React desk still needs Node
mailroom-observer         # standalone bin watcher — or MAILROOM_OBSERVER=1 on mailroom-web (never both)
# optional React desk: cd ui && npm install && npm run build  →  /desk
```

<details>
<summary>What you see on each surface</summary>

**Pixel console** (`mailroom-web`)

- **FLOOR** — the mailroom: a conveyor belt carrying document envelopes
  through the pipeline's seven stations (SORTER · EXTRACT · JUDGE · BOSS ·
  REPORT · ARCHIVE, plus the human-review siding) grouped into three rooms
  (Intake & Sort · Extraction & Adjudication · Reporting & Archive). The
  JUDGE station is the KANBAN-063 quality gate (`judge_verify` +
  `arbitrate-verdict`). Click an envelope for its full run.
- **REVIEW** — the review siding as a queue: every run waiting on a human,
  with its escalation reason and confidence. Approve / Reject / Requeue
  (and record-only audit), plus doc-type / subtype correction and a raw
  document text viewer, when `MAILROOM_PIPELINE_URL` +
  `MAILROOM_PIPELINE_TOKEN` point at llm-mailroom `:8000`; one click still
  opens the inspector.
- **INSPECTOR** — drill-down into any trace: node-span timeline, LLM
  generations (model, tokens, latency, cost), confidence and judge scores.
- **SESSIONS** — matter explorer grouped by Langfuse session.
- **HISTORY** — recent runs with per-hour volume and **REPLAY** (animates
  a stored trace through its real span sequence on the floor).
- **METRICS** — docs processed, archived/review/failed, cost, tokens, p95
  generation latency, judge-verdict mix, per-doc-type counts.
- **CONSOLE** — a live scrolling log of the pipeline, AgentLaboratory-style.

**Observatory** (`/live`, `mailroom-hosted`) — the **hosted** edition: a
modern, accessible public desk (semantic HTML, keyboard views `1`–`6`,
native inspect dialog, paced replay, Debug desk). Same live traces as the
console; different surface, different URL. Not GitHub Pages.

**TUI** (`mailroom-tui`) — the same pipeline in a terminal: per-doc tables,
`*** Beginning station: ... ***` banners as runs arrive and advance, judge
verdict banners, review siding, sessions, metrics, inspect (`[` / `]` cycle
runs), and a debug ring. It subscribes to the same WebSocket floor snapshots
as the web UI (`--once --view floor|review|metrics|sessions|inspect|debug`
renders a single frame for scripting). `--resolve TRACE --decision
approved|rejected --disposition resume|record|requeue --notes "..."
[--doc-type X --doc-subclass Y]` posts through this visualizer to the
producer. `--source TRACE` prints parked document text. Never point
`MAILROOM_API_URL` at the producer `:8000`.

</details>

<a id="screenshots"></a>

## 🖼️ Screenshots

Live captures of the three surfaces against the same display API. Values on
screen are interpreted traces (fixture-shaped exactly like the test suite);
Langfuse remains the sole display source. The full gallery, including the
PR screen recording, lives in the **[demos notebook](docs/demos/The-Mailroom-Demos.ipynb)**
and [`docs/demos.md`](docs/demos.md) (wiki twin: [`Demos`](wiki/Demos.md)).

> **Media note:** the recorded videos, posters, and notebook are heavy
> assets that are pruned from this checkout (`docs/demos/` and
> `docs/screenshots/` do not exist locally). They live upstream in the
> `LLM-Mailroom-Services/Digital-Mailroom` repo at
> `packages/The-Mailroom/docs/demos/` and `packages/The-Mailroom/docs/screenshots/`
> (raw URLs on github.com); open the files there to play them.

**Hugging Face Space — live Observatory** (~102s) — public Docker Space
after #30 (classification cards, headline strip, inbox setup hint, Export
snapshot, then Review / History / Matters / Metrics / Debug). Live:
<https://lucius-morningstar-mailroom-observatory.hf.space/>
[hf-space-observatory-live-walkthrough.mp4](docs/demos/hf-space-observatory-live-walkthrough.mp4)

[![HF Space Observatory Pipeline](docs/demos/hf-space-observatory-poster.png)](docs/demos/hf-space-observatory-live-walkthrough.mp4)

**Working REVIEW tray** (Approve / Record / Requeue / Complete against a `/v1` stub):

```bash
PYTHONPATH=. python scripts/demo_review_tray.py --port 8006
# http://127.0.0.1:8006/?api=  and  /live?api=
```

**v0.3.0 pixel desks** (~42s) — FLOOR hopper, inspector resolve form, REVIEW
Approve → honest 503, then SESSIONS / HISTORY / METRICS / CONSOLE:
[v030-pixel-desks-review-resolve.mp4](docs/demos/v030-pixel-desks-review-resolve.mp4)

[![v0.3.0 pixel REVIEW](docs/demos/v030-pixel-poster.png)](docs/demos/v030-pixel-desks-review-resolve.mp4)

**v0.3.0 Observatory** (~52s) — Inbox tray, Review resolve, inspect dialog,
History / Matters / Metrics / Debug:
[v030-observatory-review-resolve.mp4](docs/demos/v030-observatory-review-resolve.mp4)

[![v0.3.0 Observatory Pipeline](docs/demos/v030-observatory-poster.png)](docs/demos/v030-observatory-review-resolve.mp4)

**Walkthrough video** (~56s, pixel desks then Observatory):
[tui-server-observatory-desk-walkthrough.mp4](docs/demos/tui-server-observatory-desk-walkthrough.mp4)
— click the file on GitHub to play it.

[![Desk walkthrough poster](docs/demos/walkthrough-poster.png)](docs/demos/tui-server-observatory-desk-walkthrough.mp4)

**Pilot run — documents moving through the pipeline** (~25s): five envelopes
slide SORTER → EXTRACT → JUDGE → REPORT → ARCHIVE; the merger agreement
peels onto REVIEW; a corporate record fails. Re-record with
`python scripts/demo_pilot_run.py --port 8005`.

[![Pilot run — envelopes on the conveyor](docs/demos/pilot-run-poster.png)](docs/demos/pilot-run-documents-through-pipeline.mp4)

Open a section below to expand the stills.

<details open>
<summary>Pixel-art console (<code>mailroom-web</code>)</summary>

| | |
| --- | --- |
| ![The Mailroom floor — conveyor, stations, envelopes](docs/screenshots/floor.png) |
| **FLOOR** — seven stations, per-doc-type envelope tints, review siding and failed bin. Click an envelope to inspect. |
| ![Pilot run — four envelopes in motion](docs/screenshots/pilot-floor.png) |
| **PILOT RUN** — live envelopes mid-flight (ACTIVE: 4). Full motion: [pilot-run-documents-through-pipeline.mp4](docs/demos/pilot-run-documents-through-pipeline.mp4). |
| ![Inspector overlay on the floor](docs/screenshots/inspector.png) |
| **INSPECTOR** — node spans, LLM generations, classification / extraction / judge scores. |
| ![REVIEW siding — human-review queue](docs/screenshots/review.png) |
| **REVIEW** — parked + RECONSIDER cards with Approve / Reject / Requeue / Complete (disposition resume/record/requeue/complete). |
| ![SESSIONS / matters](docs/screenshots/sessions.png) |
| **SESSIONS** — Langfuse matters with their traces, stages, and verdicts. |
| ![HISTORY with replay](docs/screenshots/history.png) |
| **HISTORY** — recent runs, per-hour volume, REPLAY onto the floor. |
| ![METRICS dashboard](docs/screenshots/metrics.png) |
| **METRICS** — docs processed, archived/review/failed split, cost, tokens, judge-verdict mix, per-doc-type counts. |
| ![LIVE CONSOLE log](docs/screenshots/console.png) |
| **CONSOLE** — AgentLab-style live log plus the DEBUG capture toggle. |

</details>

<details open>
<summary>Hosted Observatory (<code>/live</code>, <code>mailroom-hosted</code>)</summary>

| | |
| --- | --- |
| ![Observatory pipeline trays](docs/screenshots/observatory-pipeline.png) |
| **Pipeline** — live trays including INBOX hopper, Sorter · Extract · Judge · Boss · Report · Archive · Review · Completed. |
| ![Observatory review queue](docs/screenshots/observatory-review.png) |
| **Review** — human-review queue with inline resolve (Approve / Reject / Requeue / Complete). |
| ![Observatory run history](docs/screenshots/observatory-history.png) |
| **History** — recent runs with paced Replay of stored span sequences. |
| ![Observatory matters](docs/screenshots/observatory-matters.png) |
| **Matters** — Langfuse sessions grouped as matters. |
| ![Observatory metrics](docs/screenshots/observatory-metrics.png) |
| **Metrics** — the same window aggregates as the pixel desk. |
| ![Observatory debug desk](docs/screenshots/observatory-debug.png) |
| **Debug** — client ring, `GET /api/debug/bundle`, `POST /api/debug/client`. |

</details>

<details open>
<summary>TUI (<code>mailroom-tui</code>)</summary>

| | |
| --- | --- |
| ![TUI floor table and live log](docs/screenshots/tui-console.png) |
| **Floor** (`mailroom-tui --once`) — per-doc table, verdicts, station banners, live log. |
| ![TUI review siding](docs/screenshots/tui-review.png) |
| **Review** (`--view review`) — waiting-on-a-human queue with escalation reasons. |
| ![TUI sessions](docs/screenshots/tui-sessions.png) |
| **Sessions** (`--view sessions`) — Langfuse matters. |
| ![TUI metrics](docs/screenshots/tui-metrics.png) |
| **Metrics** (`--view metrics`) — the same aggregates as `/api/metrics`. |

Keys: `[f]loor` `[r]eview` `[s]essions` `[m]etrics` `[i]nspect` `[` `]` `[d]ebug` `[q]uit`.

</details>

<a id="mailroom-reloaded"></a>

## 🔁 Mailroom Reloaded

[`mailroom-reloaded`](https://github.com/Exios66/mailroom-reloaded) is the compressed, deployment-ready
Digital Mailroom: a CrewAI-Flows pipeline that classifies, extracts and archives documents with a
verifiable audit chain. The-Mailroom reads it through the **Phoenix source**: its `mailroom.document` root
and `mailroom.node.<node>` spans map onto the floor's stations (`RELOADED_NODE_STAGES` in
`mailroom_ui/pipeline_schema.py`), `parked` runs land on the REVIEW siding, and repeated `sort` / `extract`
spans fold into the retry stages. Set `MAILROOM_SOURCE=phoenix` (or `both`) and `MAILROOM_PHOENIX_PROJECT`
to the Reloaded project; eval runs use `eval-<run_id>`. Details: [`docs/architecture.md`](docs/architecture.md).

Reloaded ships its own terminal, replay viewer, run table and offline sandbox UI in the same visual
language. These are its committed captures (1200×800, dark theme), pinned to
[`mailroom-reloaded@0e1dbd0`](https://github.com/Exios66/mailroom-reloaded/tree/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo).

<table>
<tr><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/01-tui-help.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/01-tui-help.png?raw=true" alt="The /tui terminal after boot, running help" width="100%"/></a><br/><sub><b>01</b> · The /tui terminal after boot, running `help`.</sub></td><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/02-replay-viewer.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/02-replay-viewer.png?raw=true" alt="Replay viewer paused at 01:30: station grid with per-station counts, scrub bar and the run metrics line" width="100%"/></a><br/><sub><b>02</b> · Replay viewer paused at 01:30: station grid with per-station counts, scrub bar and the run metrics line.</sub></td></tr>
<tr><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/03-replay-panel-metrics.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/03-replay-panel-metrics.png?raw=true" alt="Replay insight panel metrics (first p)" width="100%"/></a><br/><sub><b>03</b> · Replay insight panel `metrics` (first `p`).</sub></td><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/08-inspector-retry.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/08-inspector-retry.png?raw=true" alt="Inspector on the retry document (gate_decision then retry events)" width="100%"/></a><br/><sub><b>08</b> · Inspector on the retry document (gate_decision then retry events).</sub></td></tr>
<tr><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/11-inspector-boss.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/11-inspector-boss.png?raw=true" alt="Inspector on the boss-escalated document (arbiter and escalation events)" width="100%"/></a><br/><sub><b>11</b> · Inspector on the boss-escalated document (arbiter and escalation events).</sub></td><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/14-ledger.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/14-ledger.png?raw=true" alt="The ledger listing followed by ledger verify (hash-chain check)" width="100%"/></a><br/><sub><b>14</b> · The `ledger` listing followed by `ledger verify` (hash-chain check).</sub></td></tr>
<tr><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/13-ui-replay-links.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/13-ui-replay-links.png?raw=true" alt="/ui Eval runs table with replay, grafana and phoenix links per run" width="100%"/></a><br/><sub><b>13</b> · /ui Eval runs table with `replay`, `grafana` and `phoenix` links per run.</sub></td><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/17-sandbox-dock-open.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/17-sandbox-dock-open.png?raw=true" alt="Boss mailbox dock expanded: draft awaiting approval and the hostile_forward entry (pending Release / Quarantine)" width="100%"/></a><br/><sub><b>17</b> · Boss mailbox dock expanded: draft awaiting approval and the hostile_forward entry (pending Release / Quarantine).</sub></td></tr>
</table>

<details>
<summary>The other 13 captures: replay panels, inspectors, outbound links, ledger, sandbox dock</summary>

<table>
<tr><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/04-replay-panel-tokens.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/04-replay-panel-tokens.png?raw=true" alt="Replay insight panel tokens (second p)" width="100%"/></a><br/><sub><b>04</b> · Replay insight panel `tokens` (second `p`).</sub></td><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/05-replay-panel-decisions.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/05-replay-panel-decisions.png?raw=true" alt="Replay insight panel decisions (third p)" width="100%"/></a><br/><sub><b>05</b> · Replay insight panel `decisions` (third `p`).</sub></td></tr>
<tr><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/06-replay-panel-latency.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/06-replay-panel-latency.png?raw=true" alt="Replay insight panel latency (fourth p)" width="100%"/></a><br/><sub><b>06</b> · Replay insight panel `latency` (fourth `p`).</sub></td><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/07-outbound-links.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/07-outbound-links.png?raw=true" alt="Inspector (no document selected) listing the Phoenix and Grafana links, after pressing o and g (each opens a new tab)" width="100%"/></a><br/><sub><b>07</b> · Inspector (no document selected) listing the Phoenix and Grafana links, after pressing `o` and `g` (each opens a new tab).</sub></td></tr>
<tr><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/09-inspector-failed.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/09-inspector-failed.png?raw=true" alt="Inspector on the failed document (failure run_budget, cause extraction_miss)" width="100%"/></a><br/><sub><b>09</b> · Inspector on the failed document (failure `run_budget`, cause `extraction_miss`).</sub></td><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/10-inspector-parked.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/10-inspector-parked.png?raw=true" alt="Inspector on the parked document (parked in review, cause judge_partial)" width="100%"/></a><br/><sub><b>10</b> · Inspector on the parked document (parked in review, cause `judge_partial`).</sub></td></tr>
<tr><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/12-links-json.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/12-links-json.png?raw=true" alt="Raw GET /links: the public base URLs the UI and viewer link out to" width="100%"/></a><br/><sub><b>12</b> · Raw `GET /links`: the public base URLs the UI and viewer link out to.</sub></td><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/15-pipeline-ls-runs.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/15-pipeline-ls-runs.png?raw=true" alt="Pipeline commands ls (catalog documents, hostile filename shown as literal text) and runs (eval runs)" width="100%"/></a><br/><sub><b>15</b> · Pipeline commands `ls` (catalog documents, hostile filename shown as literal text) and `runs` (eval runs).</sub></td></tr>
<tr><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/16-sandbox-dock-badge.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/16-sandbox-dock-badge.png?raw=true" alt="Sandbox UI with the docked Boss mailbox collapsed: unread badge on the toggle" width="100%"/></a><br/><sub><b>16</b> · Sandbox UI with the docked Boss mailbox collapsed: unread badge on the toggle.</sub></td><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/18-sandbox-pending-review.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/18-sandbox-pending-review.png?raw=true" alt="Pending boss review tab: payment_fraud hostile_forward from E1 awaiting a Boss decision (nothing is decided by the capture)" width="100%"/></a><br/><sub><b>18</b> · Pending boss review tab: payment_fraud hostile_forward from E1 awaiting a Boss decision (nothing is decided by the capture).</sub></td></tr>
<tr><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/19-tui-inbox-command.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/19-tui-inbox-command.png?raw=true" alt="The inbox --print command in /tui: the sandbox deep link it would open (Ingress queue, Boss mailbox dock open, Correspondent filter) and the hint that the token is never put in the link" width="100%"/></a><br/><sub><b>19</b> · The `inbox --print` command in /tui: the sandbox deep link it would open (Ingress queue, Boss mailbox dock open, Correspondent filter) and the hint that the token is never put in the link.</sub></td><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/20-sandbox-inbox-deeplink.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/20-sandbox-inbox-deeplink.png?raw=true" alt="Sandbox UI opened through the inbox deep link: Ingress queue tab active, Boss mailbox dock open with the filter: role=correspondent line and the seeded A1 + E1 mail" width="100%"/></a><br/><sub><b>20</b> · Sandbox UI opened through the `inbox` deep link: Ingress queue tab active, Boss mailbox dock open with the `filter: role=correspondent` line and the seeded A1 + E1 mail.</sub></td></tr>
<tr><td width="50%"><a href="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/21-tui-status-links.png?raw=true"><img src="https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/21-tui-status-links.png?raw=true" alt="The /tui status bar (top of the terminal window) with both outbound links: ui ↗ (/ui, same tab) and inbox ↗ (the sandbox ingress simulator, new tab)" width="100%"/></a><br/><sub><b>21</b> · The /tui status bar (top of the terminal window) with both outbound links: `ui ↗` (/ui, same tab) and `inbox ↗` (the sandbox ingress simulator, new tab).</sub></td><td></td></tr>
</table>

Images 19 and 21 were captured on Reloaded's `feature/ingress-sandbox` branch. Regeneration steps and the
capture manifest live in the
[`docs/demo` README](https://github.com/Exios66/mailroom-reloaded/blob/0e1dbd0ce15b8ee661901cd16faec923b178c13c/docs/demo/README.md).

</details>

<details>
<summary>Demo data (play-testing without a live run)</summary>

Demo runs are seeded **into** Langfuse (env `demo`) — the visualizer still
reads Langfuse only, so nothing on screen is ever canned data:

```bash
python scripts/seed_demo.py                       # seed 13 demo runs (incl.
                                                  # judge-gate + arbiter paths)
python scripts/seed_demo.py --list-scenarios      # what the demo set covers
python scripts/seed_demo.py --check --check-api   # verify seeded runs against
                                                  # stored Langfuse logs AND the
                                                  # running server's display API
python scripts/seed_demo.py --check-logs <dir>    # verify against run logs saved
                                                  # by llm-mailroom's
                                                  # scripts/sync_langfuse_logs.py
```

The pixel `D` key does **not** fabricate envelopes on a live floor. Demo
envelopes are opt-in (`?demo=1`) and only when the trace source is down.

</details>

<details>
<summary>Requirements</summary>

- Python 3.11+
- A Langfuse project (the `llm-mailroom` project on US cloud by default)
  with project-scoped API keys in `.env`
- The sister pipeline repo `../llm-mailroom` (optional — `MAILROOM_TAXONOMY`
  live override, production-pilot scripts, or `mailroom_ui/producer.py`
  checkout import). Prefer `pip install -e ".[pipeline]"` to pin dist
  `mailroom` @ `1a1ec3dfb4e71f615f5d34f6198f9d06fd8c26dd` (0.8.1, main after v0.7.1) when you want to import `pipeline.review_resolve`.
- `arize-phoenix-client` (optional — only for the Phoenix trace source)

</details>

<details>
<summary>Hosted Observatory (public URL — not GitHub Pages)</summary>

The Observatory is a **separate live site** meant to be deployed to a real
host (Railway, Hugging Face Spaces, Fly, Render, Cloud Run, a VPS). It is not the
Pages snapshot and not the pixel-art console.

```bash
mailroom-hosted                          # 0.0.0.0:8001  →  / and /live
docker build -t mailroom-observatory .
docker run --rm -p 7860:7860 --env-file .env mailroom-observatory
python scripts/publish_space.py --check  # Hugging Face Docker Space payload
# Railway: see docs/deployment.md (.railway/railway.py IaC + PORT preference;
# GET /health = liveness (+ platform, build_sha), GET /api/health = Langfuse)
```

Hugging Face Space: SDK **Docker**, root directory **empty** (repo-root
`Dockerfile`), port **7860**. Railway / Fly inject `$PORT` (preferred over
image `MAILROOM_PORT`). Secrets: `LANGFUSE_PUBLIC_KEY`,
`LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST=https://us.cloud.langfuse.com`
(`LANGFUSE_BASE_URL` is accepted as an alias). Do not configure the Space
as FastAPI/Vercel — the image is `python -m server.hosted`.

```bash
HF_TOKEN=hf_... LANGFUSE_PUBLIC_KEY=pk-lf-... LANGFUSE_SECRET_KEY=sk-lf-... \
  python scripts/publish_space.py --repo <user>/mailroom-observatory
```

Full deploy notes (Spaces secrets, keyboard map, how it differs from the
other surfaces): [`hosted/README.md`](hosted/README.md) and
[`hosted/SPACE_README.md`](hosted/SPACE_README.md).

</details>

<details>
<summary>GitHub Pages edition (static site + local Phoenix)</summary>

The Mailroom also runs as a **static site on GitHub Pages** with three data
modes:

```bash
# one-time: Settings → Pages → Source: "Deploy from a branch" → gh-pages /docs
scripts/publish_pages.sh                          # build site/ + push gh-pages docs/
scripts/publish_pages.sh --source both            # Langfuse + Phoenix snapshot
scripts/publish_pages.sh --dry-run                # build + verify, don't push
scripts/publish_pages.sh --status                 # is the live site in sync with HEAD?
```

**Keeping main and gh-pages in sync** (no Actions): enable the committed
pre-push hook once per clone — `git config core.hooksPath hooks` — and every
push of `main` republishes `gh-pages:/docs` automatically. A failed
republish (e.g. a Langfuse hiccup) warns without blocking the code push;
set `MAILROOM_STRICT_SYNC=1` to make failures block instead.
`scripts/publish_pages.sh --status` reports drift any time (exit 1 = stale).
The publisher must run from `main` — it refuses cleanly if another branch
(e.g. `gh-pages` in GitHub Desktop) is checked out.

The publisher needs no GitHub Actions (deliberately — it uses Pages' native
deploy-from-branch mode): it stages `web/` with relative asset paths, exports
a JSON snapshot of the configured trace source, verifies it, and pushes the
site into `docs/` on the `gh-pages` branch (anything else on that branch's
root is left untouched). Re-run any time to refresh the snapshot.

1. **Snapshot mode** — a build-time JSON export of the configured trace
   source is bundled into the site (`data/*.json`). Works with zero backend,
   zero secrets in the browser; the lamp shows `SOURCE: SNAPSHOT`. Published
   locally by `scripts/publish_pages.sh` (no GitHub Actions required) from
   Langfuse repo secrets or a local Phoenix — without a reachable source the
   site ships empty and shows its honest CLOSED state.
2. **Live mode** — point the static page at any reachable Mailroom API:
   append `?api=http://localhost:8001` once (persisted to `localStorage`).
   `?api=` (empty) **clears** a stale persisted base. Run the server locally
   with CORS enabled (`MAILROOM_CORS_ORIGINS`) and the Pages UI goes fully
   live, WS included. Note: Chrome/Firefox allow HTTPS→`http://localhost`
   calls; Safari may block them.
3. **Phoenix mode** — traces from a *locally running* Arize Phoenix
   (default `http://localhost:6006`) can drive the console:

   ```bash
   pip install arize-phoenix-client
   # start Phoenix (e.g. `phoenix serve`) and point your pipeline's OTLP
   # exporter at it, then:
   MAILROOM_SOURCE=phoenix mailroom-web     # or MAILROOM_SOURCE=both for Langfuse + Phoenix
   ```

   Phoenix spans are mapped into the llm-mailroom display contract:
   verb-first span names route through the stage map, LLM spans become
   generations (model/tokens/cost), annotations become scores. Unmapped
   spans degrade to unknown staging — same visible-by-design breakage map.

</details>

<details>
<summary>Debug console for agents</summary>

Every fetch, WS frame, error, and console line lands in a client-side ring
buffer at `window.__MAILROOM_DEBUG__` (`dump()`, clipboard copy,
`pullServer()`, `pushClient()`, `export()` → `mailroom-debug.json`);
`?debug=1` or the CONSOLE tab's DEBUG toggle enables verbose capture.

The hosted Observatory has a parallel suite: `window.__OBSERVATORY_DEBUG__`,
Debug desk `#debug` (`?debug=1`). The TUI records urllib/WS failures in
`LAST_ERRORS` (`[d]ebug`, `--view debug`) and can pull the same bundle.

Server side:

- `GET /api/debug/bundle` — one-pull: health + source + server ring + last
  client dumps
- `POST /api/debug/client` — store a browser dump for the next agent pull
- `GET /api/debug/logs?limit=` — always-on request ring buffer
- `GET /api/debug/source` — configured sources / knobs
- `GET /api/meta` — machine-readable endpoint index plus active sources and
  version
- `MAILROOM_DEBUG=1` — verbose stdout logging

Snapshot builds add `debug/build-info.json` (git SHA, counts, generation time).

</details>

<details>
<summary>Configuration reference</summary>

All knobs live in `.env` (see `.env.example`): Langfuse keys/host
(`LANGFUSE_HOST`, default `https://us.cloud.langfuse.com`), poll cadence
(`MAILROOM_POLL_INTERVAL`), recent window (default **7 days**,
`MAILROOM_RECENT_WINDOW=604800`), trace limit (`MAILROOM_TRACE_LIMIT=200`),
optional tag/env filters, `MAILROOM_PORT` (default `8001`),
`MAILROOM_TAXONOMY`, and `MAILROOM_PIPELINE_URL` + `MAILROOM_PIPELINE_TOKEN`
(producer on `http://127.0.0.1:8000` or a public Space such as
`https://<user>-mailroom-producer.hf.space` — watcher/inbox liveness,
`POST /v1/upload` enqueue, human-review resolve, class correction mapped
to `override_doc_type`, parked-file source via `/v1`). Token is the
producer `MAILROOM_API_TOKEN`.
`MAILROOM_PIPELINE_API_PREFIX` defaults to `/v1`. `MAILROOM_API_URL` is the TUI → this
visualizer (`:8001`), not the producer. The operator desk (`operator_desk/`)
adds `MAILROOM_OPERATOR_*` (JWT, admin seed, ingest token) plus
`MAILROOM_BASE_DIR`, `MAILROOM_OPERATOR_DB`, and `MAILROOM_OBSERVER`. The GH Pages edition adds `MAILROOM_SOURCE`
(`langfuse|phoenix|both`), `PHOENIX_ENDPOINT` / `PHOENIX_API_KEY` /
`MAILROOM_PHOENIX_PROJECT`, `MAILROOM_CORS_ORIGINS`, and `MAILROOM_DEBUG`.

> [!WARNING]
> **Public deploys fail closed (0.5.0).** When
> `MAILROOM_OPERATOR_AUTH=1` (the default), the hosted edition and any
> non-loopback `MAILROOM_HOST` require reviewer+ login for review resolve
> and inbox upload. Login is refused until
> `MAILROOM_OPERATOR_JWT_SECRET` (or `JWT_SECRET`) is set and the admin password is rotated
> away from `changeme`. Defaults require explicit loopback-only
> `MAILROOM_OPERATOR_ALLOW_DEV_DEFAULTS=1`; otherwise operator access stays disabled.
> `MAILROOM_OPERATOR_AUTH=0` explicitly bypasses operator role checks and
> the reviewer-login requirement for public writes; it is a local-trust
> development setting. Read-only display is unaffected. Cross-origin browser
> writes need the origin listed in `MAILROOM_CORS_ORIGINS`; the TUI sends
> `MAILROOM_OPERATOR_TOKEN`. See `docs/operator-desk.md`.

Admin environment settings seed an empty operator store; they do not rotate
accounts in an existing volume. A public login stays locked while any stored
admin still has the documented default password. Archive verification without
an expected checksum reports an unverified result with a reason.

The poller owns the shared outage floor snapshot. Filtered trace reads do not
replace it; reconnect frames retain stale status and the last successful fetch
time. The TUI shows a closed floor when both WS and HTTP offer only stale/cache
data. Its `history` command shares the last 200 submitted editor commands and
prints the most recent 40.


> [!IMPORTANT]
> `pipeline_schema.py` is cached at process level — editing `taxonomy.yaml`
> (or pointing `MAILROOM_TAXONOMY` at the pipeline's copy) requires a server
> restart to take effect.

</details>

<details>
<summary>The trace contract &amp; the mirror duty</summary>

The-Mailroom does not own the trace contract it renders — it **mirrors** it
from the upstream pipeline. This is the repo's #1 maintenance duty: when
`llm-mailroom` changes span names, observation types (`NODE_OBSERVATION_TYPES`:
chain / agent / evaluator / retriever / generation / span), node order, the
agent roster, live doc classes (five extract classes, including distinct `merger_agreement`,
plus the `unknown` routing token), Hub subclasses, confidence thresholds, or
judge score names (`mailroom-pipeline-judge`, `mailroom-pipeline-quality`),
this repo must update `mailroom_ui/pipeline_schema.py` and
`mailroom_ui/trace_interpreter.py` in the same change window.

Until mirrored, breakage is visible by design: new spans render as an
`unknown` stage, new observation types can hide a node or mis-file a
generation, new doc classes fall back to the gray default stamp color,
renamed judge scores vanish from runs. The full contract — span inventory,
observation types, score names, metadata/tags, and the complete breakage map
— lives in [`AGENTS.md`](AGENTS.md) ("Sister repo" section), which is
authoritative for pipeline internals alongside the pipeline's own `AGENTS.md`.

</details>

<details>
<summary>Project layout</summary>

```
mailroom_ui/   data core — Langfuse + Phoenix adapters, trace interpreter,
               topology mirror, models, metrics (reads trace sources only)
server/        FastAPI, read-only: /api/* + debug endpoints + WebSocket + serves web/
               (also mounts operator_desk at /v1/* + /ws/pipeline)
operator_desk/ operator submodule — JWT auth, local archive, Langfuse-backed
               ops, bin observer (not a display source)
ui/            optional React operator desk (npm; /desk when built — never
               required for mailroom-web; pixel + Observatory stay vanilla)
web/           pixel-art SPA (vanilla HTML/CSS/JS, no build step)
hosted/        Observatory — public modern accessible desk
tui/           rich console — the pipeline in a terminal (mailroom-tui)
scripts/       seed_demo (demo runs INTO Langfuse) · demo_pilot_run
               (staggered floor recording) · run_production_pilot
               (live Qwen 3.7-Flash HF subset) · eval_pipeline
               (Langfuse traces vs mailroom-dataset GT) · export_snapshot (Pages
               data) · publish_pages (gh-pages push, no Actions) · release
               · render_tui_shots (README TUI SVGs)
docs/ + wiki/  mirrored documentation (wiki/sync-wiki.sh publishes the wiki)
docs/screenshots/  stills of every pixel / Observatory / TUI desk
docs/demos/        HF Space live walkthrough + v030/pilot mp4s + The-Mailroom-Demos.ipynb
tests/         pytest suite against fake clients — never the real APIs
```

</details>

<details>
<summary>Tests</summary>

```bash
python -m pytest tests/ -q
```

Tests never hit real Langfuse — `tests/fake_langfuse.py` provides v2/v3
snake_case and v4 camelCase fixtures mirroring the trace contract. The
suite covers the TUI, every `/api/meta` endpoint, and SPA source contracts
(no JS test harness).

</details>

<details>
<summary>Releases</summary>

Semantic versioning with a Keep-a-Changelog `CHANGELOG.md`, README/wiki
updates on major changes, and annotated `vX.Y.Z` tags matching the changelog.
`python scripts/release.py --help` drives the mechanical steps. See
`AGENTS.md` → "Release process" for the full procedure.

</details>

---

<a id="governed-constellation"></a>

<details>
<summary>The governed constellation</summary>

The-Mailroom is one node of a governed family of repositories sharing one kanban
board, one discussion log, and one trace contract:

```
        ┌─────────────────────────┐         ┌─────────────────────────┐
        │  llm-entity-extraction  │ breeds  │      llm-mailroom       │
        │  prompt-experiment loop │ ──────▶ │   the document pipeline │
        └─────────────────────────┘         └────────────┬────────────┘
                                                         │ Langfuse traces (US cloud)
                                                         ▼
                                        ┌──────────────────────────────┐
                             YOU ARE    │         THE-MAILROOM         │
                               HERE ▶   │    pixel-art visual engine   │
                                        └──────────────────────────────┘
```

| Repository | Role | Relationship to The-Mailroom |
| --- | --- | --- |
| [llm-mailroom](https://github.com/Exios66/llm-mailroom) | LangGraph state machine processing legal documents through specialist LLM agents (classify → extract → report → archive); pin `@1a1ec3dfb4e71f615f5d34f6198f9d06fd8c26dd` / **0.8.1** (reviewed source adoption) (package `mailroom` 0.8.1) | **Upstream** — its Langfuse project is this visualizer's sole data source; optional `pip install -e ".[pipeline]"` imports `pipeline.review_resolve` |
| [llm-entity-extraction](https://github.com/Exios66/llm-entity-extraction) | Prompt-experiment loop (prompt versions × models, paired-bootstrap ablations) | Breeds the pipeline's sorter/specialist prompts; hosts the shared kanban board + governance log for the whole chain |
| [llm-dojo-scoring](https://github.com/Exios66/llm-dojo-scoring) | Canonical scoring engine (`@4740d768`, Dojo v0.24.2) | Upstream engine for pipeline and sandbox; visualizer offline evaluation uses optional `[eval]` |
| [Enron-Evaluation-Environment](https://github.com/Exios66/Enron-Evaluation-Environment) | EDA + pipeline-ready correspondence dataset (CMU Enron corpus) | Corpus feed for the pipeline's `correspondence` doc class |
| [claims-data-eda](https://github.com/Exios66/claims-data-eda) | Insurance-claims candidate-corpus EDA (CMS DE-SynPUF direction) | Candidate corpus feed for the `insurance_claim` doc class |
| [atticus-investigation](https://github.com/Exios66/atticus-investigation) | LegalBench classification prompt-engineering pipeline | Eval sibling — same methodology family, LegalBench focus |
| [llm-mailroom-graph](https://exios66.github.io/llm-mailroom-graph/) · [llm-entity-extraction-graph](https://exios66.github.io/llm-entity-extraction-graph/) | Interactive graphify knowledge graphs | Derived sites mapping the pipeline's and the loop's code structure |

Full relationship map: [`llm-mailroom/docs/pipeline-reference-llm-mailroom/sister-repos.md`](https://github.com/Exios66/llm-mailroom/blob/main/docs/pipeline-reference-llm-mailroom/sister-repos.md).

</details>

<a id="where-it-fits"></a>

## 🌌 Where it fits

<div align="center">
<picture>
  <source media="(max-width: 640px)" srcset="docs/assets/readme/constellation-mobile.svg"/>
  <img src="docs/assets/readme/constellation.svg" alt="Data-flow map of the Mailroom constellation with The-Mailroom highlighted: the pipeline sends traces to Langfuse, which feed this visualizer, shared by the pipeline and the sandbox" width="100%"/>
</picture>
</div>

| | Neighbour | Relationship |
| :---: | :--- | :--- |
| 🏛️ | [`Digital-Mailroom`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom) | The integration hub. It imports this repository as `packages/The-Mailroom` and owns the wiring |
| 🧠 | [`llm-mailroom`](https://github.com/Exios66/llm-mailroom) | The pipeline whose Langfuse traces are this visualizer's data source |
| 🔁 | [`mailroom-reloaded`](https://github.com/Exios66/mailroom-reloaded) | The CrewAI-Flows pipeline, read through the Phoenix source (see [Mailroom Reloaded](#mailroom-reloaded)) |
| 🧪 | [`local-mailroom-sandbox`](https://github.com/Exios66/local-mailroom-sandbox) | The offline and GPU testing interface that shares this visualizer |
| 🥋 | [`llm-dojo-scoring`](https://github.com/Exios66/llm-dojo-scoring) | The scoring engine, used here only by the optional `[eval]` extra |

The older governed-family table, with the sibling prompt-loop and corpus repositories, is under
[The governed constellation](#governed-constellation).

<a id="faq"></a>

## ❓ FAQ

<details>
<summary><b>Where does the data on screen come from?</b></summary>

Langfuse traces, always, plus the Phoenix source for Mailroom Reloaded. Even demo runs are seeded **into** Langfuse with `scripts/seed_demo.py`, so nothing on screen is canned data.

</details>

<details>
<summary><b>Do I need the pipeline running?</b></summary>

Not to watch. The floor, inspector, history and metrics read Langfuse. Review actions (Approve / Reject / Requeue) need `MAILROOM_PIPELINE_URL` and `MAILROOM_PIPELINE_TOKEN` pointing at the llm-mailroom API on `:8000`.

</details>

<details>
<summary><b>Why does the TUI say not to point `MAILROOM_API_URL` at `:8000`?</b></summary>

The TUI talks to this visualizer's display API (`/api/*` + `/ws`), not to the producer. Resolutions still reach the producer because the visualizer forwards them.

</details>

<details>
<summary><b>Is the Observatory the same as the GitHub Pages site?</b></summary>

No. The Observatory (`mailroom-hosted`, `/live`) is a live site for a real host such as a Hugging Face Docker Space or Railway. GitHub Pages carries a static edition and the terminal site.

</details>

<details>
<summary><b>Can I try it without a live run?</b></summary>

Yes. Seed the 13 demo runs with `python scripts/seed_demo.py`, or start the review-tray stub with `PYTHONPATH=. python scripts/demo_review_tray.py --port 8006`.

</details>

<a id="built-on"></a>

## 🙏 Built on

The visualizer is built on:

| Project | What it does here |
| :--- | :--- |
| [Langfuse](https://langfuse.com/) | The sole display source for llm-mailroom runs |
| [Arize Phoenix](https://phoenix.arize.com/) (optional) | The trace source for [Mailroom Reloaded](#mailroom-reloaded) |
| [FastAPI](https://github.com/fastapi/fastapi) · [Uvicorn](https://github.com/encode/uvicorn) | The shared display API and WebSocket |
| [AgentLaboratory](https://github.com/SamuelSchmidgall/AgentLaboratory) | The visual palette and character direction derive from its artwork |

<a id="contributing-security-and-license"></a>
<a id="license--credits"></a>

## 🤝 Contributing, security and license

| | |
| :--- | :--- |
| **Contributing** | Read [`AGENTS.md`](AGENTS.md) before changing code. This repository owns the visualizer used by both the pipeline and the sandbox; the hub [contributing guide](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/CONTRIBUTING.md) covers the card workflow and the import into Digital-Mailroom. For the full governed constellation, see the llm-mailroom [sister-repos map](https://github.com/Exios66/llm-mailroom/blob/main/docs/pipeline-reference-llm-mailroom/sister-repos.md). |
| **Security** | Report vulnerabilities privately as described in the hub [security policy](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/SECURITY.md), which covers this package. Keep Langfuse keys and the pipeline token in `.env` or host secrets, never in the repository. |
| **License** | No license published yet. |


---

<div align="center">

**[Digital-Mailroom](https://github.com/LLM-Mailroom-Services/Digital-Mailroom)** ·
**[llm-mailroom](https://github.com/Exios66/llm-mailroom)** ·
**[llm-dojo-scoring](https://github.com/Exios66/llm-dojo-scoring)** ·
**[The-Mailroom](https://github.com/Exios66/The-Mailroom)** ·
**[local-mailroom-sandbox](https://github.com/Exios66/local-mailroom-sandbox)** ·
**[Mailroom-Corpus-EDA](https://github.com/Exios66/Mailroom-Corpus-EDA)** ·
**[mailroom-ml](https://github.com/LLM-Mailroom-Services/mailroom-ml)**

<sub>The-Mailroom · one of the Mailroom constellation's independent source repositories, with shared interfaces.</sub>
<br/>
<sub>Core packages integrate in Digital-Mailroom; mailroom-ml is a standalone contractor.</sub>
<br/>
<sub>🏤 <i>Watch the work move.</i> · Artwork: <a href="docs/assets/readme/README.md">design and regeneration</a></sub>

</div>
