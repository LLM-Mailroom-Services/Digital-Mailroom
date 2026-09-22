"""Revision-pinned, deterministic HF corpus subsets + offline JSONL path (DMR-027).

Mirrors ``llm-mailroom`` ``hf_corpus_loader.py`` (HUB-053): ``content_sha256 ==
sha256(doc_text)`` verification, ``default`` (blind text) + ``ground_truth``
(labels) joined on ``filename``, no ``datasets`` library — ``huggingface_hub``
+ ``pyarrow`` only. Deterministic subsetting: rows sorted by ``(filename, id)``,
per-stratum sub-seeded draws, union, global re-sort, then ``limit``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import re
from typing import Any

from mailroom_sandbox.job.spec import DatasetSpec, FAMILY_HF_REVISION

_log = logging.getLogger("mailroom_sandbox.corpus")

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _resolve_revision(repo: str, revision: str) -> str:
    """Resolve a Hub revision to a full 40-hex sha.

    A revision that already is a full sha is trusted as-is (no network call —
    the pinned default is a full sha, so the default path is network-free for
    resolution). Any other revision (branch/tag/partial sha) is resolved via
    ``dataset_info``; auth/gating/network failures propagate with context
    instead of silently floating to the requested string.
    """
    if _SHA_RE.fullmatch(revision):
        return revision
    import huggingface_hub

    try:
        info = huggingface_hub.HfApi().dataset_info(repo, revision=revision)
    except Exception as exc:
        raise RuntimeError(
            f"cannot resolve dataset revision {revision!r} for {repo}: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    resolved = getattr(info, "sha", "") or revision
    if not _SHA_RE.fullmatch(resolved):
        raise RuntimeError(
            f"dataset_info for {repo}@{revision} returned non-sha {resolved!r}"
        )
    return resolved

GT_FIELD_LISTS = {
    "insurance_claim": [
        "claim_number", "policy_number", "insurer", "insured_party", "claim_type",
        "date_of_loss", "date_filed", "claimed_amount", "adjuster",
        "damages_description", "coverage_determination", "denial_reasons",
        "supporting_documents",
    ],
    "contract": ["cuad_clause_labels"],
    "merger_agreement": ["maud_clause_labels"],
    "correspondence": ["intent", "subject_matter", "keywords", "sentiment_label"],
    "corporate_record": ["intent", "subject_matter", "keywords"],
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("filename") or ""), str(row.get("id") or ""))


def _read_jsonl(path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _read_parquet(path) -> list[dict[str, Any]]:
    import pyarrow.parquet as pq

    return [dict(r) for r in pq.read_table(path).to_pylist()]


def merge_default_and_gt(default_rows: list[dict[str, Any]], gt_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_filename = {str(r.get("filename")): r for r in default_rows}
    merged: list[dict[str, Any]] = []
    for gt in gt_rows:
        fname = str(gt.get("filename"))
        base = by_filename.get(fname, {})
        row = {**base, **gt, "filename": fname}
        if not row.get("doc_text") and base.get("doc_text"):
            row["doc_text"] = base["doc_text"]
        merged.append(row)
    return merged


def load_hf_rows(spec: DatasetSpec) -> list[dict[str, Any]]:
    """Fetch pinned parquet shards, merge default+ground_truth, return raw rows."""
    import huggingface_hub

    repo = spec.repo
    revision = spec.revision or FAMILY_HF_REVISION
    resolved = _resolve_revision(repo, revision)
    files = set(huggingface_hub.list_repo_files(repo, revision=resolved, repo_type="dataset"))

    def shard(config: str) -> str:
        return f"parquet/{config}/{spec.split}/{spec.split}-00000-of-00001.parquet"

    def read_config(config: str) -> list[dict[str, Any]] | None:
        f = shard(config)
        if f not in files:
            return None
        path = huggingface_hub.hf_hub_download(repo, f, revision=resolved, repo_type="dataset")
        return _read_parquet(path)

    default = read_config("default")
    ground_truth = read_config("ground_truth")

    if ground_truth is not None:
        merged = merge_default_and_gt(default or [], ground_truth)
        for r in merged:
            r["source_revision"] = resolved
        return merged
    if default is not None:
        if spec.config in ("", "ground_truth"):
            # The blind rows would be scored as unlabeled (expected_doc_class
            # "") — a silent 0.0/unknown scorecard. Refuse instead (DMR-049).
            raise RuntimeError(
                f"ground_truth config is absent at {repo}@{resolved} for split "
                f"{spec.split!r} — refusing to prepare blind rows as labeled data"
            )
        for r in default:
            r["source_revision"] = resolved
        return default
    cfg = read_config(spec.config)
    if cfg is None:
        raise RuntimeError(
            f"no parquet shards for {spec.config or 'default'} / {spec.split} at {repo}@{resolved}"
        )
    for r in cfg:
        r["source_revision"] = resolved
    return cfg


def normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Canonical dataset.jsonl row shape; verifies/fills content_sha256."""
    out: list[dict[str, Any]] = []
    for row in rows:
        doc_class = row.get("expected") or row.get("expected_doc_class") or row.get("doc_type")
        text = row.get("doc_text") or row.get("text") or ""
        content_sha = row.get("content_sha256")
        if content_sha and content_sha != sha256_text(text):
            raise ValueError(f"corpus integrity: content_sha256 mismatch on {row.get('id') or row.get('filename')}")
        if not content_sha:
            content_sha = sha256_text(text)
        expected_fields = row.get("expected_fields")
        if isinstance(expected_fields, str):
            # Same parser discipline as datasets.parse_expected_fields — a JSON
            # string is decoded, never silently flattened to {} (DMR-049).
            try:
                expected_fields = json.loads(expected_fields) if expected_fields.strip() else {}
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"corpus integrity: row {row.get('id') or row.get('filename') or '?'} "
                    f"has malformed expected_fields JSON: "
                    f"{expected_fields[:120]!r} — refusing to prepare corrupt "
                    "ground truth as empty expectations"
                ) from exc
        normalized = {
            "id": str(row.get("id") or row.get("document_id") or row.get("filename")),
            "filename": str(row.get("filename") or row.get("id")),
            "doc_text": text,
            "expected_doc_class": doc_class,
            "expected_subclass": row.get("expected_subclass"),
            "expected_stage": row.get("expected_stage"),
            "expected_fields": dict(expected_fields or {}),
            "content_sha256": content_sha,
            "split": row.get("split", ""),
            "source_revision": row.get("source_revision", ""),
        }
        # LegalBench-style rows keep their question/answer for the live path.
        if row.get("question") is not None:
            normalized["question"] = row.get("question")
        if row.get("answer") is not None:
            normalized["answer"] = row.get("answer")
        out.append(normalized)
    return out


