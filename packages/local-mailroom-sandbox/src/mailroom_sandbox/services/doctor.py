"""``sandbox doctor``: one status table for every service the sandbox talks to.

Offline by default — binaries on ``PATH``, configuration and credentials *present* (never their
values), nothing over the network. ``--live`` adds probes; against a scale-to-zero Modal URL a
probe can cold-start a billed GPU container, so it says so. A warning never fails the command; a
failing check (the active profile has no endpoint, a probed provider is down) exits 1.
``--publish`` writes the result as ``mailroom.services/v1`` for the job board.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import asdict, dataclass
from importlib.util import find_spec
from pathlib import Path

from mailroom_sandbox.services._cli import print_json, warn
from mailroom_sandbox.services._exec import ServiceError, run_tool, strip_ansi
from mailroom_sandbox.services._redact import redact_urls

SERVICES = (
    "modal", "modal-auth", "hf", "hf-auth", "docker", "ollama", "ssh", "git", "vllm",
    "provider", "openrouter", "langfuse", "phoenix", "tunnel", "compose",
)
_MARK = {"ok": "ok  ", "warn": "WARN", "fail": "FAIL", "skipped": "skip"}


@dataclass
class ServiceStatus:
    name: str
    state: str  # ok | warn | fail | skipped
    detail: str
    hint: str = ""

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def _version(argv: list[str]) -> str | None:
    result = run_tool(argv, timeout=15.0, check=False)
    match = re.search(r"\d+\.\d+\.\d+", result.stdout or "")
    return match.group(0) if match else None


def _binary(name: str, *, needed: bool, hint: str, version: list[str] | None = None, pin: str | None = None) -> ServiceStatus:
    import shutil

    path = shutil.which(name)
    if not path:
        state = "warn" if needed else "skipped"
        return ServiceStatus(name, state, "not installed" + ("" if needed else " (not needed by this profile)"), hint)
    found = _version(version) if version else None
    if version and not found:
        return ServiceStatus(name, "warn", f"could not determine {name} version", hint)
    if pin and found and found != pin:
        return ServiceStatus(name, "warn", f"{name} {found}, sandbox verified against {pin}", hint)
    return ServiceStatus(name, "ok", f"{name} {found}" if found else path)


def _modal(profile_name: str, *, live: bool) -> ServiceStatus:
    from mailroom_sandbox.services.modal_cli import INSTALL_HINT, PINNED_SDK, app_status, vllm_app

    needed = profile_name == "modal-vllm"
    row = _binary("modal", needed=needed, hint=INSTALL_HINT, version=["modal", "--version"], pin=PINNED_SDK)
    if not live or "not installed" in row.detail:
        return row
    app = vllm_app()
    try:
        status = app_status(app)
    except ServiceError as exc:
        detail = f"{row.detail}; account check failed: {' '.join(str(exc).split())}"
        return ServiceStatus("modal", "fail" if needed else "warn", detail, "modal token new  (or check MODAL_PROFILE)")
    tasks = "" if not status["deployed"] else f", containers={'?' if status['tasks'] is None else status['tasks']}"
    account = os.environ.get("MODAL_PROFILE") or "active profile"
    detail = f"{row.detail}; {account}: {app} {status['state']}{tasks}"
    if needed and not status["deployed"] and row.state != "fail":
        # The modal-vllm profile has nothing to call until its app is deployed.
        return ServiceStatus("modal", "fail", detail, "sandbox modal deploy")
    return ServiceStatus("modal", row.state, detail, row.hint)


def _modal_auth(profile_name: str) -> ServiceStatus:
    if os.environ.get("MODAL_TOKEN_ID") and os.environ.get("MODAL_TOKEN_SECRET"):
        return ServiceStatus("modal-auth", "ok", "token from MODAL_TOKEN_ID/MODAL_TOKEN_SECRET")
    config = Path(os.environ.get("MODAL_CONFIG_PATH") or Path.home() / ".modal.toml").expanduser()
    if config.is_file():
        return ServiceStatus("modal-auth", "ok", f"config file {config}")
    state = "warn" if profile_name == "modal-vllm" else "skipped"
    return ServiceStatus("modal-auth", state, "no Modal token found", "modal token new")


def _hf_auth() -> ServiceStatus:
    if os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN"):
        return ServiceStatus("hf-auth", "ok", "token from the environment")
    home = Path(os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface")
    if (home / "token").is_file():
        return ServiceStatus("hf-auth", "ok", f"token file {home / 'token'}")
    return ServiceStatus(
        "hf-auth", "warn", "no token (the public sandbox dataset works anonymously)", "hf auth login  (or export HF_TOKEN) for gated repos"
    )


def _provider(profile: dict, *, live: bool) -> ServiceStatus:
    from mailroom_sandbox.health import _effective_base_url, explain_modal_timeout, missing_modal_endpoint, probe_models
    from mailroom_sandbox.providers import endpoints_for

    if missing_modal_endpoint(profile):
        return ServiceStatus(
            "provider", "fail", "modal-vllm has no endpoint (VLLM_BASE_URL and MODAL_WORKSPACE unset)",
            "sandbox modal deploy, then export VLLM_BASE_URL=<printed url>/v1",
        )
    base = endpoints_for(profile, base_url_override=_effective_base_url(profile)).base_url
    if not live:
        return ServiceStatus("provider", "ok", f"{base} (not probed; use --live)")
    result = probe_models(profile)
    if not result.ok:
        state = "warn" if explain_modal_timeout(profile, result) else "fail"
        return ServiceStatus("provider", state, f"{base}: {result.detail}", "sandbox modal status / sandbox health")
    listed = result.models or []
    models = ", ".join(listed[:3]) + (f" … ({len(listed)} models)" if len(listed) > 3 else "") if listed else "no models listed"
    return ServiceStatus("provider", "ok", f"{base}: {models}")


def _openrouter(profile: dict, *, live: bool) -> ServiceStatus:
    """API credential for the ``openrouter`` profile and for hybrid ``--agent-route NAME=openrouter:MODEL`` runs."""
    from mailroom_sandbox.health import _api_key, probe_openrouter_key

    needed = str(profile.get("provider")) == "openrouter"
    key_env = str(profile.get("api_key_env") or "OPENROUTER_API_KEY") if needed else "OPENROUTER_API_KEY"
    hint = f"export {key_env}=… (or add it to .env); rotate throwaway keys after testing"
    if not _api_key(key_env):
        if needed:
            return ServiceStatus("openrouter", "fail", f"{key_env} unset; the openrouter profile cannot call the API", hint)
        return ServiceStatus("openrouter", "skipped", f"{key_env} unset (only needed for the openrouter profile or API agent routes)")
    if not live:
        return ServiceStatus("openrouter", "ok", f"{key_env} set (value hidden; not probed, use --live)")
    base = (profile.get("base_url") if needed else None) or None
    result = probe_openrouter_key(os.environ.get("OPENROUTER_BASE_URL") or base, key_env=key_env)
    if result.ok:
        return ServiceStatus("openrouter", "ok", result.detail)
    return ServiceStatus("openrouter", "fail" if needed else "warn", result.detail, hint)


def _sink(name: str, url: str | None, *, configured: bool, live: bool, default_hint: str) -> ServiceStatus:
    from mailroom_sandbox.health import probe_models

    if not configured:
        return ServiceStatus(name, "skipped", f"not configured ({default_hint})")
    if not live:
        return ServiceStatus(name, "ok", f"{url} (not probed; use --live)")
    result = probe_models({"name": name, "base_url": url, "health": {"models_url": url}}, expect_json=False)
    if result.ok:
        return ServiceStatus(name, "ok", f"{url} reachable")
    return ServiceStatus(name, "warn", f"{url}: {result.detail}", "optional; never gates `sandbox health`")


def _langfuse(*, live: bool) -> ServiceStatus:
    host = os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL")
    if not host and not live:
        return ServiceStatus("langfuse", "skipped", "LANGFUSE_HOST unset (default http://localhost:3000 after `sandbox up`)")
    host = host or "http://localhost:3000"
    row = _sink("langfuse", f"{host.rstrip('/')}/api/public/health", configured=True, live=live, default_hint="")
    if os.environ.get("OBSERVABILITY_PROVIDER", "langfuse") == "langfuse" and not find_spec("langfuse"):
        return ServiceStatus(
            "langfuse", "warn", f"{row.detail}; langfuse SDK not installed, so runs record no traces",
            'pip install -e ".[observability]"',
        )
    return row


def _phoenix(*, live: bool) -> ServiceStatus:
    endpoint = os.environ.get("PHOENIX_ENDPOINT")
    root = endpoint.rsplit("/v1", 1)[0] if endpoint else None
    return _sink("phoenix", root, configured=bool(endpoint), live=live, default_hint="optional sidecar; set PHOENIX_ENDPOINT")


def _tunnel(profile: dict, *, live: bool) -> ServiceStatus:
    from mailroom_sandbox import tunnel as tunnel_mod

    if not isinstance(profile.get("tunnel"), dict):
        return ServiceStatus("tunnel", "skipped", "profile has no tunnel block")
    name = str(profile.get("name"))
    try:
        spec = tunnel_mod.tunnel_spec(profile)
    except ServiceError as exc:
        return ServiceStatus("tunnel", "warn", str(exc), f"set the tunnel env vars, then `sandbox tunnel --profile {name} up`")
    pid = tunnel_mod.read_pid(name)
    if pid is not None and tunnel_mod.is_alive(pid) and tunnel_mod.is_ssh_process(pid):
        if live and not tunnel_mod.is_up(spec.local_port):
            return ServiceStatus("tunnel", "warn", f"ssh pid {pid} alive but localhost:{spec.local_port} is not answering")
        return ServiceStatus("tunnel", "ok", f"ssh pid {pid} forwarding localhost:{spec.local_port}")
    return ServiceStatus("tunnel", "warn", "no forward running", f"sandbox tunnel --profile {name} up")


def _compose(*, live: bool, docker_present: bool) -> ServiceStatus:
    from mailroom_sandbox.compose import compose_argv

    if not docker_present:
        return ServiceStatus("compose", "skipped", "docker not installed")
    if not live:
        return ServiceStatus("compose", "skipped", "not probed (use --live)")
    result = run_tool(compose_argv([], "ps", "--services", "--status", "running"), timeout=30.0, check=False)
    if result.returncode != 0:
        return ServiceStatus("compose", "warn", " ".join(strip_ansi(result.stderr or "").split())[:160] or "docker compose failed")
    running = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
    if running:
        return ServiceStatus("compose", "ok", "running: " + ", ".join(running))
    return ServiceStatus("compose", "warn", "no compose service running", "sandbox up")


def run_doctor(profile_name: str, *, live: bool = False, services: list[str] | None = None) -> list[ServiceStatus]:
    """Evaluate the requested checks (default: all) for ``profile_name``."""
    import shutil

    from mailroom_sandbox.overlay import load_profile
    profile = load_profile(profile_name)
    docker_present = bool(shutil.which("docker"))
    checks = {
        "modal": lambda: _modal(profile_name, live=live),
        "modal-auth": lambda: _modal_auth(profile_name),
        "hf": lambda: _binary("hf", needed=True, hint="pip install -U huggingface_hub", version=["hf", "--version"]),
        "hf-auth": _hf_auth,
        "docker": lambda: _binary("docker", needed=bool(profile.get("compose_profiles")), hint="install Docker (needed for `sandbox up`)"),
        "ollama": lambda: _binary("ollama", needed=str(profile.get("provider")) == "ollama", hint="install Ollama (offline fallback profile)"),
        "ssh": lambda: _binary("ssh", needed=isinstance(profile.get("tunnel"), dict), hint="install an OpenSSH client (`sandbox tunnel`)"),
        "git": lambda: _binary("git", needed=True, hint="install git (`sandbox fetch-deps`)"),
        "vllm": lambda: _binary("vllm", needed=profile_name == "vllm-local", hint="pip install vllm on an NVIDIA host, or `sandbox modal deploy`"),
        "provider": lambda: _provider(profile, live=live),
        "openrouter": lambda: _openrouter(profile, live=live),
        "langfuse": lambda: _langfuse(live=live),
        "phoenix": lambda: _phoenix(live=live),
        "tunnel": lambda: _tunnel(profile, live=live),
        "compose": lambda: _compose(live=live, docker_present=docker_present),
    }
    wanted = [name for name in SERVICES if not services or name in services]
    rows = []
    for name in wanted:
        try:
            row = checks[name]()
        except ServiceError as exc:
            row = ServiceStatus(name, "warn", " ".join(str(exc).split()))
        row.detail = redact_urls(row.detail)
        row.hint = redact_urls(row.hint)
        rows.append(row)
    return rows


def _cmd_doctor(args: argparse.Namespace) -> int:
    from mailroom_sandbox.services.beacon import service_job

    with service_job("doctor", title=f"doctor · {args.profile}") as job:
        job.update(phase="CHECKING")
        rc = _run_doctor_command(args)
        job.finish("failed" if rc else "done", metrics={"returncode": rc})
        return rc


def _run_doctor_command(args: argparse.Namespace) -> int:
    from mailroom_sandbox.runtime import load_env_file

    load_env_file()
    if args.live and args.profile == "modal-vllm":
        warn("--live sends a request to the Modal endpoint; a scale-to-zero app will cold-start a billed GPU container")
    rows = run_doctor(args.profile, live=args.live, services=args.service or None)
    failed = [r for r in rows if r.state == "fail"]
    if args.publish:
        from mailroom_sandbox.tui.services_snapshot import publish_services

        path = publish_services([r.as_dict() for r in rows], profile=args.profile, live=args.live)
        print(f"published {path}", file=sys.stderr)
    if args.json:
        print_json({"profile": args.profile, "live": args.live, "ok": not failed, "services": [r.as_dict() for r in rows]})
        return 1 if failed else 0
    print(f"sandbox doctor · profile {args.profile} · {'live probes' if args.live else 'offline (no network)'}")
    for row in rows:
        print(f"  {_MARK[row.state]}  {row.name:<11} {row.detail}")
        if row.state in ("warn", "fail") and row.hint:
            print(f"        -> {row.hint}")
    print("next: " + ("fix the FAIL rows above, then re-run" if failed else "`sandbox doctor --live` to probe the endpoints, `--publish` to show this on `sandbox board`"))
    return 1 if failed else 0


def register(sub: argparse._SubParsersAction, leaf: argparse.ArgumentParser) -> None:
    """Add ``doctor`` to the root parser."""
    doctor = sub.add_parser("doctor", parents=[leaf], help="status of every service the sandbox uses (offline by default)")
    doctor.add_argument("--service", action="append", choices=SERVICES, default=[], metavar="NAME", help=f"limit to one service (repeatable): {', '.join(SERVICES)}")
    doctor.add_argument("--live", action="store_true", help="also probe endpoints over the network (can wake a billed Modal GPU)")
    doctor.add_argument("--publish", action="store_true", help="write the result for `sandbox board` (mailroom.services/v1)")
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(handler=_cmd_doctor)
