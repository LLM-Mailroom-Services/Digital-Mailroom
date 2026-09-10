"""Activation, mock LLM, eval runners, experiment log (network-free)."""

from __future__ import annotations

import json
import os

import pytest

from mailroom_sandbox.cli import main
from mailroom_sandbox.datasets import dataset_fingerprint, load_hf_fixtures, load_legalbench_fixtures, load_manifest
from mailroom_sandbox.eval import experiment_log, matrix, runners, scoring
from mailroom_sandbox.mock_llm import fake_client, fake_structured_payload
from mailroom_sandbox.runtime import activate


def test_activate_writes_taxonomy(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    act = activate("ollama", load_env_file=False)
    assert act.profile_name == "ollama"
    assert act.taxonomy_path.is_file()
    text = act.taxonomy_path.read_text(encoding="utf-8")
    assert "qwen3:8b" in text
    assert "provider: ollama" in text


def test_fake_client_classify():
    expect = {"doc_type": "contract", "conf": 0.97}
    client = fake_client(expect)
    resp = client.chat.completions.create(
        messages=[{"role": "user", "content": "Classify this legal document.\njson"}]
    )
    payload = json.loads(resp.choices[0].message.content)
    assert payload["doc_type"] == "contract"
    assert payload["confidence"] == 0.97


def test_fake_payload_ambiguous():
    payload = fake_structured_payload(
        "Classify this legal document",
        {"id": "ambiguous_01", "doc_type": "correspondence"},
    )
    assert payload["confidence"] == 0.40
    assert payload["doc_type"] == "correspondence"


def test_manifest_and_hf_fixtures():
    rows = load_manifest()
    assert len(rows) >= 8
    classes = {r["expected_doc_class"] for r in rows}
    assert "contract" in classes
    assert "correspondence" in classes
    assert dataset_fingerprint(rows)
    hf = load_hf_fixtures()
    assert {r["doc_type"] for r in hf} >= {"contract", "correspondence", "insurance_claim"}
    lb = load_legalbench_fixtures()
    assert all(r["answer"] in {"Yes", "No"} for r in lb)


def test_sorter_eval_mock(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    # experiment log writes under repo reports/; isolate via env used by dojo
    log = tmp_path / "experiment_log.jsonl"
    monkeypatch.setenv("EXPERIMENT_LOG_PATH", str(log))
    monkeypatch.setattr(experiment_log, "jsonl_path", lambda: log)
    monkeypatch.setattr(experiment_log, "md_path", lambda: tmp_path / "experiment_log.md")
    result = runners.run_sorter_eval(mock=True, dry_run=True)
    assert result["n"] >= 1
    result = runners.run_sorter_eval(mock=True, sample=3, experiment_name="test_sorter")
    assert result["scores"]["exact_match"] == 1.0
    assert log.is_file()


def test_extract_eval_mock(tmp_path, monkeypatch):
    log = tmp_path / "experiment_log.jsonl"
    monkeypatch.setenv("EXPERIMENT_LOG_PATH", str(log))
    monkeypatch.setattr(experiment_log, "jsonl_path", lambda: log)
    monkeypatch.setattr(experiment_log, "md_path", lambda: tmp_path / "experiment_log.md")
    result = runners.run_extract_eval(mock=True, sample=2)
    assert result["scores"]["n"] >= 1
    assert result["scores"]["overall_extraction_score"] >= 0.0


def test_legalbench_eval_mock(tmp_path, monkeypatch):
    log = tmp_path / "experiment_log.jsonl"
    monkeypatch.setenv("EXPERIMENT_LOG_PATH", str(log))
    monkeypatch.setattr(experiment_log, "jsonl_path", lambda: log)
    monkeypatch.setattr(experiment_log, "md_path", lambda: tmp_path / "experiment_log.md")
    result = runners.run_legalbench_eval(mock=True)
    # The mock is deterministic md5 parity, never a self-fulfilling 1.0 —
    # a perfect mock would mask scoring defects (DMR-049 F8).
    assert 0.0 <= result["scores"]["exact_match"] < 1.0
    assert result["seed"] == 42
    assert result["legalbench_task"] == "contract_qa"


def test_matrix_dry_run():
    plan = matrix.run_matrix(
        task="sorter",
        providers=["ollama"],
        models=["qwen3:8b", "llama3.1:8b"],
        prompts=["mailroom-default", "sorter_local_v0"],
        dry_run=True,
    )
    assert plan["n"] == 4
    names = {c["experiment_name"] for c in plan["cells"]}
    assert any("sorter_local_v0" in n for n in names)


def test_cli_help():
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_cli_profiles():
    rc = main(["profiles"])
    assert rc == 0


def test_cli_eval_dry_run(capsys):
    rc = main(["eval", "sorter", "--mock", "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["task"] == "sorter"


def test_cli_matrix_dry_run(capsys):
    rc = main(
        [
            "matrix",
            "--task",
            "sorter",
            "--providers",
            "ollama",
            "--models",
            "qwen3:8b",
            "--prompts",
            "sorter_local_v0",
            "--dry-run",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["n"] == 1


def test_classification_scoring_smoke():
    scores = scoring.score_classification(
        ["contract", "correspondence"],
        ["contract", "correspondence"],
    )
    assert scores["exact_match"] == 1.0
    assert scores["accuracy"] == 1.0
    assert scores["f1_macro"] == 1.0


def test_dojo_pin_is_v0_12():
    import re

    import llm_dojo_scoring as dojo
    from llm_dojo_scoring import get_suite, headline_metrics
    from mailroom_sandbox.paths import repo_root

    pin = (repo_root() / "pyproject.toml").read_text(encoding="utf-8")
    assert "llm-dojo-scoring.git@v0.12.2" in pin
    # Monorepo dev: the [tool.uv.sources] workspace redirect installs the
    # workspace member, which can be newer than the release pin above.
    version = re.match(r"(\d+)\.(\d+)", dojo.__version__)
    assert version is not None
    assert tuple(map(int, version.groups())) >= (0, 12)
    assert headline_metrics("sorter") == ["accuracy", "f1_macro"]
    assert "ttft_seconds" in headline_metrics("local_vs_api")
    assert "tokens_per_second" in headline_metrics("local_vs_api")
    assert "ttft_seconds" not in headline_metrics("sorter")
    suite = get_suite("local_vs_api")
    assert suite.kind == "serving"


def test_local_vs_api_fixtures_need_no_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    log = tmp_path / "experiment_log.jsonl"
    monkeypatch.setenv("EXPERIMENT_LOG_PATH", str(log))
    monkeypatch.setattr(experiment_log, "jsonl_path", lambda: log)
    monkeypatch.setattr(experiment_log, "md_path", lambda: tmp_path / "experiment_log.md")
    plan = runners.run_local_vs_api_eval(mock=True, dry_run=True)
    assert plan["task"] == "local_vs_api"
    assert plan["requires_api_key"] is False
    result = runners.run_local_vs_api_eval(mock=True, experiment_name="test_local_vs_api")
    scores = result["scores"]
    assert scores["ttft_seconds_local"] == 0.4
    assert scores["ttft_seconds_api"] == 0.15
    assert scores["ttft_delta_local_minus_api"] == 0.25
    assert scores["gpu_utilization_api"] is None
    gaps = scores["honest_gaps"]
    assert any("gpu" in g.lower() for g in gaps)
    comparison = result["comparison"]["comparison"]
    assert comparison["metrics"]["gpu_utilization"]["api"] is None
    assert comparison["local"]["identity"]["serving_kind"] == "local"
    assert comparison["api"]["identity"]["serving_kind"] == "api"
    # local Ollama slug has no OpenRouter price table
    assert comparison["local"]["estimated_cost_usd"] is None
    rows = {r["metric"]: r for r in comparison["table"]}
    assert rows["ttft_seconds"]["status"] == "compared"
    assert rows["gpu_utilization"]["status"] == "local_only"
    assert rows["gpu_utilization"]["api"] is None
    assert rows["queue_time_seconds"]["status"] == "missing"
    assert rows["queue_time_seconds"]["local"] is None
    card = comparison["scorecard"]
    assert card["agent"] == "local_vs_api"
    assert card["cost"]["local"]["estimated_cost_usd"] is None
    assert "queue_time_seconds" in card["missing"]
    assert comparison["markdown"].startswith("# local vs API serving scorecard")
    assert scores["table_n"] == len(comparison["table"])
    assert scores["cost_local"] is None
    assert "queue_time_seconds" in scores["missing"]


def test_serving_ttft_not_inferred_from_e2e():
    run = scoring.score_one_serving_run(
        {
            "provider": "ollama",
            "model": "qwen3:8b",
            "e2e_latency_seconds": 3.0,
            "completion_tokens": 60,
        }
    )
    assert run["ttft_seconds"] is None
    assert run["identity"]["serving_kind"] == "local"
    assert any("ttft" in g for g in run["honest_gaps"])


def test_compare_from_log_pairs_local_and_api(tmp_path, monkeypatch):
    monkeypatch.setenv("MAILROOM_BASE_DIR", str(tmp_path))
    log = tmp_path / "experiment_log.jsonl"
    monkeypatch.setenv("EXPERIMENT_LOG_PATH", str(log))
    monkeypatch.setattr(experiment_log, "jsonl_path", lambda: log)
    monkeypatch.setattr(experiment_log, "md_path", lambda: tmp_path / "experiment_log.md")
    local = experiment_log.new_record(
        experiment_name="cell_ollama",
        task="sorter",
        profile="ollama",
        provider="ollama",
        model="qwen3:8b",
        prompt_version="mailroom-default",
        dataset_fingerprint="abc123",
        ttft_seconds=0.5,
        e2e_latency_seconds=2.0,
        completion_tokens=40,
        scores={"exact_match": 1.0, "f1_macro": 1.0},
    )
    api = experiment_log.new_record(
        experiment_name="cell_openrouter",
        task="sorter",
        profile="openrouter",
        provider="openrouter",
        model="qwen/qwen3.7-flash",
        prompt_version="mailroom-default",
        dataset_fingerprint="abc123",
        ttft_seconds=0.2,
        e2e_latency_seconds=0.8,
        completion_tokens=40,
        gpu_utilization=0.9,
        scores={"exact_match": 1.0, "f1_macro": 1.0},
    )
    experiment_log.append(local)
    experiment_log.append(api)
    result = runners.run_local_vs_api_eval(from_log=True, experiment_name="test_from_log")
    assert result["scores"]["api_n"] == 1
    assert result["scores"]["local_n"] == 1
    assert result["scores"]["gpu_utilization_api"] is None
    assert result["comparison"]["markdown"].startswith("# local vs API serving scorecard")
    assert result["comparison"]["scorecard"]["cost"]["local"]["estimated_cost_usd"] is None
    assert local["serving_kind"] == "local"
    assert api["serving_kind"] == "api"
    md = (tmp_path / "experiment_log.md").read_text(encoding="utf-8")
    assert "local vs API serving scorecard" in md


def test_cli_local_vs_api_dry_run(capsys):
    rc = main(["eval", "local_vs_api", "--mock", "--dry-run"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["task"] == "local_vs_api"
    assert "ttft_seconds" in payload["headlines"]


@pytest.mark.local_llm
def test_live_ollama_health():
    if os.environ.get("SANDBOX_LOCAL_LLM", "").strip() not in {"1", "true", "yes"}:
        pytest.skip("SANDBOX_LOCAL_LLM not set")
    from mailroom_sandbox.health import health_check

    result = health_check("ollama")
    assert result["ok"] is True