def _derive_expected_fields(row: dict[str, Any]) -> dict[str, Any]:
    explicit = row.get("expected_fields")
    if explicit:
        return explicit
    doc_class = str(row.get("expected_doc_class") or "")
    keys = GT_FIELD_LISTS.get(doc_class, [])
    return {k: row.get(k) for k in keys if row.get(k) not in (None, "")}


def _normalize_subclass(doc_class: str, value: str) -> str:
    """Canonical subclass token via the vendored dojo normalizer (DMR-066).

    ``normalize_corpus_subclass`` already maps the corpus's raw surface
    spellings (CUAD folder forms like ``License_Agreements`` /
    ``Consulting Agreements``) onto the 25-key snake_case catalog for
    contract rows. Fallback = identity only when the vendored dojo tree is
    unavailable (BASE installs) — the DMR-066 guards then compare raw
    strings, which is the pre-fix behavior.
    """
    try:
        from llm_dojo_scoring.corpus import normalize_corpus_subclass

        return normalize_corpus_subclass(doc_class, value)
    except Exception:  # noqa: BLE001 — vendored tree absent / unknown token
        return value


def _row_stratum_value(row: dict[str, Any], field: str) -> str:
    v = str(row.get(field) or "")
    if field == "expected_subclass":
        return _normalize_subclass(str(row.get("expected_doc_class") or ""), v)
    return v


def _subclass_matches(row: dict[str, Any], requested: str) -> bool:
    """Raw-or-normalized subclass match, normalized per-row class (DMR-066).

    A requested ``license`` matches a raw ``License_Agreements`` row; a raw
    ``License_Agreements`` request also matches — the comparison always
    normalizes BOTH sides through the row's own doc class, so canonical
    requests work against surface spellings and vice versa.

    Guard: a normalized equality is only a match when the normalized value
    is not the unknown-token fallback (``other``) — otherwise every row of
    every *other* doc class would collapse to ``other == other`` and match
    any requested subclass (the DMR-066 candidate-inflation bug). An
    explicit raw ``other`` request still matches raw ``other`` rows via the
    exact-string branch above.
    """
    row_val = str(row.get("expected_subclass") or "")
    if requested == row_val:
        return True
    doc_class = str(row.get("expected_doc_class") or "")
    norm_req = _normalize_subclass(doc_class, requested)
    norm_row = _normalize_subclass(doc_class, row_val)
    if norm_req == "other" or norm_row == "other":
        return False
    return norm_req == norm_row


def strata_field(strata: dict[str, Any] | None) -> str:
    """The effective stratum field for a strata block (DMR-066).

    ``field`` wins when given; the ``values`` form defaults to
    ``expected_subclass`` (the subclass-stratified surface); legacy
    ``expected:``/``expected_subclass:`` filters imply their own field.
    """
    strata = strata or {}
    if strata.get("field"):
        return str(strata["field"])
    if "values" in strata:
        return "expected_subclass"
    if "expected_subclass" in strata:
        return "expected_subclass"
    return "expected_doc_class"


