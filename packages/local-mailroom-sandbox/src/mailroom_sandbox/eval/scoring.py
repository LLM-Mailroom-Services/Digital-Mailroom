"""Deterministic scoring via llm-dojo-scoring + local JSONL score sink."""

from __future__ import annotations

import logging
import re
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
from llm_dojo_scoring.scorecard_honesty import ProvenanceExportError
from llm_dojo_scoring.serving import CANONICAL_SERVING_KEYS, pair_comparable_runs

from mailroom_sandbox.eval.extraction_scope import scope_extraction_pair
from mailroom_sandbox.eval.schema_adherence import (
    assess_extraction_payload,
    merge_schema_adherence,
)
from mailroom_sandbox.eval.serving_parity import split_serving_records, to_dojo_serving_record
from mailroom_sandbox.eval.cuad_scoring import score_cuad
from mailroom_sandbox.eval.maud_scoring import score_maud

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


def scores_path(run_id: str | None = None, *, metadata: Mapping[str, Any] | None = None) -> Path:
    from mailroom_sandbox.report_paths import experiment_prefix, report_folder

    prefix = report_folder(experiment_prefix(run_id, metadata))
    base = reports_dir() / "scores"
    dest = base / prefix / "scores.jsonl" if prefix else base / "scores.jsonl"
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


def emit(record: ScoreRecord, path: Path | None = None) -> None:
    LocalManifestSink(path or scores_path(record.run_id, metadata=record.metadata)).emit(record)


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
    raw_expected = expected  # MAUD/CUAD label maps may be scoped out below
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
    if doc_type == "merger_agreement" and raw_expected.get("maud_clause_labels"):
        # SAND-032: merger GT is MAUD question→answer labels only; the suite's
        # field map never meets it (F1 0 by construction). Headline = MAUD accuracy.
        maud = score_maud(predicted, raw_expected["maud_clause_labels"])
        payload.update(maud)
        payload["suite_overall_extraction_score"] = payload["overall_extraction_score"]
        payload["overall_extraction_score"] = maud["maud_accuracy"]
        payload["scoring_method"] = f"{scoring_method}+maud"
    if doc_type == "contract" and raw_expected.get("cuad_clause_labels"):
        # SAND-032: contract GT is CUAD clause spans only; headline = CUAD
        # category-detection F1 within the row's labeled universe.
        cuad = score_cuad(predicted, raw_expected["cuad_clause_labels"])
        payload.update(cuad)
        payload["suite_overall_extraction_score"] = payload["overall_extraction_score"]
        payload["overall_extraction_score"] = cuad["cuad_presence_f1"]
        payload["scoring_method"] = f"{scoring_method}+cuad"
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


_DERIVED_COMPARISON_TASKS = ("local_vs_api", "sorter_vs_modernbert")


