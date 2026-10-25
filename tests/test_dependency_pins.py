"""Optional extras must resolve immutable, mutually compatible refs.

The 2026-10-25 drift audit flagged the visualizer for pinning a *movable*
release tag while the pipeline pinned an exact commit, and for extras that
demanded different Dojo versions. These tests parse the real ``pyproject``
so re-introducing a tag (or drifting the extras apart) fails here.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOJO_RELEASE_COMMIT = "4740d76825217e746c645864c8510f12869db965"
PIPELINE_REVIEW_COMMIT = "60cd5fad0c7a616ec575857841bb9897b9e8c3ed"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _extras() -> dict[str, list[str]]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return data["project"]["optional-dependencies"]


def _ref(dep: str) -> str:
    return dep.rsplit("@", 1)[-1]


def test_eval_extra_pins_the_immutable_dojo_release_commit():
    deps = [d for d in _extras()["eval"] if d.startswith("llm-dojo-scoring")]
    assert len(deps) == 1
    ref = _ref(deps[0])
    assert _SHA_RE.match(ref), f"eval pin is not an immutable commit: {ref}"
    assert ref == DOJO_RELEASE_COMMIT


def test_pipeline_extra_pins_an_immutable_producer_commit():
    deps = [d for d in _extras()["pipeline"] if d.startswith("mailroom @")]
    assert len(deps) == 1
    ref = _ref(deps[0])
    assert _SHA_RE.match(ref), f"pipeline pin is not an immutable commit: {ref}"
    assert ref == PIPELINE_REVIEW_COMMIT


def test_combined_extras_only_reference_immutable_commits():
    """`pip install -e ".[eval,pipeline]"` resolves both extras at once."""
    combined = _extras()["eval"] + _extras()["pipeline"]
    refs = {
        _ref(d)
        for d in combined
        if d.startswith(("llm-dojo-scoring", "mailroom @"))
    }
    assert refs == {DOJO_RELEASE_COMMIT, PIPELINE_REVIEW_COMMIT}
