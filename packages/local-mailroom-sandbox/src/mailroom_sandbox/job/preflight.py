"""Preflight: confirm, prepare, and lock a job run (DMR-027).

Writes ``spec.lock.json`` (immutable) LAST — it is the commit point. Resume
refuses on spec drift unless ``--force`` (which archives the old generation,
re-preps, and re-locks). Live engine/sink probes are opt-in (``live=True``)
so the default is network-free and CI-safe.
"""

from __future__ import annotations

import os
from typing import Any

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
    spec_hash,
)
from mailroom_sandbox.prompt_registry import prompt_lock_block


def _versions() -> dict[str, Any]:
    out: dict[str, str] = {
        "mailroom_sandbox": sandbox_version,
        "llm_dojo_scoring": getattr(llm_dojo_scoring, "__version__", "?"),
    }
    try:
        import opentelemetry  # type: ignore

        out["opentelemetry"] = getattr(opentelemetry, "__version__", "?")
    except Exception:
        pass
    return out


def _engine_errors(spec: RunSpec) -> list[str]:
    errs: list[str] = []
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
    return errs


def _engine_summary(spec: RunSpec) -> str:
    v = spec.engine.vllm
    modal = spec.engine.modal
    parts = [
        f"kind={spec.engine.kind} model={spec.engine.model}",
        f"max_model_len={v.max_model_len} gpu_util={v.gpu_memory_utilization} max_num_seqs={v.max_num_seqs}",
    ]
    if v.quantization:
        parts[1] += f" quantization={v.quantization}"
    if modal:
        modal_part = f"modal app={modal.app} gpu={modal.gpu} image={modal.image_tag} max_containers={modal.max_containers}"
        parts.append(modal_part)
    return ", ".join(parts)


def _probe_engine(spec: RunSpec) -> dict[str, Any]:
    base = engine_base_url(spec)
    api_key = os.environ.get("VLLM_API_KEY", "").strip()
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    detail: dict[str, Any] = {"base_url": base}
    import httpx

    try:
        resp = httpx.get(f"{base}/v1/models", headers=headers, timeout=10.0)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"unreachable: {type(exc).__name__}: {exc}", **detail}
    if resp.status_code == 401:
        return {"ok": False, "reason": "401 — set VLLM_API_KEY to the deployed token", **detail}
    if resp.status_code >= 400:
        return {"ok": False, "reason": f"HTTP {resp.status_code} from /v1/models", **detail}
    try:
        ids = [str(m.get("id")) for m in (resp.json().get("data") or []) if isinstance(m, dict)]
    except Exception:
        ids = []
    detail["served_models"] = ids
    if spec.engine.model not in ids:
        return {"ok": False, "reason": f"served {sorted(ids)} lacks spec.model={spec.engine.model}", **detail}
    return {"ok": True, **detail}


def _modal_check(spec: RunSpec) -> bool:
    modal = spec.engine.modal
    if modal is None:
        return True
    return modal.image_tag != "latest" and modal.max_containers >= 1


def _prompt_summary(block: dict[str, Any]) -> str:
    agents = block.get("agents") or {}
    bits = [f"default={block.get('default', {}).get('source')}"]
    for agent, r in agents.items():
        bits.append(f"{agent}={r.get('source')}")
    return "; ".join(bits) if bits else "code-default"


def _dataset_lock(prov: dict[str, Any], spec: RunSpec) -> dict[str, Any]:
    return {
        "repo": (spec.dataset.local_file().name if spec.dataset.local_file() else spec.dataset.repo),
        "config": spec.dataset.config,
        "split": spec.dataset.split,
        "revision": prov.get("revision_requested") or spec.dataset.effective_revision(),
        "limit": spec.dataset.limit,
        "sample_seed": spec.dataset.sample_seed,
        "strata": spec.dataset.strata,
        "rows": prov.get("rows"),
        "sha256": prov.get("sha256"),
        "metadata": prov.get("metadata", {}),
    }


def preflight(
    spec: RunSpec,
    *,
    run_id: str = "",
    offline: bool = False,
    force: bool = False,
    dry_run: bool = False,
    live: bool = False,
) -> dict[str, Any]:
    """Confirm all spec domains, prepare artifacts, and write the lock.

    Returns a report dict with status ``prepared | drift_refused | failed``.
    ``dry_run`` validates without writing; ``force`` re-locks a drifted run.
    """
    run_id = run_id or resolve_run_id(spec)
    store = RunStore(run_dir(run_id))

    existing = store.read_lock()
    if existing and not force:
        if existing.get("spec_hash") != spec.spec_hash():
            return {
                "status": "drift_refused",
                "run_id": run_id,
                "spec_hash": spec.spec_hash(),
                "locked_spec_hash": existing.get("spec_hash"),
                "detail": "spec drifted since the lock; pass --force to re-lock",
            }

    report: dict[str, Any] = {"run_id": run_id, "status": "prepared", "checks": []}
    if dry_run:
        return report

    # 1) prompt surface — resolves all agent overrides (fails fast on typos).
    try:
        prompt_block = prompt_lock_block(spec.prompt, offline=offline)
    except KeyError as exc:
        report["status"] = "failed"
        report["checks"] = [{"name": "prompt", "ok": False, "detail": str(exc)}]
        return report
    report["checks"].append(
        {"name": "prompt", "ok": True, "detail": _prompt_summary(prompt_block)}
    )

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

    # 3) engine spec validators (pydantic ranges + repo guards)
    eng_errors = _engine_errors(spec)
    if eng_errors:
        report["status"] = "failed"
        report["checks"].append({"name": "engine_spec", "ok": False, "detail": "; ".join(eng_errors)})
        return report
    report["checks"].append({"name": "engine_spec", "ok": True, "detail": _engine_summary(spec)})

    # 4) optional live engine probe
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
        "spec_hash": spec.spec_hash(),
        "task": spec.task,
        "profile": spec.profile,
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
    store.write_lock(lock)
    total = len(store.dataset_rows())
    store.write_checkpoint(state="prepared", cursor=0, total=total, remote=None)
    store.append_event("preflight_ok", "info", spec_hash=spec.spec_hash())
    report.update({"status": "prepared", "spec_hash": spec.spec_hash(), "lock_path": str(store.lock_path)})
    return report