def compare_from_records(
    records: Sequence[Mapping[str, Any]],
    *,
    group: str | int | None = None,
) -> dict[str, Any]:
    """Partition an experiment log and compare local (or Modal) vs API-key runs.

    Dojo ``split_local_api`` no longer folds ``modal-vllm`` into ``local``
    (#21); the sandbox splitter keeps its own Modal bucket (DMR-049) and a
    Modal↔API comparison still goes through ``get_suite("local_vs_api")`` after
    ``to_dojo_serving_record`` so Grant cost-compare logs work without a live
    GPU.

    Rows are grouped by FULL identity (serving kind, model, prompt, task,
    dataset fingerprint / revision, split, draw seed) before comparing, because
    the dojo marks a leg that pools runs differing on any of them
    ``identity_mixed`` and ``emit_serving_scorecard`` refuses it. A local-side
    leg is paired with an API-side leg only when they measured the same thing
    (:func:`mailroom_sandbox.serving_groups.pair_legs`), so a multi-model log
    yields one comparison per comparable pair — ``payload["groups"]`` — instead
    of one pooled, meaningless one.

    ``payload["comparison"]`` (and ``table`` / ``scorecard`` / ``cost`` /
    ``markdown``) are filled when exactly one pair exists or ``group``
    (1-based index or unique label substring) selects one; with several pairs
    and no ``group`` they stay ``None`` and ``note`` lists the choices.
    Legs that found no counterpart are listed under ``unpaired``.
    """
    from mailroom_sandbox.serving_groups import group_legs, pair_legs, select_pair

    # `sandbox eval local_vs_api` / `sorter_vs_modernbert` log their own
    # comparison output as a record; that is a derived result, not a serving
    # run, and would only appear as an unpaired leg on the next --from-log.
    derived = [r for r in records if r.get("task") in _DERIVED_COMPARISON_TASKS]
    rows = [
        to_dojo_serving_record(r) for r in records if r.get("task") not in _DERIVED_COMPARISON_TASKS
    ]
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
        "derived_skipped_n": len(derived),
        "pairs": [],
        "groups": [],
        "unpaired": [],
        "selected_group": None,
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
            "identity.serving_kind is 'modal' (no modal→local remap, dojo #21)."
        )
    if not left or not api:
        payload["note"] = (
            "Need API-key (OpenRouter) records plus local (Ollama/vLLM/"
            "llama.cpp/LM Studio) or Modal (modal-vllm) records. Offline "
            "fixtures work without OPENROUTER_API_KEY."
        )
        return payload
    # pair_comparable_runs pairs single runs (record-level); the group pairs
    # below are the leg-level comparisons.
    pairs = pair_comparable_runs(rows)
    suite = get_suite("local_vs_api")
    payload["pairs"] = [suite.score(a, b) for a, b in pairs]

    bucket_of = lambda rec: str(rec.get("serving_kind") or "unknown")  # noqa: E731
    left_legs = group_legs(left, bucket_of)
    api_legs = group_legs(api, bucket_of)
    leg_pairs, lone_left, lone_api = pair_legs(left_legs, api_legs)
    payload["left_serving"] = left_label
    for idx, pair in enumerate(leg_pairs, start=1):
        comparison = suite.score(pair.left.rows, pair.right.rows)
        payload["groups"].append(
            {
                "group": idx,
                "label": pair.label,
                "left_serving": left_label,
                "key": pair.key,
                "local_identity": pair.left.identity,
                "api_identity": pair.right.identity,
                "local_n": len(pair.left.rows),
                "api_n": len(pair.right.rows),
                "comparison": comparison,
                "incomparable_reason": comparison.get("incomparable_reason"),
            }
        )
    for side, legs in ((left_label, lone_left), ("api", lone_api)):
        for leg in legs:
            payload["unpaired"].append(
                {
                    "side": side,
                    "label": leg.label,
                    "identity": leg.identity,
                    "n": len(leg.rows),
                    "reason": (
                        "no opposite-side leg measured the same task / prompt / "
                        "dataset fingerprint / revision / split / draw seed"
                    ),
                }
            )
    if not leg_pairs:
        payload["note"] = (
            f"{len(left_legs)} {left_label} leg(s) and {len(api_legs)} API leg(s) found, "
            "but none measured the same task / prompt / dataset (fingerprint, "
            "revision, split, draw seed) — nothing comparable. See `unpaired`."
        )
        return payload

    chosen = None
    if group is not None:
        chosen = select_pair(leg_pairs, group)
    elif len(leg_pairs) == 1:
        chosen = leg_pairs[0]
    else:
        choices = "; ".join(f"{g['group']}: {g['label']}" for g in payload["groups"])
        payload["note"] = (
            f"{len(leg_pairs)} comparable groups (one comparison each in `groups`); "
            f"pass group=<n|label> (CLI: --group) to pick one for the headline. {choices}"
        )
    if chosen is not None:
        idx = leg_pairs.index(chosen) + 1
        comparison = payload["groups"][idx - 1]["comparison"]
        payload["selected_group"] = idx
        payload["comparison"] = comparison
        payload["table"] = comparison.get("table") or []
        payload["scorecard"] = comparison.get("scorecard")
        payload["cost"] = comparison.get("cost")
        payload["markdown"] = comparison.get("markdown")
    elif payload["groups"]:
        payload["markdown"] = "\n\n".join(
            f"### Group {g['group']}: {g['label']}\n\n{g['comparison'].get('markdown') or ''}".rstrip()
            for g in payload["groups"]
        )
    return payload


