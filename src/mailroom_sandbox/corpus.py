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

from mailroom_sandbox.job.spec import (
    DatasetSpec,
    FAMILY_CLASS_COUNTS,
    FAMILY_HF_REVISION,
    LIVE_DOC_CLASSES,
)

_log = logging.getLogger("mailroom_sandbox.corpus")

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_ALL_SPLIT_ALIASES = frozenset({"all", "*", "both", "train+test", "train,test"})


def expand_hf_splits(split: str) -> tuple[str, ...]:
    """Map a DatasetSpec.split value onto parquet split names.

    ``all`` / ``train+test`` loads BOTH evaluation partitions (3,302 rows at
    the family pin). The Hub 90/10 split is an evaluation partition, not ML
    train/test — Modal 20/40/100-per-class draws must use ``all``.
    """
    raw = (split or "test").strip().lower().replace(" ", "")
    if raw in _ALL_SPLIT_ALIASES:
        return ("train", "test")
    if raw in {"train", "test"}:
        return (raw,)
    raise ValueError(
        f"unknown dataset split {split!r} — use train, test, or all (train+test)"
    )


def per_class_strata(per_class: int) -> dict[str, Any]:
    """Strata block: ``per_class`` rows from each live extract class."""
    if not isinstance(per_class, int) or per_class < 1:
        raise ValueError(f"per_class must be a positive int (got {per_class!r})")
    return {
        "buckets": [
            {"doc_class": cls, "count": per_class} for cls in LIVE_DOC_CLASSES
        ]
    }


def _ensure_hf_home() -> None:
    """Keep Hub parquet in the sandbox cache (gitignored ``data/cache/hf``)."""
    import os

    from mailroom_sandbox.paths import repo_root

    hf_home = repo_root() / "data" / "cache" / "hf"
    hf_home.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(hf_home))


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
    """Read JSONL without ``str.splitlines()``.

    Legal ``doc_text`` can contain U+2028/U+2029; ``splitlines()`` would
    break a ``json.dumps(ensure_ascii=False)`` record in the middle.
    """
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
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
    """Fetch pinned parquet shards, merge default+ground_truth, return raw rows.

    ``split=all`` concatenates train+test (the full 3,302-row evaluation
    corpus). Duplicate ``filename`` across splits is a pin-integrity failure.
    """
    import huggingface_hub

    _ensure_hf_home()
    repo = spec.repo
    revision = spec.revision or FAMILY_HF_REVISION
    resolved = _resolve_revision(repo, revision)
    files = set(huggingface_hub.list_repo_files(repo, revision=resolved, repo_type="dataset"))
    splits = expand_hf_splits(spec.split)

    def shard(config: str, split: str) -> str:
        return f"parquet/{config}/{split}/{split}-00000-of-00001.parquet"

    def read_config(config: str, split: str) -> list[dict[str, Any]] | None:
        f = shard(config, split)
        if f not in files:
            return None
        path = huggingface_hub.hf_hub_download(repo, f, revision=resolved, repo_type="dataset")
        return _read_parquet(path)

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for split in splits:
        default = read_config("default", split)
        ground_truth = read_config("ground_truth", split)
        if ground_truth is not None:
            merged = merge_default_and_gt(default or [], ground_truth)
        elif default is not None:
            if spec.config in ("", "ground_truth"):
                # The blind rows would be scored as unlabeled (expected_doc_class
                # "") — a silent 0.0/unknown scorecard. Refuse instead (DMR-049).
                raise RuntimeError(
                    f"ground_truth config is absent at {repo}@{resolved} for split "
                    f"{split!r} — refusing to prepare blind rows as labeled data"
                )
            merged = default
        else:
            cfg = read_config(spec.config, split)
            if cfg is None:
                raise RuntimeError(
                    f"no parquet shards for {spec.config or 'default'} / {split} "
                    f"at {repo}@{resolved}"
                )
            merged = cfg
        for row in merged:
            fname = str(row.get("filename") or "")
            if fname in seen:
                raise RuntimeError(
                    f"duplicate filename {fname!r} across splits at {repo}@{resolved}"
                )
            seen.add(fname)
            row["source_revision"] = resolved
            row.setdefault("split", split)
            out.append(row)
    return out


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
        # SAND-019: the pinned HF ``ground_truth`` config names its field-level
        # labels ``gt_fields`` (a JSON string); ``expected_fields`` only exists
        # on the local fixture/derived shape. Reading only the latter silently
        # produced {} for all 3,302 corpus rows, so every specialist extraction
        # scored null. Prefer the explicit key, then fall back to the Hub column.
        expected_fields = row.get("expected_fields")
        if expected_fields is None:
            expected_fields = row.get("gt_fields")
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
            for sb in b.get("sub_buckets") or []:
                ssc = str(sb.get("subclass") or "")
                if ssc:
                    out.add(("expected_subclass", ssc))
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


