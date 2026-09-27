"""Deterministic scoring via llm-dojo-scoring + local JSONL score sink."""

from __future__ import annotations

import logging
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
    suite_for_doc_type,
)
from llm_dojo_scoring.extraction_metrics import extraction_binary_metrics
from llm_dojo_scoring.serving import CANONICAL_SERVING_KEYS, pair_comparable_runs

from mailroom_sandbox.eval.extraction_scope import scope_extraction_pair
from mailroom_sandbox.eval.schema_adherence import (
    assess_extraction_payload,
    merge_schema_adherence,
)
from mailroom_sandbox.eval.serving_parity import split_serving_records, to_dojo_serving_record

from mailroom_sandbox.paths import reports_dir

_log = logging.getLogger("mailroom_sandbox.eval.scoring")

_SCORING_WARNED: set[str] = set()


def _warn_once(key: str, message: str, exc: BaseException | None = None) -> None:
    if key not in _SCORING_WARNED:
        _SCORING_WARNED.add(key)
        _log.warning("%s", message, exc_info=exc)

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
    task_source = "sorter-suite"
    if not isinstance(task, dict):
        task_source = "score_task-docclass"
        _warn_once(
            "sorter-suite-non-dict",
            "get_suite('sorter').score returned a non-dict — fell back to "
            "score_task('docclass'); macro fields (f1/recall/precision) may be "
            "absent from the payload for this run",
        )
        task = score_task("docclass", expected, predicted)
    payload: dict[str, Any] = {
        "exact_match": acc,
        "accuracy": task.get("accuracy", acc),
        "exact_match_ci": ci,
        "n": len(expected),
        "task": task,
        "task_source": task_source,
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
    scoring_method = "suite"
    try:
        suite = suite_for_doc_type(doc_type)
        field_types = getattr(suite, "field_types", None) or {}
    except Exception as exc:
        scoring_method = "generic"
        _warn_once(
            f"suite-unavailable-{doc_type}",
            f"suite_for_doc_type({doc_type!r}) failed — scoring switched to the "
            "GENERIC extraction path; a suite-side defect would hide as a "
            "different score on this doc type",
            exc,
        )
        field_types = {}
        suite = None
    predicted = predicted or {}
    expected = expected or {}
    predicted, expected = scope_extraction_pair(doc_type, predicted, expected)
    if suite is not None:
        try:
            result = suite.score(expected, predicted, doc_text=doc_text)
        except Exception as exc:
            scoring_method = "suite-fallback-generic"
            _warn_once(
                f"suite-score-failed-{doc_type}",
                f"suite.score({doc_type!r}) RAISED — fell back to generic "
                "score_extraction; record carries scoring_method="
                "'suite-fallback-generic' so the methodology swap is visible",
                exc,
            )
            result = score_extraction(
                doc_type, field_types, predicted, expected, doc_text=doc_text
            )
    else:
        result = score_extraction(
            doc_type, field_types, predicted, expected, doc_text=doc_text
        )
    overall = getattr(result, "overall_score", None)
    if overall is None and isinstance(result, dict):
        # SAND-019: the mailroom suites return a FLAT dict whose real aggregate is
        # nested at ``result["extraction"].overall_score`` (an
        # ExtractionScoreResult). Reading only top-level ``overall_score``/
        # ``extraction_overall_score`` left every correspondence row null even
        # with ground truth present — extraction_f1 was computed but the headline
        # score was not.
        overall = result.get("overall_score")
        if overall is None:
            overall = result.get("extraction_overall_score")
        if overall is None:
            nested = result.get("extraction")
            overall = getattr(nested, "overall_score", None)
            if overall is None and isinstance(nested, dict):
                overall = nested.get("overall_score")
    payload: dict[str, Any] = {
        "overall_extraction_score": overall,
        "doc_type": doc_type,
        "scoring_method": scoring_method,
    }
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
        except Exception as exc:
            _warn_once(
                f"prf-failed-{doc_type}",
                f"extraction_binary_metrics({doc_type!r}) failed — extraction "
                "PRF fields are DROPPED from the payload for this row",
                exc,
            )
            prf = {}
        for key in _EXTRACT_PRF_KEYS:
            if key in prf and prf[key] is not None:
                payload[key] = prf[key]
    elif isinstance(result, dict):
        for key in _EXTRACT_PRF_KEYS:
            if key in result:
                payload[key] = result[key]
    payload.update(assess_extraction_payload(predicted, doc_type))
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


def aggregate_schema_adherence(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Run-level parse/schema rates from per-row ``score_extraction_row`` dicts."""
    return merge_schema_adherence(rows)


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
    """Partition an experiment log and compare local (or Modal) vs API-key runs.

    Dojo ``split_local_api`` folds ``modal-vllm`` into ``local``. The sandbox
    splitter keeps a Modal bucket (DMR-049) and still scores Modal↔API through
    ``get_suite("local_vs_api")`` after ``to_dojo_serving_record`` so Grant
    cost-compare logs work without a live GPU.
    """
    rows = [to_dojo_serving_record(r) for r in records]
    buckets = split_serving_records(rows)
    local = buckets["local"]
    modal = buckets["modal"]
    api = buckets["api"]
    unknown = buckets["unknown"]
    payload: dict[str, Any] = {
        "local_n": len(local),
        "modal_n": len(modal),
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
    left = local
    left_label = "local"
    if not left and modal and api:
        left = modal
        left_label = "modal"
        payload["note"] = (
            "Compared Modal vs API via get_suite('local_vs_api'); dojo "
            "identity.serving_kind remaps modal→local (sandbox keeps modal)."
        )
    if not left or not api:
        payload["note"] = (
            "Need API-key (OpenRouter) records plus local (Ollama/vLLM/"
            "llama.cpp/LM Studio) or Modal (modal-vllm) records. Offline "
            "fixtures work without OPENROUTER_API_KEY."
        )
        return payload
    # pair_comparable_runs still uses dojo split (modal counts as local there).
    pairs = pair_comparable_runs(rows)
    suite = get_suite("local_vs_api")
    payload["pairs"] = [suite.score(a, b) for a, b in pairs]
    comparison = suite.score(left, api)
    payload["left_serving"] = left_label
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
