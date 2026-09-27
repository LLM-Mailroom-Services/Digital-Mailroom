"""DMR-077 — two-operator suite manifests + estimate-suite track filter."""

from __future__ import annotations

from pathlib import Path

import pytest

from mailroom_sandbox.job import metrics
from mailroom_sandbox.job.suite import (
    DEFAULT_TRACK_A_PROFILE,
    MODAL_PROFILE_ENV_TRACK_B,
    SUITE_ALIASES,
    load_suite,
    list_suite_ids,
    resolve_suite_path,
    suite_shell_loop,
)


ROOT = Path(__file__).resolve().parents[1]


def test_list_suite_ids_includes_tracks():
    ids = list_suite_ids()
    assert "run-30-specialists-track-a" in ids
    assert "run-30-specialists-track-b" in ids
    assert "run-30-specialists-full" in ids


@pytest.mark.parametrize(
    "alias,suite_id,n_configs,track",
    [
        ("track-a", "run-30-specialists-track-a", 3, "a"),
        ("a", "run-30-specialists-track-a", 3, "a"),
        ("track-b", "run-30-specialists-track-b", 2, "b"),
        ("full", "run-30-specialists-full", 5, "full"),
    ],
)
def test_load_suite_aliases(alias, suite_id, n_configs, track):
    suite = load_suite(alias)
    assert suite.suite_id == suite_id
    assert suite.track == track
    assert len(suite.configs) == n_configs
    assert suite.scaledown_seconds == 120
    assert suite.warm_once is True
    for cfg in suite.configs:
        assert cfg.is_file(), cfg


def test_track_a_membership_and_profile():
    suite = load_suite("track-a")
    stems = [p.stem for p in suite.configs]
    assert stems == [
        "run-30-contracts-specialist",
        "run-30-corporate-records-specialist",
        "run-30-correspondence-specialist",
    ]
    assert suite.modal_profile_default == DEFAULT_TRACK_A_PROFILE
    assert suite.resolve_modal_profile() == DEFAULT_TRACK_A_PROFILE


def test_track_b_membership_requires_env(monkeypatch):
    suite = load_suite("track-b")
    stems = [p.stem for p in suite.configs]
    assert stems == [
        "run-30-merger-specialist",
        "run-30-insurance-claims-specialist",
    ]
    monkeypatch.delenv(MODAL_PROFILE_ENV_TRACK_B, raising=False)
    assert suite.resolve_modal_profile() is None
    monkeypatch.setenv(MODAL_PROFILE_ENV_TRACK_B, "other-modal-account")
    assert suite.resolve_modal_profile() == "other-modal-account"


def test_full_suite_is_union_of_tracks():
    full = load_suite("full")
    a = load_suite("track-a")
    b = load_suite("track-b")
    assert set(p.stem for p in full.configs) == set(
        p.stem for p in (*a.configs, *b.configs)
    )
    assert len(full.configs) == 5


def test_run_30_merger_task_is_dedicated_specialist():
    from mailroom_sandbox.job.spec import load_run_spec

    spec = load_run_spec(ROOT / "config/runs/run-30-merger-specialist.yaml")
    assert spec.task == "merger_agreement_specialist"
    agents = spec.prompt.get("agents") or {}
    pin = agents.get("merger_agreement_specialist") or {}
    assert pin.get("source") == "local"
    assert pin.get("file") == "merger_agreement_specialist_production"
    assert "contracts_specialist" not in agents


def test_example_per_class_uses_full_corpus_split():
    from mailroom_sandbox.job.spec import load_run_spec

    spec = load_run_spec(ROOT / "config/runs/example-per-class.yaml")
    assert spec.dataset.split == "all"
    buckets = spec.dataset.strata["buckets"]
    assert [b["doc_class"] for b in buckets] == [
        "contract",
        "corporate_record",
        "correspondence",
        "insurance_claim",
        "merger_agreement",
    ]
    assert all(b["count"] == 20 for b in buckets)


def test_resolve_suite_path_unknown():
    with pytest.raises(FileNotFoundError, match="unknown suite"):
        resolve_suite_path("no-such-track-xyz")


def test_suite_shell_loop_mentions_teardown():
    loop = suite_shell_loop(load_suite("track-a"))
    assert "run-30-contracts-specialist.yaml" in loop
    assert "teardown_vllm.sh" in loop
    assert "sandbox run start" in loop


def test_estimate_suite_track_a_filter():
    suite = load_suite("track-a")
    result = metrics.estimate_suite(suite.configs, corpus_size=None)
    assert result["suite"]["runs"] == 3
    assert result["suite"]["docs"] == 90
    assert result["suite"]["scaledown_seconds"] == 120
    assert {r["run_id"] for r in result["rows"]} == {
        "run-30-contracts-specialist",
        "run-30-corporate-records-specialist",
        "run-30-correspondence-specialist",
    }
    # Busy likely ~42.5 min; total with overhead under ~1 hour likely.
    assert result["suite"]["wall_seconds"]["likely"] > 2400
    assert result["suite"]["wall_seconds"]["likely"] < 4000
    assert 0.4 < result["suite"]["gpu_usd"]["likely"] < 1.0


def test_estimate_suite_track_b_filter():
    suite = load_suite("track-b")
    result = metrics.estimate_suite(suite.configs, corpus_size=None)
    assert result["suite"]["runs"] == 2
    assert result["suite"]["docs"] == 60
    assert {r["run_id"] for r in result["rows"]} == {
        "run-30-merger-specialist",
        "run-30-insurance-claims-specialist",
    }
    # Balanced vs track A within ~$0.15 likely.
    a = metrics.estimate_suite(load_suite("track-a").configs, corpus_size=None)
    delta = abs(a["suite"]["gpu_usd"]["likely"] - result["suite"]["gpu_usd"]["likely"])
    assert delta < 0.15


def test_estimate_suite_cli_suite_flag(capsys):
    from mailroom_sandbox.cli import main

    rc = main(["metrics", "estimate-suite", "--suite", "track-b", "--no-corpus", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "run-30-merger-specialist" in out
    assert "run-30-insurance-claims-specialist" in out
    assert "run-30-contracts-specialist" not in out


def test_suite_aliases_cover_cli_shortcuts():
    assert SUITE_ALIASES["track-a"] == "run-30-specialists-track-a"
    assert SUITE_ALIASES["track-b"] == "run-30-specialists-track-b"
    assert SUITE_ALIASES["full"] == "run-30-specialists-full"


def test_check_suite_benchmark_posture_lists_configs(monkeypatch):
    from mailroom_sandbox.job.benchmark_check import check_suite_benchmark_posture

    monkeypatch.setattr(
        "mailroom_sandbox.job.benchmark_check.active_modal_profile_name",
        lambda: "hermes-agent-jjb",
    )
    monkeypatch.setattr(
        "mailroom_sandbox.job.benchmark_check._modal_cli_ok",
        lambda: {"ok": True, "version": "modal mock"},
    )
    report = check_suite_benchmark_posture("track-a", require_hermes=True)
    assert report["suite_id"] == "run-30-specialists-track-a"
    assert len(report["configs"]) == 3
    assert all(row["run_id"].startswith("run-30-") for row in report["configs"])
    # Spec pins should pass; env may still warn — ok depends on env posture.
    assert "markdown" in report