class ScorecardEmissionError(ProvenanceExportError):
    """A scorecard cannot be emitted with honest provenance — never downgraded.

    A :class:`~llm_dojo_scoring.scorecard_honesty.ProvenanceExportError` (so
    ``except ProvenanceExportError`` still catches it) that carries the sandbox
    hint: ``field`` is the missing/contradicted provenance key, ``group`` the
    comparison group it was raised for, ``hint`` how to supply it. :meth:`one_line`
    is the single-line CLI reason.
    """

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        group: str | int | None = None,
        hint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.field = field
        self.group = group
        self.hint = hint

    def one_line(self) -> str:
        return " ".join(str(self).split())


_REVISION_HINT = (
    "pin a Hub revision (run through a job spec whose dataset pins a 40-hex "
    "`revision`, e.g. job.spec.FAMILY_HF_REVISION) or pass `--dataset-revision "
    "<40-hex Hub sha>` with the real revision the run scored; it is never derived "
    "from the dataset fingerprint"
)


_FULL_SHA = re.compile(r"[0-9a-f]{40}")


def validate_dataset_revision(value: str) -> str:
    """A caller-supplied ``dataset_revision`` must be a full 40-hex Hub sha.

    A branch name (``main``) moves and a short sha is ambiguous; neither is a
    revision a scorecard can honestly claim, so both raise.
    """
    rev = str(value or "").strip().lower()
    if not _FULL_SHA.fullmatch(rev):
        raise ScorecardEmissionError(
            f"dataset_revision {value!r} is not a full 40-hex Hub commit sha; "
            "resolve the branch/tag to the commit the rows were scored from",
            field="dataset_revision",
            hint=_REVISION_HINT,
        )
    return rev


class _CollectSink:
    """In-memory sink: validates a whole emission before anything is written."""

    def __init__(self) -> None:
        self.records: list[Any] = []

    def emit(self, record: Any) -> None:
        self.records.append(record)

    def flush(self) -> None:
        return None


def _leg_revisions(comparison: Mapping[str, Any]) -> dict[str, str]:
    ident = ((comparison.get("scorecard") or {}).get("identity")) or {}
    return {
        side: str((ident.get(side) or {}).get("dataset_revision") or "")
        for side in ("local", "api")
    }


def _check_override_agrees(
    comparison: Mapping[str, Any], provenance: Mapping[str, Mapping[str, Any]] | None
) -> None:
    """A caller-supplied revision may fill a gap, never contradict the records."""
    recorded = _leg_revisions(comparison)
    for side, stamp in (provenance or {}).items():
        claimed = str((stamp or {}).get("dataset_revision") or "")
        have = recorded.get(side) or ""
        if claimed and have and claimed != have:
            raise ScorecardEmissionError(
                f"{side} leg records dataset_revision {have[:12]} but the supplied "
                f"provenance claims {claimed[:12]}; refusing to restamp a scorecard "
                "with a different revision than the run scored",
                field="dataset_revision",
            )


