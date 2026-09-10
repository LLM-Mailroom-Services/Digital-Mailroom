"""Corpus subset + integrity tests (DMR-027) — network-free."""

from __future__ import annotations

import hashlib
import json

import pytest

from mailroom_sandbox.corpus import (
    normalize_rows,
    prepare_subset,
    select_rows,
    sha256_text,
)
from mailroom_sandbox.job.spec import DatasetSpec


def _write_fixture(tmp_path, rows) -> str:
    path = tmp_path / "fixture.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            r.setdefault("content_sha256", sha256_text(r.get("doc_text") or r.get("text") or ""))
            fh.write(json.dumps(r) + "\n")
    return f"file://{path}"


def _rows(n=6):
    out = []
    for i in range(n):
        cls = "insurance_claim" if i % 2 == 0 else "contract"
        out.append(
            {
                "id": f"doc-{i}",
                "filename": f"f-{i}.txt",
                "doc_text": f"text {i}",
                "expected": cls,
                "expected_subclass": "auto" if cls == "insurance_claim" else "service",
            }
        )
    return out


def test_prepare_local_is_deterministic(tmp_path):
    src = _rows_fixture(tmp_path, _rows())
    dest = tmp_path / "runs" / "d.jsonl"
    p1 = prepare_subset(DatasetSpec(local_path=src), dest)
    p2 = prepare_subset(DatasetSpec(local_path=src), dest)
    assert p1["sha256"] == p2["sha256"]
    assert dest.read_bytes() == dest.read_bytes()


def test_prepare_respects_limit_and_order(tmp_path):
    src = _rows_fixture(tmp_path, _rows(8))
    dest = tmp_path / "d.jsonl"
    prov = prepare_subset(DatasetSpec(local_path=src, limit=3), dest)
    assert prov["rows"] == 3
    rows = [json.loads(l) for l in dest.read_text().splitlines() if l]
    assert [r["id"] for r in rows] == sorted(r["id"] for r in rows)


def test_strata_filter(tmp_path):
    src = _rows_fixture(tmp_path, _rows(10))
    dest = tmp_path / "d.jsonl"
    prov = prepare_subset(
        DatasetSpec(local_path=src, strata={"expected": ["insurance_claim"]}), dest
    )
    rows = [json.loads(l) for l in dest.read_text().splitlines() if l]
    assert rows and all(r["expected_doc_class"] == "insurance_claim" for r in rows)


def test_content_sha_mismatch_raises(tmp_path):
    rows = _rows(2)
    rows[0]["content_sha256"] = "deadbeef"
    src = _rows_fixture(tmp_path, rows)
    with pytest.raises(ValueError):
        prepare_subset(DatasetSpec(local_path=src), tmp_path / "x.jsonl")


def test_select_rows_buckets_deterministic():
    rows = normalize_rows(_rows(12))
    strata = {"buckets": [{"doc_class": "contract", "count": 2}]}
    a = select_rows(rows, strata=strata, sample_seed=7, limit=None)
    b = select_rows(rows, strata=strata, sample_seed=7, limit=None)
    assert [r["id"] for r in a] == [r["id"] for r in b]


def test_stratified_draw_needs_seed(tmp_path):
    src = _rows_fixture(tmp_path, _rows(6))
    spec = DatasetSpec(local_path=src, strata={"buckets": [{"doc_class": "contract", "count": 2}]})
    with pytest.raises(ValueError):
        prepare_subset(spec, tmp_path / "y.jsonl")


def _rows_fixture(tmp_path, rows):
    path = tmp_path / "f.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            r.setdefault("content_sha256", sha256_text(r["doc_text"]))
            fh.write(json.dumps(r) + "\n")
    return f"file://{path}"