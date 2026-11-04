"""Dojo source resolution: the installed release first, the vendored snapshot as fallback."""
from __future__ import annotations

import re
import sys
import types
from pathlib import Path

import pytest

from mailroom_sandbox import dojo_source
from mailroom_sandbox.paths import repo_root, vendored_dojo_src

PIN = dojo_source.pinned()


@pytest.fixture
def isolated(monkeypatch):
    """Restore sys.path, sys.modules['llm_dojo_scoring*'] and the cached choice after each test."""
    saved_path = list(sys.path)
    saved_mods = {k: v for k, v in sys.modules.items() if k.startswith("llm_dojo_scoring")}
    saved_choice = dojo_source._CHOICE
    monkeypatch.delenv("DOJO_SRC", raising=False)
    monkeypatch.delenv("SANDBOX_DOJO_SOURCE", raising=False)
    yield monkeypatch
    sys.path[:] = saved_path
    for k in [k for k in sys.modules if k.startswith("llm_dojo_scoring")]:
        del sys.modules[k]
    sys.modules.update(saved_mods)
    dojo_source._CHOICE = saved_choice


def _installed(monkeypatch, version, commit, *, import_error=None, origin_error=None):
    monkeypatch.setattr(dojo_source, "installed", lambda: {"version": version, "commit": commit})
    monkeypatch.setattr(dojo_source, "_import_ok", lambda: import_error)
    monkeypatch.setattr(dojo_source, "_origin_mismatch", lambda: origin_error)


def test_pin_matches_vendor_and_extra():
    assert PIN["version"] and re.fullmatch(r"[0-9a-f]{40}", PIN["commit"] or "")
    release = (repo_root() / "requirements" / "dojo-release.txt").read_text(encoding="utf-8")
    assert f"llm-dojo-scoring.git@{PIN['commit']}" in release


def test_not_installed_falls_back_to_vendored(isolated):
    isolated.setattr(dojo_source, "installed", lambda: None)
    choice = dojo_source.choose()
    assert choice.source == "vendored" and "not installed" in choice.reason
    assert sys.path[0] == str(vendored_dojo_src().resolve())


def test_matching_release_is_primary(isolated):
    _installed(isolated, PIN["version"], PIN["commit"])
    choice = dojo_source.choose()
    assert choice.source == "installed" and choice.path is None
    assert all(Path(p).resolve() != vendored_dojo_src().resolve() for p in sys.path if p)
    assert dojo_source.import_root() is None


@pytest.mark.parametrize("version,commit,why", [("0.1.0", None, "!= pinned"), (PIN["version"], "f" * 40, "commit"),
                                                 (PIN["version"], None, "no recorded commit")])
def test_off_pin_release_falls_back_in_auto(isolated, version, commit, why):
    _installed(isolated, version, commit)
    choice = dojo_source.choose()
    assert choice.source == "vendored" and why in choice.reason


def test_installed_mode_accepts_off_pin(isolated):
    _installed(isolated, "0.1.0", None)
    assert dojo_source.choose(mode="installed").source == "installed"


def test_broken_release_falls_back(isolated):
    _installed(isolated, PIN["version"], PIN["commit"], import_error="ImportError: boom")
    choice = dojo_source.choose()
    assert choice.source == "vendored" and "failed to import" in choice.reason


def test_vendored_mode_and_env_override(isolated, tmp_path):
    _installed(isolated, PIN["version"], PIN["commit"])
    assert dojo_source.choose(mode="vendored").source == "vendored"
    (tmp_path / "llm_dojo_scoring").mkdir()
    (tmp_path / "llm_dojo_scoring" / "__init__.py").write_text("")
    isolated.setenv("DOJO_SRC", str(tmp_path))
    choice = dojo_source.choose()
    assert choice.source == "env" and sys.path[0] == str(tmp_path.resolve())


def test_import_failure_purges_partial_modules(isolated):
    isolated.setitem(sys.modules, "llm_dojo_scoring.partial", types.ModuleType("x"))
    dojo_source._purge()
    assert "llm_dojo_scoring.partial" not in sys.modules


def test_resolve_dojo_src_skips_prepend_for_installed(isolated):
    from mailroom_sandbox.runtime import resolve_dojo_src

    _installed(isolated, PIN["version"], PIN["commit"])
    dojo_source.choose()
    assert resolve_dojo_src() is None


def test_installed_mode_still_accepts_an_unknown_commit(isolated):
    _installed(isolated, PIN["version"], None)
    assert dojo_source.choose(mode="installed").source == "installed"


def test_a_shadowing_checkout_falls_back(isolated):
    """A module that imports from somewhere other than the installed distribution is not recorded as it."""
    _installed(isolated, PIN["version"], PIN["commit"], origin_error="llm_dojo_scoring imported from /elsewhere")
    choice = dojo_source.choose()
    assert choice.source == "vendored" and "/elsewhere" in choice.reason


def test_origin_mismatch_compares_the_module_file(isolated, tmp_path):
    pkg = tmp_path / "site" / "llm_dojo_scoring"
    isolated.setattr(dojo_source, "_installed_package_dirs", lambda: [pkg.resolve()])
    isolated.setitem(sys.modules, "llm_dojo_scoring", types.SimpleNamespace(__file__=str(pkg / "__init__.py")))
    assert dojo_source._origin_mismatch() is None
    other = tmp_path / "checkout" / "llm_dojo_scoring" / "__init__.py"
    isolated.setitem(sys.modules, "llm_dojo_scoring", types.SimpleNamespace(__file__=str(other)))
    assert "checkout" in dojo_source._origin_mismatch()


def test_policy_is_read_from_dotenv(isolated, tmp_path):
    """SANDBOX_DOJO_SOURCE in .env applies even though choose() runs before the CLI loads .env."""
    env = tmp_path / ".env"
    env.write_text("SANDBOX_DOJO_SOURCE=vendored\n")
    isolated.delenv("SANDBOX_SKIP_DOTENV", raising=False)
    isolated.setattr(dojo_source, "dotenv_files", lambda: [env])
    _installed(isolated, PIN["version"], PIN["commit"])
    assert dojo_source.choose().source == "vendored"
    isolated.setenv("SANDBOX_DOJO_SOURCE", "auto")  # the real environment wins over .env
    assert dojo_source.choose().source == "installed"
