"""SAND-042 figure rendering: per-run, per-cell and master PNGs (network-free, no LLM)."""

from __future__ import annotations

import json

import pytest

from mailroom_sandbox.job import sand42_cards, sand42_figures as figs
from mailroom_sandbox.paths import repo_root

CELL = "1l4-c8"
REAL_CARD = (
    sand42_cards.specialist_dir(CELL, "contracts_specialist", repo=repo_root())
    / "sand42-50-contracts-specialist-awq-1l4-c8.card.json"
)


def _card(run_id: str) -> dict:
    return {
        "run_id": run_id,
        "specialist": "Contracts",
        "task": "contracts_specialist",
        "n": 3,
        "conditions": {
            "replicas": 1,
            "concurrency": 8,
            "model": "Qwen/Qwen3-8B-AWQ",
            "spec_hash": "deadbeefdeadbeefdeadbeef",
        },
        "quality": {"ok": 3, "errors": 0, "overall_mean": 0.5, "overall_sd": 0.1},
        "latency": {"p50": 2.0, "p95": 4.0, "mean": 2.3, "max": 3.0},
        "cost": {"usd_per_ok_document": 0.001, "usd_per_document": 0.001, "busy_gpu_usd": 0.01},
        "throughput": {"documents_per_minute": 10.0, "tokens_per_second_per_gpu": 100.0},
        "engine_telemetry": {
            "gpu": {
                "captured": True,
                "util_mean_perc": 90.0,
                "util_p95_perc": 99.0,
                "util_peak_perc": 100.0,
                "sampling_coverage_pct": 100.0,
                "power_draw_w": {"mean": 70.0, "max": 75.0},
                "temperature_c": {"mean": 60.0, "max": 70.0},
            }
        },
        "documents": [
            {"score": 0.4, "latency_seconds": 1.5, "ok": True},
            {"score": 0.6, "latency_seconds": 2.5, "ok": True},
            {"score": 0.5, "latency_seconds": 3.0, "ok": True},
        ],
    }


def _fake_tree(repo, cell: str) -> None:
    for run_id in sand42_cards.cell_run_ids(cell):
        task = sand42_cards._task_of(run_id)
        directory = sand42_cards.specialist_dir(cell, task, repo=repo)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{run_id}.card.json").write_text(json.dumps(_card(run_id)), encoding="utf-8")


def _png_ok(path):
    return path.is_file() and path.stat().st_size > 0 and path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


# ── per-run dashboard ────────────────────────────────────────────────────────


def test_maybe_write_run_figure_from_committed_card(tmp_path):
    if not REAL_CARD.is_file():
        pytest.skip("committed 1L4-c8 contracts card absent")
    card = json.loads(REAL_CARD.read_text(encoding="utf-8"))
    path = figs.maybe_write_run_figure(card, tmp_path)
    assert path == tmp_path / "sand42-50-contracts-specialist-awq-1l4-c8.card.png"
    assert _png_ok(path)


def test_maybe_write_run_figure_from_synthetic_card(tmp_path):
    path = figs.maybe_write_run_figure(_card("sand42-synthetic-1"), tmp_path)
    assert path is not None and _png_ok(path)


def test_broken_card_returns_none_without_raising(tmp_path):
    for broken in ({"run_id": "x"}, {"run_id": "y", "documents": "not-a-list"}, None, "nope", []):
        assert figs.maybe_write_run_figure(broken, tmp_path) is None
    assert not list(tmp_path.glob("*.png"))


def test_run_figure_is_byte_stable(tmp_path):
    if not REAL_CARD.is_file():
        pytest.skip("committed 1L4-c8 contracts card absent")
    card = json.loads(REAL_CARD.read_text(encoding="utf-8"))
    first = figs.maybe_write_run_figure(card, tmp_path / "a")
    second = figs.maybe_write_run_figure(card, tmp_path / "b")
    assert first is not None and second is not None
    assert first.read_bytes() == second.read_bytes()


# ── per-cell dashboard ───────────────────────────────────────────────────────


def test_write_cell_figure_from_fake_tree(tmp_path):
    _fake_tree(tmp_path, CELL)
    path = figs.maybe_write_cell_figure(CELL, repo=tmp_path)
    assert path == tmp_path / "reports" / "SAND42" / "figures" / "1l4-c8-dashboard.png"
    assert _png_ok(path)


def test_write_cell_figure_none_when_empty_or_unknown(tmp_path):
    assert figs.maybe_write_cell_figure(CELL, repo=tmp_path) is None  # no cards in the fake repo
    assert figs.maybe_write_cell_figure("nope", repo=tmp_path) is None


# ── master figures ───────────────────────────────────────────────────────────


def test_master_figure_paths_has_five_keys_under_the_study(tmp_path):
    paths = figs.master_figure_paths(repo=tmp_path)
    assert set(paths) == {"quality", "cost", "latency", "throughput", "gpu"}
    for key, path in paths.items():
        assert path == tmp_path / "reports" / "SAND42" / "figures" / f"cmp-{key}.png"


def test_write_master_figures_from_fake_tree(tmp_path):
    _fake_tree(tmp_path, CELL)
    written = figs.maybe_write_master_figures(repo=tmp_path)
    assert [p.name for p in written] == [
        "cmp-quality.png", "cmp-cost.png", "cmp-latency.png", "cmp-throughput.png", "cmp-gpu.png",
    ]
    assert all(_png_ok(p) for p in written)


def test_write_master_figures_empty_repo_is_empty(tmp_path):
    assert figs.maybe_write_master_figures(repo=tmp_path) == []
