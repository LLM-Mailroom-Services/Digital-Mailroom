"""DMR-089: publish_hf_dataset.main_with_args must exit non-zero on a RED verify.

Fully offline: the ``huggingface_hub`` module is replaced with a fake whose
``HfApi`` never touches the network; the index is a tiny synthetic JSONL.
"""

from __future__ import annotations

import hashlib
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import publish_hf_dataset as pub  # noqa: E402


def _install_fake_hub(monkeypatch, hub_sha_for):
    """Install a fake huggingface_hub; ``hub_sha_for(local_bytes)`` -> LFS sha."""

    class FakeApi:
        uploaded: bytes | None = None

        def __init__(self, token=None):
            pass

        def whoami(self):
            return {"name": "fake-user"}

        def create_repo(self, **kw):
            pass

        def upload_folder(self, folder_path, **kw):
            FakeApi.uploaded = (Path(folder_path) / pub.STAGED_NAME).read_bytes()

        def list_repo_tree(self, *a, **kw):
            sha = hub_sha_for(FakeApi.uploaded)
            lfs = types.SimpleNamespace(sha256=sha) if sha else None
            return [types.SimpleNamespace(path=pub.STAGED_NAME, lfs=lfs)]

    fake = types.ModuleType("huggingface_hub")
    fake.HfApi = FakeApi
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake)
    monkeypatch.delenv("HF_TOKEN", raising=False)


def _argv(tmp_path):
    index = tmp_path / "index.jsonl"
    index.write_text(json.dumps({
        "parseable": True,
        "filename": "allen-p/inbox/1.",
        "custodian": "allen-p",
        "folder": "inbox",
        "subject": "Meeting request",
        "body": "Can we meet on Tuesday?",
        "recipients": [],
    }) + "\n", encoding="utf-8")
    return ["--index", str(index),
            "--out", str(tmp_path / "out" / pub.STAGED_NAME),
            "--repo-id", "fake/enron-test"]


def test_red_verification_exits_nonzero(monkeypatch, tmp_path, capsys):
    _install_fake_hub(monkeypatch, lambda data: "0" * 64)  # sha mismatch
    code = pub.main_with_args(_argv(tmp_path))
    assert "VERIFY: RED" in capsys.readouterr().out
    assert code != 0
    summary = json.loads((tmp_path / "out" / "PUBLISH_SUMMARY.json").read_text())
    assert summary["enron_correspondence"]["verified"] is False


def test_missing_hub_file_exits_nonzero(monkeypatch, tmp_path):
    _install_fake_hub(monkeypatch, lambda data: None)  # no LFS entry on the Hub
    assert pub.main_with_args(_argv(tmp_path)) != 0


def test_green_verification_exits_zero(monkeypatch, tmp_path, capsys):
    _install_fake_hub(monkeypatch, lambda data: hashlib.sha256(data).hexdigest())
    code = pub.main_with_args(_argv(tmp_path))
    assert "VERIFY: GREEN" in capsys.readouterr().out
    assert code == 0
    summary = json.loads((tmp_path / "out" / "PUBLISH_SUMMARY.json").read_text())
    assert summary["enron_correspondence"]["verified"] is True


def test_main_returns_main_with_args_code(monkeypatch):
    """main() feeds ``raise SystemExit(main())`` — it must pass the code through."""
    monkeypatch.setattr(pub, "main_with_args", lambda argv: 1)
    assert pub.main() == 1
