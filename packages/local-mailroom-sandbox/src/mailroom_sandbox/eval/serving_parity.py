"""Grant-style cost-compare records → dojo-scorable serving records.

Vendored ``llm_dojo_scoring.serving`` is a two-bucket suite (``local`` | ``api``).
It does not keep ``serving_kind=modal``, does not read ``latency_ms`` /
``ttft_ms``, and has no OpenRouter price row for HF ids such as
``Qwen/Qwen3-8B``. Sandbox jobs emit those Modal/vLLM fields (DMR-027 /
DMR-049). This adapter is the single translation so:

* ``sandbox metrics compare`` (three-way local / modal / api + GPU $)
* ``get_suite("local_vs_api").score`` / ``compare_serving``

see the same e2e, tokens, token-proxy $, and quality numbers.

Do **not** patch the vendored snapshot here (hub#62 drift). The checklist
records the honest remapping: dojo identity ``serving_kind`` for a Modal
run becomes ``local``.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from llm_dojo_scoring.serving import (
    CANONICAL_SERVING_KEYS,
    classify_serving_kind,
    compare_serving,
    score_serving_run,
)

from mailroom_sandbox.job.metrics import (
    _estimate_cost,
    bucket_kind,
    compare as sandbox_compare,
    estimate_gpu_cost_usd,
    record_from_run,
)

# Fields Grant's Modal / cost-compare table uses (sandbox == dojo after adapt).
GRANT_TABLE_KEYS: tuple[str, ...] = (
    "serving_kind",
    "e2e_latency_seconds",
    "ttft_seconds",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "estimated_cost_usd",
    "cost_per_document",
    "accuracy",
    "f1_macro",
)

# Sandbox-only GPU attribution (dojo has no GPU $ column).
SANDBOX_GPU_KEYS: tuple[str, ...] = (
    "gpu_seconds",
    "estimated_gpu_cost_usd",
    "gpu_cost_per_document",
    "gpu",
)


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    num = _as_float(value)
    if num is None:
        return None
    return int(num)


def _first(mapping: Mapping[str, Any] | None, *keys: str) -> Any:
    if not mapping:
        return None
    for key in keys:
        if "." in key:
            cur: Any = mapping
            ok = True
            for part in key.split("."):
                if isinstance(cur, Mapping) and part in cur:
                    cur = cur[part]
                else:
                    ok = False
                    break
            if ok and cur not in (None, ""):
                return cur
            continue
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


def ms_to_seconds(ms: Any) -> float | None:
    num = _as_float(ms)
    if num is None:
        return None
    return num / 1000.0


def grant_quality(record: Mapping[str, Any]) -> dict[str, float]:
    scores = record.get("scores") if isinstance(record.get("scores"), Mapping) else {}
    out: dict[str, float] = {}
    for key in ("accuracy", "exact_match", "f1_macro", "doc_type_accuracy"):
        val = scores.get(key) if scores else record.get(key)
        num = _as_float(val)
        if num is not None:
            out[key] = num
    return out


def to_dojo_serving_record(
    record: Mapping[str, Any],
    *,
    items: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Normalize a Grant / items.jsonl / experiment-log dict for dojo scoring.

    Converts millisecond job fields, stamps champion token $ when the dojo
    price table does not know the HF id, and keeps ``serving_kind=modal``
    on the record (dojo will still remap identity to ``local``).
    """
    raw = dict(record)
    usage = raw.get("usage") if isinstance(raw.get("usage"), Mapping) else {}
    tokens = raw.get("tokens") if isinstance(raw.get("tokens"), Mapping) else {}
    timings = raw.get("timings") if isinstance(raw.get("timings"), Mapping) else {}

    e2e = _as_float(
        _first(raw, "e2e_latency_seconds", "latency_seconds", "duration_seconds")
    )
    if e2e is None:
        e2e = ms_to_seconds(_first(raw, "latency_ms", "e2e_latency_ms"))
    if e2e is None:
        e2e = ms_to_seconds(_first(timings, "latency_ms", "e2e_latency_ms"))

    ttft = _as_float(_first(raw, "ttft_seconds", "ttft"))
    if ttft is None:
        ttft = ms_to_seconds(_first(raw, "ttft_ms"))
    if ttft is None:
        ttft = ms_to_seconds(_first(timings, "ttft_ms"))

    prompt = _as_int(
        _first(raw, "prompt_tokens", "input_tokens")
        or _first(usage, "prompt_tokens", "input_tokens")
        or _first(tokens, "prompt_tokens", "input_tokens")
    )
    completion = _as_int(
        _first(raw, "completion_tokens", "output_tokens")
        or _first(usage, "completion_tokens", "output_tokens")
        or _first(tokens, "completion_tokens", "output_tokens")
    )
    total = _as_int(_first(raw, "total_tokens") or _first(usage, "total_tokens"))
    if total is None and prompt is not None and completion is not None:
        total = prompt + completion

    out: dict[str, Any] = dict(raw)
    if e2e is not None:
        out["e2e_latency_seconds"] = e2e
    if ttft is not None:
        out["ttft_seconds"] = ttft
    if prompt is not None:
        out["prompt_tokens"] = prompt
    if completion is not None:
        out["completion_tokens"] = completion
    if total is not None:
        out["total_tokens"] = total

    model = str(out.get("model") or "")
    cost = _as_float(_first(out, "estimated_cost_usd", "cost_usd"))
    if cost is None and (prompt or completion):
        cost = _estimate_cost(prompt or 0, completion or 0, model)
    n = _as_int(out.get("n")) or (len(items) if items else None) or 1
    out["n"] = n
    if cost is not None:
        out["estimated_cost_usd"] = float(cost)
        if n:
            out.setdefault("cost_per_document", round(float(cost) / n, 8))

    gpu_seconds = _as_float(out.get("gpu_seconds"))
    if gpu_seconds is None:
        billed = _as_float(out.get("billed_window_seconds"))
        if billed is not None:
            gpu_seconds = billed
        elif items:
            lat_ms = [
                float(i["latency_ms"])
                for i in items
                if i.get("ok", True) is not False and i.get("latency_ms") is not None
            ]
            if lat_ms:
                gpu_seconds = sum(lat_ms) / 1000.0
        elif e2e is not None and n:
            # Run-level record: mean e2e × n is the same busy-sum job/metrics uses
            # when items.jsonl latencies are not attached.
            gpu_seconds = float(e2e) * int(n)
    kind = bucket_kind(out)
    gpu_profiles = {"vllm-local", "vllm-remote"}
    if gpu_seconds is not None and (
        kind == "modal" or str(out.get("profile") or "") in gpu_profiles
    ):
        out["gpu_seconds"] = round(gpu_seconds, 3)
        gpu_cost = estimate_gpu_cost_usd(gpu_seconds, gpu=out.get("gpu"))
        if gpu_cost is not None:
            out["estimated_gpu_cost_usd"] = gpu_cost
            if n:
                out["gpu_cost_per_document"] = round(gpu_cost / n, 8)

    if items and "requests" not in out:
        reqs = []
        for item in items:
            reqs.append(to_dojo_serving_record(item))
        out["requests"] = reqs

    if "serving_kind" not in out or not out.get("serving_kind"):
        out["serving_kind"] = bucket_kind(out)
    return out