def _seeded_prefix(
    candidates: list[dict[str, Any]], count: int, *, seed: int
) -> list[dict[str, Any]]:
    """Deterministic prefix of a seeded shuffle (nested draws: k ⊂ m when k < m)."""
    if count >= len(candidates):
        return list(candidates)
    rng = random.Random(seed)
    ordered = list(candidates)
    rng.shuffle(ordered)
    return ordered[:count]


def _draw_buckets(
    rows: list[dict[str, Any]],
    buckets: list[dict[str, Any]],
    *,
    field: str,
    sample_seed: int | None,
) -> list[dict[str, Any]]:
    """Per-stratum sub-seeded draws; union; stable-key preserved.

    A doc_class bucket may carry ``sub_buckets`` (per-subclass quotas within
    the class): each quota is drawn from the class candidates matching that
    subclass, sub-seeded per ``field::class::subclass``, with earlier
    sub-bucket picks excluded from later ones so the bucket total is exactly
    the quota sum (zero duplicates by construction across the whole strata
    block). A quota above the subclass's availability HARD-FAILS (loud — a
    shortfall here is a spec design bug, not a truncate-and-warn condition).
    """
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
        sub_buckets = bucket.get("sub_buckets") or []
        if sub_buckets and field == "expected_doc_class":
            drawn: list[dict[str, Any]] = []
            excluded: set[tuple[str, str]] = set()
            for sb in sub_buckets:
                sc = str(sb.get("subclass") or sb.get("value") or "")
                c = sb.get("count")
                if not sc or not isinstance(c, int) or c < 1:
                    raise ValueError(
                        "strata sub_bucket requires a 'subclass' and a positive "
                        f"'count' (got {sb!r})"
                    )
                sub_candidates = [
                    r
                    for r in candidates
                    if _stable_key(r) not in excluded and _subclass_matches(r, sc)
                ]
                if not sub_candidates:
                    raise ValueError(
                        f"strata sub_bucket {value!r}::{sc!r}: no candidate rows "
                        "in prepared set"
                    )
                if c > len(sub_candidates):
                    raise ValueError(
                        f"strata sub_bucket {value!r}::{sc!r}: requested {c} but "
                        f"only {len(sub_candidates)} available"
                    )
                bucket_key = f"{field}::{value}::{sc}"
                if c < len(sub_candidates):
                    if sample_seed is None:
                        raise ValueError("sample_seed required for stratified draws")
                    sub_seed = int(hashlib.sha256(f"{sample_seed}:{bucket_key}".encode()).hexdigest()[:16], 16)
                    picked = _seeded_prefix(sub_candidates, c, seed=sub_seed)
                else:
                    picked = sub_candidates
                drawn.extend(picked)
                excluded.update(_stable_key(r) for r in picked)
            keep.update(_stable_key(r) for r in drawn)
        else:
            if count is not None and count > len(candidates):
                hint = ""
                if str(value) in FAMILY_CLASS_COUNTS:
                    hint = (
                        f" (full-corpus availability at FAMILY_HF_REVISION is "
                        f"{FAMILY_CLASS_COUNTS[str(value)]}; use split=all — "
                        f"test-only cannot back 40/100-per-class draws)"
                    )
                raise ValueError(
                    f"strata bucket {field}={value!r}: requested {count} but "
                    f"only {len(candidates)} available{hint}"
                )
            if count is not None and count < len(candidates):
                if sample_seed is None:
                    raise ValueError("sample_seed required for stratified draws")
                bucket_key = f"{field}::{value}"
                sub_seed = int(hashlib.sha256(f"{sample_seed}:{bucket_key}".encode()).hexdigest()[:16], 16)
                drawn = _seeded_prefix(candidates, count, seed=sub_seed)
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
    dest.write_text(payload, encoding="utf-8")
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