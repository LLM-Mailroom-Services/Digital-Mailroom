"""Preflight: confirm, prepare, and lock a job run (DMR-027).

Writes ``spec.lock.json`` (immutable) LAST — it is the commit point. Resume
refuses on spec drift unless ``--force`` (which archives the old generation,
re-preps, and re-locks) — except that a store locked to a DIFFERENT Modal app
is refused outright, even under ``--force``: see ``_foreign_app``
(``SANDBOX_TAKEOVER_FOREIGN_STORE=1`` is the deliberate override). Live
engine/sink probes are opt-in (``live=True``) so the default is network-free
and CI-safe.
"""

from __future__ import annotations

import ipaddress
import os
import time
import uuid
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

import llm_dojo_scoring
from llm_dojo_scoring.experiment import git_snapshot

from mailroom_sandbox import __version__ as sandbox_version
from mailroom_sandbox.corpus import prepare_subset
from mailroom_sandbox.job import checkpoint
from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.job.otel import resolve_sink
from mailroom_sandbox.job.spec import (
    RunSpec,
    engine_base_url,
    resolve_run_id,
    run_dir,
    spec_core,
)
from mailroom_sandbox.prompt_registry import prompt_lock_block
from mailroom_sandbox.prompt_versions import PromptSelectionError, selection_from_lock


def _versions() -> dict[str, Any]:
    out: dict[str, str] = {
        "mailroom_sandbox": sandbox_version,
        "llm_dojo_scoring": getattr(llm_dojo_scoring, "__version__", "?"),
    }
    from mailroom_sandbox import dojo_source

    choice = dojo_source.current()
    if choice is not None:
        # installed (the release) or vendored (the fallback snapshot): which one scored this run.
        out["llm_dojo_scoring_source"] = choice.source
    try:
        import opentelemetry  # type: ignore

        out["opentelemetry"] = getattr(opentelemetry, "__version__", "?")
    except Exception:
        pass
    return out


def _effective_model(spec: RunSpec, agent: str) -> str:
    """The model activation installs for ``agent``: ``agent_models`` wins, then its route, then the engine."""
    route = spec.agent_routes.get(agent)
    return spec.agent_models.get(agent) or (route.model if route else spec.engine.model)


def _in_house_url(spec: RunSpec, base_url: str) -> bool:
    """Whether a ``vllm`` route's URL is one the run controls, not any OpenAI-compatible host.

    Loopback, private and link-local addresses (a local server or SSH tunnel),
    the run's own engine host (unless that engine is OpenRouter), and this Modal
    workspace's apps qualify.
    """
    host = (urlparse(base_url).hostname or "").lower()
    if not host:
        return False
    if host == "localhost":
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None:
        return address.is_loopback or address.is_private or address.is_link_local
    workspace = os.environ.get("MODAL_WORKSPACE", "").strip().lower()
    if workspace and host.endswith(".modal.run") and host.startswith(f"{workspace}--"):
        return True
    if spec.engine.kind == "openrouter":
        return False  # the engine itself is a third party, so its host proves nothing
    try:
        engine_host = (urlparse(engine_base_url(spec)).hostname or "").lower()
    except Exception:  # noqa: BLE001 - an unresolvable engine proves nothing about the route
        return False
    return host == engine_host


def _local_reviewer_errors(spec: RunSpec) -> list[str]:
    """The in-house reviewer must be a second model, on a route the run controls."""
    model = spec.reviewer.model
    errs = []
    reviewer_model = _effective_model(spec, "sorter_reviewer")
    if model == _effective_model(spec, "sorter") or (
            spec.agent_routes.get("sorter_reviewer") and reviewer_model == _effective_model(spec, "sorter")):
        errs.append("decision reviewer backend local must use a different model from the sorter, or it only repeats its answer")
    if spec.job.mock:
        return errs
    route = spec.agent_routes.get("sorter_reviewer")
    if route is None:
        errs.append("decision reviewer backend local needs an agent_routes.sorter_reviewer entry serving its model")
    elif route.provider not in {"modal-vllm", "vllm"}:
        errs.append(f"decision reviewer backend local must stay in-house; agent route provider {route.provider!r} is a third party")
    else:
        if route.provider == "vllm" and not _in_house_url(spec, route.base_url or ""):
            errs.append(f"decision reviewer backend local must stay in-house; vllm route {route.base_url!r} is not a "
                        "loopback/private address, the run's engine host or this MODAL_WORKSPACE (use provider modal-vllm)")
        if reviewer_model != model:
            errs.append(f"decision reviewer model {model!r} differs from the sorter_reviewer agent's effective model "
                        f"{reviewer_model!r}")
    return errs


def _api_reviewer_errors(spec: RunSpec) -> list[str]:
    """The API reviewer must be a second model on an OpenRouter route with a token cap."""
    model = spec.reviewer.model
    errs = []
    # A sorter_reviewer calibration never runs the sorter (the engine model IS the reviewer), so the
    # same-model guard applies to a pipeline, where the reviewer would only repeat the sorter's answer.
    if spec.task != "sorter_reviewer" and model == _effective_model(spec, "sorter"):
        errs.append("decision reviewer backend api must use a different model from the sorter, or it only repeats its answer")
    if spec.job.mock:
        return errs
    route = spec.agent_routes.get("sorter_reviewer")
    if route is None:
        errs.append("decision reviewer backend api needs an agent_routes.sorter_reviewer entry serving its model")
    elif route.provider != "openrouter":
        errs.append(f"decision reviewer backend api needs provider openrouter; agent route provider is {route.provider!r}")
    elif _effective_model(spec, "sorter_reviewer") != model:
        errs.append(f"decision reviewer model {model!r} differs from the sorter_reviewer agent's effective model "
                    f"{_effective_model(spec, 'sorter_reviewer')!r}")
    if spec.job.mode == "modal":
        errs.append("decision reviewer backend api is not supported for modal jobs (use job.mode endpoint)")
    return errs


