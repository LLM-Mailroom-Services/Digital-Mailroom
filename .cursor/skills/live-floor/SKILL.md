---
name: live-floor
description: Keep The-Mailroom live floor in sync with Langfuse (PollHub, WebSocket /ws, inflight re-enrich, MAILROOM_POLL_INTERVAL, MAILROOM_PIPELINE_URL watcher/inbox). Use when envelopes lag stations, traces feel stale, the watcher lamp is wrong, or HTTP fallback poll is too slow.
---

# Live floor (poll + watcher lamp)

**When:** Envelopes stuck on the previous station, new traces lag, WS vs HTTP
fallback mismatch, `MAILROOM_PIPELINE_URL`, inbox pending, watcher live/stale.
**Display data stays Langfuse.** Pipeline URL is operator liveness only.

## Behavior

| Piece | Contract |
| --- | --- |
| Poll | `MAILROOM_POLL_INTERVAL` (default 3s); list/obs TTL matches it |
| In-flight | `inflight_ttl=0` — re-enrich every poll |
| Terminal | 60s detail cache until fingerprint (`updated_at` / stage / latency) changes |
| Review parked | 15s `review_ttl` |
| WS | `/ws` snapshot includes `poll_interval_s` + `pipeline` |
| HTTP fallback | same interval as the hub (pixel + Observatory); retune if interval changes |
| Watcher | `GET /api/pipeline` ← producer `GET /v1/health` (`checks.watcher`, inbox_pending) |

`mailroom_ui/pipeline_ops.py` never fabricates queue rows. Missing
`MAILROOM_PIPELINE_URL` → `configured: false`.

Pixel console logs inbox pending **only when the count changes**.

## Producer pairing

Visualizer freshness without producer per-node `flush()` still waits on
Langfuse list lag. The pipeline should embed the inbox watcher with the API
and publish `output.stage` after each node (see `llm-mailroom` watcher/tracing).
Set:

```bash
MAILROOM_PIPELINE_URL=http://127.0.0.1:8000
# or https://<user>-mailroom-producer.hf.space  (required from a Space Observatory)
MAILROOM_PIPELINE_TOKEN=$MAILROOM_API_TOKEN
MAILROOM_PIPELINE_API_PREFIX=/v1
```

`MAILROOM_API_URL` is the TUI’s pointer at **this** visualizer (`:8001`), not
the producer.

## Related

- Source: [langfuse](../langfuse/SKILL.md)
- Pixel: [pixel-console](../pixel-console/SKILL.md)
- Code: `server/poller.py`, `mailroom_ui/pipeline_ops.py`
