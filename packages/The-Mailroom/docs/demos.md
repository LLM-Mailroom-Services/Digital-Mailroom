# Demos & screenshots

> Mirrored at `wiki/Demos.md`. Stills live in [`docs/screenshots/`](screenshots/);
> the walkthrough video and notebook live in [`docs/demos/`](demos/).

> **Media note:** these assets are pruned from this checkout (`docs/demos/`
> and `docs/screenshots/` do not exist locally) — they live upstream in the
> `LLM-Mailroom-Services/Digital-Mailroom` repo under
> `packages/The-Mailroom/docs/{demos,screenshots}/` (raw URLs on github.com).

The pixel console, hosted Observatory, and TUI share one display API.
These captures document those desks. **Langfuse is still the sole display
source** — nothing here is canned data served to the UI.

## Hugging Face Space — live Observatory (2026-08-30)

~102 seconds, recorded against the public Docker Space after #30
(classification cards, headline strip, inbox queue, snapshot cache).
Langfuse is live (74 runs in the window). Producer knobs were unset, so
Queue a document shows the honest setup hint. Approve / Reject were not
clicked.

Live app: https://lucius-morningstar-mailroom-observatory.hf.space/  
Hub card: https://huggingface.co/spaces/Lucius-Morningstar/mailroom-observatory

[![HF Space Observatory Pipeline](demos/hf-space-observatory-poster.png)](demos/hf-space-observatory-live-walkthrough.mp4)

- Video: [`docs/demos/hf-space-observatory-live-walkthrough.mp4`](demos/hf-space-observatory-live-walkthrough.mp4)
- Covers Pipeline (inspect + filters + Export snapshot) → Review → History
  replay → Matters → Metrics → Debug → back to Pipeline.

## Working REVIEW tray (producer stub)

`scripts/demo_v030_cast.py` still shows the honest 503 when the producer URL
is unset. For a **working** resolve path (lookup, source fallback, resume /
record / requeue / complete):

```bash
PYTHONPATH=. python scripts/demo_review_tray.py --check-api
PYTHONPATH=. python scripts/demo_review_tray.py --port 8006
# pixel        → http://127.0.0.1:8006/?api=
# Observatory  → http://127.0.0.1:8006/live?api=
```

Display traces are FakeClient (same contract as the test suite). The stub is
`tests/fake_producer.py` and speaks llm-mailroom `/v1` — including
`override_doc_type`. Lookup serialization comes from pinned
`pipeline.review_resolve.serialize_document` when `[pipeline]` (or a sibling
checkout) is importable. It does **not** implement `GET /documents/{id}/source`
(same as producer main); the text pane uses catalog lookup.

## v0.3.0 release demos

Full-screen recordings of the new desks (INBOX hopper, REVIEW resolve,
RECONSIDER, Observatory Inbox tray). FakeClient traces via
`scripts/demo_v030_cast.py` — Langfuse remains the display contract; resolve
posts show the honest 503 when `MAILROOM_PIPELINE_URL` is unset.

**Pixel desks** (~42s): FLOOR → inspector → REVIEW Approve → SESSIONS /
HISTORY / METRICS / CONSOLE.

[![v0.3.0 pixel REVIEW](demos/v030-pixel-poster.png)](demos/v030-pixel-desks-review-resolve.mp4)

- Video: [`docs/demos/v030-pixel-desks-review-resolve.mp4`](demos/v030-pixel-desks-review-resolve.mp4)
- Re-record: `PYTHONPATH=. python scripts/demo_v030_cast.py --port 8006`

**Observatory** (~52s): Pipeline (Inbox tray) → Review resolve + inspect
dialog → History / Matters / Metrics / Debug.

[![v0.3.0 Observatory Pipeline](demos/v030-observatory-poster.png)](demos/v030-observatory-review-resolve.mp4)

- Video: [`docs/demos/v030-observatory-review-resolve.mp4`](demos/v030-observatory-review-resolve.mp4)