def _strata_requested(strata: dict[str, Any] | None) -> set[tuple[str, str]]:
    """Requested (field, raw-value) pairs for a strata block (raw, unnormalized)."""
    strata = strata or {}
    out: set[tuple[str, str]] = set()
    if "buckets" in strata:
        for b in strata["buckets"]:
            dc = str(b.get("doc_class") or "")
            sc = str(b.get("subclass") or "")
            if dc:
                out.add(("expected_doc_class", dc))
            if sc:
                out.add(("expected_subclass", sc))
        return out
    field = strata_field(strata)
    if "values" in strata:
        values = list(strata.get("values") or [])
    elif field == "expected_doc_class":
        values = list(strata.get("expected") or [])
    else:
        values = list(strata.get("expected_subclass") or [])
    for v in values:
        out.add((field, v))
    return out


def _strata_present(
    rows: list[dict[str, Any]], strata: dict[str, Any] | None
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Map (field, raw-value) -> sample rows carrying it (class-aware for subclass)."""
    out: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for r in rows:
        for field in ("expected_doc_class", "expected_subclass"):
            v = r.get(field)
            if not v:
                continue
            out.setdefault((field, str(v)), []).append(r)
    return out


def _requested_satisfied(
    requested: tuple[str, str], present: dict[tuple[str, str], list[dict[str, Any]]]
) -> bool:
    """Is the requested (field, value) present — exact or subclass-normalized?"""
    field, value = requested
    for (p_field, p_value), sample_rows in present.items():
        if p_field != field:
            continue
        if value == p_value:
            return True
        if field == "expected_subclass":
            if any(_subclass_matches(r, value) for r in sample_rows):
                return True
    return False


def strata_guard(rows: list[dict[str, Any]], strata: dict[str, Any] | None) -> None:
    """Loud strata sanity (DMR-066): never silently collapse or truncate.

    Hard-fails (ValueError) when: (1) a requested stratum value is absent
    from the prepared rows; (2) the stratum field is constant while more
    than one value was requested (the old ``expected:`` list on a constant
    field silently produced a single-class subset); (3) after the draw +
    ``limit``, a requested stratum was dropped entirely.
    """
    if not strata:
        return
    requested = _strata_requested(strata)
    if not requested:
        return
    present = _strata_present(rows, strata)
    # (2) constant-field check FIRST: it explains the run-50 trap exactly —
    # a >1-value request on a constant field implies the other values are
    # absent, so the dedicated message wins over the generic missing-list.
    present_fields = {f for f, _ in present}
    for field in sorted(present_fields):
        present_vals = {v for f, v in present if f == field}
        requested_vals = {v for f, v in requested if f == field}
        if len(present_vals) == 1 and len(requested_vals) > 1:
            raise ValueError(
                f"strata field {field!r} is constant across prepared rows "
                f"(value={sorted(present_vals)!r}); cannot stratify on "
                f"requested values {sorted(requested_vals)}"
            )
    # (1) genuinely absent requested values (no constant field involved).
    missing = sorted(
        req for req in requested if not _requested_satisfied(req, present)
    )
    if missing:
        raise ValueError(
            "strata requested value(s) absent from prepared rows: "
            f"{missing} (present: {sorted(present)})"
        )


def strata_draw_guard(
    drawn: list[dict[str, Any]], strata: dict[str, Any] | None
) -> None:
    """Post-draw coverage check: a requested stratum must survive the draw."""
    if not strata:
        return
    requested = _strata_requested(strata)
    if not requested:
        return
    present = _strata_present(drawn, strata)
    dropped = sorted(req for req in requested if not _requested_satisfied(req, present))
    if dropped:
        present_vals = {v for f, v in present}
        raise ValueError(
            f"strata: draw/limit dropped requested strata {dropped} "
            f"(drawn: {sorted(present_vals)})"
        )


def filter_rows(rows: list[dict[str, Any]], spec: DatasetSpec) -> list[dict[str, Any]]:
    if spec.exclude_expected:
        rows = [r for r in rows if r["expected_doc_class"] not in set(spec.exclude_expected)]
    strata = spec.strata or {}
    if not strata:
        return rows
    if "buckets" in strata or "values" in strata:
        return rows
    expected_set = set(strata.get("expected") or [])
    subclass_set = set(strata.get("expected_subclass") or [])
    return [
        r
        for r in rows
        if (not expected_set or r["expected_doc_class"] in expected_set)
        and (not subclass_set or any(_subclass_matches(r, s) for s in subclass_set))
    ]


def _bucket_candidates(
    rows: list[dict[str, Any]], *, field: str, value: str | None
) -> list[dict[str, Any]]:
    if field == "expected_subclass":
        return [
            r for r in rows if value is None or _subclass_matches(r, value)
        ]
    return [r for r in rows if value is None or r["expected_doc_class"] == value]


def _draw_buckets(
    rows: list[dict[str, Any]],
    buckets: list[dict[str, Any]],
    *,
    field: str,
    sample_seed: int | None,
) -> list[dict[str, Any]]:
    """Per-stratum sub-seeded draws; union; stable-key preserved."""
    keep: set[tuple[str, str]] = set()
    for bucket in buckets:
        value = bucket.get("value") or bucket.get("subclass")
        if field == "expected_doc_class":
            value = bucket.get("doc_class") or bucket.get("value")
        count = bucket.get("count")
        candidates = _bucket_candidates(rows, field=field, value=value)
        if not candidates:
            raise ValueError(
                f"strata bucket {field}={value!r}: no candidate rows in prepared set"
            )
        if count is not None and count < len(candidates):
            if sample_seed is None:
                raise ValueError("sample_seed required for stratified draws")
            bucket_key = f"{field}::{value}"
            sub_seed = int(hashlib.sha256(f"{sample_seed}:{bucket_key}".encode()).hexdigest()[:16], 16)
            drawn = random.Random(sub_seed).sample(candidates, k=count)
        else:
            drawn = candidates
        keep.update(_stable_key(r) for r in drawn)
    return [r for r in rows if _stable_key(r) in keep]


def select_rows(
    rows: list[dict[str, Any]],
    *,
    strata: dict[str, Any] | None,
    sample_seed: int | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    """Deterministic selection: canonical sort, per-stratum sub-seed draws, union, limit."""
    rows = sorted(rows, key=_stable_key)
    strata = strata or {}
    if "buckets" in strata:
        chosen = _draw_buckets(rows, strata["buckets"], field="expected_doc_class", sample_seed=sample_seed)
    elif "values" in strata:
        field = strata_field(strata)
        counts = strata.get("counts") or [None] * len(strata["values"])
        if len(counts) != len(strata["values"]):
            raise ValueError("strata.counts length must match strata.values")
        buckets = [
            {"value": v, "count": c}
            for v, c in zip(strata["values"], counts)
        ]
        chosen = _draw_buckets(rows, buckets, field=field, sample_seed=sample_seed)
    else:
        chosen = rows
    if limit is not None:
        chosen = chosen[:limit]
    return sorted(chosen, key=_stable_key)


def prepare_subset(spec: DatasetSpec, dest_file) -> dict[str, Any]:
    """Materialize the locked subset to ``dest_file``; returns provenance.

    ``file://`` / local paths bypass all Hub calls. Hub path requires
    ``huggingface_hub`` + ``pyarrow`` at call time (lazy imports).
    """
    from pathlib import Path

    dest = Path(dest_file)
    dest.parent.mkdir(parents=True, exist_ok=True)

    local_file = spec.local_file() if spec.is_local() else None
    if local_file is not None:
        if not local_file.is_file():
            raise FileNotFoundError(f"dataset file not found: {local_file}")
        rows = _read_jsonl(local_file)
        source_meta = {"source": "local", "revision": "offline"}
    else:
        rows = load_hf_rows(spec)
        resolved = str(rows[0].get("source_revision") or "") if rows else ""
        source_meta = {
            "source": "huggingface",
            "repo": spec.repo,
            "config": spec.config,
            "split": spec.split,
            "revision": spec.revision or FAMILY_HF_REVISION,
            "revision_resolved": resolved or None,
        }

    rows = normalize_rows(rows)
    rows = filter_rows(rows, spec)
    # DMR-066: refuse silent strata collapse BEFORE the draw…
    strata_guard(rows, spec.strata)
    for r in rows:
        r.setdefault("source_revision", source_meta.get("revision", ""))
        r["expected_fields"] = r.get("expected_fields") or _derive_expected_fields(r)
    chosen = select_rows(rows, strata=spec.strata, sample_seed=spec.sample_seed, limit=spec.limit)
    # …and refuse a draw/limit that dropped a requested stratum AFTER it.
    strata_draw_guard(chosen, spec.strata)

    payload = "".join(_cache_line(r) for r in chosen)
    dest.write_bytes(payload.encode("utf-8"))
    file_sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    counts: dict[str, int] = {}
    for r in chosen:
        key = f"{r['expected_doc_class']}::{r['expected_subclass']}"
        counts[key] = counts.get(key, 0) + 1
    return {
        "rows": len(chosen),
        "sha256": file_sha,
        "strata_actual": dict(sorted(counts.items())),
        "metadata": source_meta,
        "revision_requested": spec.revision or FAMILY_HF_REVISION,
        "revision_resolved": source_meta.get("revision_resolved"),
    }


def _cache_line(row: dict[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False, default=str) + "\n"