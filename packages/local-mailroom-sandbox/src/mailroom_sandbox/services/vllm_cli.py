"""``sandbox vllm …``: probe an endpoint, print or run the ``vllm serve`` command, scrape metrics.

The ``vllm serve`` argv always comes from ``deploy/modal_vllm.py::build_vllm_command`` (loaded
without needing the Modal SDK), so what ``command`` prints is exactly what the Modal app
launches. ``probe`` is the one place that checks the endpoint's ``/health`` and ``/metrics``
as well as the models/chat probes ``sandbox health`` already runs.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx

from mailroom_sandbox.paths import repo_root
from mailroom_sandbox.services._cli import format_command, print_json, print_plan, strip_separator, warn
from mailroom_sandbox.services._exec import ServiceError, ToolFailed, stream_tool
from mailroom_sandbox.services._redact import redact_urls
from mailroom_sandbox.services.modal_cli import _matrix_env

SERVE_HINT = (
    "vLLM is not installed here — install it on an NVIDIA host (pip install vllm), run the compose "
    "service (`docker compose --profile vllm up`), or use `sandbox modal deploy`"
)
DEPLOY_HINT = (
    "modal-vllm has no endpoint — set VLLM_BASE_URL (the URL `modal deploy` prints, plus /v1) "
    "or MODAL_WORKSPACE; see `sandbox modal deploy`"
)


def _load_modal_vllm(overrides: dict[str, str]) -> ModuleType:
    """Import ``deploy/modal_vllm.py`` under ``overrides`` without leaking them into the process.

    The module reads its knobs from the environment at import and calls the Modal SDK only to
    declare the app, so a stand-in ``modal`` is enough to reach ``build_vllm_command``.
    """
    path: Path = repo_root() / "deploy" / "modal_vllm.py"
    saved = {key: os.environ.get(key) for key in overrides}
    stubbed = "modal" not in sys.modules and importlib.util.find_spec("modal") is None
    os.environ.update(overrides)
    if stubbed:
        from unittest.mock import MagicMock

        sys.modules["modal"] = MagicMock()
    try:
        spec = importlib.util.spec_from_file_location("_sandbox_modal_vllm", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except (ValueError, RuntimeError, SystemExit) as exc:
        raise ServiceError(f"deploy/modal_vllm.py rejected the settings: {exc}") from exc
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        if stubbed:
            sys.modules.pop("modal", None)


def _serve_argv(args: argparse.Namespace) -> tuple[list[str], dict[str, str], ModuleType]:
    from mailroom_sandbox.runtime import load_env_file

    load_env_file()
    overrides = _matrix_env(args)
    module = _load_modal_vllm(overrides)
    model = overrides.get("MODAL_VLLM_MODEL") or module.MODEL
    return list(module.build_vllm_command(model)), overrides, module


def _cmd_command(args: argparse.Namespace) -> int:
    argv, overrides, module = _serve_argv(args)
    if args.json:
        print_json(
            {
                "argv": argv,
                "model": overrides.get("MODAL_VLLM_MODEL") or module.MODEL,
                "gpu": overrides.get("MODAL_VLLM_GPU") or module.GPU,
                "env": overrides,
            }
        )
    else:
        print(format_command(argv))
    return 0


def _local_host(argv: list[str]) -> list[str]:
    """Bind loopback for a local serve: the Modal argv binds 0.0.0.0 behind Modal's gateway."""
    out = list(argv)
    if "--host" in out:
        out[out.index("--host") + 1] = "127.0.0.1"
    return out


