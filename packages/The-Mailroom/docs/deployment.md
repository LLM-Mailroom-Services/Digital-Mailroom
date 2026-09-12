# Deployment Guide — The-Mailroom

The-Mailroom is a **read-only** visualizer. It never writes Langfuse events
and never runs the document graph. Deploy it next to (or pointed at) a live
[`llm-mailroom`](https://github.com/Exios66/llm-mailroom) Langfuse project.

## Prerequisites

- Python 3.11+
- Langfuse project API keys (`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`)
- Optional: producer URL + token for REVIEW resolve / Inbox upload
  (`MAILROOM_PIPELINE_URL` / `MAILROOM_PIPELINE_TOKEN`)

Copy `.env.example` → `.env` and fill the Langfuse keys before a local run.

```bash
pip install -e ".[dev]"
python -m server.main          # pixel console on :8001
mailroom-hosted                # Observatory on 0.0.0.0
```

---

## Railway

Railway **retired Config as Code** (`railway.json` / `railway.toml`) — new
projects stopped reading it on 2026-08-28, existing services stop on
2026-12-01. The repo ships **Infrastructure as Code** instead:
[`.railway/railway.py`](../.railway/railway.py) (`railway_sdk`, the beta
Python mirror of the TypeScript DSL — authoring-only, never a runtime dep).
The CLI evaluates it against the live environment: `railway config plan`
previews the diff, `railway config apply` applies it. Railway builds the
repo's root **Dockerfile** when it finds one (no build command needed).

Deploys probe `GET /health` (fast process liveness — **not** a Langfuse call).
`GET /api/health` remains the SPA / TUI source-reachability check. Both
`/health` and `/api/meta` now carry `platform` (`railway` / `render` / `fly` /
`huggingface`) and `build_sha` (commit baked from `RAILWAY_GIT_COMMIT_SHA`)
so a deploy is verifiable at a glance. `nixpacks.toml` is a fallback if the
service is ever switched off the Dockerfile builder.

### Why `PORT` matters

The image defaults `MAILROOM_PORT=7860` (Hugging Face Spaces). Railway
injects `$PORT` and proxies to that port. The server prefers **`PORT` over
`MAILROOM_PORT`** so the process binds where the edge expects — same
contract as the llm-mailroom producer.

### Why deploys looked “crashed”

1. **Wrong listen port.** Binding image `7860` while Railway proxies
   `$PORT` → edge connection refused → `CRASHED` / restart loop.
2. **Health probe hung on Langfuse.** An older `/health` alias called the
   Langfuse API (SDK timeout ~15s). Docker `HEALTHCHECK` is 5s; a slow or
   missing key set made the container look unhealthy. `/health` is now
   pure liveness (`{"ok": true, "status": "alive"}`).

### Variable ownership

`.railway/railway.py` declares the non-secret service variables
(`MAILROOM_EDITION=hosted`, `MAILROOM_HOST=0.0.0.0`,
`MAILROOM_POLL_ENRICH=inflight`, `MAILROOM_TRACE_CACHE_DIR=...`) and
`preserve()`s the secrets — Railway keeps whatever the service already holds.
Only these must be set on the service (dashboard / `railway variables set`):

| Variable | Value |
|---|---|
| `LANGFUSE_PUBLIC_KEY` | Langfuse project public key |
| `LANGFUSE_SECRET_KEY` | Langfuse project secret key |
| `LANGFUSE_HOST` | `https://us.cloud.langfuse.com` (or EU / self-hosted) |
| `MAILROOM_PIPELINE_URL` | public producer URL (optional REVIEW pairing) |
| `MAILROOM_PIPELINE_TOKEN` | same secret as producer `MAILROOM_API_TOKEN` |
| `MAILROOM_PIPELINE_API_PREFIX` | `/v1` |

Optional Hub/eval knobs on this service (same as the producer side):

| Variable | Value |
|---|---|
| `MAILROOM_TRACE_LIMIT` | `100` (keeps floor polls snappy) |
| `HF_TOKEN` | Hub token (eval / sync / Space publish) |
| `MAILROOM_HF_DATASET` | `Lucius-Morningstar/mailroom-dataset` |
| `MAILROOM_HF_REVISION` | corrected GT tip (see `mailroom_ui/hf_corpus.py`) |
| `MAILROOM_HF_CONFIG` | `ground_truth` |

On the **producer** (`llm-mailroom`) set the same `MAILROOM_HF_*` plus
`HF_HOME=/data/huggingface` and `HF_HUB_CACHE=/data/huggingface/hub` so
pilots read the pinned parquet from a volume cache instead of re-pulling
Hub every run.

Display stays Langfuse-only. Without Langfuse keys the UI shows
**MAILROOM CLOSED** — never canned envelopes. The process still passes
`GET /health` so Railway does not restart-loop on a closed floor.
GT / pilot intake derive from the Hub corpus above
(`scripts/eval_pipeline.py`, `scripts/sync_pilot_dataset.py`).

### Deploy

```bash
railway link        # once (select the project/environment)
pip install railway-sdk   # authoring only — evaluates .railway/railway.py

railway config plan    # preview: service, healthcheck, variables
railway config apply   # confirm and apply
# If the service was still on legacy railway.json, migrate it first:
#   railway config migrate --lang py --apply --delete-files

railway up -m "mailroom observatory"   # deploy the current tree
```

Generate a public domain (`railway domain`) and open it. Health:

```bash
curl -sS https://<domain>/health      # liveness (+ platform, build_sha)
curl -sS https://<domain>/api/health  # Langfuse / cache status
```

Pair the producer the same way llm-mailroom documents under its
`docs/deployment.md` § Railway — point this service's
`MAILROOM_PIPELINE_*` at the producer domain.

### Railway deploy CRASHED / restart loop

- Confirm runtime logs show `Uvicorn running on http://0.0.0.0:<PORT>`
  where `<PORT>` matches Railway’s injected `PORT` (not stuck on 7860).
- Confirm `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` are set on the
  **service** (not only shared) if you expect a live floor.
- Confirm `railway config plan` shows the service managed by
  `.railway/railway.py` (not a leftover `railway.json` — Railway blocks dual
  management; `railway config migrate --lang py --apply --delete-files`
  clears a legacy file and its service setting).
- Confirm `curl /health` returns quickly with `"status":"alive"` even when
  `/api/health` reports `"ok": false` (MAILROOM CLOSED).

---

## Hugging Face Spaces (Docker)

The same root `Dockerfile` is the Space image (`MAILROOM_EDITION=hosted`,
`0.0.0.0:7860`, `python -m server.hosted`). Publish with
`scripts/publish_space.py` — Langfuse keys stay Space **secrets**, never
the git tree. Details: [`hosted/SPACE_README.md`](../hosted/SPACE_README.md).

---

## GitHub Pages (static snapshot)

Deploy-from-branch only — `scripts/publish_pages.sh` → `gh-pages:/docs`.
No Actions. See [`.cursor/skills/gh-pages/SKILL.md`](../.cursor/skills/gh-pages/SKILL.md).
