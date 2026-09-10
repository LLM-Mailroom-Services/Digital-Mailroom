"""Provider × model × prompt experiment matrix."""

from __future__ import annotations

from typing import Any

from mailroom_sandbox.eval import experiment_log, runners
from mailroom_sandbox.overlay import load_profile, map_model, serving_family


def cell_name(task: str, provider: str, model: str, prompt: str) -> str:
    slug = model.split("/")[-1].replace(":", "-")
    prompt_slug = prompt.replace("/", "-")
    return f"matrix_{task}_{provider}_{slug}_{prompt_slug}"


def plan_matrix(
    *,
    task: str,
    providers: list[str],
    models: list[str],
    prompts: list[str],
    sample: int = 10,
    seed: int = 42,
) -> list[dict[str, Any]]:
    from mailroom_sandbox.overlay import list_profiles

    # --providers takes PROFILE names, not serving families (DMR-048 G34):
    # 'vllm' is a family, 'vllm-local'/'modal-vllm' are profiles. A silent
    # family name used to plan cells that crashed at activate().
    known = set(list_profiles())
    unknown = [p for p in providers if p not in known]
    if unknown:
        raise ValueError(
            f"unknown provider profile(s) {unknown}; have {sorted(known)} — "
            "--providers takes profile names (e.g. vllm-local, modal-vllm), not families"
        )
    cells = []
    for provider in providers:
        profile = load_profile(provider)
        family = serving_family(profile)
        for model in models:
            mapped = map_model(model, family) if "/" in model else model
            for prompt in prompts:
                cells.append(
                    {
                        "task": task,
                        "provider": provider,
                        "model": mapped,
                        "prompt": prompt,
                        "sample": sample,
                        "seed": seed,
                        "experiment_name": cell_name(task, provider, mapped, prompt),
                    }
                )
    return cells


def run_matrix(
    *,
    task: str = "sorter",
    providers: list[str],
    models: list[str],
    prompts: list[str],
    sample: int = 10,
    seed: int = 42,
    mock: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    cells = plan_matrix(
        task=task,
        providers=providers,
        models=models,
        prompts=prompts,
        sample=sample,
        seed=seed,
    )
    if dry_run:
        return {"task": task, "cells": cells, "n": len(cells)}

    runner = {
        "sorter": runners.run_sorter_eval,
        "extract": runners.run_extract_eval,
        "chained": runners.run_chained_eval,
        "pipeline": runners.run_pipeline_eval,
        "legalbench": runners.run_legalbench_eval,
        "local_vs_api": runners.run_local_vs_api_eval,
    }.get(task)
    if runner is None:
        from mailroom_sandbox.eval.agents import SPECS

        if task in SPECS:
            def runner(**kwargs: Any) -> dict[str, Any]:
                return runners.run_isolated_eval(task, **kwargs)
        else:
            raise ValueError(f"Unknown matrix task {task!r}")

    results = []
    for cell in cells:
        kwargs: dict[str, Any] = {
            "mock": mock,
            "sample": sample,
            "experiment_name": cell["experiment_name"],
            "profile": cell["provider"],
            "model": cell["model"],
        }
        if task != "legalbench":
            kwargs["prompt_version"] = cell["prompt"]
        results.append(runner(**kwargs))
    payload: dict[str, Any] = {
        "task": task,
        "cells": cells,
        "results": results,
        "log": str(experiment_log.jsonl_path()),
    }
    records = []
    for result in results:
        rec = result.get("record") if isinstance(result, dict) else None
        if rec:
            records.append(rec)
        for nested in ("sorter", "extract"):
            inner = result.get(nested) if isinstance(result, dict) else None
            if isinstance(inner, dict) and inner.get("record"):
                records.append(inner["record"])
    if records:
        from mailroom_sandbox.eval import scoring

        compared = scoring.compare_from_records(records)
        if compared.get("comparison") is not None:
            payload["local_vs_api"] = compared
    return payload