def emit_local_vs_api_scorecard(
    comparison: Mapping[str, Any],
    *,
    run_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    provenance: Mapping[str, Mapping[str, Any]] | None = None,
    emitter: Emitter | None = None,
) -> dict[str, Any]:
    """Persist local and API T0/T1 as separate scorecards (never averaged).

    The dojo (v0.22) refuses to emit a metric without a provenance stamp
    (``dataset_revision``, ``prompt_id``, ``serving_kind``, ``model_id``) and
    refuses an ``identity_mixed`` leg; that refusal is RAISED
    (:class:`ScorecardEmissionError`, a ``ProvenanceExportError``) — nothing is
    written and nothing is downgraded to a report entry. ``provenance`` is the
    optional ``{"local": {...}, "api": {...}}`` override; keys it leaves out
    come from the leg's own records, which is why serving records carry
    ``dataset_revision`` (and ``split`` / ``draw_seed`` where known — see
    ``job.metrics.lock_dataset_provenance``). ``dataset_revision`` is never
    derived from the dataset fingerprint, and an override may fill a gap but
    never contradict a revision the records already carry.
    """
    _check_override_agrees(comparison, provenance)
    em = emitter or Emitter(sinks=[LocalManifestSink(scores_path(run_id, metadata=metadata))])
    try:
        return emit_serving_scorecard(
            comparison, run_id=run_id, emitter=em, provenance=provenance
        )
    except ScorecardEmissionError:
        raise
    except ProvenanceExportError as exc:
        field = "dataset_revision" if "dataset_revision" in str(exc) else None
        hint = _REVISION_HINT if field else None
        raise ScorecardEmissionError(
            f"{exc}" + (f" [sandbox: {hint}]" if hint else ""),
            field=field,
            hint=hint,
        ) from exc


def emit_group_scorecards(
    compared: Mapping[str, Any],
    *,
    run_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    provenance: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Emit one scorecard per comparable group of :func:`compare_from_records`.

    One group keeps ``run_id`` unchanged (back-compatible); several get
    ``<run_id>.g<n>`` so their rows never collide. Every group is validated
    against an in-memory sink BEFORE any is written, and a group that cannot be
    emitted with honest provenance — missing ``dataset_revision``, an
    incomparable (``identity_mixed``) leg — RAISES
    :class:`ScorecardEmissionError` naming the group. There is no "refused"
    entry, no skip and no fabricated stamp: the call either writes every
    group's scorecard or none.
    """
    groups = list(compared.get("groups") or [])
    plan: list[tuple[dict[str, Any], Mapping[str, Any], str | None]] = []
    for entry in groups:
        comparison = entry.get("comparison") or {}
        gid = f"{run_id}.g{entry['group']}" if run_id and len(groups) > 1 else run_id
        label = f"group {entry['group']} ({entry['label']})"
        if comparison.get("incomparable"):
            raise ScorecardEmissionError(
                f"local_vs_api {label}: cannot emit a scorecard for an incomparable "
                f"comparison ({comparison.get('incomparable_reason')}); fix the "
                "records so the legs measure the same thing, or drop the group",
                field=str(comparison.get("incomparable_reason") or "identity"),
                group=entry["group"],
            )
        plan.append(({"group": entry["group"], "label": entry["label"], "run_id": gid}, comparison, gid))

    def _emit(comparison: Mapping[str, Any], gid: str | None, entry: Mapping[str, Any], em: Emitter | None) -> None:
        try:
            emit_local_vs_api_scorecard(
                comparison, run_id=gid, metadata=metadata, provenance=provenance, emitter=em
            )
        except ScorecardEmissionError as exc:
            label = f"group {entry['group']} ({entry['label']})"
            raise ScorecardEmissionError(
                f"local_vs_api {label}: scorecard not emitted: {exc}",
                field=exc.field,
                group=entry["group"],
                hint=exc.hint,
            ) from exc

    # Validate every group first so a late failure cannot leave a partial manifest.
    for entry, comparison, gid in plan:
        _emit(comparison, gid, entry, Emitter(sinks=[_CollectSink()]))
    results: list[dict[str, Any]] = []
    for entry, comparison, gid in plan:
        _emit(comparison, gid, entry, None)
        results.append({**entry, "emitted": True})
    return results


def score_one_serving_run(record: Mapping[str, Any]) -> dict[str, Any]:
    return score_serving_run(record)


def canonical_serving_keys() -> tuple[str, ...]:
    return CANONICAL_SERVING_KEYS
