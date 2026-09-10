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
import random
import re
from typing import Any

from mailroom_sandbox.job.spec import DatasetSpec, FAMILY_HF_REVISION

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
            expected_fields = {}
        out.append(
            {
                "id": str(row.get("id") or row.get("document_id") or row.get("filename")),
                "filename": str(row.get("filename") or row.get("id")),
                "doc_text": text,
                "expected_doc_class": doc_class,
                "expected_subclass": row.get("expected_subclass"),
                "expected_fields": dict(expected_fields or {}),
                "content_sha256": content_sha,
                "split": row.get("split", ""),
                "source_revision": row.get("source_revision", ""),
            }
        )
    return out


def _derive_expected_fields(row: dict[str, Any]) -> dict[str, Any]:
    explicit = row.get("expected_fields")
    if explicit:
        return explicit
    doc_class = str(row.get("expected_doc_class") or "")
    keys = GT_FIELD_LISTS.get(doc_class, [])
    return {k: row.get(k) for k in keys if row.get(k) not in (None, "")}


def filter_rows(rows: list[dict[str, Any]], spec: DatasetSpec) -> list[dict[str, Any]]:
    if spec.exclude_expected:
        rows = [r for r in rows if r["expected_doc_class"] not in set(spec.exclude_expected)]
    strata = spec.strata or {}
    if not strata:
        return rows
    if "buckets" in strata:
        return rows
    expected_set = set(strata.get("expected") or [])
    subclass_set = set(strata.get("expected_subclass") or [])
    return [
        r
        for r in rows
        if (not expected_set or r["expected_doc_class"] in expected_set)
        and (not subclass_set or r["expected_subclass"] in subclass_set)
    ]


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
    if "buckets" not in strata:
        chosen = rows
    else:
        keep: set[tuple[str, str]] = set()
        for bucket in strata["buckets"]:
            doc_class = bucket.get("doc_class")
            subclass = bucket.get("subclass")
            count = bucket.get("count")
            candidates = [
                r
                for r in rows
                if r["expected_doc_class"] == doc_class
                and (subclass is None or r["expected_subclass"] == subclass)
            ]
            if not candidates:
                continue
            if count is not None and count < len(candidates):
                if sample_seed is None:
                    raise ValueError("sample_seed required for stratified draws")
                bucket_key = f"{doc_class}::{subclass}"
                sub_seed = int(hashlib.sha256(f"{sample_seed}:{bucket_key}".encode()).hexdigest()[:16], 16)
                drawn = random.Random(sub_seed).sample(candidates, k=count)
            else:
                drawn = candidates
            keep.update(_stable_key(r) for r in drawn)
        chosen = [r for r in rows if _stable_key(r) in keep]
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
        source_meta = {
            "source": "huggingface",
            "repo": spec.repo,
            "config": spec.config,
            "split": spec.split,
            "revision": spec.revision or FAMILY_HF_REVISION,
        }

    rows = normalize_rows(rows)
    rows = filter_rows(rows, spec)
    for r in rows:
        r.setdefault("source_revision", source_meta.get("revision", ""))
        r["expected_fields"] = r.get("expected_fields") or _derive_expected_fields(r)
    chosen = select_rows(rows, strata=spec.strata, sample_seed=spec.sample_seed, limit=spec.limit)

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
    }


def _cache_line(row: dict[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False, default=str) + "\n"