def split_serving_records(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Partition into local / modal / api / unknown. Modal is never local."""
    buckets: dict[str, list[dict[str, Any]]] = {
        "local": [],
        "modal": [],
        "api": [],
        "unknown": [],
    }
    for rec in records:
        adapted = to_dojo_serving_record(rec)
        kind = bucket_kind(adapted)
        buckets.setdefault(kind, []).append(adapted)
    return buckets


def grant_table_row(record: Mapping[str, Any]) -> dict[str, Any]:
    """One row of the Grant cost-compare table from a (possibly raw) record."""
    adapted = to_dojo_serving_record(record)
    quality = grant_quality(adapted)
    row = {
        "serving_kind": adapted.get("serving_kind") or bucket_kind(adapted),
        "profile": adapted.get("profile"),
        "provider": adapted.get("provider"),
        "model": adapted.get("model"),
        "n": adapted.get("n"),
        "e2e_latency_seconds": adapted.get("e2e_latency_seconds"),
        "ttft_seconds": adapted.get("ttft_seconds"),
        "prompt_tokens": adapted.get("prompt_tokens"),
        "completion_tokens": adapted.get("completion_tokens"),
        "total_tokens": adapted.get("total_tokens"),
        "estimated_cost_usd": adapted.get("estimated_cost_usd"),
        "cost_per_document": adapted.get("cost_per_document"),
        "estimated_gpu_cost_usd": adapted.get("estimated_gpu_cost_usd"),
        "gpu_cost_per_document": adapted.get("gpu_cost_per_document"),
        "gpu": adapted.get("gpu"),
        "accuracy": quality.get("accuracy"),
        "f1_macro": quality.get("f1_macro"),
        "exact_match": quality.get("exact_match"),
    }
    return {k: v for k, v in row.items() if v is not None}


def _approx_equal(a: Any, b: Any, *, rel: float = 1e-6, abs_tol: float = 1e-8) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        fa, fb = float(a), float(b)
    except (TypeError, ValueError):
        return a == b
    return abs(fa - fb) <= max(abs_tol, rel * max(abs(fa), abs(fb)))


def _dojo_side_metrics(agg: Mapping[str, Any]) -> dict[str, Any]:
    ident = agg.get("identity") or {}
    if isinstance(ident, list):
        ident = ident[0] if ident else {}
    quality = agg.get("quality") if isinstance(agg.get("quality"), Mapping) else {}
    return {
        "serving_kind_dojo": ident.get("serving_kind") if isinstance(ident, Mapping) else None,
        "e2e_latency_seconds": agg.get("e2e_latency_seconds"),
        "ttft_seconds": agg.get("ttft_seconds"),
        "prompt_tokens": agg.get("prompt_tokens"),
        "completion_tokens": agg.get("completion_tokens"),
        "total_tokens": agg.get("total_tokens"),
        "estimated_cost_usd": agg.get("estimated_cost_usd"),
        "cost_per_document": agg.get("cost_per_document"),
        "accuracy": quality.get("accuracy"),
        "f1_macro": quality.get("f1_macro"),
    }


def score_cost_compare(
    sides: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Score a Grant-style local / modal / api triple both ways.

    ``sides`` is ``{"local": rec, "modal": rec, "api": rec}`` or a list of
    records. Returns sandbox ``compare()``, dojo pairwise payloads, Grant
    table rows, and a field-level parity checklist.
    """
    if isinstance(sides, Mapping) and any(k in sides for k in ("local", "modal", "api")):
        records = [to_dojo_serving_record(sides[k]) for k in ("local", "modal", "api") if sides.get(k)]
        labeled = {
            k: to_dojo_serving_record(sides[k])
            for k in ("local", "modal", "api")
            if sides.get(k)
        }
    else:
        labeled = {bucket_kind(r): to_dojo_serving_record(r) for r in sides}  # type: ignore[arg-type]
        records = list(labeled.values())

    sandbox = sandbox_compare(records)
    pairs: dict[str, Any] = {}
    if labeled.get("local") and labeled.get("api"):
        pairs["local_vs_api"] = compare_serving(labeled["local"], labeled["api"])
    if labeled.get("modal") and labeled.get("api"):
        pairs["modal_vs_api"] = compare_serving(labeled["modal"], labeled["api"])
    if labeled.get("local") and labeled.get("modal"):
        pairs["local_vs_modal"] = compare_serving(labeled["local"], labeled["modal"])

    grant_rows = {kind: grant_table_row(rec) for kind, rec in labeled.items()}
    dojo_scored = {kind: score_serving_run(rec) for kind, rec in labeled.items()}

    checklist: list[dict[str, Any]] = []
    for kind, rec in labeled.items():
        grant = grant_rows[kind]
        dojo = _dojo_side_metrics(dojo_scored[kind])
        dojo_kind = classify_serving_kind(rec)
        checklist.append(
            {
                "side": kind,
                "sandbox_serving_kind": grant.get("serving_kind"),
                "dojo_serving_kind": dojo_kind,
                "dojo_remaps_modal_to_local": kind == "modal" and dojo_kind == "local",
                "fields": {
                    key: {
                        "sandbox": grant.get(key),
                        "dojo": dojo.get(key),
                        "match": _approx_equal(grant.get(key), dojo.get(key)),
                    }
                    for key in (
                        "e2e_latency_seconds",
                        "ttft_seconds",
                        "prompt_tokens",
                        "completion_tokens",
                        "total_tokens",
                        "estimated_cost_usd",
                        "cost_per_document",
                        "accuracy",
                        "f1_macro",
                    )
                },
            }
        )

    all_match = all(
        cell["match"]
        for row in checklist
        for cell in row["fields"].values()
    )
    markdown = _parity_md(grant_rows, checklist, sandbox)
    return {
        "agent": "cost_compare",
        "canonical_keys": list(CANONICAL_SERVING_KEYS),
        "grant_table": grant_rows,
        "sandbox": sandbox,
        "dojo_pairs": pairs,
        "dojo_runs": {k: _dojo_side_metrics(v) for k, v in dojo_scored.items()},
        "checklist": checklist,
        "parity_ok": all_match,
        "honest_gaps": [
            "dojo classify_serving_kind remaps serving_kind=modal → local "
            "(two-bucket suite; sandbox bucket_kind keeps modal)",
            "dojo has no estimated_gpu_cost_usd — GPU $ is sandbox-only "
            "(MODAL_GPU_USD_PER_HOUR / MODAL_BILLED_GPU_SECONDS)",
            "dojo price_for() has no Qwen/Qwen3-8B row — adapter stamps "
            "estimated_cost_usd from the sandbox champion table first",
        ],
        "markdown": markdown,
    }


def records_from_run_items(
    *,
    run_id: str,
    spec_hash: str,
    task: str,
    profile: str,
    model: str,
    prompt_version: str,
    dataset_fingerprint: str,
    items: Sequence[Mapping[str, Any]],
    scores: Mapping[str, Any] | None = None,
    gpu: str | None = None,
    billed_window_seconds: float | None = None,
    mock: bool = False,
) -> dict[str, Any]:
    """``record_from_run`` then the dojo adapter (shared CLI / job path)."""
    rec = record_from_run(
        run_id=run_id,
        spec_hash=spec_hash,
        task=task,
        profile=profile,
        model=model,
        prompt_version=prompt_version,
        dataset_fingerprint=dataset_fingerprint,
        items=items,
        scores=scores,
        gpu=gpu,
        billed_window_seconds=billed_window_seconds,
        mock=mock,
    )
    return to_dojo_serving_record(rec, items=items)


def _parity_md(
    grant_rows: Mapping[str, Mapping[str, Any]],
    checklist: Sequence[Mapping[str, Any]],
    sandbox: Mapping[str, Any],
) -> str:
    lines = [
        "## Grant-style cost-compare (sandbox == dojo token/latency/quality)",
        "",
        "| side | serving_kind | n | e2e (s) | ttft (s) | token $ | GPU $ | $/doc | accuracy | F1 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for kind in ("local", "modal", "api"):
        row = grant_rows.get(kind)
        if not row:
            continue
        lines.append(
            f"| {kind} | {row.get('serving_kind')} | {row.get('n', '-')} | "
            f"{row.get('e2e_latency_seconds', '-')} | {row.get('ttft_seconds', '-')} | "
            f"{row.get('estimated_cost_usd', '-')} | {row.get('estimated_gpu_cost_usd', '-')} | "
            f"{row.get('cost_per_document', '-')} | {row.get('accuracy', '-')} | "
            f"{row.get('f1_macro', '-')} |"
        )
    lines += ["", "### Parity checklist (adapted record vs dojo score_serving_run)", ""]
    lines += [
        "| side | field | sandbox | dojo | match |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for row in checklist:
        for key, cell in (row.get("fields") or {}).items():
            lines.append(
                f"| {row.get('side')} | {key} | {cell.get('sandbox')} | "
                f"{cell.get('dojo')} | {'yes' if cell.get('match') else 'NO'} |"
            )
        lines.append(
            f"| {row.get('side')} | serving_kind | {row.get('sandbox_serving_kind')} | "
            f"{row.get('dojo_serving_kind')} | "
            f"{'remap' if row.get('dojo_remaps_modal_to_local') else 'yes'} |"
        )
    sb_md = sandbox.get("markdown")
    if sb_md:
        lines += ["", str(sb_md)]
    return "\n".join(lines)
