"""Corpus subset + integrity tests (DMR-027) — network-free."""

from __future__ import annotations

import hashlib
import json

import pytest

from mailroom_sandbox.corpus import (
    _normalize_subclass,
    load_hf_rows,
    normalize_rows,
    prepare_subset,
    select_rows,
    sha256_text,
)
from mailroom_sandbox.job.spec import DatasetSpec, FAMILY_HF_REVISION


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


def test_jsonl_roundtrip_preserves_unicode_line_separators(tmp_path):
    text = "clause\u2028effective time"
    rows = [
        {
            "id": "u2028",
            "filename": "u2028.txt",
            "doc_text": text,
            "expected": "merger_agreement",
            "expected_subclass": "all_cash",
            "content_sha256": sha256_text(text),
        }
    ]
    src = _rows_fixture(tmp_path, rows)
    dest = tmp_path / "u.jsonl"
    prepare_subset(DatasetSpec(local_path=src), dest)
    loaded = [json.loads(line) for line in dest.open(encoding="utf-8") if line.strip()]
    assert loaded[0]["doc_text"] == text


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


# ── Hub-path tests (DMR-042): stub huggingface_hub, no network ───────────────

def _make_hub_parquet(tmp_path, name, rows):
    """Write a tiny parquet shard and return its path (requires pyarrow)."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pa.Table.from_pylist(rows)
    path = tmp_path / f"{name}.parquet"
    pq.write_table(table, path)
    return path


def _hub_fixture(tmp_path, *, tamper_sha: bool = False):
    """Return (default_rows, gt_rows) and materialize parquet shards in tmp."""
    default_rows = []
    gt_rows = []
    for i in range(3):
        doc_class = "insurance_claim" if i % 2 == 0 else "contract"
        text = f"hub text {i}"
        content_sha = sha256_text(text)
        if tamper_sha and i == 0:
            content_sha = "deadbeef" * 5
        default_rows.append(
            {
                "filename": f"f{i}.txt",
                "doc_text": text,
                "prompt": "",
                "metadata": {"source": "test"},
            }
        )
        gt_rows.append(
            {
                "filename": f"f{i}.txt",
                "expected": doc_class,
                "expected_subclass": "auto" if doc_class == "insurance_claim" else "service",
                "content_sha256": content_sha,
                "split": "test",
            }
        )
    dflt = _make_hub_parquet(tmp_path, "default", default_rows)
    gth = _make_hub_parquet(tmp_path, "ground_truth", gt_rows)
    return dflt, gth


def _stub_hub(monkeypatch, tmp_path, *, tamper_sha: bool = False, files=None):
    """Monkeypatch huggingface_hub calls used by corpus.load_hf_rows."""
    import huggingface_hub

    dflt, gth = _hub_fixture(tmp_path, tamper_sha=tamper_sha)
    parquet_files = {
        "parquet/default/test/test-00000-of-00001.parquet": dflt,
        "parquet/ground_truth/test/test-00000-of-00001.parquet": gth,
    }

    class _FakeInfo:
        sha = FAMILY_HF_REVISION

    def _fake_dataset_info(repo, revision=None):
        return _FakeInfo()

    def _fake_list_repo_files(repo, revision=None, repo_type=None):
        return list(parquet_files)

    def _fake_hf_hub_download(repo, filename, revision=None, repo_type=None, **kw):
        return str(parquet_files[filename])

    monkeypatch.setattr(huggingface_hub.HfApi, "dataset_info", _fake_dataset_info)
    monkeypatch.setattr(huggingface_hub, "list_repo_files", _fake_list_repo_files)
    monkeypatch.setattr(huggingface_hub, "hf_hub_download", _fake_hf_hub_download)


def test_load_hf_rows_merges_and_verifies(monkeypatch, tmp_path):
    _stub_hub(monkeypatch, tmp_path)
    spec = DatasetSpec(provider="huggingface", revision=FAMILY_HF_REVISION)
    rows = load_hf_rows(spec)
    assert len(rows) == 3
    for r in rows:
        assert r["expected"] in {"insurance_claim", "contract"}
        assert r["doc_text"]
        assert r["source_revision"] == FAMILY_HF_REVISION


def test_load_hf_rows_tampered_sha_raises(monkeypatch, tmp_path):
    _stub_hub(monkeypatch, tmp_path, tamper_sha=True)
    spec = DatasetSpec(provider="huggingface", revision=FAMILY_HF_REVISION)
    rows = load_hf_rows(spec)
    with pytest.raises(ValueError):
        normalize_rows(rows)


def test_prepare_subset_hub_path_roundtrip(monkeypatch, tmp_path):
    _stub_hub(monkeypatch, tmp_path)
    dest = tmp_path / "d.jsonl"
    prov = prepare_subset(
        DatasetSpec(provider="huggingface", revision=FAMILY_HF_REVISION, limit=2),
        dest,
    )
    assert prov["rows"] == 2
    assert prov["revision_requested"] == FAMILY_HF_REVISION
    assert prov["metadata"]["source"] == "huggingface"
    rows = [json.loads(l) for l in dest.read_text().splitlines() if l]
    assert all(r["content_sha256"] == sha256_text(r["doc_text"]) for r in rows)


def test_resolve_revision_raises_on_bad_tag(monkeypatch, tmp_path):
    """A non-sha revision that cannot be resolved must surface, not float."""
    import huggingface_hub

    from mailroom_sandbox.corpus import _resolve_revision

    def _boom(repo, revision=None):
        raise RuntimeError("401 Unauthorized")

    monkeypatch.setattr(huggingface_hub.HfApi, "dataset_info", _boom)
    with pytest.raises(RuntimeError, match="cannot resolve"):
        _resolve_revision("some/repo", "some-tag")

# --- DMR-066: subclass-stratified draws + loud strata guards -----------------

def _subclass_rows():
    """Contract rows across raw surfaces incl. CUAD folder spellings."""
    raw = [
        ("d-service-1", "service"),
        ("d-service-2", "service"),
        ("d-supply-1", "supply"),
        ("d-license-1", "License_Agreements"),   # raw surface -> catalog 'license'
        ("d-license-2", "License_Agreements"),
        ("d-ip-1", "IP"),
    ]
    out = []
    for i, (rid, sub) in enumerate(raw):
        out.append(
            {
                "id": rid,
                "filename": f"{rid}.txt",
                "doc_text": f"text {rid}",
                "expected": "contract",
                "expected_doc_class": "contract",
                "expected_subclass": sub,
            }
        )
    return out


def test_values_strata_draws_normalized_subclass_buckets(tmp_path):
    src = _rows_fixture(tmp_path, _subclass_rows())
    dest = tmp_path / "d.jsonl"
    prov = prepare_subset(
        DatasetSpec(
            local_path=src,
            strata={
                "field": "expected_subclass",
                "values": ["service", "license", "ip"],
                "counts": [2, 1, 1],
            },
            sample_seed=42,
        ),
        dest,
    )
    rows = [json.loads(l) for l in dest.read_text().splitlines() if l]
    assert prov["rows"] == 4
    # 'license' requested as a catalog token must match the raw 'License_Agreements'
    assert len(rows) == 4
    ids = sorted(r["id"] for r in rows)
    assert ids == sorted(
        ["d-service-1", "d-service-2", "d-license-1", "d-ip-1"]
    )


def test_values_strata_is_deterministic(tmp_path):
    src = _rows_fixture(tmp_path, _subclass_rows())
    strata = {"field": "expected_subclass", "values": ["service", "supply"], "counts": [1, 1]}
    a = select_rows(normalize_rows(_subclass_rows()), strata=strata, sample_seed=7, limit=None)
    b = select_rows(normalize_rows(_subclass_rows()), strata=strata, sample_seed=7, limit=None)
    assert [r["id"] for r in a] == [r["id"] for r in b]


def test_strata_guard_constant_field_raises(tmp_path):
    # All rows contract; requesting >1 doc-class strata on a constant field
    # must FAIL loudly (the old behavior silently drew contract x N).
    src = _rows_fixture(tmp_path, _subclass_rows())
    spec = DatasetSpec(
        local_path=src,
        strata={"expected": ["contract", "insurance_claim"]},
        sample_seed=42,
    )
    with pytest.raises(ValueError, match="constant"):
        prepare_subset(spec, tmp_path / "y.jsonl")


def test_strata_guard_missing_value_raises(tmp_path):
    src = _rows_fixture(tmp_path, _subclass_rows())
    spec = DatasetSpec(
        local_path=src,
        strata={"field": "expected_subclass", "values": ["service", "reseller"]},
        sample_seed=42,
    )
    with pytest.raises(ValueError, match="absent from prepared rows"):
        prepare_subset(spec, tmp_path / "z.jsonl")


def test_strata_guard_draw_drop_raises(tmp_path):
    # limit truncation that drops a requested stratum must fail loudly.
    src = _rows_fixture(tmp_path, _subclass_rows())
    spec = DatasetSpec(
        local_path=src,
        strata={"field": "expected_subclass", "values": ["service", "supply"], "counts": [1, 1]},
        limit=1,
        sample_seed=42,
    )
    with pytest.raises(ValueError, match="draw/limit dropped requested strata"):
        prepare_subset(spec, tmp_path / "w.jsonl")


def test_values_strata_draw_needs_seed(tmp_path):
    src = _rows_fixture(tmp_path, _subclass_rows())
    spec = DatasetSpec(
        local_path=src,
        strata={"field": "expected_subclass", "values": ["service"], "counts": [1]},
    )
    with pytest.raises(ValueError, match="sample_seed required"):
        prepare_subset(spec, tmp_path / "v.jsonl")


# --- nested sub_buckets (corrected 5-doc-type run spec, DMR-072) ------------

def _five_type_rows():
    """Multi-class, multi-subclass rows mirroring the published corpus shape."""
    raw = [
        ("ins-a1", "insurance_claim", "auto"),
        ("ins-a2", "insurance_claim", "auto"),
        ("ins-p1", "insurance_claim", "property"),
        ("ins-p2", "insurance_claim", "property"),
        ("ins-p3", "insurance_claim", "property"),
        ("ct-s1", "contract", "Service"),
        ("ct-s2", "contract", "Service"),
        ("ct-s3", "contract", "Service"),
        ("ct-l1", "contract", "License_Agreements"),
        ("ct-l2", "contract", "License_Agreements"),
        ("mg-a1", "merger_agreement", "all_cash"),
        ("mg-a2", "merger_agreement", "all_cash"),
        ("mg-o1", "merger_agreement", "other"),
        ("mg-m1", "merger_agreement", "mixed_cash_stock"),
    ]
    out = []
    for rid, cls, sub in raw:
        out.append(
            {
                "id": rid,
                "filename": f"{rid}.txt",
                "doc_text": f"text {rid}",
                "expected": cls,
                "expected_doc_class": cls,
                "expected_subclass": sub,
            }
        )
    return out


def _five_type_strata():
    return {
        "buckets": [
            {
                "doc_class": "insurance_claim",
                "sub_buckets": [
                    {"subclass": "auto", "count": 2},
                    {"subclass": "property", "count": 3},
                ],
            },
            {
                "doc_class": "contract",
                "sub_buckets": [
                    {"subclass": "service", "count": 2},
                    {"subclass": "license", "count": 1},
                ],
            },
            {
                "doc_class": "merger_agreement",
                "sub_buckets": [
                    {"subclass": "all_cash", "count": 1},
                    {"subclass": "other", "count": 1},
                    {"subclass": "mixed_cash_stock", "count": 1},
                ],
            },
        ]
    }


def test_nested_buckets_exact_per_class_subclass_counts(tmp_path):
    src = _rows_fixture(tmp_path, _five_type_rows())
    dest = tmp_path / "d.jsonl"
    prov = prepare_subset(
        DatasetSpec(local_path=src, strata=_five_type_strata(), sample_seed=42, limit=50),
        dest,
    )
    rows = [json.loads(l) for l in dest.read_text().splitlines() if l]
    assert prov["rows"] == 11
    by = {}
    for r in rows:
        key = (
            r["expected_doc_class"],
            _normalize_subclass(r["expected_doc_class"], r["expected_subclass"]),
        )
        by[key] = by.get(key, 0) + 1
    assert by == {
        ("insurance_claim", "auto"): 2,
        ("insurance_claim", "property"): 3,
        ("contract", "service"): 2,
        ("contract", "license"): 1,  # raw surface 'License_Agreements' -> catalog
        ("merger_agreement", "all_cash"): 1,
        ("merger_agreement", "other"): 1,
        ("merger_agreement", "mixed_cash_stock"): 1,
    }
    # zero duplicates across the whole draw
    assert len({(r["id"], r["filename"]) for r in rows}) == len(rows)


def test_nested_buckets_deterministic(tmp_path):
    rows = normalize_rows(_five_type_rows())
    a = select_rows(rows, strata=_five_type_strata(), sample_seed=7, limit=None)
    b = select_rows(rows, strata=_five_type_strata(), sample_seed=7, limit=None)
    assert [r["id"] for r in a] == [r["id"] for r in b]


def test_nested_bucket_over_quota_hard_fails(tmp_path):
    # A quota above the subclass's availability is a spec design bug: loud.
    src = _rows_fixture(tmp_path, _five_type_rows())
    strata = {
        "buckets": [
            {
                "doc_class": "insurance_claim",
                "sub_buckets": [{"subclass": "auto", "count": 3}],  # only 2 auto rows
            }
        ]
    }
    spec = DatasetSpec(local_path=src, strata=strata, sample_seed=42)
    with pytest.raises(ValueError, match="only 2 available"):
        prepare_subset(spec, tmp_path / "q.jsonl")


def test_nested_bucket_missing_subclass_hard_fails(tmp_path):
    # The DMR-066 strata_guard fires BEFORE the draw: an absent requested
    # subclass is a preflight error, not a draw-time surprise.
    src = _rows_fixture(tmp_path, _five_type_rows())
    strata = {
        "buckets": [
            {
                "doc_class": "contract",
                "sub_buckets": [{"subclass": "reseller", "count": 1}],
            }
        ]
    }
    spec = DatasetSpec(local_path=src, strata=strata, sample_seed=42)
    with pytest.raises(ValueError, match="absent from prepared rows"):
        prepare_subset(spec, tmp_path / "r.jsonl")


def test_expand_hf_splits_all_is_train_and_test():
    from mailroom_sandbox.corpus import expand_hf_splits

    assert expand_hf_splits("all") == ("train", "test")
    assert expand_hf_splits("train+test") == ("train", "test")
    assert expand_hf_splits("TEST") == ("test",)
    with pytest.raises(ValueError, match="unknown dataset split"):
        expand_hf_splits("dev")


def test_class_bucket_over_quota_hard_fails(tmp_path):
    src = _rows_fixture(tmp_path, _rows(6))  # 3 contract / 3 insurance_claim
    spec = DatasetSpec(
        local_path=src,
        strata={"buckets": [{"doc_class": "contract", "count": 99}]},
        sample_seed=42,
    )
    with pytest.raises(ValueError, match="only 3 available"):
        prepare_subset(spec, tmp_path / "z.jsonl")


def test_load_hf_rows_all_splits_concatenates(monkeypatch, tmp_path):
    import huggingface_hub

    def _split_rows(split: str, start: int):
        default_rows = []
        gt_rows = []
        for i in range(start, start + 2):
            text = f"hub text {i}"
            default_rows.append(
                {
                    "filename": f"f{i}.txt",
                    "doc_text": text,
                    "prompt": "",
                    "metadata": {"source": "test"},
                }
            )
            gt_rows.append(
                {
                    "filename": f"f{i}.txt",
                    "expected": "contract",
                    "expected_subclass": "service",
                    "content_sha256": sha256_text(text),
                    "split": split,
                }
            )
        return default_rows, gt_rows

    parquet_files = {}
    for split, start in (("train", 0), ("test", 2)):
        dflt, gth = _split_rows(split, start)
        parquet_files[f"parquet/default/{split}/{split}-00000-of-00001.parquet"] = _make_hub_parquet(
            tmp_path, f"default_{split}", dflt
        )
        parquet_files[f"parquet/ground_truth/{split}/{split}-00000-of-00001.parquet"] = _make_hub_parquet(
            tmp_path, f"gt_{split}", gth
        )

    class _FakeInfo:
        sha = FAMILY_HF_REVISION

    monkeypatch.setattr(huggingface_hub.HfApi, "dataset_info", lambda *a, **k: _FakeInfo())
    monkeypatch.setattr(huggingface_hub, "list_repo_files", lambda *a, **k: list(parquet_files))
    monkeypatch.setattr(
        huggingface_hub,
        "hf_hub_download",
        lambda repo, filename, revision=None, repo_type=None, **kw: str(parquet_files[filename]),
    )
    spec = DatasetSpec(provider="huggingface", revision=FAMILY_HF_REVISION, split="all")
    rows = load_hf_rows(spec)
    assert len(rows) == 4
    assert {r["filename"] for r in rows} == {"f0.txt", "f1.txt", "f2.txt", "f3.txt"}
    assert {r["split"] for r in rows} == {"train", "test"}