## Walkthrough video (PR recording)

~56 seconds, 1920×1200: FLOOR → REVIEW → SESSIONS → HISTORY → METRICS →
CONSOLE → inspector, then Observatory Pipeline → Review → History →
Matters → Metrics → Debug.

[![Walkthrough poster](demos/walkthrough-poster.png)](demos/tui-server-observatory-desk-walkthrough.mp4)

- Video: [`docs/demos/tui-server-observatory-desk-walkthrough.mp4`](demos/tui-server-observatory-desk-walkthrough.mp4)
  (click the file on GitHub to play it)
- Notebook gallery: [`docs/demos/The-Mailroom-Demos.ipynb`](demos/The-Mailroom-Demos.ipynb)

## Pilot run — documents moving through the pipeline

~25 seconds, 1920×1200. A staggered FakeClient pilot (`scripts/demo_pilot_run.py`)
feeds `/api` + `/ws` so envelopes actually travel the conveyor: contract and
claim archive, the merger agreement peels to REVIEW, correspondence goes
through JUDGE/ARBITER, a corporate record fails.

[![Pilot run poster](demos/pilot-run-poster.png)](demos/pilot-run-documents-through-pipeline.mp4)

- Video: [`docs/demos/pilot-run-documents-through-pipeline.mp4`](demos/pilot-run-documents-through-pipeline.mp4)
- Still: [`docs/screenshots/pilot-floor.png`](screenshots/pilot-floor.png)
- Re-record:

```bash
PYTHONPATH=. python scripts/demo_pilot_run.py --port 8005 --delay 8
# then open http://127.0.0.1:8005/?api=
```

## Pixel-art console (`mailroom-web`)

| Still | Desk |
|---|---|
| [floor.png](screenshots/floor.png) | FLOOR conveyor |
| [pilot-floor.png](screenshots/pilot-floor.png) | PILOT RUN — envelopes in motion |
| [inspector.png](screenshots/inspector.png) | INSPECTOR |
| [review.png](screenshots/review.png) | REVIEW siding — Approve / Reject / Requeue + RECONSIDER |
| [sessions.png](screenshots/sessions.png) | SESSIONS / matters |
| [history.png](screenshots/history.png) | HISTORY + REPLAY |
| [metrics.png](screenshots/metrics.png) | METRICS |
| [console.png](screenshots/console.png) | CONSOLE |

## Hosted Observatory (`/live`)

| Still | Desk |
|---|---|
| [observatory-pipeline.png](screenshots/observatory-pipeline.png) | Pipeline trays (incl. Inbox) |
| [observatory-review.png](screenshots/observatory-review.png) | Review resolve forms |
| [observatory-history.png](screenshots/observatory-history.png) | History + Replay |
| [observatory-matters.png](screenshots/observatory-matters.png) | Matters |
| [observatory-metrics.png](screenshots/observatory-metrics.png) | Metrics |
| [observatory-debug.png](screenshots/observatory-debug.png) | Debug |

## TUI (`mailroom-tui`)

| Still | Desk |
|---|---|
| [tui-console.png](screenshots/tui-console.png) | Floor |
| [tui-review.png](screenshots/tui-review.png) | Review |
| [tui-sessions.png](screenshots/tui-sessions.png) | Sessions |
| [tui-metrics.png](screenshots/tui-metrics.png) | Metrics |

TUI SVGs (re-renderable): `tui-console.svg`, `tui-review.svg`,
`tui-sessions.svg`, `tui-metrics.svg` in the same folder.
`MAILROOM_API_URL=http://127.0.0.1:8001 python scripts/render_tui_shots.py`

## Seed traces into Langfuse

```bash
python scripts/seed_demo.py
python scripts/seed_demo.py --list-scenarios
python scripts/seed_demo.py --check --check-api
```

Demo envelopes are never served as a local JSON fallback. The pixel `D`
key is opt-in (`?demo=1`) and only when the source is down.
