"""api_evals.invoke — run an OpenRouter API eval task through the sandbox job
machinery and return per-item rows + the experiment record + REAL cost.

The sandbox's ``run_job`` whole-run path (task = registered agent name) already
does everything an isolated specialist run needs: preflight dataset lockdown
(same strata/seed/revision as the Modal runs), prompt-lock application, live
agent invocation through the vendored agents, per-item usage capture, and
experiment-log append. This module is the thin OpenRouter-coded wrapper: it
points the run at the api-evals run-spec YAMLs (profile=openrouter / model
qwen/qwen3.7-flash) and layers REAL API cost accounting on top.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

_log = logging.getLogger("api_evals.invoke")


def _same_generation(record: dict[str, Any], store, lock: dict[str, Any]) -> bool:
    """Return whether a successful record belongs to the locked run generation."""
    from mailroom_sandbox.job.evidence import record_matches

    return record_matches(record, store, lock)


def run_task(
    yaml_path: Path | str,
    *,
    api_key: str | None = None,
    prices: tuple[float, float] | None = None,
    mock: bool = False,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Run one api-evals task end-to-end and return the decorated summary.

    Returns per-item ``rows``, the experiment-log ``record``, ``scores``,
    ``cost``, wall time in seconds, and run, spec, and dataset identity.
    ``prices`` overrides input/output prices in USD per million tokens.
    A matching completed generation is reused without an API key or new
    calls; its rows are empty and cost uses aggregate token counts.
    ``force`` bypasses reuse and requests a new preflight generation.
    ``dry_run`` returns spec metadata only, without preflight or API calls.

    A supplied ``api_key`` is stored in ``OPENROUTER_API_KEY`` for execution.
    Raises RuntimeError for a missing execution key, rejected preflight,
    unusable terminal evidence, or a run that does not finish as ``done``.
    Spec-loading, store, runner, and cost-accounting errors propagate.
    """
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job import preflight, runner
    from mailroom_sandbox.job.spec import load_run_spec, run_dir

    from api_evals import cost as cost_mod
    from api_evals.registry import DEFAULT_API_MODEL

    path = Path(yaml_path)
    spec = load_run_spec(path)

    run_id = spec.run_id or path.stem
    if dry_run:
        return {
            "run_id": run_id,
            "task": spec.task,
            "profile": spec.profile,
            "model": spec.engine.model,
            "n": spec.dataset.limit or 0,
            "dry_run": True,
        }

    existing_store = RunStore(run_dir(run_id))
    if not force and existing_store.terminal():
        from mailroom_sandbox.eval import experiment_log

        report = preflight.preflight(spec, run_id=run_id, offline=True)
        if report.get("status") != "prepared":
            raise RuntimeError(f"preflight failed for {path.name}: {report.get('status')} — {report.get('checks')}")
        with existing_store.acquire():
            lock = existing_store.verify_generation()
            expected_hash = spec.spec_hash()
            expected_name = f"sandbox_{spec.task}_{run_id}"
            if existing_store.state() != "done":
                raise RuntimeError(f"run {run_id} is {existing_store.state()}; no successful terminal record can be reused")
            records = [rec for rec in experiment_log.load()
                       if rec.get("spec_hash") == expected_hash
                       and (rec.get("run_id") == run_id if rec.get("run_id") is not None
                            else rec.get("experiment_name") == expected_name)
                       and _same_generation(rec, existing_store, lock)]
            if not records:
                raise RuntimeError(f"run {run_id} has no matching terminal record for its exact run/spec identity")
            rec = records[-1]
            model = rec.get("model") or spec.engine.model
            c = cost_mod.cost_from_aggregate(
                prompt_tokens=int(rec.get("prompt_tokens") or 0),
                completion_tokens=int(rec.get("completion_tokens") or 0),
                n=int(rec.get("n") or spec.dataset.limit or 0), model=model, prices=prices)
            return {"run_id": run_id, "task": spec.task, "profile": spec.profile,
                    "model": model, "n": int(rec.get("n") or spec.dataset.limit or 0),
                    "rows": [], "record": rec, "scores": rec.get("scores") or {}, "cost": c,
                    "wall_seconds": rec.get("wall_seconds"), "spec_hash": expected_hash,
                    "dataset_fingerprint": rec.get("dataset_fingerprint") or "", "resumed": True}
    if api_key:
        os.environ["OPENROUTER_API_KEY"] = api_key
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set — api-evals runs are live OpenRouter "
            "calls; set the key in .env (gitignored) or pass --api-key"
        )

    report = preflight.preflight(
        spec,
        run_id=run_id,
        offline=False,
        force=force,
        dry_run=False,
        live=False,
    )
    if report.get("status") != "prepared":
        raise RuntimeError(f"preflight failed for {path.name}: {report.get('status')} — {report.get('checks')}")

    store = RunStore(run_dir(run_id))
    with store.acquire():
        summary = runner.run_job(store, mock=mock, dry_run=False)

    if summary.get("state") != "done":
        raise RuntimeError(
            f"run {run_id} ended {summary.get('state')} — error: "
            f"{summary.get('last_error') or summary.get('error')}"
        )

    result = summary.get("result") or {}
    rows = (
        result.get("rows")
        if isinstance(result.get("rows"), list)
        else (summary.get("rows") if isinstance(summary.get("rows"), list) else [])
    )
    record = result.get("record") if isinstance(result, dict) else summary.get("record")
    scores = result.get("scores") if isinstance(result, dict) else summary.get("scores")
    model = (record or {}).get("model") or spec.engine.model or DEFAULT_API_MODEL

    # REAL API cost from per-item tokens x OpenRouter list price.
    c = cost_mod.cost_from_rows(rows, model=model, prices=prices)
    cost_block = {
        "model": c["model"],
        "n": c["n"],
        "n_ok": c["n_ok"],
        "price_per_million_in": c["price_per_million_in"],
        "price_per_million_out": c["price_per_million_out"],
        "prompt_tokens": c["prompt_tokens"],
        "completion_tokens": c["completion_tokens"],
        "total_tokens": c["total_tokens"],
        "tokens_per_document": c["tokens_per_document"],
        "cost_usd": c["cost_usd"],
        "cost_per_document": c["cost_per_document"],
        "honest_gaps": c["honest_gaps"],
    }

    return {
        "run_id": run_id,
        "task": spec.task,
        "profile": spec.profile,
        "model": model,
        "n": len(rows) or (spec.dataset.limit or 0),
        "rows": rows,
        "record": record,
        "scores": scores or {},
        "cost": cost_block,
        "wall_seconds": round(float(result.get("wall_seconds") or summary.get("wall_seconds") or 0.0), 3),
        "spec_hash": summary.get("spec_hash") or (record or {}).get("spec_hash") or "",
        "dataset_fingerprint": summary.get("dataset_fingerprint") or (record or {}).get("dataset_fingerprint") or "",
    }