def _extraction_gate_lock(spec: RunSpec) -> dict[str, Any]:
    """The pipeline extraction-gate block as locked: the question set frozen by content and hash."""
    import hashlib

    from mailroom_sandbox.decision_backends import EXTRACTION_GATE, decisions_dir, load_question_set

    gate = spec.extraction_gate
    qset = load_question_set(gate.questions)
    if qset.get("kind") != EXTRACTION_GATE:
        raise ValueError(f"extraction_gate.questions {gate.questions!r} is not an extraction_gate question set")
    path = decisions_dir() / f"{gate.questions}.yaml"
    return {**gate.model_dump(), "questions_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "question_set": qset}


def _reviewer_lock(spec: RunSpec) -> dict[str, Any]:
    """The reviewer block as locked; a Decisions question set is frozen by content and hash."""
    block = spec.reviewer.model_dump()
    if spec.reviewer.backend == "decisions" and spec.reviewer.questions:
        import hashlib

        from mailroom_sandbox.decision_backends import decisions_dir, load_question_set

        path = decisions_dir() / f"{spec.reviewer.questions}.yaml"
        block["questions_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        block["question_set"] = load_question_set(spec.reviewer.questions)
    if spec.reviewer.handoff_run:
        # Freeze the handoff (by document id) so a resumed run sees the same answers: the
        # sorter's on a reviewer calibration, the specialist's extraction on a gate run.
        block["handoff"] = (extraction_handoff_map(spec.reviewer.handoff_run) if spec.task == "extraction_gate"
                            else sorter_handoff_map(spec.reviewer.handoff_run))
    return block


def extraction_handoff_map(run_id: str | list[str]) -> dict[str, dict[str, Any]]:
    """``{doc_id: extraction handoff}`` from finished specialist runs (task: <class>_specialist).

    Each item's prediction is the specialist's real extraction; the class is the run's
    specialist class. A list merges several runs (one per class), later runs winning.
    """
    import json

    from mailroom_sandbox.decision_backends import extraction_handoff
    from mailroom_sandbox.eval.agents import SPECIALIST_CLASS
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    out: dict[str, dict[str, Any]] = {}
    for rid in [run_id] if isinstance(run_id, str) else list(run_id):
        store = RunStore(run_dir(str(rid)))
        lock = store.read_lock() or {}
        doc_type = SPECIALIST_CLASS.get(str(lock.get("task") or ""))
        if not doc_type:
            raise ValueError(f"handoff_run {rid!r} is not a specialist run (task {lock.get('task')!r})")
        if (lock.get("job") or {}).get("mock", True):
            raise ValueError(f"handoff_run {rid!r} is a mock run; the gate calibrates on real extractions only")
        state = (store.read_checkpoint() or {}).get("state")
        if state != "done":
            raise ValueError(f"handoff_run {rid!r} is not a finished run (state {state!r})")
        found = 0
        for item in store.load_items():
            pred = item.get("pred")
            if item.get("ok") and isinstance(pred, dict) and pred and not pred.get("_parse_error"):
                out[str(item.get("item_id"))] = extraction_handoff(doc_type, pred)
                found += 1
        if not found:
            raise ValueError(f"handoff_run {rid!r} has no usable extractions")
    json.dumps(out)
    return out


def _committed_handoff(path: str) -> dict[str, dict[str, Any]]:
    """A sorter pass saved by scripts/export_sorter_handoff.py (repo-relative .jsonl path)."""
    import json
    from pathlib import Path

    from mailroom_sandbox.paths import repo_root

    file = Path(path)
    file = file if file.is_absolute() else repo_root() / file
    if not file.is_file():
        raise ValueError(f"handoff_run file {path!r} not found")
    out: dict[str, dict[str, Any]] = {}
    with file.open(encoding="utf-8", newline="\n") as handle:
        for line in handle.read().split("\n"):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("ok") and row.get("sorter_doc_type"):
                out[str(row["id"])] = {
                    "sorter_doc_type": row["sorter_doc_type"],
                    "sorter_doc_subclass": row.get("sorter_doc_subclass"),
                    "sorter_confidence": row.get("sorter_confidence"),
                }
    if not out:
        raise ValueError(f"handoff_run file {path!r} has no usable sorter answers")
    return out


def sorter_handoff_map(run_id: str | list[str]) -> dict[str, dict[str, Any]]:
    """``{doc_id: sorter answer}`` from finished sorter runs (isolated or per-item sorter task).

    A list merges several runs, the later run winning on overlap. A run stopped by its API
    cost cap counts as finished: every persisted item is a complete sorter answer, and the
    run that sorts the documents it did not reach goes later in the list.
    """
    import json

    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    out: dict[str, dict[str, Any]] = {}
    for rid in [run_id] if isinstance(run_id, str) else list(run_id):
        if str(rid).endswith(".jsonl"):
            out.update(_committed_handoff(rid))
            continue
        store = RunStore(run_dir(rid))
        checkpoint = store.read_checkpoint() or {}
        state = checkpoint.get("state")
        capped = state == "failed" and "api_cost_cap_usd" in str((checkpoint.get("last_error") or {}).get("message"))
        if state != "done" and not capped:
            raise ValueError(f"handoff_run {rid!r} is not a finished run (state {state!r})")
        found = 0
        for item in store.load_items():
            pred = item.get("pred") or {}
            if not item.get("ok") or not isinstance(pred, dict) or not pred.get("doc_type"):
                continue
            found += 1
            out[str(item.get("item_id"))] = {
                "sorter_doc_type": pred.get("doc_type"),
                "sorter_doc_subclass": pred.get("doc_subclass") or pred.get("contract_subtype"),
                "sorter_confidence": pred.get("confidence"),
            }
        if not found:
            raise ValueError(f"handoff_run {rid!r} has no usable sorter answers")
    json.dumps(out)  # must serialise into the lock
    return out


def _reviewer_route_bills_tokens(spec: RunSpec) -> bool:
    """Whether the sorter_reviewer chat agent would call a token-billed API.

    Its own route decides when it has one (a paid route can sit on a local engine); otherwise
    it runs on the engine.
    """
    from mailroom_sandbox.job.api_budget import API_PROVIDERS

    route = spec.agent_routes.get("sorter_reviewer")
    provider = route.provider if route is not None else spec.engine.kind
    return str(provider) in API_PROVIDERS


def _decisions_reviewer_errors(spec: RunSpec) -> list[str]:
    """The Decisions reviewer: a loadable question set, an OpenRouter key, and on a calibration
    run the engine model must be the reviewer model (the run's model label and price)."""
    from mailroom_sandbox.decision_backends import decision_questions, load_question_set

    from mailroom_sandbox.decision_backends import EXTRACTION_GATE

    errs: list[str] = []
    gate = spec.task == "extraction_gate"
    try:
        qset = load_question_set(spec.reviewer.questions or "")
        if (qset.get("kind") == EXTRACTION_GATE) != gate:
            raise ValueError("an extraction_gate run needs a kind: extraction_gate question set, and only it may use one")
        if not gate:
            decision_questions(qset)
    except Exception as exc:  # noqa: BLE001 - every shape error is a preflight error
        errs.append(f"decision reviewer questions: {exc}")
    if spec.job.mode == "modal":
        errs.append("decision reviewer backend decisions is not supported for modal jobs (use job.mode endpoint)")
    if not spec.job.mock and not os.environ.get("OPENROUTER_API_KEY", "").strip():
        errs.append("decision reviewer backend decisions needs OPENROUTER_API_KEY")
    if spec.reviewer.handoff_run:
        try:
            (extraction_handoff_map if gate else sorter_handoff_map)(spec.reviewer.handoff_run)
        except Exception as exc:  # noqa: BLE001
            errs.append(f"decision reviewer handoff_run: {exc}")
    elif gate:
        errs.append("an extraction_gate run needs reviewer.handoff_run: the finished specialist runs it reviews")
    if spec.task in ("sorter_reviewer", "extraction_gate") and spec.engine.model != spec.reviewer.model:
        errs.append(f"{spec.task} calibration: engine.model {spec.engine.model!r} must equal reviewer.model "
                    f"{spec.reviewer.model!r}, so the run is labelled and priced as the model it calls")
    return errs


def _engine_errors(spec: RunSpec) -> list[str]:
    errs: list[str] = []
    if spec.agent_models or spec.agent_knobs:
        from mailroom_sandbox.agent_routes import known_agents
        unknown = (set(spec.agent_models) | set(spec.agent_knobs)) - known_agents()
        if unknown:
            errs.append(f"unknown or retired agents: {sorted(unknown)}")
    if spec.agent_routes:
        from mailroom_sandbox.agent_routes import validate
        from mailroom_sandbox.services._exec import ServiceError
        try:
            validate(spec.agent_routes, credentials=not spec.job.mock)
        except (ValueError, ServiceError) as exc:
            errs.append(str(exc))
    if spec.reviewer:
        from mailroom_sandbox.overlay import live_doc_classes

        live = live_doc_classes()
        unknown = sorted(set(spec.reviewer.classes) - set(live))
        if unknown:
            errs.append(f"decision reviewer classes {unknown} are not live taxonomy classes; valid: {sorted(live)}")
        if spec.reviewer.backend == "jev" and spec.job.mock:
            # A mock pipeline run patches the LLM clients but not the decision backend.
            errs.append("decision reviewer backend jev would make live Jev calls in a mock run; use backend mock")
        elif spec.reviewer.backend == "jev" and spec.job.mode == "modal":
            # The Modal worker image excludes the decision extra.
            errs.append("decision reviewer backend jev is not supported for modal jobs (the Modal worker image has no decision extra); use endpoint mode or backend mock")
        elif spec.reviewer.backend == "jev" and not os.environ.get("TYPESAFE_API_KEY", "").strip():
            errs.append("decision reviewer backend jev needs TYPESAFE_API_KEY set (offline runs should use backend mock)")
        if spec.reviewer.backend == "local":
            errs.extend(_local_reviewer_errors(spec))
        if spec.reviewer.backend == "api":
            errs.extend(_api_reviewer_errors(spec))
        if spec.reviewer.backend == "decisions":
            errs.extend(_decisions_reviewer_errors(spec))
        if spec.task == "pipeline" and not spec.reviewer.classes:
            errs.append("decision reviewer on a pipeline run needs at least one class with a cutoff")
        if spec.task == "extraction_gate" and not spec.job.mock and spec.reviewer.backend != "decisions":
            errs.append("a live extraction_gate run needs reviewer backend decisions; "
                        f"{spec.reviewer.backend!r} has no extraction-gate path")
    elif spec.task == "extraction_gate" and not spec.job.mock:
        errs.append("a live extraction_gate run needs a reviewer block: backend decisions with a Decisions-API "
                    "model, a kind: extraction_gate question set and reviewer.handoff_run")
    elif spec.task == "sorter_reviewer" and not spec.job.mock and _reviewer_route_bills_tokens(spec):
        # A paid reviewer calibration must name its reviewer: without a reviewer block the
        # sorter_reviewer chat agent runs, which is how chat Luna was calibrated by mistake.
        errs.append("a paid sorter_reviewer run needs a reviewer block: backend decisions with a Decisions-API model "
                    "(e.g. openai/gpt-6-luna-decisions) and questions, or backend api with allow_chat_model: true")
    vllm = spec.engine.vllm
    if vllm.max_model_len < 1:
        errs.append("max_model_len must be >= 1")
    if not 0.0 < vllm.gpu_memory_utilization <= 1.0:
        errs.append("gpu_memory_utilization must be in (0, 1]")
    if vllm.max_num_seqs < 1:
        errs.append("max_num_seqs must be >= 1")
    if spec.engine.modal:
        if spec.engine.modal.image_tag == "latest":
            errs.append("modal image_tag must be pinned (never 'latest')")
        if spec.engine.modal.max_containers < 1:
            errs.append("modal max_containers must be >= 1 (cost guard)")
        # Mock runs call no vLLM endpoint, so admission cannot serialize billed GPU time.
        if not spec.job.mock and spec.engine.kind == "modal-vllm" and spec.job.concurrency > 1 and vllm.max_inputs < 1:
            errs.append(
                f"job.concurrency {spec.job.concurrency} needs engine.vllm.max_inputs >= 1: "
                "with 0 Modal serves one request at a time while the GPU bills"
            )
    return errs


def _engine_summary(spec: RunSpec) -> str:
    v = spec.engine.vllm
    modal = spec.engine.modal
    parts = [
        f"kind={spec.engine.kind} model={spec.engine.model}",
        f"max_model_len={v.max_model_len} gpu_util={v.gpu_memory_utilization} "
        f"max_num_seqs={v.max_num_seqs} "
        f"prefix_caching={'on' if v.enable_prefix_caching else 'off'} "
        f"enforce_eager={'on' if v.enforce_eager else 'off'}",
    ]
    if v.quantization:
        parts[1] += f" quantization={v.quantization}"
    if modal:
        modal_part = f"modal app={modal.app} gpu={modal.gpu} image={modal.image_tag} max_containers={modal.max_containers}"
        parts.append(modal_part)
    return ", ".join(parts)


def _probe_timeout_seconds(spec: RunSpec) -> float:
    """Timeout for the live engine probe.

    A scale-to-zero Modal app accepts the request and holds it open until the
    container is up (minutes), so the old hard 10 s would misreport a *booting*
    app as unreachable and fail the preflight (SAND-018). Modal probes get the
    boot budget; every other profile keeps the short CI-safe default. Override
    with ``SANDBOX_ENGINE_PROBE_TIMEOUT_SECONDS``.
    """
    env = os.environ.get("SANDBOX_ENGINE_PROBE_TIMEOUT_SECONDS", "").strip()
    if env:
        return float(env)
    if spec.engine.kind == "modal-vllm":
        return float(os.environ.get("MODAL_VLLM_STARTUP_TIMEOUT_SECONDS", "1200"))
    return 10.0


def _probe_engine(spec: RunSpec) -> dict[str, Any]:
    base = engine_base_url(spec)
    from mailroom_sandbox.overlay import load_profile
    profile = load_profile(spec.profile)
    api_key_env = str(profile.get("api_key_env") or "VLLM_API_KEY")
    # ``engine_base_url`` resolves VLLM_BASE_URL BEFORE the profile base for
    # every non-OpenRouter kind. The probe must then use the vLLM credential:
    # an ``openrouter`` profile pointed at a vLLM endpoint would otherwise
    # send OPENROUTER_API_KEY to that host.
    if spec.engine.kind != "openrouter" and os.environ.get("VLLM_BASE_URL", "").strip():
        api_key_env = "VLLM_API_KEY"
    api_key = os.environ.get(api_key_env, "").strip()
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    detail: dict[str, Any] = {"base_url": base}
    import httpx

    timeout = _probe_timeout_seconds(spec)
    detail["probe_timeout_seconds"] = timeout
    # URL-seam normalization: VLLM_BASE_URL / profile base_url carry the
    # OpenAI-style "/v1" suffix (deploy README + .env.example contract) —
    # appending "/v1/models" to an already-seamed base yields
    # ".../v1/v1/models" and a 404 from vLLM. Only add the seam when the
    # base does not already end with it.
    base = base.rstrip("/")
    models_path = f"{base}/models" if base.endswith("/v1") else f"{base}/v1/models"

    started = time.perf_counter()
    deadline = started + timeout
    last_reason = "no response from /v1/models"
    while True:
        attempt_timeout = max(1.0, deadline - time.perf_counter())
        try:
            resp = httpx.get(models_path, headers=headers, timeout=attempt_timeout)
        except httpx.ConnectError as exc:
            # Connection refused = wrong / dead endpoint (e.g. the localhost
            # fallback when VLLM_BASE_URL is unset) — fail fast, never retry.
            return {
                "ok": False,
                "reason": f"unreachable: {type(exc).__name__}: {exc}",
                "cold_boot_seconds": round(time.perf_counter() - started, 3),
                **detail,
            }
        except Exception as exc:  # noqa: BLE001 — boot can drop the held request
            last_reason = f"unreachable: {type(exc).__name__}: {exc}"
        else:
            if resp.status_code == 401:
                return {
                    "ok": False,
                    "reason": f"401 — set {api_key_env} to the configured provider token",
                    "cold_boot_seconds": round(time.perf_counter() - started, 3),
                    **detail,
                }
            if resp.status_code >= 400:
                return {
                    "ok": False,
                    "reason": f"HTTP {resp.status_code} from /v1/models",
                    "cold_boot_seconds": round(time.perf_counter() - started, 3),
                    **detail,
                }
            try:
                ids = [
                    str(m.get("id"))
                    for m in (resp.json().get("data") or [])
                    if isinstance(m, dict)
                ]
            except Exception as exc:  # noqa: BLE001
                # A booting Modal web_server can answer 2xx with an empty body
                # before vLLM is ready — retry until the boot budget elapses
                # (SAND-018: this is what misreported a boot as "wrong API").
                last_reason = (
                    f"/v1/models returned unparseable JSON (not a models payload): "
                    f"{type(exc).__name__}: {str(resp.text)[:160]!r} — the endpoint may be "
                    f"answering the wrong API"
                )
            else:
                detail["served_models"] = ids
                if spec.engine.model not in ids:
                    return {
                        "ok": False,
                        "reason": f"served {sorted(ids)} lacks spec.model={spec.engine.model}",
                        "cold_boot_seconds": round(time.perf_counter() - started, 3),
                        **detail,
                    }
                detail["cold_boot_seconds"] = round(time.perf_counter() - started, 3)
                return {"ok": True, **detail}
        if time.perf_counter() >= deadline:
            detail["cold_boot_seconds"] = round(time.perf_counter() - started, 3)
            return {"ok": False, "reason": last_reason, **detail}
        time.sleep(1.0)


def probe_engine(spec: RunSpec) -> dict[str, Any]:
    """Live engine probe: /v1/models at the resolved base URL vs the spec model.

    Public wrapper around the preflight live check so ``run start --job-mode
    modal`` can verify the endpoint BEFORE firing (DMR-048) without re-running
    the whole preflight.
    """
    return _probe_engine(spec)


def probe_timeout_seconds(spec: RunSpec) -> float:
    """Public boot budget for direct probes (CLI and per-agent route checks)."""
    return _probe_timeout_seconds(spec)


def record_cold_boot(store: RunStore, probe: Mapping[str, Any], *, run_id: str | None = None) -> dict[str, Any] | None:
    """Persist a successful live-probe measurement as the run's cold boot.

    Direct probes (``sandbox run preflight --live`` / ``run start``) bypass
    ``preflight(live=True)``, so the runner and metrics never saw the measured
    boot time. Only successful measurements are recorded; a failed probe must
    not overwrite an existing measurement.
    """
    boot_seconds = probe.get("cold_boot_seconds") if probe.get("ok") else None
    if boot_seconds is None:
        return None
    measurement = {
        "cold_boot_seconds": float(boot_seconds),
        "base_url": probe.get("base_url"),
        "served_models": probe.get("served_models"),
        "probe_timeout_seconds": probe.get("probe_timeout_seconds"),
        "measured_at": checkpoint.utc_now(),
        "run_id": run_id or store.run_id,
    }
    store.write_cold_boot(measurement)
    store.append_event("cold_boot", "info", **measurement)
    return measurement


def _modal_check(spec: RunSpec) -> bool:
    modal = spec.engine.modal
    if modal is None:
        return True
    return modal.image_tag != "latest" and modal.max_containers >= 1


def _foreign_app(existing: Mapping[str, Any], spec: RunSpec) -> str | None:
    """The lock's Modal app when the store belongs to a DIFFERENT fleet, else None.

    The run store is the one writable resource the app name does not scope (the
    Modal cache volumes are app-scoped for exactly this reason), so ``--force``
    is how two fleets sharing a run_id would collide: ``archive_generation()``
    moves ``items.jsonl`` aside, but a LIVE writer reopens it by path
    (``RunStore.append_item`` opens ``"a"`` per item) and recreates it under the
    same name — both fleets then append to one ``items.jsonl``. A plain resume
    already refuses (``engine.modal`` is inside ``spec_hash``); this closes the
    ``--force`` door too.
    """
    locked = ((existing.get("engine") or {}).get("modal") or {}).get("app")
    current = spec.engine.modal.app if spec.engine.modal else None
    if locked and current and locked != current:
        return str(locked)
    return None


def _takeover_foreign_store() -> bool:
    """Deliberate override for ``_foreign_app`` — a human taking over a store."""
    return os.environ.get("SANDBOX_TAKEOVER_FOREIGN_STORE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _prompt_summary(block: dict[str, Any]) -> str:
    agents = block.get("agents") or {}
    bits = [f"default={block.get('default', {}).get('source')}"]
    for agent, r in agents.items():
        bits.append(f"{agent}={r.get('key') or r.get('source')}" if r.get("source") == "eval-environment" else f"{agent}={r.get('source')}")
    return "; ".join(bits) if bits else "code-default"


def _dataset_lock(prov: dict[str, Any], spec: RunSpec) -> dict[str, Any]:
    return {
        "repo": (spec.dataset.local_file().name if spec.dataset.local_file() else spec.dataset.repo),
        "config": spec.dataset.config,
        "split": spec.dataset.split,
        "revision": prov.get("revision_requested") or spec.effective_revision(),
        # DMR-049: the resolved 40-hex sha (branch/tag revisions resolve via
        # dataset_info; the default pin is already a full sha).
        "revision_resolved": prov.get("revision_resolved"),
        "limit": spec.dataset.limit,
        "sample_seed": spec.dataset.sample_seed,
        "strata": spec.dataset.strata,
        # DMR-066: actual drawn (doc_class::subclass) distribution — the lock
        # now proves the requested strata were really drawn (no silent
        # single-class collapse), not just recorded as a spec.
        "strata_actual": prov.get("strata_actual"),
        "rows": prov.get("rows"),
        "sha256": prov.get("sha256"),
        "metadata": prov.get("metadata", {}),
    }


def _prompt_text_sha(block: dict[str, Any]) -> str:
    """Hash of the RESOLVED prompt texts (local/langfuse), not just refs.

    ``spec_hash`` covers prompt REFS; two identical refs whose file bodies
    changed hash the same, so a resume would replay with different prompt
    text. This sha lands in the lock and is checked on every preflight
    (DMR-049).
    """
    import hashlib

    agents = block.get("agents") or {}
    parts = []
    for agent in sorted(agents):
        ref = agents[agent]
        if not isinstance(ref, dict):
            continue
        parts.append(f"{agent}:{ref.get('sha256') or ''}:{ref.get('text') or ''}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _resolve_report_group(
    spec: RunSpec,
    *,
    run_id: str,
    config_path: str | Path | None,
) -> str | None:
    """Resolve the report group; fail if an explicit runbook id is unknown."""
    from mailroom_sandbox.report_paths import (
        experiment_prefix,
        report_group_for_config,
        report_group_for_runbook,
    )

    if spec.runbook_id:
        group = report_group_for_runbook(spec.runbook_id)
        if group is None:
            raise ValueError(
                f"unknown runbook_id {spec.runbook_id!r}: no report-group catalog entry"
            )
        return group
    return report_group_for_config(config_path) or experiment_prefix(run_id)


def preflight(
    spec: RunSpec,
    *,
    run_id: str = "",
    config_path: str | Path | None = None,
    offline: bool = False,
    force: bool = False,
    dry_run: bool = False,
    live: bool = False,
) -> dict[str, Any]:
    """Prepare or validate a generation under the writer and control locks.

    Load dotenv configuration before resolving prompts and probes. Return
    the preflight report, or ``busy_refused`` when the writer lock is held.
    ``force`` requests archival and a new generation but refuses possibly
    active writers; ``offline`` avoids remote prompt/tracing requirements.
    ``live`` probes the engine for a new generation. ``dry_run`` only checks
    lock readability and returns without resolving or preparing artifacts;
    the run directory and lock files may still be created.
    Uncaught configuration and file-access errors propagate.
    """
    # Dotenv supplies prompt credentials, endpoint and tracing configuration.
    # Loading it is independent of graph activation and preserves explicit env.
    from mailroom_sandbox.runtime import load_env_file

    load_env_file()
    run_id = run_id or resolve_run_id(spec)
    if dry_run:
        # Read-only: no run directory and no lock files for a dry run.
        if not run_dir(run_id).exists():
            return {"run_id": run_id, "status": "prepared", "checks": []}
        return _preflight(spec, run_id=run_id, config_path=config_path,
                          offline=offline, force=force, dry_run=True, live=live)
    store = RunStore(run_dir(run_id))
    try:
        with store.acquire(blocking=False), store.control():
            return _preflight(spec, run_id=run_id, config_path=config_path,
                              offline=offline, force=force, dry_run=dry_run, live=live)
    except BlockingIOError:
        return {"status": "busy_refused", "run_id": run_id,
                "detail": "run writer is active; cancel and wait for paused before resetting"}


def _preflight(
    spec: RunSpec,
    *,
    run_id: str = "",
    config_path: str | Path | None = None,
    offline: bool = False,
    force: bool = False,
    dry_run: bool = False,
    live: bool = False,
) -> dict[str, Any]:
    """Validate an existing generation or prepare artifacts and write a new lock.

    Return ``prepared``, ``failed``, ``drift_refused``, ``busy_refused``, or
    ``foreign_store_refused`` in the report's status. ``dry_run`` checks only
    existing lock readability, without validating domains or writing artifacts.
    ``force`` archives an eligible existing generation before preparing its
    replacement. Caught prompt, dataset, and tracing errors become failed
    reports; uncaught configuration and file-access errors propagate.
    """
    run_id = run_id or resolve_run_id(spec)
    store = RunStore(run_dir(run_id))

    try:
        existing = store.read_lock()
    except RuntimeError as exc:
        # hub#41: a corrupt spec.lock.json is a LOUD preflight failure —
        # never a silent run with spec_hash: null.
        return {
            "status": "failed",
            "run_id": run_id,
            "checks": [{"name": "lock", "ok": False, "detail": str(exc)}],
        }

    report: dict[str, Any] = {"run_id": run_id, "status": "prepared", "checks": []}
    if dry_run:
        return report

    # 1) prompt surface — resolves all agent overrides (fails fast on typos).
    #    Resolved FIRST so the drift check can hash the prompt TEXTS: spec_hash
    #    covers refs only, and two identical refs whose file bodies changed
    #    would otherwise resume with different prompt text (DMR-049).
    try:
        prompt_block = prompt_lock_block(spec.prompt, offline=offline)
    except (KeyError, PromptSelectionError) as exc:
        report["status"] = "failed"
        report["checks"] = [{"name": "prompt", "ok": False, "detail": str(exc)}]
        return report
    prompt_text_sha = _prompt_text_sha(prompt_block)
    report["checks"].append(
        {"name": "prompt", "ok": True, "detail": _prompt_summary(prompt_block)}
    )

    try:
        report_group = _resolve_report_group(spec, run_id=run_id, config_path=config_path)
    except ValueError as exc:
        report["status"] = "failed"
        report["checks"].append({"name": "report_group", "ok": False, "detail": str(exc)})
        return report

    if existing and not force:
        drifted = existing.get("spec_hash") != spec.spec_hash()
        if not drifted and existing.get("prompt_text_sha") and existing.get("prompt_text_sha") != prompt_text_sha:
            drifted = True
        # Keys absent on pre-catalog locks: resume. Present keys still drift.
        if (
            not drifted
            and "runbook_id" in existing
            and existing.get("runbook_id") != (spec.runbook_id or None)
        ):
            drifted = True
        if (
            not drifted
            and "report_group" in existing
            and existing.get("report_group") != (report_group or None)
        ):
            drifted = True
        if drifted:
            return {
                "status": "drift_refused",
                "run_id": run_id,
                "spec_hash": spec.spec_hash(),
                "locked_spec_hash": existing.get("spec_hash"),
                "detail": (
                    "spec, resolved prompt text, runbook, or report group drifted "
                    "since the lock; pass --force to re-lock"
                ),
            }

    # A --force re-lock of a store locked to ANOTHER Modal app is refused: the
    # archive below cannot stop that fleet's live writer (it reopens items.jsonl
    # by path and recreates it), so two fleets would end up appending to one
    # file. Taking the store over anyway is a deliberate, named act.
    if existing and force and not _takeover_foreign_store():
        foreign = _foreign_app(existing, spec)
        if foreign:
            current_app = spec.engine.modal.app if spec.engine.modal else None
            return {
                "status": "foreign_store_refused",
                "run_id": run_id,
                "lock_app": foreign,
                "spec_app": current_app,
                "detail": (
                    f"this store is locked to modal app {foreign!r}, this fleet is "
                    f"{current_app!r} — a --force re-lock would archive another "
                    "fleet's items and both fleets would then append to the same "
                    "items.jsonl. Run the cell on the fleet that owns the store, "
                    "remove the store, or set SANDBOX_TAKEOVER_FOREIGN_STORE=1 to "
                    "take it over deliberately."
                ),
            }

    if existing:
        cp = store.read_checkpoint() or {}
        remote_call = (cp.get("remote") or {}).get("call_id")
        if force and remote_call:
            from mailroom_sandbox.job.remote import terminal_confirmed

            # A stale checkpoint or diagnostic call graph is not proof of death.
            remote_busy = not terminal_confirmed(store)
        else:
            remote_busy = False
        if force and (remote_busy or (cp.get("state") == "running" and not remote_call)):
            return {"status": "busy_refused", "run_id": run_id,
                    "detail": "generation may still have a live writer; cancel and confirm termination first"}
        if not force:
            # Existing lock is the generation's commit point. Validate its
            # artifacts, never recreate missing bytes under that identity.
            try:
                store.verify_generation()
            except RuntimeError as exc:
                report["status"] = "failed"
                report["checks"].append({"name": "generation", "ok": False, "detail": str(exc)})
                return report
            report.update({"spec_hash": existing["spec_hash"], "lock_path": str(store.lock_path)})
            return report

    # write_lock refuses to overwrite in place, so a forced re-lock archives
    # the old generation first — new dataset bytes must never sit under an old
    # lock/checkpoint (DMR-049).
    archived = store.archive_generation() if (existing and force) else None
    if archived is not None:
        report["archived"] = str(archived)

    # 2) dataset — prepared subset (idempotent; network only for Hub specs).
    try:
        prov = prepare_subset(spec.dataset, store.dataset_path)
        report["checks"].append(
            {
                "name": "dataset",
                "ok": True,
                "detail": (
                    f"rows={prov['rows']} sha256={prov['sha256'][:12]} "
                    f"revision={prov.get('revision_requested')}"
                ),
            }
        )
    except Exception as exc:  # noqa: BLE001
        report["status"] = "failed"
        report["checks"].append({"name": "dataset", "ok": False, "detail": str(exc)})
        return report

    if spec.target:
        # Level-2 target: the lock keeps the prepared subset (its sha is the
        # dataset identity); the runner narrows it. Zero matching rows is a
        # config error now, not an empty run later.
        from mailroom_sandbox.eval.primary import rows_for_class

        try:
            narrowed = len(rows_for_class(store.dataset_rows(), spec.target))
        except ValueError as exc:
            report["status"] = "failed"
            report["checks"].append({"name": "target", "ok": False, "detail": str(exc)})
            return report
        report["checks"].append({"name": "target", "ok": True, "detail": f"{spec.target}: {narrowed} row(s)"})

    # 3) engine spec validators (pydantic ranges + repo guards)
    eng_errors = _engine_errors(spec)
    if eng_errors:
        report["status"] = "failed"
        report["checks"].append({"name": "engine_spec", "ok": False, "detail": "; ".join(eng_errors)})
        return report
    report["checks"].append({"name": "engine_spec", "ok": True, "detail": _engine_summary(spec)})

    # 4) optional live engine probe — also the cold-boot measurement (SAND-018)
    if live:
        probe = _probe_engine(spec)
        report["checks"].append(
            {
                "name": "engine_probe",
                "ok": probe["ok"],
                "detail": probe.get("reason", probe.get("detail", "ok")),
            }
        )
        if not probe["ok"]:
            report["status"] = "failed"
            report["checks"][-1]["detail"] = probe.get("reason", "probe failed")
            return report
        boot_seconds = probe.get("cold_boot_seconds")
        if boot_seconds is not None:
            measurement = record_cold_boot(store, probe, run_id=run_id)
            if measurement is not None:
                report["cold_boot_seconds"] = measurement["cold_boot_seconds"]
                report["cold_boot_path"] = str(store.cold_boot_path)
                report["checks"][-1]["detail"] += (
                    f" | cold_boot={measurement['cold_boot_seconds']:.2f}s"
                )

    # 5) trace sink
    try:
        sink = resolve_sink(
            sink=spec.trace.sink,
            otlp=spec.trace.otlp,
            endpoint=spec.trace.endpoint,
            environment=spec.trace.environment,
            service_name="sandbox-job",
            run_id=run_id,
            tags=spec.trace.tags,
        )
        if spec.trace.sink == "langfuse" and not offline and not sink.headers.get("Authorization"):
            report["status"] = "failed"
            report["checks"].append(
                {"name": "trace_sink", "ok": False, "detail": "langfuse keys unset (LANGFUSE_PUBLIC_KEY/SECRET_KEY)"}
            )
            return report
        if spec.trace.sink == "langfuse" and not offline and find_spec("langfuse") is None:
            report["status"] = "failed"
            report["checks"].append(
                {"name": "trace_sink", "ok": False,
                 "detail": "langfuse SDK missing: install mailroom-sandbox[observability] or set trace.sink: none"}
            )
            return report
        report["checks"].append({"name": "trace_sink", "ok": True, "detail": f"{spec.trace.sink} -> {sink.endpoint or '(no exporter)'}"})
    except Exception as exc:  # noqa: BLE001
        report["status"] = "failed"
        report["checks"].append({"name": "trace_sink", "ok": False, "detail": str(exc)})
        return report

    # 6) modal cost guards
    report["checks"].append(
        {"name": "modal_spec", "ok": _modal_check(spec), "detail": "modal guards ok" if _modal_check(spec) else "modal guard failed"}
    )

    # Commit point: prompt lock then spec lock then prepared checkpoint.
    store.write_prompt_lock(prompt_block)
    lock = {
        "schema_version": 1,
        "lock_kind": "spec.lock",
        "run_id": run_id,
        "created_at": checkpoint.utc_now(),
        "generation_id": uuid.uuid4().hex,
        "spec_hash": spec.spec_hash(),
        "prompt_text_sha": prompt_text_sha,
        "task": spec.task,
        **({"target": spec.target} if spec.target else {}),
        "profile": spec.profile,
        "agent_models": dict(spec.agent_models),
        **({"agent_routes": {name: route.model_dump() for name, route in spec.agent_routes.items()}} if spec.agent_routes else {}),
        **({"reviewer": _reviewer_lock(spec)} if spec.reviewer else {}),
        **({"extraction_gate": _extraction_gate_lock(spec)} if spec.extraction_gate else {}),
        "prompt": prompt_block,
        "engine": spec.engine.model_dump(),
        "job": spec.job.model_dump(),
        "trace": spec.trace.model_dump(),
        "dataset": _dataset_lock(prov, spec),
        "otel": {"sink": spec.trace.sink, "environment": spec.trace.environment},
        "versions": _versions(),
        "git": git_snapshot(),
        "spec_core": spec_core(spec),
    }
    # Freeze the resolved per-agent generation knobs (max_tokens / max_input_chars /
    # chunk_chars / temperature). Without this the card can only read the LIVE posture
    # table, so editing a posture later silently rewrites what every historical card
    # claims the run was configured with — and the contracts whole-document change is
    # exactly such an edit.
    from mailroom_sandbox.job.specialist_posture import agent_knobs_for_run
    from mailroom_sandbox.runtime import resolve_agent_knobs

    lock["agent_knobs"] = resolve_agent_knobs(spec.agent_knobs or agent_knobs_for_run(run_id))
    # Freeze the resolved table for model-only runs too: otherwise runtime.activate()
    # rebuilds the remaining agents from the live profile/taxonomy, so a later
    # judge_model edit silently changes a resumed run without changing its lock.
    if spec.agent_routes or spec.agent_knobs or spec.agent_models:
        from mailroom_sandbox.agent_routes import describe
        lock["agent_assignments"] = describe(spec)
    selected = selection_from_lock(prompt_block)
    if selected:
        # The selected eval-environment keys + sha256 are part of the run's identity.
        lock["prompt_versions"] = selected.versions_stamp()
    if spec.runbook_id:
        lock["runbook_id"] = spec.runbook_id
    if report_group:
        lock["report_group"] = report_group
    store.write_lock(lock)
    total = len(store.dataset_rows())
    if spec.target:
        from mailroom_sandbox.eval.primary import rows_for_class

        total = len(rows_for_class(store.dataset_rows(), spec.target))
    store.write_checkpoint(state="prepared", cursor=0, total=total, remote=None)
    store.append_event("preflight_ok", "info", spec_hash=spec.spec_hash())
    report.update({"status": "prepared", "spec_hash": spec.spec_hash(), "lock_path": str(store.lock_path)})
    return report
