"""SAND-032: vLLM Prometheus /metrics parsing + per-replica grouping (network-free)."""

import json

from mailroom_sandbox.job.vllm_metrics import (
    group_replicas,
    parse_prometheus,
    replica_coverage,
    summarize,
)

TEXT_A = """# HELP process_start_time_seconds x
process_start_time_seconds 1000.0
vllm:request_success_total{finished_reason="stop",model_name="m"} 40.0
vllm:request_success_total{finished_reason="length",model_name="m"} 2.0
vllm:num_preemptions_total{model_name="m"} 0.0
vllm:kv_cache_usage_perc{model_name="m"} 0.31
vllm:prefix_cache_hits_total{model_name="m"} 600.0
vllm:prefix_cache_queries_total{model_name="m"} 1000.0
vllm:time_to_first_token_seconds_sum{model_name="m"} 21.0
vllm:time_to_first_token_seconds_count{model_name="m"} 42.0
vllm:time_to_first_token_seconds_bucket{le="0.5",model_name="m"} 30.0
"""
TEXT_B = TEXT_A.replace("process_start_time_seconds 1000.0", "process_start_time_seconds 2000.0")


def test_parse_sums_label_sets_and_ignores_buckets():
    m = parse_prometheus(TEXT_A)
    assert m["vllm:request_success_total"] == 42.0
    assert m["process_start_time_seconds"] == 1000.0
    assert "vllm:time_to_first_token_seconds_bucket" not in m


def test_group_by_process_start():
    reps = group_replicas([parse_prometheus(TEXT_A), parse_prometheus(TEXT_B), parse_prometheus(TEXT_A)])
    assert sorted(reps) == ["1000.0", "2000.0"]


def test_summarize_derives_rates():
    s = summarize(parse_prometheus(TEXT_A))
    assert s["requests"] == 42.0
    assert s["length_finishes"] == 2.0
    assert s["prefix_cache_hit_rate"] == 0.6
    assert s["ttft_mean_seconds"] == 0.5
    assert s["kv_cache_usage_perc"] == 0.31


def test_summarize_without_ttft_is_none_not_inferred():
    s = summarize(parse_prometheus("process_start_time_seconds 1.0\n"))
    assert s["ttft_mean_seconds"] is None
    assert s["prefix_cache_hit_rate"] is None


def test_scrape_reports_unobserved_replicas():
    reps = group_replicas([parse_prometheus(TEXT_A)] * 5)
    assert replica_coverage(reps, expected=2) == "replicas observed: 1 of 2"


def test_scrape_samples_and_records_errors(monkeypatch):
    from mailroom_sandbox.job import vllm_metrics

    bodies = iter([TEXT_A, TEXT_B, RuntimeError("boom"), TEXT_A])

    class _Resp:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

    def fake_get(url, headers=None, timeout=None):
        assert url == "https://x.modal.run/metrics"
        assert headers == {"Authorization": "Bearer tok"}
        nxt = next(bodies)
        if isinstance(nxt, Exception):
            raise nxt
        return _Resp(nxt)

    import httpx

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(vllm_metrics.time, "sleep", lambda s: None)
    out = vllm_metrics.scrape("https://x.modal.run/v1", "tok", attempts=4, expected=2)
    assert out["coverage"] == "replicas observed: 2 of 2"
    assert len(out["errors"]) == 1 and "RuntimeError" in out["errors"][0]
    json.dumps(out)  # serializable


def test_cli_scrape_metrics_writes_labelled_json(tmp_path, monkeypatch, capsys):
    from mailroom_sandbox.cli import main
    from mailroom_sandbox.job import spec as spec_mod
    from mailroom_sandbox.job import vllm_metrics
    from mailroom_sandbox.paths import config_dir

    monkeypatch.setattr(spec_mod, "runs_root", lambda: tmp_path)
    monkeypatch.setenv("VLLM_BASE_URL", "https://x.modal.run/v1")
    monkeypatch.setenv("VLLM_API_KEY", "tok")
    seen = {}

    def fake_scrape(base, key, *, attempts=12, expected=1):
        seen.update(base=base, key=key, expected=expected)
        return {"coverage": "replicas observed: 2 of 2", "replicas": {}, "errors": [], "at": 0}

    monkeypatch.setattr(vllm_metrics, "scrape", fake_scrape)
    cfg = config_dir() / "runs" / "run-50-correspondence-specialist-awq.yaml"
    rc = main(["run", "scrape-metrics", "--config", str(cfg), "--label", "after"])
    assert rc == 0
    assert seen["expected"] == 2 and seen["key"] == "tok"
    out = tmp_path / "run-50-correspondence-specialist-awq" / "vllm_metrics_after.json"
    assert json.loads(out.read_text())["coverage"] == "replicas observed: 2 of 2"
    assert "replicas observed: 2 of 2" in capsys.readouterr().out
