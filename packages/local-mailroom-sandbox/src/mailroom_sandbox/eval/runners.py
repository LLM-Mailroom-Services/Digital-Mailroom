"""Eval runners: sorter / extract / chained / pipeline / legalbench."""

from __future__ import annotations

import json
import os
from contextlib import ExitStack
from pathlib import Path
from typing import Any
from unittest.mock import patch

from mailroom_sandbox.datasets import (
    LEGALBENCH_TASKS,
    dataset_fingerprint,
    fixture_file,
    load_hf_fixtures,
    load_legalbench_fixtures,
    load_legalbench_suite_rows,
    load_manifest,
    parse_expected_fields,
)
from mailroom_sandbox.eval import experiment_log, scoring, tracing
from mailroom_sandbox.eval.scoring import emit
from mailroom_sandbox.mock_llm import fake_client, fake_structured_payload
from mailroom_sandbox.runtime import activate, resolve_mailroom_src

try:
    from llm_dojo_scoring.emitter import ScoreRecord
except Exception:  # pragma: no cover
    ScoreRecord = None  # type: ignore


def _expect_from_row(row: dict[str, Any]) -> dict[str, Any]:
    doc_type = row.get("expected_doc_class") or row.get("doc_type") or "contract"
    conf = 0.40 if row.get("id") == "ambiguous_01" else 0.97
    return {
        "id": row.get("id"),
        "doc_type": doc_type,
        "expected_doc_class": doc_type,
        "conf": conf,
        "expected_fields": parse_expected_fields(row) if "expected_fields" in row else row.get("expected_fields"),
        "legalbench_answer": row.get("answer"),
    }


def _classify_mock(row: dict[str, Any]) -> str:
    return str(row.get("expected_doc_class") or row.get("doc_type") or "unknown")


def _predict_spec(spec, row: dict[str, Any], *, mock: bool) -> tuple[dict[str, Any], bool]:
    """Predict one row; ``fell_back`` is True only when NO live fn exists.

    Live-or-loud (DMR-044): a live-configured eval never degrades to the mock
    predictor on error — the exception propagates and the caller records it as
    an item error instead of silently scoring a mock prediction.
    """
    if mock:
        return spec.mock_predict(row), False
    if spec.live_predict is None:
        return spec.mock_predict(row), True
    return spec.live_predict(row), False


