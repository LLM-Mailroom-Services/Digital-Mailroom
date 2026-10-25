"""Source-level contracts for the vanilla SPA.

There is no JS test harness (see AGENTS.md). These assertions lock the
exact bugs that blanked REVIEW / GH Pages / the floor animation so they
cannot silently regress.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = (ROOT / "web" / "js" / "api.js").read_text()
MAIN = (ROOT / "web" / "js" / "main.js").read_text()
FLOOR = (ROOT / "web" / "js" / "floor.js").read_text()
INDEX = (ROOT / "web" / "index.html").read_text()


def test_review_queue_dispatch_uses_object_key():
    """REVIEW tab called dispatch('review-queue') but remote/snapshots
    are keyed reviewQueue — TypeError on every refresh, live and Pages."""
    assert 'reviewQueue: (...a) => dispatch("reviewQueue", ...a)' in API
    assert "since = 604800" in API
    assert 'get(`/api/traces?since=${since}&limit=${limit}`)' in API
    assert "pullServer" in API and "pushClient" in API
    assert 'url("/api/debug/bundle")' in API
    assert "href: location.href" in API
    assert "eventCount: dbgEvents.length" in API
    assert 'dispatch("review-queue"' not in API
    assert 'dispatch("reviewResolve"' in API
    assert 'post("/api/review/resolve"' in API
    assert "function reviewPanel" in API
    assert "function bindReviewForms" in API
    assert "snapshot mode is read-only — review resolve needs a live API" in API
    assert "reviewSource" in API
    assert "review-source-text" in API
    assert 'name="doc_type"' in API
    assert 'name="doc_subclass"' in API
    assert 'name="extracted_data"' in API
    assert 'data-disposition="complete"' in API


def test_snapshot_fetches_are_same_origin_not_api_base():
    """A persisted ?api= pointing at a dead host used to prefix data/*.json
    and blank the GH Pages fallback (often as http://host:8001data/meta.json)."""
    assert "const snapUrl =" in API
    assert 'fetch(url("data/meta.json")' not in API
    assert "fetch(url(`data/${name}.json`)" not in API
    assert "snapUrl(`data/${name}.json`)" in API
    assert 'snapUrl("data/meta.json")' in API


def test_empty_api_query_clears_persisted_base():
    assert "if (qs.has(\"api\"))" in API
    assert 'localStorage.setItem("mailroom.api", BASE)' in API


def test_run_detail_uses_export_safe_id():
    assert "safeId(id)" in API
    assert "return snap(`runs/${safeId(id)}`)" in API
    assert "encodeURIComponent(id)" in API  # live /api/traces/{id} still encodes


def test_boot_does_not_fetch_meta_before_health():
    """Pages has no /api/meta — a boot-time meta() painted ERROR — HTTP 404
    across the status bar on every visit."""
    assert "Mailroom.api.meta()" not in MAIN.split("function boot()")[1]
    assert "async function loadMeta()" in MAIN
    assert "await loadMeta()" in MAIN


def test_floor_uses_week_window_and_demo_is_opt_in():
    assert "traces(604800, 200)" in MAIN
    assert "since = 604800" in API
    # Bare D must not fabricate envelopes on a live floor.
    before = MAIN.split("Demo envelopes")[0]
    assert 'if (ev.key === "d" || ev.key === "D")' not in before


def test_floor_frame_does_not_self_schedule():
    """Leftover requestAnimationFrame(frame) defeated the V-17 idle pause
    and ran a second 60fps chain on top of loop()."""
    assert "requestAnimationFrame(frame)" not in FLOOR
    assert "requestAnimationFrame(loop)" in FLOOR


def test_archive_station_is_a_real_target():
    """catalog/archive stages used to park on REPORT; ARCHIVE was decorative."""
    assert "STATIONS[5].x" in FLOOR
    assert 'st === "catalog" || st === "archive"' in FLOOR
    assert "catalog: 5, archive: 5, archived: 5" in FLOOR
    assert "drawInboxHopper" in FLOOR
    assert 'st === "inbox"' in FLOOR
    assert "INBOX" in FLOOR


def test_live_poll_matches_server_interval_and_pipeline_ops():
    """Fallback poll used to be a hard-coded 10s, so new traces lagged the
    3s WebSocket snapshot. Pipeline watcher/inbox rides the same snapshot."""
    assert "pollIntervalMs" in MAIN
    assert "applyPipeline" in MAIN
    assert "ops.inbox_pending !== prevInbox" in MAIN
    assert "fallbackPollMs === pollIntervalMs" in MAIN
    assert 'dispatch("pipeline"' in API
    assert 'get("/api/pipeline")' in API
    hosted_app = (ROOT / "hosted" / "js" / "app.js").read_text()
    hosted_client = (ROOT / "hosted" / "js" / "client.js").read_text()
    assert '"normalize-intake": "intake"' in hosted_app
    assert "applyPipelineOps" in hosted_app
    assert "startFallbackPolling" in hosted_app
    assert '{ key: "inbox", label: "Inbox", stages: ["inbox"] }' in hosted_app
    assert 'get("/api/pipeline")' in hosted_client
    assert "reviewResolve" in hosted_client
    assert "reviewSource" in hosted_client
    assert "function reviewForm" in hosted_app
    assert 'data-decision="approved"' in hosted_app
    assert 'name="doc_type"' in hosted_app
    assert "review-source-text" in hosted_app
    assert 'name="extracted_data"' in hosted_app
    assert 'data-disposition="complete"' in hosted_app
    assert "run.failure_class" in hosted_app
    assert "run.run_aborted" in hosted_app
    assert "Primary" in hosted_app
    assert "Secondary" in hosted_app
    assert "primary_outcome" in hosted_app
    assert "headline-strip" in hosted_app or "renderHeadlines" in hosted_app
    card_fn = hosted_app.split("function cardHTML")[1].split("function matchesFilter")[0]
    assert "classification_confidence" not in card_fn
    assert "extraction_confidence" not in card_fn
    assert "inboxEnqueue" in hosted_client
    assert "postForm" in hosted_client
    assert "FormData" in hosted_app
    assert "snapshot" in hosted_client
    assert "/api/inbox/enqueue" in hosted_client
    assert "/api/snapshot" in hosted_client
    assert "Export snapshot" in (ROOT / "hosted" / "index.html").read_text()
    assert "Queue a document" in (ROOT / "hosted" / "index.html").read_text()


def test_error_banner_is_outside_overflow_hidden_screen():
    screen_close = INDEX.find('id="error-banner"')
    bezel_close = INDEX.find("</div>\n<div id=\"error-banner\"")
    assert bezel_close != -1
    assert screen_close > INDEX.find('class="screen"')


def test_favicon_is_inline_to_avoid_pages_404():
    assert 'rel="icon"' in INDEX
    assert "data:image/svg+xml" in INDEX


def test_desk_tabs_show_loading_placeholder():
    """SESSIONS / REVIEW / METRICS / HISTORY used to stay blank while a
    2-minute Langfuse enrich ran, so verification looked like empty desks."""
    review = (ROOT / "web" / "js" / "review.js").read_text()
    sessions = (ROOT / "web" / "js" / "sessions.js").read_text()
    metrics = (ROOT / "web" / "js" / "metrics.js").read_text()
    history = (ROOT / "web" / "js" / "history.js").read_text()
    assert "LOADING REVIEW QUEUE FROM LANGFUSE" in review
    assert "r.failure_class" in review
    assert "Mailroom.reviewPanel(r)" in review
    assert "producerBanner().catch" in review
    assert 'data-decision="approved"' in API
    assert "stopPropagation" in API
    assert "LOADING SESSIONS FROM LANGFUSE" in sessions
    assert ".slice(0, 20)" not in sessions
    theme = (ROOT / "web" / "css" / "theme.css").read_text()
    assert "max-height" in theme.split(".session-runs")[1][:200]
    assert "LOADING METRICS FROM LANGFUSE" in metrics
    assert "LOADING RUN HISTORY FROM LANGFUSE" in history


def test_inspector_renders_typed_observations():
    """llm-mailroom #29 types nodes as AGENT/EVALUATOR/RETRIEVER/CHAIN.
    The pixel inspector must surface those types (and user/release)."""
    inspector = (ROOT / "web" / "js" / "inspector.js").read_text()
    theme = (ROOT / "web" / "css" / "theme.css").read_text()
    assert "<h3>OBSERVATIONS</h3>" in inspector
    assert "observation_type" in inspector
    assert "obsTypeChip" in inspector
    assert "run.user_id" in inspector and "run.release" in inspector
    assert "run.doc_subclass" in inspector
    assert "run.doc_id" in inspector
    assert "Mailroom.reviewPanel(run)" in inspector
    assert "run.expected_subclass" in inspector
    assert "run.intake_messy" in inspector
    assert "run.failure_class" in inspector
    assert "run.run_aborted" in inspector
    assert "SUITE EXTRAS" in inspector
    assert "content_topic_accuracy" in inspector
    assert ".chip.obs-agent" in theme
    assert ".chip.obs-evaluator" in theme
    assert ".chip.obs-retriever" in theme
    assert ".chip.obs-chain" in theme
