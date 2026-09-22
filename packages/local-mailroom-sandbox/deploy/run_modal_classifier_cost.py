#!/usr/bin/env python3
"""Orchestrator for the Modal (self-hosted vLLM) leg of the cost-per-token
classifier experiment: Qwen/Qwen3-8B on the isolated sorter, driven by the
existing run spec ``config/runs/qwen3_8b_cost_compare_modal.yaml``.

This script COORDINATES existing pieces; it does not reimplement the eval:

* ``deploy/modal_vllm.py``  — deploy facts (``APP_NAME``, ``build_vllm_command``,
  ``_smoke_check``) and the env-knob contract (``MODAL_VLLM_MODEL``/``GPU``/
  ``MAX_MODEL_LEN``/``IMAGE_TAG``/``API_TOKEN``, ``VLLM_API_KEY``,
  ``VLLM_BASE_URL``).
* ``mailroom_sandbox.job.metrics.record_from_run`` / ``aggregate_bucket`` — the
  serving record builder (accepts ``gpu_hourly_usd`` / ``warm_span_seconds`` /
  ``gpu_cost_usd``).
* ``mailroom_sandbox.eval.experiment_log.new_record(identity=...)`` /
  ``append`` — the log row, with the ``PROVIDER_IDENTITY_KEYS`` GPU identity.
* ``sandbox run preflight --force`` + ``sandbox run start`` — the isolated
  classifier eval, executed by the sandbox CLI against a LOCAL token-counting
  proxy that forwards to the Modal /v1 endpoint and captures per-request usage,
  TTFT, and latency.

Flow (``--run``): pre-warm HF cache -> ``modal deploy`` -> poll /v1/models
(Modal returns 503 while scaled to zero) -> uncounted warm-up chat calls
(CUDA-graph/TTFT isolation) -> eval through the proxy -> measure
``warm_span_seconds`` (first request -> last request end) -> price the GPU
(``gpu_hourly_usd`` x warm span, default $0.80/hr, env ``MODAL_GPU_HOURLY_USD``)
-> write the serving record -> print the cost card + OpenRouter-leg comparison
-> ``modal app stop sandbox-vllm``.

Reproducibility: the run spec's ``engine.modal.revision`` (Qwen/Qwen3-8B
commit pin) is propagated to ``MODAL_VLLM_REVISION`` for BOTH the pre-warm
(``download_model``) and the serve boot, so the weights cannot drift between
the two (deploy/modal_vllm.py passes ``--revision`` only when that env is
set). ``--run`` refuses the placeholder ``REVISION_PIN_ME``.

Thinking-mode (Qwen3-8B ChatML): ``enable_thinking`` is ON by default and
adds thinking tokens under ``response_format json_object``, inflating
completion tokens and skewing cost-per-token vs OpenRouter. The warm-up bodies
this driver builds pass ``chat_template_kwargs: {"enable_thinking": false}``.
The MEASURED sorter calls are built by the isolated sorter eval (sandbox CLI)
inside the sandbox, NOT here — that path must be verified to disable thinking
before a billed run (see the run spec comment).

``--mock`` runs the same flow against a fake local /v1 endpoint (no Modal, no
network, no paid ops). ``--preview`` / ``--dry-run`` prints the exact commands
and the cost plan without executing anything.

Secrets are never printed (only presence, mirroring ``modal_vllm._masked_config``).

Usage:
    python deploy/run_modal_classifier_cost.py {--preview|--dry-run|--mock|--run}
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "deploy") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "deploy"))

import modal_vllm  # noqa: E402  (deploy facts only; import has no deploy side effects)

SPEC_PATH = REPO_ROOT / "config" / "runs" / "qwen3_8b_cost_compare_modal.yaml"
RUN_ID = "qwen3-8b-modal-sorter"
OPENROUTER_LEG_RUN_ID = "qwen3-8b-openrouter-sorter"
EXPERIMENT_NAME = "qwen3-8b-cost-per-token"
DEFAULT_GPU_HOURLY_USD = 0.80
WARMUP_CALLS = 3
READY_RETRIES = 240
READY_BACKOFF_SECONDS = 5.0
PROXY_REQUEST_TIMEOUT = 30.0 * 60


def _step(msg: str) -> None:
    print(f"\n== {msg} ==", flush=True)


def _log(msg: str) -> None:
    print(f"  {msg}", flush=True)


def _usd(value: Any) -> str:
    if value is None:
        return "-"
    return f"${float(value):,.4f}"


def _int(value: Any) -> str:
    if value is None:
        return "-"
    return f"{int(value):,}"


def _load_spec() -> Any:
    from mailroom_sandbox.job.spec import load_run_spec

    if not SPEC_PATH.is_file():
        raise SystemExit(f"run spec not found: {SPEC_PATH}")
    return load_run_spec(SPEC_PATH)


def _sandbox_cmd() -> list[str]:
    exe = os.environ.get("SANDBOX_CMD") or shutil.which("sandbox")
    if exe:
        return [exe]
    here = Path(sys.executable).resolve().parent
    for name in ("sandbox.exe", "sandbox"):
        cand = here / name
        if cand.is_file():
            return [str(cand)]
    return [sys.executable, "-m", "mailroom_sandbox.cli"]


def _modal_cmd() -> list[str]:
    exe = os.environ.get("MODAL_CMD") or shutil.which("modal")
    if exe:
        return [exe]
    return [sys.executable, "-m", "modal"]


def _run(cmd: list[str], *, env: dict[str, str] | None = None, allow_fail: bool = False) -> tuple[int, str]:
    _log("$ " + " ".join(cmd))
    proc = subprocess.Popen(
        cmd,
        cwd=REPO_ROOT,
        env=env or os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    out_lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            print(f"    | {line}", flush=True)
        out_lines.append(line)
    proc.wait()
    rc = proc.returncode
    if rc != 0 and not allow_fail:
        raise RuntimeError(f"command failed (rc={rc}): {' '.join(cmd)}")
    return rc, "\n".join(out_lines)


def _v1_base(url: str) -> str:
    url = str(url).strip().rstrip("/")
    return url if url.endswith("/v1") else url + "/v1"


def _resolve_upstream(spec: Any) -> str:
    env_base = os.environ.get("VLLM_BASE_URL", "").strip()
    if env_base:
        return _v1_base(env_base)
    workspace = os.environ.get("MODAL_WORKSPACE", "").strip()
    if workspace:
        return _v1_base(f"https://{workspace}--{modal_vllm.APP_NAME}-serve.modal.run")
    return ""


def _resolve_api_token() -> str:
    return (os.environ.get("VLLM_API_KEY") or os.environ.get("MODAL_VLLM_API_TOKEN") or "").strip()


def _gpu_hourly() -> float:
    try:
        return float(os.environ.get("MODAL_GPU_HOURLY_USD") or DEFAULT_GPU_HOURLY_USD)
    except ValueError:
        return DEFAULT_GPU_HOURLY_USD


REVISION_PLACEHOLDER = "REVISION_PIN_ME"


def _modal_revision(spec: Any) -> str:
    """The pinned Hub weight revision from the run spec.

    Primary source is ``engine.modal.revision`` (the pin the driver propagates
    as ``MODAL_VLLM_REVISION``); ``engine.vllm.revision`` is kept as a
    backward-compatible fallback.
    """
    modal = getattr(spec.engine, "modal", None)
    if modal is not None:
        rev = str(getattr(modal, "revision", "") or "").strip()
        if rev:
            return rev
    return str(getattr(getattr(spec.engine, "vllm", None), "revision", "") or "").strip()


def _load_log_records() -> list[dict[str, Any]]:
    from mailroom_sandbox.eval import experiment_log

    return experiment_log.load()


def _latest_eval_scores(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    target = f"sandbox_isolated_{RUN_ID}"
    candidates = [r for r in records if r.get("experiment_name") == target and r.get("scores")]
    return candidates[-1].get("scores") if candidates else None


class _CaptureStore:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(self, item: dict[str, Any]) -> None:
        with self._lock:
            self.items.append(item)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self.items)


class _ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args: Any) -> None:
        pass

    def _serve(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        upstream_base = self.server.upstream_base  # type: ignore[attr-defined]
        path = self.path
        relative = path[len("/v1"):] if path.startswith("/v1") else path
        target = upstream_base.rstrip("/") + relative
        forward_headers = {
            k: v
            for k, v in self.headers.items()
            if k.lower() not in ("host", "content-length", "accept-encoding", "connection")
        }
        capture = path.rstrip("/").endswith("/chat/completions")
        started = time.monotonic()
        try:
            with httpx.Client(timeout=PROXY_REQUEST_TIMEOUT) as client:
                with client.stream(self.command, target, headers=forward_headers, content=body) as resp:
                    first_byte_at = time.monotonic()
                    chunks = list(resp.iter_bytes())
        except httpx.HTTPError as exc:
            payload = json.dumps(
                {"error": {"message": f"proxy upstream error: {type(exc).__name__}: {str(exc)[:200]}"}}
            ).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        ended = time.monotonic()
        body_bytes = b"".join(chunks)
        self.send_response(resp.status_code)
        for key, value in resp.headers.items():
            if key.lower() in ("transfer-encoding", "content-encoding", "connection", "content-length"):
                continue
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)
        if capture:
            usage: dict[str, Any] = {}
            if resp.status_code < 400:
                try:
                    usage = (json.loads(body_bytes.decode("utf-8")) or {}).get("usage") or {}
                except (ValueError, AttributeError):
                    usage = {}
            self.server.captures.add(  # type: ignore[attr-defined]
                {
                    "ok": resp.status_code < 400,
                    "latency_ms": round((ended - started) * 1000.0, 3),
                    "ttft_ms": round((first_byte_at - started) * 1000.0, 3),
                    "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                    "completion_tokens": int(usage.get("completion_tokens") or 0),
                    "end_monotonic": ended,
                }
            )

    do_GET = _serve
    do_POST = _serve


class TokenCountingProxy:
    """Local reverse proxy forwarding /v1 to an upstream endpoint while
    recording per-request usage / TTFT / latency for chat completions."""

    def __init__(self, upstream_base: str) -> None:
        self.upstream_base = upstream_base.rstrip("/")
        self.captures = _CaptureStore()
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> str:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _ProxyHandler)
        server.daemon_threads = True  # type: ignore[attr-defined]
        server.upstream_base = self.upstream_base  # type: ignore[attr-defined]
        server.captures = self.captures  # type: ignore[attr-defined]
        self._httpd = server
        self._thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._thread.start()
        host, port = server.server_address[:2]
        return f"http://{host}:{port}"

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None


FAKE_MODEL = "Qwen/Qwen3-8B"


class _FakeEndpointHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args: Any) -> None:
        pass

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/v1/models":
            self._send(
                200,
                {
                    "object": "list",
                    "data": [{"id": FAKE_MODEL, "object": "model", "created": 0, "owned_by": "mock"}],
                },
            )
        else:
            self._send(404, {"error": {"message": f"unknown path {self.path}"}})

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._send(404, {"error": {"message": f"unknown path {self.path}"}})
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b"{}"
        try:
            request = json.loads(body or b"{}")
        except ValueError:
            request = {}
        messages = request.get("messages") or []
        prompt_len = sum(len(str(m.get("content") or m)) for m in messages)
        time.sleep(0.05)
        content = json.dumps(
            {
                "doc_type": "correspondence",
                "contract_subtype": None,
                "doc_subclass": None,
                "confidence": 0.5,
                "reasoning": "mock endpoint response",
            }
        )
        prompt_tokens = max(1, prompt_len // 4)
        self._send(
            200,
            {
                "id": "chatcmpl-mock",
                "object": "chat.completion",
                "created": 0,
                "model": FAKE_MODEL,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": 40,
                    "total_tokens": prompt_tokens + 40,
                },
            },
        )


class FakeEndpointServer:
    """Minimal OpenAI-compatible /v1 endpoint for the offline --mock rehearsal."""

    def __init__(self) -> None:
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.v1_base = ""

    def start(self) -> str:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeEndpointHandler)
        server.daemon_threads = True  # type: ignore[attr-defined]
        self._httpd = server
        self._thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._thread.start()
        host, port = server.server_address[:2]
        self.v1_base = f"http://{host}:{port}/v1"
        return self.v1_base

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None


def _poll_ready(base: str, token: str) -> list[str]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    for attempt in range(1, READY_RETRIES + 1):
        try:
            resp = httpx.get(f"{base}/models", headers=headers, timeout=5.0)
        except httpx.HTTPError as exc:
            if attempt == READY_RETRIES:
                raise RuntimeError(f"endpoint {base} never became reachable: {type(exc).__name__}")
            _log(f"not ready (attempt {attempt}/{READY_RETRIES}): {type(exc).__name__}; retrying in {READY_BACKOFF_SECONDS}s")
            time.sleep(READY_BACKOFF_SECONDS)
            continue
        if resp.status_code in (502, 503, 504):
            if attempt == READY_RETRIES:
                raise RuntimeError(f"endpoint {base} stayed at HTTP {resp.status_code} (scaled to zero)")
            _log(
                f"not ready (attempt {attempt}/{READY_RETRIES}): HTTP {resp.status_code} "
                f"(Modal returns 503 while scaled to zero); retrying in {READY_BACKOFF_SECONDS}s"
            )
            time.sleep(READY_BACKOFF_SECONDS)
            continue
        if resp.status_code == 401:
            raise RuntimeError(
                "401 from /v1/models — set VLLM_API_KEY (or MODAL_VLLM_API_TOKEN) to the deployed bearer token"
            )
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code} from {base}/models")
        try:
            ids = [m.get("id") for m in (resp.json().get("data") or []) if isinstance(m, dict)]
        except ValueError:
            ids = []
        _log(f"ready: {base}/models -> {ids}")
        return ids
    raise RuntimeError("readiness poll exhausted")


def _warm_up(base: str, token: str, model: str, *, n: int) -> float:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    start = time.monotonic()
    for i in range(1, n + 1):
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": f"Warm-up call {i}. Reply with the single word: ok"}],
            "max_tokens": 8,
            "temperature": 0,
            # Qwen3-8B ChatML ships enable_thinking ON by default; turn it OFF
            # so the warm-ups exercise the same non-thinking posture as the
            # billed calls (no extra thinking tokens, no grammar-decoder
            # conflict). The MEASURED sorter bodies are built by the isolated
            # eval (sandbox CLI), not this driver — see the run spec note.
            "chat_template_kwargs": {"enable_thinking": False},
        }
        try:
            resp = httpx.post(f"{base}/chat/completions", headers=headers, json=payload, timeout=180.0)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"warm-up call {i}/{n} failed: {type(exc).__name__}: {exc}")
        if resp.status_code != 200:
            raise RuntimeError(f"warm-up call {i}/{n} returned HTTP {resp.status_code}")
        _log(f"warm-up call {i}/{n}: ok")
    return start


def _run_eval(proxy_url: str, api_token: str) -> None:
    # The isolated sorter eval builds its OWN chat-completions bodies inside
    # the sandbox CLI (SorterAgent.classify) — this driver cannot inject
    # chat_template_kwargs here. Qwen3-8B ChatML ships enable_thinking ON by
    # default, so if the eval does not disable it the MEASURED completion
    # tokens include thinking output (skewing cost-per-token vs OpenRouter).
    # Verify the eval path disables thinking before a billed --run (see the
    # thinking-mode note in config/runs/qwen3_8b_cost_compare_modal.yaml).
    env = dict(os.environ)
    env["VLLM_BASE_URL"] = proxy_url
    env["VLLM_API_KEY"] = api_token or "not-needed"
    env.setdefault("DEFAULT_PROVIDER", "vllm")
    cmd = _sandbox_cmd()
    _step("Eval — sandbox run preflight + start against the token-counting proxy")
    _run([*cmd, "run", "preflight", "--force", "--config", str(SPEC_PATH)], env=env)
    _run([*cmd, "run", "start", "--config", str(SPEC_PATH)], env=env)


def _warm_span_seconds(items: list[dict[str, Any]], warm_start: float) -> float:
    ends = [i.get("end_monotonic") or 0.0 for i in items]
    last_end = max(ends) if ends else warm_start
    return max(0.0, last_end - warm_start)


def _build_record(
    spec: Any,
    items: list[dict[str, Any]],
    scores: dict[str, Any] | None,
    gpu_hourly_usd: float,
    warm_span_seconds: float | None,
) -> dict[str, Any]:
    from mailroom_sandbox.datasets import dataset_fingerprint
    from mailroom_sandbox.eval import experiment_log
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.metrics import record_from_run
    from mailroom_sandbox.job.spec import run_dir

    store = RunStore(run_dir(RUN_ID))
    rows = store.dataset_rows()
    fingerprint = dataset_fingerprint(rows) if rows else ""
    serving = record_from_run(
        run_id=RUN_ID,
        spec_hash=spec.spec_hash(),
        task="sorter",
        profile=spec.profile,
        model=spec.engine.model,
        prompt_version="code-default",
        dataset_fingerprint=fingerprint,
        items=items,
        scores=scores or None,
        gpu_hourly_usd=gpu_hourly_usd,
        warm_span_seconds=warm_span_seconds,
    )
    modal = spec.engine.modal
    identity = {
        "gpu_hourly_usd": gpu_hourly_usd,
        "warm_span_seconds": warm_span_seconds,
        "scaledown_seconds": modal.scaledown_seconds if modal else None,
        "revision": _modal_revision(spec) or None,
        "image_tag": modal.image_tag if modal else None,
        "gpu_memory_utilization": spec.engine.vllm.gpu_memory_utilization,
        "max_num_seqs": spec.engine.vllm.max_num_seqs,
    }
    record = experiment_log.new_record(
        identity=identity,
        experiment_name=EXPERIMENT_NAME,
        **serving,
    )
    experiment_log.append(record)
    _log(f"experiment-log row appended: {experiment_log.jsonl_path()}")
    return record


def _print_cost_card(record: dict[str, Any], warm_span_seconds: float | None) -> None:
    prompt = record.get("prompt_tokens") or 0
    completion = record.get("completion_tokens") or 0
    total = prompt + completion
    hourly = record.get("gpu_hourly_usd")
    gpu_cost = record.get("gpu_cost_usd")
    effective_tps = (total / warm_span_seconds) if warm_span_seconds else None
    _step("Cost card")
    _log(f"  run_id               : {record.get('run_id')}")
    _log(f"  profile/model        : {record.get('profile')} / {record.get('model')}")
    _log(f"  gpu_hourly_usd       : {_usd(hourly)}/hour (env MODAL_GPU_HOURLY_USD)")
    warm_span_str = f"{warm_span_seconds:.2f}" if warm_span_seconds is not None else "unknown"
    _log(f"  warm_span_seconds    : {warm_span_str} (first warm-up request -> last eval request end)")
    _log(f"  gpu_cost_usd         : {_usd(gpu_cost)}  = gpu_hourly_usd x warm_span_seconds / 3600")
    _log(f"  prompt_tokens        : {_int(prompt)}")
    _log(f"  completion_tokens    : {_int(completion)}")
    _log(f"  total_tokens         : {_int(total)}")
    effective_tps_str = f"{effective_tps:.2f}" if effective_tps is not None else "-"
    _log(f"  effective tokens/sec : {effective_tps_str}  (= total_tokens / warm_span_seconds)")
    if record.get("e2e_latency_seconds") is not None:
        _log(f"  mean e2e latency (s) : {record['e2e_latency_seconds']:.2f}")
    if record.get("ttft_seconds") is not None:
        _log(f"  mean ttft (s)        : {record['ttft_seconds']:.2f}")
    scores = record.get("scores") or {}
    if scores.get("exact_match") is not None:
        _log(f"  score (exact_match)  : {float(scores['exact_match']):.3f} (n={scores.get('n')})")


def _print_openrouter_comparison(records: list[dict[str, Any]], modal_record: dict[str, Any]) -> None:
    from mailroom_sandbox.job.metrics import aggregate_bucket

    openrouter_rec = next((r for r in records if r.get("run_id") == OPENROUTER_LEG_RUN_ID), None)
    if openrouter_rec is None:
        openrouter_rec = next(
            (r for r in records if r.get("profile") == "openrouter" and r.get("prompt_tokens")),
            None,
        )
    _step(f"OpenRouter-leg comparison (run_id {OPENROUTER_LEG_RUN_ID})")
    if openrouter_rec is None:
        _log(
            f"  no OpenRouter-leg serving record present in reports/experiment_log.jsonl yet — "
            f"run the OpenRouter leg (run_id {OPENROUTER_LEG_RUN_ID}) first to get a comparison table"
        )
        return
    modal_agg = aggregate_bucket([modal_record])
    openrouter_agg = aggregate_bucket([openrouter_rec])
    or_label = openrouter_rec.get("run_id") or openrouter_rec.get("experiment_name") or OPENROUTER_LEG_RUN_ID
    _log(f"  modal      : {RUN_ID}     (profile {modal_record.get('profile')})")
    _log(f"  openrouter : {or_label} (profile {openrouter_rec.get('profile')})")
    _log("")
    rows = [
        ("n (requests)", modal_agg.get("n"), openrouter_agg.get("n")),
        ("prompt tokens", modal_record.get("prompt_tokens"), openrouter_rec.get("prompt_tokens")),
        ("completion tokens", modal_record.get("completion_tokens"), openrouter_rec.get("completion_tokens")),
        ("total tokens", modal_agg.get("total_tokens"), openrouter_agg.get("total_tokens")),
        ("mean e2e latency (s)", modal_agg.get("mean_e2e_s"), openrouter_agg.get("mean_e2e_s")),
        ("mean ttft (s)", modal_agg.get("mean_ttft_s"), openrouter_agg.get("mean_ttft_s")),
        ("tokens/s (dojo)", modal_agg.get("tokens_per_s"), openrouter_agg.get("tokens_per_s")),
        ("gpu cost ($)", modal_agg.get("gpu_cost_usd"), "-"),
        ("est. API cost ($)", "-", openrouter_agg.get("estimated_cost_usd")),
    ]
    for label, left, right in rows:
        def fmt(value: Any) -> str:
            if value is None:
                return "-"
            if isinstance(value, float):
                return f"{value:.3f}"
            return str(value)

        _log(f"  {label:<24} modal={fmt(left):>12}  openrouter={fmt(right):>12}")


def _finalize(spec: Any, items: list[dict[str, Any]], warm_start: float, gpu_hourly_usd: float) -> dict[str, Any]:
    records = _load_log_records()
    scores = _latest_eval_scores(records)
    if not items:
        # Zero captures means the eval produced nothing to time, but the GPU
        # was still billed during deploy/warm-up — a 0.00 USD here would
        # fabricate a spend that did not happen. Leave the cost UNKNOWN.
        warm_span: float | None = None
        print(
            "\n" + "!" * 72
            + "\nWARNING: eval produced ZERO proxy captures — GPU cost is UNKNOWN, not zero."
            + "\nGPU minutes were still billed during deploy/warm-up; gpu_cost_usd is recorded"
            + "\nas unknown (None) rather than a fabricated $0.00."
            + "\n" + "!" * 72,
            flush=True,
        )
    else:
        warm_span = _warm_span_seconds(items, warm_start)
    record = _build_record(spec, items, scores, gpu_hourly_usd, warm_span)
    _print_cost_card(record, warm_span)
    _print_openrouter_comparison(records, record)
    return record


def _teardown() -> None:
    _step(f"Teardown — modal app stop {modal_vllm.APP_NAME}")
    _run([*_modal_cmd(), "app", "stop", "-y", modal_vllm.APP_NAME], allow_fail=True)


def _run_real(spec: Any) -> int:
    upstream = _resolve_upstream(spec)
    if not upstream:
        raise SystemExit(
            "cannot resolve the deployed Modal endpoint — export VLLM_BASE_URL (the modal.run "
            "/v1 URL printed by `modal deploy`) or MODAL_WORKSPACE"
        )
    api_token = _resolve_api_token()
    if not api_token:
        raise SystemExit(
            "no bearer token for the deployed endpoint — export VLLM_API_KEY (or MODAL_VLLM_API_TOKEN) "
            "to the value deployed by modal_vllm.py"
        )
    revision = _modal_revision(spec)
    if revision == REVISION_PLACEHOLDER:
        raise SystemExit(
            "engine.modal.revision is still the placeholder 'REVISION_PIN_ME' — pin the exact "
            "Qwen/Qwen3-8B commit before --run (see the comment in "
            "config/runs/qwen3_8b_cost_compare_modal.yaml; use the full 40-hex sha from the HF "
            "snapshot or the Qwen/Qwen3-8B release). Without a pin the Hub tip can drift between "
            "pre-warm and eval."
        )
    if revision:
        # Pin the SAME commit for pre-warm (snapshot_download) and serve boot
        # (vllm --revision): deploy/modal_vllm.py reads MODAL_VLLM_REVISION.
        os.environ["MODAL_VLLM_REVISION"] = revision
    # Propagate the spec's image_tag so the recorded identity always equals the
    # booted engine. deploy/modal_vllm.py defaults to v0.29.0, which is the
    # fallback when the spec leaves image_tag empty — so identity and reality
    # can never drift.
    image_tag = str(getattr(getattr(spec.engine, "modal", None), "image_tag", "") or "").strip()
    if image_tag:
        os.environ["MODAL_VLLM_IMAGE_TAG"] = image_tag
    os.environ["VLLM_API_KEY"] = api_token
    # The deployed bearer endpoint is authenticated by MODAL_VLLM_API_TOKEN
    # (consumed by deploy/modal_vllm.py); mirror the consumer-side VLLM_API_KEY
    # here. Never print the token value.
    os.environ["MODAL_VLLM_API_TOKEN"] = api_token
    deployed = False
    try:
        _step("Pre-warm HF cache (Modal)")
        _run([*_modal_cmd(), "run", "deploy/modal_vllm.py::download_model"])
        _step("Deploy sandbox-vllm (Modal)")
        _run([*_modal_cmd(), "deploy", "deploy/modal_vllm.py"])
        deployed = True
        _log(f"endpoint: {upstream}")
        _step("Readiness — poll /v1/models until ready")
        _poll_ready(upstream, api_token)
        modal_vllm._smoke_check(upstream)
        _step(f"Warm-up — {WARMUP_CALLS} uncounted chat calls (CUDA-graph/TTFT isolation)")
        warm_start = _warm_up(upstream, api_token, spec.engine.model, n=WARMUP_CALLS)
        proxy = TokenCountingProxy(upstream)
        proxy_url = proxy.start()
        try:
            _run_eval(proxy_url, api_token)
        finally:
            proxy.stop()
        items = proxy.captures.snapshot()
        _log(f"captured {len(items)} eval chat request(s) through the token-counting proxy")
        _finalize(spec, items, warm_start, _gpu_hourly())
        return 0
    finally:
        if deployed:
            _teardown()


def _run_mock(spec: Any) -> int:
    _step("Mock — fake local /v1 endpoint (no Modal, no deploy, no network)")
    fake = FakeEndpointServer()
    fake_base = fake.start()
    api_token = "not-needed"
    try:
        _log(f"fake endpoint: {fake_base}")
        _poll_ready(fake_base, api_token)
        _step(f"Warm-up — {WARMUP_CALLS} uncounted chat calls against the fake endpoint")
        warm_start = _warm_up(fake_base, api_token, spec.engine.model, n=WARMUP_CALLS)
        proxy = TokenCountingProxy(fake_base)
        proxy_url = proxy.start()
        try:
            _run_eval(proxy_url, api_token)
        finally:
            proxy.stop()
        items = proxy.captures.snapshot()
        _log(f"captured {len(items)} eval chat request(s) through the token-counting proxy")
        _finalize(spec, items, warm_start, _gpu_hourly())
        _log("mock rehearsal complete — no Modal resources were created")
        return 0
    finally:
        fake.stop()


def _preview(spec: Any) -> int:
    upstream = _resolve_upstream(spec) or f"https://<MODAL_WORKSPACE>--{modal_vllm.APP_NAME}-serve.modal.run/v1"
    gpu_hourly = _gpu_hourly()
    modal = spec.engine.modal
    vllm = spec.engine.vllm
    sandbox = _sandbox_cmd()
    modal_cli = _modal_cmd()
    serve_argv = " ".join(modal_vllm.build_vllm_command(spec.engine.model))
    print("=" * 72)
    print("Modal cost-per-token leg — PLAN ONLY (--preview / --dry-run)")
    print("=" * 72)
    print(f"  run spec            : {SPEC_PATH}")
    print(f"  run_id              : {RUN_ID}")
    print(f"  experiment          : {EXPERIMENT_NAME}")
    print(f"  task                : {spec.task} (isolated -> sorter classifier, one LLM call/doc)")
    print(f"  profile/engine      : {spec.profile} / {spec.engine.kind}")
    print(f"  model               : {spec.engine.model}")
    print(f"  revision            : {_modal_revision(spec) or '(unset — Hub tip, DRIFTING; pin engine.modal.revision)'}")
    print(f"  gpu                 : {modal.gpu} (image vllm/vllm-openai:{modal.image_tag})")
    print(f"  max_model_len       : {vllm.max_model_len}  gpu_memory_utilization={vllm.gpu_memory_utilization}  "
          f"max_num_seqs={vllm.max_num_seqs}  scaledown_seconds={modal.scaledown_seconds}")
    print(f"  dataset             : {spec.dataset.local_path}  limit={spec.dataset.limit}  "
          f"sample_seed={spec.dataset.sample_seed}  concurrency={spec.job.concurrency}")
    print(f"  endpoint (upstream) : {upstream}")
    print()
    print("Planned commands (--run):")
    print(f"  1. pre-warm : {modal_cli[0]} {' '.join(modal_cli[1:])} run deploy/modal_vllm.py::download_model")
    print(f"  2. deploy   : {modal_cli[0]} {' '.join(modal_cli[1:])} deploy deploy/modal_vllm.py")
    print(f"  3. readiness: poll {upstream}/models with a bearer token (retry on 503/connection until ready), "
          "then modal_vllm._smoke_check")
    print(f"  4. warm-up  : {WARMUP_CALLS} uncounted /v1/chat/completions calls (CUDA-graph/TTFT isolation)")
    print(f"                bodies pass chat_template_kwargs={{'enable_thinking': False}} (Qwen3-8B)")
    print(f"  5. eval     : start a local token-counting proxy -> VLLM_BASE_URL=<proxy>/v1 ->")
    print(f"                {' '.join(sandbox)} run preflight --force --config config/runs/qwen3_8b_cost_compare_modal.yaml")
    print(f"                {' '.join(sandbox)} run start --config config/runs/qwen3_8b_cost_compare_modal.yaml")
    print(f"                (the isolated sorter eval runs against the proxy; no eval reimplementation)")
    print(f"  6. record   : metrics.record_from_run(..., gpu_hourly_usd=..., warm_span_seconds=...) +")
    print(f"                experiment_log.new_record(identity=...) + append -> reports/experiment_log.jsonl")
    print(f"  7. compare  : cost card + OpenRouter-leg (run_id {OPENROUTER_LEG_RUN_ID}) table from the log")
    print(f"  8. teardown : {modal_cli[0]} {' '.join(modal_cli[1:])} app stop {modal_vllm.APP_NAME}")
    print()
    print("Cost plan:")
    print(f"  gpu_hourly_usd       : {_usd(gpu_hourly)}/hour (L4 bf16; override with MODAL_GPU_HOURLY_USD)")
    print("  gpu_cost_usd         = gpu_hourly_usd x warm_span_seconds / 3600")
    print("  warm_span_seconds    : measured at runtime (first warm-up request -> last eval request end)")
    for span in (300, 600, 1200):
        print(f"    example @ {span:>4}s warm : {_usd(gpu_hourly * span / 3600.0)}")
    print("  identity recorded    : gpu_hourly_usd, warm_span_seconds, scaledown_seconds, revision, "
          "image_tag, gpu_memory_utilization, max_num_seqs")
    print()
    print(f"Container serve argv (deploy/modal_vllm.build_vllm_command):")
    print(f"  {serve_argv}")
    print()
    print("--mock runs the SAME flow against a fake local /v1 endpoint (no Modal, no deploy, no teardown).")
    print("Secrets (VLLM_API_KEY / MODAL_VLLM_API_TOKEN) are never printed; presence only.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Orchestrate the Modal leg of the cost-per-token classifier experiment (qwen3-8b, isolated sorter)."
    )
    parser.add_argument("--preview", dest="mode", action="store_const", const="preview", help="print the plan + cost plan; run nothing")
    parser.add_argument("--dry-run", dest="mode", action="store_const", const="preview", help="alias for --preview")
    parser.add_argument("--mock", dest="mode", action="store_const", const="mock", help="full offline rehearsal against a fake local /v1 endpoint")
    parser.add_argument("--run", dest="mode", action="store_const", const="run", help="the real Modal leg (pre-warm -> deploy -> eval -> record -> teardown)")
    parser.set_defaults(mode=None)
    args = parser.parse_args(argv)

    if args.mode is None:
        parser.print_help()
        return 2

    spec = _load_spec()
    if args.mode == "preview":
        return _preview(spec)
    if args.mode == "mock":
        return _run_mock(spec)
    return _run_real(spec)


if __name__ == "__main__":
    raise SystemExit(main())