def run_isolated_eval(
    task: str,
    *,
    mock: bool = True,
    sample: int | None = None,
    dry_run: bool = False,
    experiment_name: str | None = None,
    prompt_version: str | None = None,
    profile: str | None = None,
    model: str | None = None,
    agent_models: dict[str, str] | None = None,
    connected: bool = False,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run one live agent / node against fixtures, nested under document-pipeline.

    ``rows`` (DMR-056): when the caller passes the locked live dataset rows
    (the ``sandbox run`` whole-run path), score THOSE rows; otherwise fall
    back to the agent's committed fixture rows.
    """
    from mailroom_sandbox.eval.agents import spec_for

    spec = spec_for(task)
    rows = spec.load_rows() if rows is None else rows
    if sample:
        rows = rows[: sample]
    plan = {
        "task": task,
        "n": len(rows),
        "mock": mock,
        "prompt_version": prompt_version,
        "profile": profile,
        "model": model,
        "observation": spec.observation,
        "observation_type": tracing.observation_type_for(spec.observation),
        "fingerprint": dataset_fingerprint(rows) if rows else "",
        "connected": False,
    }
    if dry_run:
        return plan

    os.environ["SANDBOX_RUN_MODE"] = "mock" if mock else "local"
    activation = activate(
        profile, model=model, prompt_variant=prompt_version, agent_models=agent_models
    )
    session = tracing.session_id_for(task)
    matches: list[float] = []
    per_row: list[dict[str, Any]] = []
    offline = 0
    errors = 0
    for row in rows:
        seed = str(row.get("id") or row.get("filename") or task)
        error: str | None = None
        pred: dict[str, Any] = {}
        scored: dict[str, Any] = {}
        fell_back = False
        try:
            with tracing.document_pipeline_trace(
                seed=seed,
                session_id=session,
                input={"filename": row.get("filename") or row.get("id"), "matter_id": f"SANDBOX-{row.get('id')}"},
                metadata={"pipeline": "mailroom", "source": "sandbox-fixtures", "run_id": experiment_name, "attempt": 1},
                tags=tracing.default_tags("source-fixtures", f"agent-{task}"),
            ):
                with tracing.child_observation(
                    spec.observation,
                    as_type=tracing.observation_type_for(spec.observation),
                    input=tracing.public_ground_truth(row),
                ):
                    pred, fell_back = _predict_spec(spec, row, mock=mock)
                scored = spec.score_one(row, pred)
        except Exception as exc:  # noqa: BLE001 — recorded as an item error, never a silent mock
            error = f"{type(exc).__name__}: {str(exc)[:300]}"
            errors += 1
        if fell_back:
            offline += 1
        match = scored.get("match")
        if match is None and "overall_extraction_score" in scored:
            match = scored.get("overall_extraction_score") or 0.0
        if isinstance(match, (int, float)):
            matches.append(float(match))
        per_row.append(
            {"id": row.get("id"), "pred": pred, "score": scored, "offline_fallback": fell_back, "error": error}
        )
    if rows and errors == len(rows):
        raise RuntimeError(
            f"live eval {task!r}: all {len(rows)} row(s) failed — the live path was not "
            f"exercised (last error: {per_row[-1].get('error')})"
        )
    mean = scoring.mean_or_zero(matches)
    scores = {"exact_match": mean, "n": len(rows), "offline_fallback": offline, "error_count": errors}
    if per_row and "overall_extraction_score" in (per_row[0].get("score") or {}):
        scores["overall_extraction_score"] = mean
    tracing.emit_langfuse_score("class_correct" if spec.observation == "classify-document" else "stage_completed", mean)
    tracing.flush_traces()
    if ScoreRecord is not None:
        emit(
            ScoreRecord(
                metric="exact_match",
                value=float(mean),
                agent=task,
                run_id=experiment_name,
            )
        )
    record = experiment_log.new_record(
        experiment_name=experiment_name or f"sandbox_{task}",
        task=task,
        profile=activation.profile_name,
        provider=os.environ.get("DEFAULT_PROVIDER"),
        model=model or (activation.assignments[0][2] if activation.assignments else None),
        prompt_version=prompt_version or "mailroom-default",
        mock=mock,
        dataset_fingerprint=plan["fingerprint"],
        n=len(rows),
        scores=scores,
        tracing_backend=tracing.tracing_backend(),
        tags=tracing.default_tags("source-fixtures", f"agent-{task}"),
        session_id=session,
        trace_ids=tracing.last_trace_ids(),
    )
    experiment_log.append(record)
    return {**plan, "scores": scores, "record": record, "rows": per_row}


def run_sorter_eval(
    *,
    mock: bool = True,
    sample: int | None = None,
    dry_run: bool = False,
    experiment_name: str | None = None,
    prompt_version: str | None = None,
    profile: str | None = None,
    model: str | None = None,
    agent_models: dict[str, str] | None = None,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = load_manifest() if rows is None else rows
    if sample:
        rows = rows[: sample]
    plan = {
        "task": "sorter",
        "n": len(rows),
        "mock": mock,
        "prompt_version": prompt_version,
        "profile": profile,
        "model": model,
        "fingerprint": dataset_fingerprint(rows),
    }
    if dry_run:
        return plan

    activation = activate(profile, model=model, prompt_variant=prompt_version, agent_models=agent_models)
    predicted: list[str] = []
    expected: list[str] = []
    for row in rows:
        expected.append(row["expected_doc_class"])
        if mock:
            predicted.append(_classify_mock(row))
        else:
            predicted.append(_run_pipeline_doc(row, mock=False).get("doc_type") or "unknown")

    scores = scoring.score_classification(expected, predicted)
    if ScoreRecord is not None:
        emit(
            ScoreRecord(
                metric="exact_match",
                value=float(scores["exact_match"] or 0),
                agent="sorter",
                run_id=experiment_name,
            )
        )
        f1 = scores.get("f1_macro")
        if isinstance(f1, (int, float)):
            emit(
                ScoreRecord(
                    metric="f1_macro",
                    value=float(f1),
                    agent="sorter",
                    run_id=experiment_name,
                )
            )
    record = experiment_log.new_record(
        experiment_name=experiment_name or "sandbox_sorter",
        task="sorter",
        profile=activation.profile_name,
        provider=os.environ.get("DEFAULT_PROVIDER"),
        model=model or (activation.assignments[0][2] if activation.assignments else None),
        prompt_version=prompt_version or "mailroom-default",
        mock=mock,
        dataset_fingerprint=plan["fingerprint"],
        n=len(rows),
        scores=scores,
        tracing_backend=tracing.tracing_backend(),
        tags=tracing.default_tags("source-fixtures"),
    )
    experiment_log.append(record)
    return {**plan, "scores": scores, "record": record}


def run_extract_eval(
    *,
    mock: bool = True,
    sample: int | None = None,
    dry_run: bool = False,
    experiment_name: str | None = None,
    profile: str | None = None,
    model: str | None = None,
    prompt_version: str | None = None,
    agent_models: dict[str, str] | None = None,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = [r for r in (load_manifest() if rows is None else rows) if parse_expected_fields(r)]
    if sample:
        rows = rows[: sample]
    plan = {"task": "extract", "n": len(rows), "mock": mock, "fingerprint": dataset_fingerprint(rows)}
    if dry_run:
        return plan
    activation = activate(profile, model=model, prompt_variant=prompt_version, agent_models=agent_models)
    overall: list[float] = []
    for row in rows:
        expected_fields = parse_expected_fields(row) or {}
        if mock:
            predicted_fields = dict(expected_fields)
        else:
            predicted_fields = _run_pipeline_doc(row, mock=False).get("extracted_data") or {}
        scored = scoring.score_extraction_row(
            row["expected_doc_class"],
            predicted_fields,
            expected_fields,
            # DMR-056: live corpus rows carry doc_text inline (no fixture file).
            doc_text=row.get("doc_text")
            or (fixture_file(row).read_text(encoding="utf-8") if fixture_file(row).is_file() else None),
        )
        value = scored.get("overall_extraction_score")
        if isinstance(value, (int, float)):
            overall.append(float(value))
    mean = sum(overall) / len(overall) if overall else 0.0
    scores = {"overall_extraction_score": mean, "n": len(rows)}
    record = experiment_log.new_record(
        experiment_name=experiment_name or "sandbox_extract",
        task="extract",
        profile=activation.profile_name,
        provider=os.environ.get("DEFAULT_PROVIDER"),
        model=model,
        prompt_version=prompt_version or "mailroom-default",
        mock=mock,
        dataset_fingerprint=plan["fingerprint"],
        scores=scores,
        tracing_backend=tracing.tracing_backend(),
        tags=tracing.default_tags("source-fixtures"),
    )
    experiment_log.append(record)
    return {**plan, "scores": scores}


def run_chained_eval(**kwargs: Any) -> dict[str, Any]:
    if kwargs.get("dry_run"):
        return {"task": "chained", "dry_run": True, "sorter": run_sorter_eval(**kwargs)}
    sorter = run_sorter_eval(**kwargs)
    extract_kwargs = {k: v for k, v in kwargs.items() if k != "experiment_name"}
    extract = run_extract_eval(**extract_kwargs)
    composite = 0.25 * float(sorter.get("scores", {}).get("exact_match") or 0) + 0.75 * float(
        extract.get("scores", {}).get("overall_extraction_score") or 0
    )
    scores = {
        "sorter_exact": sorter.get("scores", {}).get("exact_match"),
        "extractor_overall": extract.get("scores", {}).get("overall_extraction_score"),
        "chained_composite": composite,
    }
    return {"task": "chained", "scores": scores, "sorter": sorter, "extract": extract}


def _seeded_sample(rows: list[dict[str, Any]], sample: int, seed: int) -> list[dict[str, Any]]:
    """Deterministic seeded sample over a canonical sort (never first-N)."""
    import random

    ordered = sorted(rows, key=lambda r: str(r.get("id") or r.get("filename") or ""))
    if sample >= len(ordered):
        return ordered
    return random.Random(seed).sample(ordered, k=sample)


def _mock_legalbench_answer(row: dict[str, Any]) -> str:
    """Deterministic mock answer (md5 parity), shared by every mock path.

    A mock must exercise the scoring machinery without being self-fulfilling:
    predicting the expected answer would pin every mock run to 1.0 and mask
    scoring defects (DMR-049 F8).
    """
    import hashlib

    blob = str(row.get("doc_text") or row.get("text") or row.get("document_text") or "")
    return "Yes" if int(hashlib.md5(blob.encode()).hexdigest()[:2], 16) % 2 else "No"


def run_legalbench_eval(
    *,
    mock: bool = True,
    sample: int | None = None,
    seed: int = 42,
    task: str = "contract_qa",
    suite: bool = False,
    dry_run: bool = False,
    experiment_name: str | None = None,
    profile: str | None = None,
    model: str | None = None,
    agent_models: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run the LegalBench harness (binary QA / family classification).

    ``suite=True`` loads a seeded subset from the vendored llm-mailroom suite
    (the real CUAD corpora — loud failure when unavailable); the default is
    the committed offline fixture. ``sample`` is a seeded draw, never
    first-N, and the seed lands in the plan/record (DMR-049 F5).
    """
    if task not in LEGALBENCH_TASKS:
        raise ValueError(f"unknown legalbench task {task!r}; have {sorted(LEGALBENCH_TASKS)}")
    if task == "family_classification":
        raise ValueError(
            "family_classification is not wired into the sandbox harness (no fixture and no "
            "family prompt) — run it from llm-mailroom's legalbench CLI: "
            "`PYTHONPATH=src python -m legalbench.cli --task family_classification`"
        )
    if suite:
        if not sample:
            raise ValueError("suite runs need an explicit --n/--sample (the full corpus is not a smoke run)")
        rows = load_legalbench_suite_rows(task, sample=sample, seed=seed)
    else:
        rows = load_legalbench_fixtures(task=task)
        if sample:
            rows = _seeded_sample(rows, sample, seed)
    if not rows:
        raise ValueError(
            f"legalbench task {task!r} produced no samples"
            + ("" if suite else " from the committed fixture — try --suite for the real corpus")
        )
    plan = {
        "task": "legalbench",
        "legalbench_task": task,
        "n": len(rows),
        "mock": mock,
        "seed": seed,
        "suite": suite,
    }
    if dry_run:
        return plan
    activation = activate(profile, model=model, agent_models=agent_models)
    expected = [str(r.get("answer") or r.get("expected") or "") for r in rows]
    errors: list[dict[str, Any]] = []
    if mock:
        predicted = [_mock_legalbench_answer(r) for r in rows]
    else:
        predicted = []
        for row in rows:
            try:
                predicted.append(_live_legalbench_answer(row, model=model))
            except Exception as exc:  # noqa: BLE001 — recorded per row, not fatal per row
                predicted.append("")
                errors.append({"id": row.get("id"), "error": f"{type(exc).__name__}: {str(exc)[:300]}"})
        if len(errors) == len(rows):
            raise RuntimeError(
                f"legalbench task {task!r}: all {len(rows)} row(s) failed — the live path was "
                f"not exercised (last error: {errors[-1]['error']})"
            )
    session = tracing.session_id_for("legalbench")
    for row, pred in zip(rows, predicted):
        with tracing.document_pipeline_trace(
            seed=str(row.get("id") or "legalbench"),
            session_id=session,
            input={"filename": row.get("id"), **tracing.public_ground_truth({"expected": row.get("answer")})},
            metadata={"pipeline": "mailroom", "source": "legalbench", "run_id": experiment_name},
            tags=tracing.default_tags("source-legalbench"),
        ):
            with tracing.child_observation("answer-question", as_type="generation"):
                pass
    tracing.flush_traces()
    scores = scoring.score_legalbench(expected, predicted)
    if errors:
        scores["error_count"] = len(errors)
    record = experiment_log.new_record(
        experiment_name=experiment_name or "sandbox_legalbench",
        task="legalbench",
        legalbench_task=task,
        profile=activation.profile_name,
        provider=os.environ.get("DEFAULT_PROVIDER"),
        model="mock/mock-legalbench" if mock else model,
        mock=mock,
        seed=seed,
        n=len(rows),
        scores=scores,
        tracing_backend=tracing.tracing_backend(),
        tags=tracing.default_tags("source-legalbench"),
    )
    experiment_log.append(record)
    return {**plan, "scores": scores}


def run_local_vs_api_eval(
    *,
    mock: bool = True,
    sample: int | None = None,
    dry_run: bool = False,
    experiment_name: str | None = None,
    profile: str | None = None,
    model: str | None = None,
    prompt_version: str | None = None,
    agent_models: dict[str, str] | None = None,
    from_log: bool = False,
    connected: bool = False,
) -> dict[str, Any]:
    """Compare local (Ollama/vLLM/…) vs API-key (OpenRouter) serving metrics.

    ``--mock`` uses committed fixture timings (no LLM, no ``OPENROUTER_API_KEY``).
    ``from_log`` partitions ``reports/experiment_log.jsonl`` via dojo
    ``split_local_api`` / ``get_suite("local_vs_api")``.
    """
    del sample, connected, agent_models  # unused; kept for eval kwargs parity
    from mailroom_sandbox.datasets import load_serving_fixtures

    headlines = scoring.serving_headlines()
    plan = {
        "task": "local_vs_api",
        "suite": "local_vs_api",
        "mock": mock,
        "from_log": from_log,
        "headlines": headlines,
        "requires_api_key": False,
        "fingerprint": "fixture-serving-v0",
    }
    if dry_run:
        return plan

    activation = activate(profile, model=model, prompt_variant=prompt_version)
    if from_log:
        compared = scoring.compare_from_records(experiment_log.load())
        source = "experiment_log"
        local_rec = None
        api_rec = None
    else:
        fixtures = load_serving_fixtures()
        local_rec = fixtures.get("local") or {}
        api_rec = fixtures.get("api") or {}
        if mock:
            # Fixture path: never call OpenRouter even if a key is in the env.
            os.environ.setdefault("SANDBOX_RUN_MODE", "mock")
        compared = scoring.compare_local_vs_api(local_rec, api_rec)
        source = "fixtures"
        compared = {
            "local_n": 1,
            "api_n": 1,
            "unknown_n": 0,
            "pairs": [compared],
            "comparison": compared,
            "headlines": headlines,
            "table": compared.get("table") or [],
            "scorecard": compared.get("scorecard"),
            "cost": compared.get("cost"),
            "markdown": compared.get("markdown"),
        }

    comparison = compared.get("comparison") or {}
    metrics = comparison.get("metrics") or {}
    ttft = (metrics.get("ttft_seconds") or {}) if isinstance(metrics, dict) else {}
    scorecard = compared.get("scorecard") or comparison.get("scorecard") or {}
    cost = compared.get("cost") or comparison.get("cost") or {}
    table = compared.get("table") or comparison.get("table") or []
    markdown = compared.get("markdown") or comparison.get("markdown")
    scores = {
        "ttft_seconds_local": ttft.get("local"),
        "ttft_seconds_api": ttft.get("api"),
        "ttft_delta_local_minus_api": ttft.get("delta_local_minus_api"),
        "tokens_per_second_local": (metrics.get("tokens_per_second") or {}).get("local"),
        "tokens_per_second_api": (metrics.get("tokens_per_second") or {}).get("api"),
        "gpu_utilization_api": (metrics.get("gpu_utilization") or {}).get("api"),
        "quality": comparison.get("quality"),
        "honest_gaps": comparison.get("honest_gaps") or [],
        "missing": scorecard.get("missing") or [],
        "cost_local": (cost.get("local") or {}).get("estimated_cost_usd") if isinstance(cost, dict) else None,
        "cost_api": (cost.get("api") or {}).get("estimated_cost_usd") if isinstance(cost, dict) else None,
        "table_n": len(table),
        "local_n": compared.get("local_n"),
        "api_n": compared.get("api_n"),
        "n": (compared.get("local_n") or 0) + (compared.get("api_n") or 0),
    }
    if comparison:
        scoring.emit_local_vs_api_scorecard(
            comparison, run_id=experiment_name or "sandbox_local_vs_api"
        )
    record = experiment_log.new_record(
        experiment_name=experiment_name or "sandbox_local_vs_api",
        task="local_vs_api",
        profile=activation.profile_name,
        provider=os.environ.get("DEFAULT_PROVIDER"),
        model=model,
        prompt_version=prompt_version or "mailroom-default",
        mock=mock,
        dataset_fingerprint=plan["fingerprint"],
        n=scores["n"],
        scores=scores,
        serving_kind="local",
        tracing_backend=tracing.tracing_backend(),
        tags=tracing.default_tags("source-serving", "local-vs-api"),
        local_vs_api=compared,
        serving_markdown=markdown,
        source=source,
    )
    experiment_log.append(record)
    return {**plan, "scores": scores, "comparison": compared, "record": record}


def run_pipeline_eval(
    *,
    mock: bool = True,
    sample: int | None = None,
    dry_run: bool = False,
    experiment_name: str | None = None,
    profile: str | None = None,
    model: str | None = None,
    prompt_version: str | None = None,
    agent_models: dict[str, str] | None = None,
    connected: bool = True,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    # DMR-056: rows=None keeps the fixture manifest default; the sandbox job
    # whole-run path passes the LOCKED live dataset rows instead.
    rows = load_manifest() if rows is None else rows
    if sample:
        rows = rows[: sample]
    plan = {
        "task": "pipeline",
        "n": len(rows),
        "mock": mock,
        "fingerprint": dataset_fingerprint(rows),
        "connected": connected,
    }
    if dry_run:
        return plan
    os.environ["SANDBOX_RUN_MODE"] = "mock" if mock else "local"
    activation = activate(
        profile, model=model, prompt_variant=prompt_version, agent_models=agent_models
    )
    session = tracing.session_id_for("pipeline")
    results = []
    for row in rows:
        results.append(_run_pipeline_doc(row, mock=mock, session_id=session, experiment_name=experiment_name))
    expected = [r["expected_doc_class"] for r in rows]
    predicted = [r.get("doc_type") or "unknown" for r in results]
    class_scores = scoring.score_classification(expected, predicted)
    stage_expected = [str(r.get("expected_stage") or "archived") for r in rows]
    stage_predicted = [str(r.get("stage") or "unknown") for r in results]
    stage_scores = scoring.score_stage(stage_expected, stage_predicted)
    extract_vals: list[float] = []
    if connected:
        for row, result in zip(rows, results):
            expected_fields = parse_expected_fields(row) or {}
            if not expected_fields:
                continue
            scored = scoring.score_extraction_row(
                row["expected_doc_class"],
                result.get("extracted_data") or {},
                expected_fields,
                # DMR-056: live corpus rows carry doc_text inline; fixture rows
                # read from disk (subdir guard — live rows have no subdir key).
                doc_text=row.get("doc_text")
                or (
                    fixture_file(row).read_text(encoding="utf-8")
                    if "subdir" in row and fixture_file(row).is_file()
                    else None
                ),
            )
            value = scored.get("overall_extraction_score")
            if isinstance(value, (int, float)):
                extract_vals.append(float(value))
    routing_expected = ["review" if s == "review" else "continue" for s in stage_expected]
    routing_predicted = ["review" if s == "review" else "continue" for s in stage_predicted]
    routing = scoring.score_classification(routing_expected, routing_predicted)
    scores = {
        **class_scores,
        "class_correct": class_scores.get("exact_match"),
        "stage_correct": stage_scores.get("stage_correct"),
        "extraction_overall": scoring.mean_or_zero(extract_vals) if extract_vals else None,
        "routing_accuracy": routing.get("exact_match"),
        "connected": connected,
    }
    tracing.emit_langfuse_score("class_correct", float(scores["class_correct"] or 0))
    tracing.emit_langfuse_score("stage_correct", float(scores["stage_correct"] or 0))
    if scores["extraction_overall"] is not None:
        tracing.emit_langfuse_score("extraction_overall_score", float(scores["extraction_overall"]))
    tracing.flush_traces()
    record = experiment_log.new_record(
        experiment_name=experiment_name or "sandbox_pipeline",
        task="pipeline",
        profile=activation.profile_name,
        provider=os.environ.get("DEFAULT_PROVIDER"),
        model=model,
        prompt_version=prompt_version or "mailroom-default",
        mock=mock,
        dataset_fingerprint=plan["fingerprint"],
        n=len(rows),
        scores=scores,
        docs=results,
        tracing_backend=tracing.tracing_backend(),
        tags=tracing.default_tags("source-fixtures"),
        session_id=session,
        trace_ids=tracing.last_trace_ids(),
    )
    experiment_log.append(record)
    return {**plan, "scores": scores, "docs": results}


def _langchain_mock_patches(expect: dict[str, Any]) -> list:
    """Mock patches for mailroom v0.6.0's vendored LangChain agents.

    The vendored agents build their own ``ChatOpenAI`` and bypass
    ``llm.client.get_llm``, so — mirroring mailroom's own test suite — the
    ``langchain_agents.base_agent.BaseAgent.llm`` property must be patched
    with the canned ``FakeLangChainLLM`` shipped alongside. The sandbox
    keeps its marker-driven payload table by overriding ``_run`` to answer
    through ``fake_structured_payload``. Returns [] when mailroom v0.5.x
    (no langchain_agents) is resolved instead.
    """
    try:
        import langchain_agents.base_agent as lc_base
        from langchain_agents.mock import FakeLangChainLLM, user_text_from_messages
    except Exception:
        return []

    class _SandboxFakeLLM(FakeLangChainLLM):
        def _run(self, messages):
            self.calls += 1
            text = user_text_from_messages(messages)
            parsed = fake_structured_payload(text, expect)
            return self._make_message(parsed)

    fake = _SandboxFakeLLM()
    return [patch.object(lc_base.BaseAgent, "llm", new=lambda self: fake)]


_TEXT_SUFFIXES = (".txt", ".md", ".json", ".csv", ".eml", ".html", ".htm")


def _doc_source_name(row: dict[str, Any]) -> str:
    """Filename for a row's document in the inbox (fixture or prepared row)."""
    filename = str(row.get("filename") or "").strip()
    if filename:
        return Path(filename).name
    ident = str(row.get("id") or "doc").strip() or "doc"
    return f"{ident}.txt"


def _materialize_row(row: dict[str, Any], inbox: Path) -> Path:
    """Place the row's document in the inbox and return the queued path.

    Fixture rows resolve to their file on disk (copied in); prepared corpus
    rows carry ``doc_text`` inline and are written as a text document. A row
    with neither raises — a live run never scores a missing document.
    """
    import shutil

    queued = inbox / _doc_source_name(row)
    doc_text = row.get("doc_text") or row.get("text")
    if doc_text:
        if queued.suffix.lower() not in _TEXT_SUFFIXES:
            queued = queued.with_suffix(".txt")
        queued.write_text(str(doc_text), encoding="utf-8")
        return queued
    source = fixture_file(row)  # KeyError when subdir/filename are absent — live-or-loud
    shutil.copyfile(source, queued)
    return queued


def _run_pipeline_doc(
    row: dict[str, Any],
    *,
    mock: bool,
    session_id: str | None = None,
    experiment_name: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run one row through mailroom ``run_pipeline`` when available.

    Rows may be fixture rows (file on disk) or prepared corpus rows
    (``doc_text`` inline — the DMR-027 job path); both are materialized into
    the inbox before the run. When the mailroom import fails a LIVE run
    raises (live-or-loud, DMR-044) instead of returning a mock-shaped
    fallback; mock runs keep the deterministic fallback. ``run_id`` rides
    into ``run_pipeline`` so the catalog provenance is not NULL for
    sandbox-driven runs (DMR-052).
    """
    src = resolve_mailroom_src()
    name = _doc_source_name(row)
    expect = _expect_from_row(row)
    public_gt = tracing.public_ground_truth(row)
    fallback = {
        "id": row.get("id"),
        "doc_type": _classify_mock(row) if mock else None,
        "stage": row.get("expected_stage"),
        "extracted_data": parse_expected_fields(row) if mock else None,
        "offline_fallback": True,
    }
    try:
        from graph.build_graph import run_pipeline  # type: ignore
        from pipeline.bins import inbox_dir  # type: ignore
    except Exception as exc:
        if not mock:
            raise RuntimeError(
                "mailroom pipeline is not importable (vendored llm-mailroom missing) — "
                "a live run would silently mock; run `sandbox fetch-deps` or use --mock"
            ) from exc
        with tracing.document_pipeline_trace(
            seed=str(row.get("id") or name),
            session_id=session_id or tracing.session_id_for("pipeline"),
            input={"filename": name, "matter_id": f"SANDBOX-{row.get('id')}", **public_gt},
            metadata={"pipeline": "mailroom", "source": "sandbox-fixtures", "run_id": experiment_name, "attempt": 1},
            tags=tracing.default_tags("source-fixtures"),
        ):
            with tracing.child_observation("pipeline-result", as_type="generation", input=public_gt):
                pass
        return fallback

    inbox = inbox_dir()
    inbox.mkdir(parents=True, exist_ok=True)
    queued = _materialize_row(row, inbox)
    matter_id = f"SANDBOX-{row.get('id')}"
    # Mailroom strips expected_fields before the trace; keep it for in-graph scoring.
    gt = {**public_gt, "expected_doc_class": str(row.get("expected_doc_class") or "")}
    fields = parse_expected_fields(row)
    if fields:
        gt["expected_fields"] = fields

    def _mock_get_llm(agent_name: str):
        return fake_client(expect), "mock-model"

    kwargs = {
        "source": "sandbox-fixtures",
        "ground_truth": gt,
        "session_id": session_id or matter_id,
        "run_id": run_id or experiment_name,
    }
    if mock:
        with ExitStack() as stack:
            stack.enter_context(
                patch("llm.client.get_llm", side_effect=_mock_get_llm)
            )
            stack.enter_context(
                patch("agents.base.get_llm", side_effect=_mock_get_llm)
            )
            for lc_patch in _langchain_mock_patches(expect):
                stack.enter_context(lc_patch)
            result = run_pipeline(queued, matter_id, **kwargs)
    else:
        result = run_pipeline(queued, matter_id, **kwargs)
    return {
        "id": row.get("id"),
        "doc_type": result.get("doc_type"),
        "stage": result.get("stage"),
        "extracted_data": result.get("extracted_data"),
        "classification_confidence": result.get("classification_confidence"),
        "offline_fallback": False,
        "mailroom_src": str(src) if src else None,
    }


def _live_serve_target() -> tuple[str, str]:
    """(base_url, model) for a direct live call, following the active provider.

    ``DEFAULT_PROVIDER`` picks the family; the fallback model matches the
    profile default (``Qwen/Qwen3-8B`` for vLLM, ``qwen3:8b`` for Ollama) so a
    served vLLM never 404s on the Ollama tag.
    """
    provider = (os.environ.get("DEFAULT_PROVIDER") or "").strip().lower()
    if provider == "vllm":
        return (
            os.environ.get("VLLM_BASE_URL") or "http://localhost:8000/v1",
            os.environ.get("VLLM_MODEL") or "Qwen/Qwen3-8B",
        )
    if provider == "ollama":
        return (
            os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434/v1",
            "qwen3:8b",
        )
    return (
        os.environ.get("OLLAMA_BASE_URL")
        or os.environ.get("VLLM_BASE_URL")
        or "http://localhost:11434/v1",
        "qwen3:8b",
    )


def _live_legalbench_answer(row: dict[str, Any], *, model: str | None) -> str:
    try:
        from openai import OpenAI
    except Exception as exc:
        raise RuntimeError(
            "openai is not installed — a live legalbench run would silently "
            "score the expected answer; install the eval extras or use --mock"
        ) from exc
    base, fallback_model = _live_serve_target()
    client = OpenAI(base_url=base, api_key=os.environ.get("VLLM_API_KEY") or "not-needed")
    prompt = (
        f"Answer Yes or No only. json required.\nQuestion: {row.get('question')}\n"
        f"Passage: {row.get('doc_text') or row.get('text') or row.get('passage') or row.get('document_text')}\n"
    )
    resp = client.chat.completions.create(
        model=model or os.environ.get("SANDBOX_MODEL") or fallback_model,
        messages=[
            {"role": "system", "content": "Return json {\"answer\": \"Yes\" or \"No\"}."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=32,
        temperature=0,
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        return str(json.loads(raw).get("answer") or raw).strip()
    except json.JSONDecodeError:
        return raw.strip()


def hf_rows_as_manifest() -> list[dict[str, str]]:
    rows = []
    for item in load_hf_fixtures():
        rows.append(
            {
                "id": str(item.get("id") or item.get("filename") or item.get("doc_type")),
                "subdir": "hf",
                "filename": str(item.get("filename") or f"{item.get('doc_type')}.txt"),
                "expected_doc_class": str(item.get("doc_type") or item.get("expected_hf_class") or "unknown"),
                # mailroom-corpus ground-truth alignment: subclass + entity
                # targets ride through so specialist/judge/reporter evals
                # score against the corpus GT schema, not ad-hoc keys.
                "expected_subclass": str(item.get("expected_subclass") or ""),
                "expected_fields": item.get("expected_fields") or {},
                "expected_stage": "archived",
                "text": str(item.get("text") or ""),
            }
        )
    return rows
