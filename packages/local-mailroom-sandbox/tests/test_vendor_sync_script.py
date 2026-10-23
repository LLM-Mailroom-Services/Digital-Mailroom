"""The local snapshot helper must attempt every requested source tree."""
import importlib.util
from pathlib import Path

import pytest


@pytest.mark.parametrize("failure", ["missing_source", "os_error"])
def test_sync_vendor_script_refreshes_later_source_after_failure(tmp_path, monkeypatch, failure, capsys):
    """A failed first source does not prevent a valid later snapshot refresh."""
    script = Path(__file__).resolve().parents[1] / "scripts/sync_vendor.py"
    spec = importlib.util.spec_from_file_location("sandbox_vendor_sync_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "second-source"
    source.mkdir()
    (source / "scorer.py").write_text("SOURCE_SENTINEL = 42\n")
    (source / "tests").mkdir()
    (source / "tests/ignored.py").write_text("ignored = True\n")
    first_source = tmp_path / "missing"
    if failure == "os_error":
        first_source = source
        (tmp_path / "vendor").mkdir()
        (tmp_path / "vendor/first").write_text("blocks destination directory\n")
    monkeypatch.setattr(module, "REPO", tmp_path)
    monkeypatch.setattr(module, "_SNAPSHOTS", [
        ("first", tmp_path / "vendor/first", first_source),
        ("second", tmp_path / "vendor/second", source),
    ])
    monkeypatch.setattr("sys.argv", [str(script)])
    assert module.main() == 1
    assert "error:" in capsys.readouterr().err
    assert (tmp_path / "vendor/second/scorer.py").read_text() == "SOURCE_SENTINEL = 42\n"
    assert not (tmp_path / "vendor/second/tests").exists()