def _cmd_serve(args: argparse.Namespace) -> int:
    # REMAINDER swallows a --dry-run placed after the extras; it must never start the server.
    extras = strip_separator(args.rest)
    dry_run = args.dry_run or "--dry-run" in extras
    extras = [part for part in extras if part != "--dry-run"]
    if any(part == "--host" or part.startswith("--host=") for part in extras):
        raise ServiceError("a local serve binds 127.0.0.1; --host cannot be overridden")
    argv, overrides, _module = _serve_argv(args)
    argv = _local_host(argv) + extras
    env = {**os.environ, **overrides}
    token = os.environ.get("MODAL_VLLM_API_TOKEN", "").strip()
    if token and not os.environ.get("VLLM_API_KEY"):
        env["VLLM_API_KEY"] = token
    if dry_run:
        print_plan(argv, overrides)
        print("dry-run: nothing started (a local serve needs an NVIDIA GPU and downloads the weights).")
        return 0
    if not shutil.which("nvidia-smi"):
        warn("nvidia-smi not found — vLLM needs an NVIDIA GPU; without one use `sandbox modal deploy`")
    print(f"-> {format_command(argv, overrides)}")
    try:
        rc = stream_tool(argv, env=env, hint=SERVE_HINT)
    except KeyboardInterrupt:
        return 130
    if rc != 0:
        raise ToolFailed(argv, rc)
    return 0


# --------------------------------------------------------------------------- probe / metrics


def _endpoint(profile_name: str) -> tuple[dict, str]:
    """(profile, base_url) for the resolved endpoint; never localhost for an unresolved modal-vllm."""
    from mailroom_sandbox.health import _effective_base_url, missing_modal_endpoint
    from mailroom_sandbox.overlay import load_profile
    from mailroom_sandbox.providers import endpoints_for
    from mailroom_sandbox.runtime import load_env_file

    load_env_file()
    profile = load_profile(profile_name)
    if missing_modal_endpoint(profile):
        raise ServiceError(DEPLOY_HINT)
    return profile, endpoints_for(profile, base_url_override=_effective_base_url(profile)).base_url


def _root(base_url: str) -> str:
    root = base_url.rstrip("/")
    return root[: -len("/v1")] if root.endswith("/v1") else root


def _get(url: str, headers: dict[str, str]) -> dict[str, Any]:
    try:
        resp = httpx.get(url, headers=headers, timeout=5.0)
    except httpx.HTTPError as exc:
        return {"ok": False, "url": url, "detail": f"{type(exc).__name__}: {exc}"}
    ok = resp.status_code < 400
    return {"ok": ok, "url": url, "detail": "ok" if ok else f"HTTP {resp.status_code}"}


def _cmd_probe(args: argparse.Namespace) -> int:
    from mailroom_sandbox.health import ProbeResult, _headers, explain_modal_timeout, probe_chat, probe_models
    from mailroom_sandbox.overlay import resolve_served_vllm_model
    from mailroom_sandbox.providers import endpoints_for

    profile, base_url = _endpoint(args.profile)
    if str(profile.get("name")) == "modal-vllm":
        warn("a request to a scale-to-zero Modal endpoint can cold-start a billed GPU container")
    headers = _headers(profile)
    models = probe_models(profile)
    starting = explain_modal_timeout(profile, models)
    chat = (
        probe_chat(profile)
        if models.ok
        else ProbeResult(
            False,
            str(profile.get("name")),
            endpoints_for(profile, base_url_override=base_url).chat_url,
            "skipped (models probe failed)",
        )
    )
    root = _root(base_url)
    skipped = {"ok": False, "detail": "skipped (endpoint still starting)"}
    health = {**skipped, "url": f"{root}/health"} if starting else _get(f"{root}/health", headers)
    metrics = {**skipped, "url": f"{root}/metrics"} if starting else _get(f"{root}/metrics", headers)

    expected = resolve_served_vllm_model() or str(profile.get("default_model") or "") or None
    served = models.models or []
    served_ok = True if (not expected or not served) else expected in served
    ok = models.ok and chat.ok and served_ok
    report = {
        "profile": args.profile,
        "base_url": base_url,
        "ok": ok,
        "models": models.as_dict(),
        "chat": chat.as_dict(),
        "health": health,
        "metrics": metrics,
        "expected_model": expected,
        "served_models": served,
        "served_model_ok": served_ok,
    }
    if args.json:
        print_json(report)
    else:
        print(f"endpoint: {redact_urls(base_url)}")
        for name, row in (("models", models.as_dict()), ("chat", chat.as_dict()), ("health", health), ("metrics", metrics)):
            print(f"  {name:<8} {'ok  ' if row['ok'] else 'FAIL'} {redact_urls(str(row['detail']))}")
        if served:
            print(f"  serving: {', '.join(served)}")
    if not served_ok:
        print(
            f"error: the endpoint serves {served} but the run will ask for {expected!r} — "
            "set VLLM_MODEL/MODAL_VLLM_MODEL to the served id (or redeploy that model)",
            file=sys.stderr,
        )
    elif starting:
        print(f"not ready: {models.detail}", file=sys.stderr)
    elif not ok:
        failing = models if not models.ok else chat
        print(f"error: endpoint is not healthy — {failing.name}: {redact_urls(str(failing.detail))}", file=sys.stderr)
    return 0 if ok else 1


