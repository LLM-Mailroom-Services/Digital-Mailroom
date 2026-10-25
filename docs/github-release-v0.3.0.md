## v0.3.0 — review resolve, live floor, skills, and reconsideration

The cut of everything on `main` since [`v0.2.0`](https://github.com/Exios66/The-Mailroom/releases/tag/v0.2.0): PRs #2–#18. Langfuse stays the sole document display source — every envelope, verdict, and metric on screen is an interpreted trace.

### Demos

Full-screen recordings of the new desks (click to play on GitHub):

| Demo | What you see |
|---|---|
| [Pixel desks (~42s)](https://github.com/Exios66/The-Mailroom/blob/main/docs/demos/v030-pixel-desks-review-resolve.mp4) | INBOX hopper, inspector resolve form, REVIEW Approve / Reject / Requeue, RECONSIDER card. Approve against an unconfigured producer shows the honest HTTP 503. |
| [Observatory (~52s)](https://github.com/Exios66/The-Mailroom/blob/main/docs/demos/v030-observatory-review-resolve.mp4) | Inbox tray, Review resolve + inspect dialog, History / Matters / Metrics / Debug. |
| [Pilot run (~25s)](https://github.com/Exios66/The-Mailroom/blob/main/docs/demos/pilot-run-documents-through-pipeline.mp4) | Envelopes travelling the conveyor (REVIEW siding + failed bin). |
| [Desk walkthrough (~56s)](https://github.com/Exios66/The-Mailroom/blob/main/docs/demos/tui-server-observatory-desk-walkthrough.mp4) | Pixel desks then Observatory (v0.2-era still). |

Re-record the v0.3.0 cast with `PYTHONPATH=. python scripts/demo_v030_cast.py --port 8006`.

### Added (highlights)

- **Human-review resolve** — pixel REVIEW, inspector, Observatory Review, and `mailroom-tui --resolve` approve / reject / record / requeue. Visualizer proxies `POST /api/review/resolve` to llm-mailroom (`MAILROOM_PIPELINE_URL` + `MAILROOM_PIPELINE_TOKEN`); the browser never holds the producer token. Snapshot / GH Pages stay read-only.
- **Project Agent Skills** — `.cursor/skills/` (router + Langfuse / Phoenix / Braintrust / Ollama / Modal / HF + pixel / Observatory / live floor / schema / Pages / TUI).
- **Live conveyor freshness + INBOX hopper** — in-flight traces re-enrich every poll; `GET /api/pipeline` reports watcher/inbox when the producer URL is set.
- **Observatory Inbox tray** — `stage=inbox` parks in its own tray.
- **Reconsideration beyond self-reported confidence** — archived objective misses (judge MISS/PARTIAL, GT mismatch, extraction floor, …) join REVIEW as RECONSIDER even at 0.99 confidence.
- **Dojo 0.9–0.11 / Langfuse data-model mirrors**, hosted Observatory, GH Pages edition, production HF eval, 7-day live window alignment.

Full record: [CHANGELOG.md](https://github.com/Exios66/The-Mailroom/blob/main/CHANGELOG.md)

<p align="center">
  <img src="https://raw.githubusercontent.com/Exios66/The-Mailroom/cursor/release-v030-62f9/docs/screenshots/review.png" width="700" alt="REVIEW siding with Approve / Reject / Requeue"/>
</p>
