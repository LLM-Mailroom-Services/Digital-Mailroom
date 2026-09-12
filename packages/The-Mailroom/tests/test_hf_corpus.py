"""Unit tests for the pinned Hub docclass-merged corpus helper."""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import mailroom_ui.hf_corpus as hf


class _Resp:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self._payload).encode()


def test_defaults_pin_corrected_merged(monkeypatch):
    monkeypatch.delenv("MAILROOM_HF_DATASET", raising=False)
    monkeypatch.delenv("MAILROOM_HF_REVISION", raising=False)
    monkeypatch.delenv("MAILROOM_HF_CONFIG", raising=False)
    assert hf.corpus_id() == "Lucius-Morningstar/mailroom-dataset"
    assert hf.corpus_revision() == hf.FULL_CORPUS_REVISION
    assert hf.gt_config() == "ground_truth"
    assert hf.FULL_CORPUS_REVISION.startswith("fe3a6f96")


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("MAILROOM_HF_DATASET", "Lucius-Morningstar/other")
    monkeypatch.setenv("MAILROOM_HF_REVISION", "abc123")
    monkeypatch.setenv("MAILROOM_HF_CONFIG", "default")
    assert hf.corpus_id() == "Lucius-Morningstar/other"
    assert hf.corpus_revision() == "abc123"
    assert hf.gt_config() == "default"


def test_fetch_rows_passes_revision(monkeypatch):
    seen: list[str] = []

    def fake_urlopen(req, timeout=0):  # noqa: ARG001
        seen.append(req.full_url)
        return _Resp(
            {
                "rows": [
                    {"row": {"filename": "a.txt", "expected": "contract"}},
                ]
            }
        )

    monkeypatch.setattr(hf.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("MAILROOM_HF_REVISION", "deadbeef")
    rows = hf.fetch_rows(config="ground_truth", split="train", page_size=10)
    assert rows == [{"filename": "a.txt", "expected": "contract"}]
    assert len(seen) == 1
    q = parse_qs(urlparse(seen[0]).query)
    assert q["dataset"] == ["Lucius-Morningstar/mailroom-dataset"]
    assert q["config"] == ["ground_truth"]
    assert q["revision"] == ["deadbeef"]


def test_load_ground_truth_indexes_filename(monkeypatch):
    def fake_fetch_rows(**kwargs):
        if kwargs["split"] == "train":
            return [{"filename": "x.htm", "expected": "corporate_record"}]
        return [{"filename": "y.htm", "expected": "contract"}]

    monkeypatch.setattr(hf, "fetch_rows", fake_fetch_rows)
    by_file = hf.load_ground_truth()
    assert by_file["x.htm"]["expected"] == "corporate_record"
    assert by_file["y.htm"]["expected"] == "contract"
