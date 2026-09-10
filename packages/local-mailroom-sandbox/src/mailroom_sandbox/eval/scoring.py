"""Deterministic scoring via llm-dojo-scoring + local JSONL score sink."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from llm_dojo_scoring import (
    Emitter,
    LocalManifestSink,
    ScoreRecord,
    accuracy,
    bootstrap_ci,
    classify_serving_kind,
    emit_serving_scorecard,
    exact_match,
    get_suite,
    headline_metrics,
    score_extraction,
    score_serving_run,
    score_task,
    split_local_api,
    suite_for_doc_type,
)
from llm_dojo_scoring.extraction_metrics import extraction_binary_metrics
from llm_dojo_scoring.serving import CANONICAL_SERVING_KEYS, pair_comparable_runs

from mailroom_sandbox.paths import reports_dir

# Sorter T0 stays accuracy + f1_macro; serving T0 is local_vs_api only.
_CLASS_MACRO_KEYS = ("f1_macro", "precision_macro", "recall_macro", "f2_macro")
_EXTRACT_PRF_KEYS = (
    "extraction_precision",
    "extraction_recall",
    "extraction_f1",
    "extraction_f2",
    "entity_list_f1",
)


def scores_path() -> Path:
    dest = reports_dir() / "scores" / "scores.jsonl"
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


def emit(record: ScoreRecord, path: Path | None = None) -> None:
    LocalManifestSink(path or scores_path()).emit(record)


def score_classification(expected: list[str], predicted: list[str]) -> dict[str, Any]:
    """Doc-class scores from the importable sorter suite (v0.10+ macros)."""
    acc = accuracy(expected, predicted)
    matches = [exact_match(p, e) for p, e in zip(predicted, expected)]
    ci = bootstrap_ci(matches) if matches else {}
    task = get_suite("sorter").score(expected, predicted)
    if not isinstance(task, dict):
        task = score_task("docclass", expected, predicted)
    payload: dict[str, Any] = {
        "exact_match": acc,
        "accuracy": task.get("accuracy", acc),
        "exact_match_ci": ci,
        "n": len(expected),
        "task": task,
    }
    for key in _CLASS_MACRO_KEYS:
        if key in task:
            payload[key] = task[key]
    return payload


def score_extraction_row(
    doc_type: str,
    predicted: dict,
    expected: dict,
    doc_text: str | None = None,
) -> dict[str, Any]:
    try:
        suite = suite_for_doc_type(doc_type)
        field_types = getattr(suite, "field_types", None) or {}
    except Exception:
        field_types = {}
        suite = None
    predicted = predicted or {}
    expected = expected or {}
    if suite is not None:
        try:
            result = suite.score(expected, predicted, doc_text=doc_text)
        except Exception:
            result = score_extraction(
                doc_type, field_types, predicted, expected, doc_text=doc_text
            )
    else:
        result = score_extraction(
            doc_type, field_types, predicted, expected, doc_text=doc_text
        )
    overall = getattr(result, "overall_score", None)
    if overall is None and isinstance(result, dict):
        overall = result.get("overall_score")
        if overall is None:
            overall = result.get("extraction_overall_score")
    payload: dict[str, Any] = {"overall_extraction_score": overall, "doc_type": doc_type}
    if hasattr(result, "__dict__"):
        payload["fields"] = {
            k: v for k, v in vars(result).items() if k != "field_scores" and not k.startswith("_")
        }
        try:
            prf = extraction_binary_metrics(
                expected,
                predicted,
                field_map=field_types,
                doc_class=doc_type,
                result=result,
                doc_text=doc_text,
            )
        except Exception:
            prf = {}
        for key in _EXTRACT_PRF_KEYS:
            if key in prf and prf[key] is not None:
                payload[key] = prf[key]
    elif isinstance(result, dict):
        for key in _EXTRACT_PRF_KEYS:
            if key in result:
                payload[key] = result[key]
    return payload


def score_legalbench(expected: list[str], predicted: list[str]) -> dict[str, Any]:
    result = score_task("legalbench", expected, predicted)
    if not isinstance(result, dict):
        result = {"result": result}
    result.setdefault("exact_match", accuracy(expected, predicted))
    return result


def score_stage(expected: list[str], predicted: list[str]) -> dict[str, Any]:
    acc = accuracy(expected, predicted)
    matches = [exact_match(p, e) for p, e in zip(predicted, expected)]
    return {
        "stage_correct": acc,
        "stage_correct_ci": bootstrap_ci(matches) if matches else {},
        "n": len(expected),
    }


def mean_or_zero(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def serving_headlines() -> list[str]:
    return list(headline_metrics("local_vs_api"))


def attach_serving_identity(record: dict[str, Any]) -> dict[str, Any]:
    """Stamp ``serving_kind`` from provider/profile. Do not invent timings.

    The dojo classifier has no ``modal`` category and maps the ``modal-vllm``
    profile to ``local`` — the sandbox's own bucket table is authoritative for
    its records (DMR-049 G), so a Modal run never lands in the local bucket.
    """
    if "serving_kind" not in record:
        record["serving_kind"] = _sandbox_serving_kind(record) or classify_serving_kind(record)
    return record


_SANDBOX_MODAL_PROFILES = ("modal-vllm",)
_SANDBOX_LOCAL_PROFILES = ("ollama", "vllm-local", "vllm-remote", "llamacpp", "lmstudio")
_SANDBOX_API_PROFILES = ("openrouter",)


def _sandbox_serving_kind(record: Mapping[str, Any]) -> str | None:
    """The sandbox bucket for a record, or None when it is not sandbox-scoped."""
    profile = str(record.get("profile") or "")
    provider = str(record.get("provider") or "").lower()
    if profile in _SANDBOX_MODAL_PROFILES or "modal" in profile:
        return "modal"
    if profile in _SANDBOX_API_PROFILES or provider == "openrouter":
        return "api"
    if profile in _SANDBOX_LOCAL_PROFILES or provider in {
        "vllm",
        "ollama",
        "llamacpp",
        "lmstudio",
        "generic",
    }:
        return "local"
    return None


def serving_record(
    *,
    provider: str | None,
    profile: str | None = None,
    model: str | None = None,
    prompt_version: str | None = None,
    task: str | None = None,
    dataset_fingerprint: str | None = None,
    scores: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a dojo-comparable serving record. Missing timings stay omitted."""
    rec: dict[str, Any] = {
        "provider": provider,
        "profile": profile or provider,
        "model": model,
        "prompt_version": prompt_version,
        "task": task,
        "dataset_fingerprint": dataset_fingerprint,
    }
    if scores:
        rec["scores"] = dict(scores)
    if extra:
        for key, value in extra.items():
            if value is not None:
                rec[key] = value
    rec = {k: v for k, v in rec.items() if v is not None}
    return attach_serving_identity(rec)


