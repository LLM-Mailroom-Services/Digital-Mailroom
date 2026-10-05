"""Aggregations over interpreted runs — every number from Langfuse data."""

from __future__ import annotations

import math
import statistics
from datetime import datetime
from typing import Iterable, Optional

from .models import Metrics, PipelineRun, Stage
from .pipeline_schema import (
    SUITE_EXTRA_SCORES,
    canonical_score_name,
    langfuse_score_name,
)


def _finite(value) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _p95(values: list[float]) -> Optional[float]:
    """Nearest-rank p95 (ceil(0.95·n)-th value). None when there is no data.

    ``round()`` rounds half to even, which picked the wrong rank (n=30 → 27th
    value instead of the 29th); 0.0 for "no data" read as a real latency.
    """
    if not values:
        return None
    values = sorted(values)
    idx = min(len(values) - 1, max(0, math.ceil(0.95 * len(values)) - 1))
    return round(values[idx], 3)


def compute_metrics(runs: Iterable[PipelineRun], since: Optional[datetime] = None) -> Metrics:
    m = Metrics()
    all_latencies: list[float] = []
    gen_latencies: list[float] = []
    qualities: list[float] = []

    # Extraction-quality score mining (llm-mailroom SCORE_CONFIGS names).
    grounded_keys = {
        "extraction_field_score": [],
        "extraction_overall_score": [],
        "entity_list_precision": [],
        "entity_list_recall": [],
        "extraction_hallucination_rate": [],
        "expected_field_presence": [],
        "run_duration_seconds": [],
        "classification_attempts": [],
        "extraction_attempts": [],
        "extraction_overall_verified_precision": [],
    }
    suite_keys = {name: [] for name in SUITE_EXTRA_SCORES}
    n_grounded = 0

    def _score_value(run: PipelineRun, name: str):
        # PipelineRun.scores maps name -> raw value (trace scores flattened).
        # Resolve the 35-char Langfuse alias in either direction.
        value = run.scores.get(name)
        if value is None:
            alias = langfuse_score_name(name)
            if alias != name:
                value = run.scores.get(alias)
        if value is None:
            canon = canonical_score_name(name)
            if canon != name:
                value = run.scores.get(canon)
        return _finite(value)

    # V-6/V-7: normalize the window to tz-aware UTC (CONVERT, never relabel —
    # the old replace(tzinfo=...) shifted metric windows by the full UTC
    # offset on non-UTC servers).
    if since is not None and since.tzinfo is None:
        from datetime import timezone as _tz

        since = since.replace(tzinfo=_tz.utc)
    elif since is not None:
        from datetime import timezone as _tz

        since = since.astimezone(_tz.utc)

    for run in runs:
        run_ts = run.updated_at or run.created_at
        if since is not None and run_ts is not None:
            if run_ts.tzinfo is None:
                from datetime import timezone as _tz

                run_ts = run_ts.replace(tzinfo=_tz.utc)
            if run_ts < since:
                continue
        m.total_docs += 1
        if run.needs_reconsideration:
            m.reconsideration += 1
        if run.needs_human:
            m.review += 1
        elif run.stage == Stage.ARCHIVED:
            m.archived += 1
        elif run.stage == Stage.FAILED:
            m.failed += 1
        else:
            m.in_flight += 1
        m.total_cost_usd += _finite(run.cost_usd) or 0.0
        m.total_tokens += run.total_tokens or 0
        m.llm_calls += run.llm_call_count or 0
        latency = _finite(run.latency)
        if latency is not None:
            all_latencies.append(latency)
        for g in run.generations:
            g_latency = _finite(g.latency)
            if g_latency is not None:
                gen_latencies.append(g_latency)
        if run.verdict:
            m.verdict_counts[run.verdict] = m.verdict_counts.get(run.verdict, 0) + 1
        quality = _finite(run.quality)
        if quality is not None:
            qualities.append(quality)
        if run.doc_type:
            m.per_doc_type[run.doc_type] = m.per_doc_type.get(run.doc_type, 0) + 1
        if run.doc_subclass:
            sub_key = f"{run.doc_type or 'unknown'}/{run.doc_subclass}"
            m.per_doc_subclass[sub_key] = m.per_doc_subclass.get(sub_key, 0) + 1

        # Grounded-run extraction quality: a run counts as grounded when the
        # deterministic field score is present (mirrors pilot grounded runs).
        field_score = _score_value(run, "extraction_field_score")
        if field_score is not None:
            n_grounded += 1
        for key, bucket in grounded_keys.items():
            value = _score_value(run, key)
            if value is not None:
                bucket.append(value)
        for key, bucket in suite_keys.items():
            value = _score_value(run, key)
            if value is not None:
                bucket.append(value)

    if m.total_docs:
        m.avg_cost_usd = round(m.total_cost_usd / m.total_docs, 4)
    if all_latencies:
        m.avg_latency_s = round(statistics.mean(all_latencies), 2)
    m.p95_generation_latency_s = _p95(gen_latencies)
    if qualities:
        m.avg_quality = round(statistics.mean(qualities), 3)

    m.n_grounded_runs = n_grounded
    for key, bucket in grounded_keys.items():
        attr = {
            "extraction_field_score": "avg_extraction_field_score",
            "extraction_overall_score": "avg_extraction_overall_score",
            "entity_list_precision": "avg_entity_list_precision",
            "entity_list_recall": "avg_entity_list_recall",
            "extraction_hallucination_rate": "avg_hallucination_rate",
            "expected_field_presence": "avg_expected_field_presence",
            "run_duration_seconds": "avg_run_duration_s",
            "classification_attempts": "avg_classification_attempts",
            "extraction_attempts": "avg_extraction_attempts",
            "extraction_overall_verified_precision": "avg_extraction_verified_precision",
        }[key]
        setattr(m, attr, round(statistics.mean(bucket), 4) if bucket else None)
    for key, bucket in suite_keys.items():
        setattr(m, f"avg_{key}", round(statistics.mean(bucket), 4) if bucket else None)
    return m
