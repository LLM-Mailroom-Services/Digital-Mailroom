"""The demos notebook and markdown index must cover every still + the PR video."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
DEMOS = ROOT / "docs" / "demos"
NOTEBOOK = DEMOS / "The-Mailroom-Demos.ipynb"
INDEX = ROOT / "docs" / "demos.md"
WIKI = ROOT / "wiki" / "Demos.md"
README = ROOT / "README.md"
VIDEO = "tui-server-observatory-desk-walkthrough.mp4"
PILOT_VIDEO = "pilot-run-documents-through-pipeline.mp4"
V030_PIXEL = "v030-pixel-desks-review-resolve.mp4"
V030_OBS = "v030-observatory-review-resolve.mp4"
HF_SPACE = "hf-space-observatory-live-walkthrough.mp4"
VIDEOS = (VIDEO, PILOT_VIDEO, V030_PIXEL, V030_OBS, HF_SPACE)


def _notebook_text() -> str:
    nb = json.loads(NOTEBOOK.read_text())
    chunks = []
    for cell in nb["cells"]:
        chunks.extend(cell.get("source") or [])
    return "".join(chunks)


@pytest.mark.skipif(
    not DEMOS.is_dir(),
    reason="docs/demos pruned in the mailroom-hub monorepo (heavy assets live upstream)",
)
def test_walkthrough_video_is_in_demos():
    for name in VIDEOS:
        path = DEMOS / name
        assert path.is_file(), path
        assert path.stat().st_size > 1_000_000, name
    assert (DEMOS / "walkthrough-poster.png").is_file()
    assert (DEMOS / "pilot-run-poster.png").is_file()
    assert (DEMOS / "hf-space-observatory-poster.png").is_file()


@pytest.mark.skipif(
    not SHOTS.is_dir(),
    reason="docs/screenshots pruned in the mailroom-hub monorepo (heavy assets live upstream)",
)
def test_notebook_and_indexes_cover_every_png():
    pngs = sorted(p.name for p in SHOTS.glob("*.png"))
    assert len(pngs) >= 17, pngs
    nb = _notebook_text()
    demos_md = INDEX.read_text()
    wiki = WIKI.read_text()
    readme = README.read_text()
    for name in pngs:
        assert name in nb, f"notebook missing {name}"
        assert name in demos_md, f"docs/demos.md missing {name}"
        assert name in wiki, f"wiki/Demos.md missing {name}"
        assert name in readme, f"README missing {name}"
    for blob in (nb, demos_md, wiki, readme):
        for name in VIDEOS:
            assert name in blob, f"missing {name}"
    assert "The-Mailroom-Demos.ipynb" in readme
    assert "The-Mailroom-Demos.ipynb" in demos_md
    assert "demo_pilot_run.py" in readme or "demo_pilot_run.py" in demos_md
