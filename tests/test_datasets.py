"""Full-corpus cache + offline per-class sampling (network-free)."""

from __future__ import annotations

import json

from mailroom_sandbox.corpus import sha256_text
from mailroom_sandbox.datasets import sample_cached_corpus
from mailroom_sandbox.job.spec import LIVE_DOC_CLASSES


def _write_mini_corpus(path, per_class: int = 5) -> None:
    rows = []
    for cls in LIVE_DOC_CLASSES:
        for i in range(per_class):
            text = f"{cls} {i}"
            rows.append(
                {
                    "id": f"{cls}-{i}",
                    "filename": f"{cls}-{i}.txt",
                    "doc_text": text,
                    "expected_doc_class": cls,
                    "expected_subclass": "other",
                    "content_sha256": sha256_text(text),
                }
            )
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_sample_cached_corpus_per_class(tmp_path, capsys):
    src = tmp_path / "full.jsonl"
    dest = tmp_path / "n2.jsonl"
    _write_mini_corpus(src, per_class=5)
    out = sample_cached_corpus(2, source=src, dest=dest, sample_seed=42)
    assert out == dest
    loaded = [json.loads(line) for line in dest.read_text().splitlines() if line]
    assert len(loaded) == 2 * len(LIVE_DOC_CLASSES)
    counts = {}
    for row in loaded:
        counts[row["expected_doc_class"]] = counts.get(row["expected_doc_class"], 0) + 1
    assert counts == {cls: 2 for cls in LIVE_DOC_CLASSES}
    assert "sampled 10 row(s)" in capsys.readouterr().out


def test_sample_cached_corpus_over_quota_fails(tmp_path):
    src = tmp_path / "full.jsonl"
    _write_mini_corpus(src, per_class=3)
    import pytest

    with pytest.raises(ValueError, match="exceeds contract availability"):
        sample_cached_corpus(4, source=src, dest=tmp_path / "x.jsonl", sample_seed=42)