def _cmd_metrics(args: argparse.Namespace) -> int:
    from mailroom_sandbox.job import vllm_metrics

    profile, base_url = _endpoint(args.profile)
    api_key = os.environ.get(str(profile.get("api_key_env") or "VLLM_API_KEY"), "").strip()
    result = vllm_metrics.scrape(base_url, api_key, attempts=args.attempts)
    if args.json:
        print_json(result)
    elif args.raw:
        for key, text in sorted((result.get("raw") or {}).items()):
            print(f"# replica {key}\n{text}")
    else:
        print(result.get("coverage", ""))
        for key, summary in sorted((result.get("replicas") or {}).items()):
            print(f"replica {key}:")
            for name, value in summary.items():
                if value is not None:
                    print(f"  {name:<24} {value}")
    if not result.get("replicas"):
        errors = result.get("errors") or ["no replica answered"]
        raise ServiceError(f"/metrics scrape failed: {errors[0]}")
    return 0


def _cmd_help(args: argparse.Namespace) -> int:
    print(
        "Use: sandbox vllm probe|command|serve|metrics\n"
        "  probe [--json]                    models + chat + /health + /metrics on the resolved endpoint\n"
        "  command [--model M] [--gpu G]     the exact `vllm serve` line the Modal app launches\n"
        "  serve [-- extra args] [--dry-run] run it locally (NVIDIA host only; binds 127.0.0.1)\n"
        "  metrics [--attempts N] [--json]   scrape /metrics (per-replica summary)\n"
        "Remote GPU without a local install: `sandbox modal deploy`; an SSH-forwarded server: `sandbox tunnel up`."
    )
    return 0


def register(sub: argparse._SubParsersAction, leaf: argparse.ArgumentParser) -> None:
    """Add the ``vllm`` group to the root parser."""
    group = sub.add_parser("vllm", parents=[leaf], help="probe/serve/metrics for a vLLM endpoint (probe/command/serve/metrics)")
    cmds = group.add_subparsers(dest="vllm_cmd")

    probe = cmds.add_parser("probe", parents=[leaf], help="models + chat + /health + /metrics on the resolved endpoint")
    probe.add_argument("--json", action="store_true")
    probe.set_defaults(handler=_cmd_probe)

    command = cmds.add_parser("command", parents=[leaf], help="print the `vllm serve` argv the Modal app launches")
    command.add_argument("--gpu", default=None, help="override the matrix GPU (e.g. A100-40GB:2)")
    command.add_argument("--json", action="store_true")
    command.set_defaults(handler=_cmd_command)

    serve = cmds.add_parser("serve", parents=[leaf], help="run vllm serve locally (NVIDIA host only)")
    serve.add_argument("--gpu", default=None)
    serve.add_argument("--dry-run", action="store_true")
    serve.add_argument("rest", nargs=argparse.REMAINDER, help="-- <extra vllm arguments>")
    serve.set_defaults(handler=_cmd_serve)

    metrics = cmds.add_parser("metrics", parents=[leaf], help="scrape /metrics and summarize per replica")
    metrics.add_argument("--attempts", type=int, default=1)
    metrics.add_argument("--json", action="store_true")
    metrics.add_argument("--raw", action="store_true", help="print the raw exporter text")
    metrics.set_defaults(handler=_cmd_metrics)

    group.set_defaults(handler=_cmd_help)