def compare_local_vs_api(
    local: Mapping[str, Any] | Sequence[Any],
    api: Mapping[str, Any] | Sequence[Any],
    *,
    quality_metric: str | None = None,
) -> dict[str, Any]:
    """Importable ``get_suite('local_vs_api')`` comparison (no API key required)."""
    kwargs: dict[str, Any] = {}
    if quality_metric:
        kwargs["quality_metric"] = quality_metric
    return get_suite("local_vs_api").score(local, api, **kwargs)


def compare_from_records(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Partition an experiment log and compare local vs API-key runs."""
    rows = list(records)
    local, api, unknown = split_local_api(rows)
    payload: dict[str, Any] = {
        "local_n": len(local),
        "api_n": len(api),
        "unknown_n": len(unknown),
        "pairs": [],
        "comparison": None,
        "headlines": serving_headlines(),
        "table": [],
        "scorecard": None,
        "cost": None,
        "markdown": None,
    }
    if not local or not api:
        payload["note"] = (
            "Need both local (Ollama/vLLM/llama.cpp/LM Studio) and API-key "
            "(OpenRouter) records. Offline fixtures work without OPENROUTER_API_KEY."
        )
        return payload
    pairs = pair_comparable_runs(rows)
    suite = get_suite("local_vs_api")
    payload["pairs"] = [suite.score(left, right) for left, right in pairs]
    comparison = suite.score(local, api)
    payload["comparison"] = comparison
    payload["table"] = comparison.get("table") or []
    payload["scorecard"] = comparison.get("scorecard")
    payload["cost"] = comparison.get("cost")
    payload["markdown"] = comparison.get("markdown")
    return payload


def emit_local_vs_api_scorecard(
    comparison: Mapping[str, Any],
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Persist local and API T0/T1 as separate scorecards (never averaged)."""
    em = Emitter(sinks=[LocalManifestSink(scores_path())])
    return emit_serving_scorecard(comparison, run_id=run_id, emitter=em)


def score_one_serving_run(record: Mapping[str, Any]) -> dict[str, Any]:
    return score_serving_run(record)


def canonical_serving_keys() -> tuple[str, ...]:
    return CANONICAL_SERVING_KEYS
