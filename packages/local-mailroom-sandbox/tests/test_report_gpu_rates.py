"""GPU-aware rate resolution for the SAND-032 report, plus an L4 golden regression.

The report used to hard-code ``L4_USD_PER_HOUR = 0.80``; it now resolves the hourly rate
and the header label from ``engine.modal.gpu`` (L4 / A100), defaulting to L4 when unknown.
The L4 render must stay byte-identical to the pre-change output — ``GOLDEN_L4_REPORT`` below
is that frozen render, captured from the synthetic run built by ``_build_run``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sand032" / "report.py"


def _report_module():
    """Import scripts/sand032/report.py fresh, as the sibling report tests do."""
    if str(SCRIPT.parent) not in sys.path:
        sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("sand032_report", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_gpu_rate_table_resolves_l4_and_a100():
    report = _report_module()
    assert report.GPU_USD_PER_HOUR["L4"] == 0.80
    assert report.GPU_USD_PER_HOUR["A100"] == 2.10
    assert report.gpu_hourly("L4") == ("L4", 0.80)
    assert report.gpu_hourly("A100") == ("A100", 2.10)
    # Modal GPU strings carry size and/or replica suffixes — both must resolve.
    assert report.gpu_hourly("A100-40GB") == ("A100", 2.10)
    assert report.gpu_hourly("A100-80GB:2") == ("A100", 2.10)
    assert report.gpu_hourly("l4") == ("L4", 0.80)
    assert report.gpu_hourly("L4:2") == ("L4", 0.80)


def test_unknown_or_missing_gpu_defaults_to_l4():
    report = _report_module()
    assert report.gpu_hourly(None) == ("L4", 0.80)
    assert report.gpu_hourly("") == ("L4", 0.80)
    assert report.gpu_hourly("H100") == ("L4", 0.80)  # unknown → documented L4 fallback
    assert report.DEFAULT_GPU == "L4"
    assert report.L4_USD_PER_HOUR == report.GPU_USD_PER_HOUR[report.DEFAULT_GPU] == 0.80


def _cost_metrics(report, gpu):
    """metrics() over a minimal record: wall 7200 s on 2 pinned replicas of ``gpu``."""
    d = {
        "spec": {"engine": {"modal": {"gpu": gpu, "max_containers": 2}},
                 "job": {"concurrency": 8}},
        "items": {}, "serving": {"wall_seconds": 7200.0}, "times": {}, "cold": {},
    }
    return report.metrics(d)


def test_wall_clock_cost_uses_the_run_gpu_rate():
    report = _report_module()
    l4 = _cost_metrics(report, "L4")
    a100 = _cost_metrics(report, "A100-40GB")
    # wall/3600 × rate × replicas
    assert l4["usd_per_hour"] == 0.80 and a100["usd_per_hour"] == 2.10
    assert l4["gpu"] == "L4" and a100["gpu"] == "A100"
    assert l4["busy_usd"] == pytest.approx(7200.0 / 3600 * 0.80 * 2)
    assert a100["busy_usd"] == pytest.approx(7200.0 / 3600 * 2.10 * 2)
    # the A100 line is 2.10/0.80× the L4 line at identical wall and replicas
    assert a100["busy_usd"] == pytest.approx(l4["busy_usd"] * 2.10 / 0.80)


def _build_run(root, gpu):
    """A tiny, fully-synthetic correspondence run so run_report renders offline."""
    rid = "sand032-l0-baseline"
    (root / "config" / "runs").mkdir(parents=True)
    spec = {
        "schema": "sandbox.run/v1", "run_id": rid, "task": "correspondence_specialist",
        "prompt": {"agents": {"correspondence_specialist": {"file": "correspondence_specialist_production"}}},
        "dataset": {"repo": "Lucius-Morningstar/mailroom-dataset", "config": "ground_truth",
                    "split": "all", "revision": "ed7576b676343e0b402ec5412cded301e629bdee",
                    "strata": {"buckets": [{"doc_class": "correspondence", "count": 2}]},
                    "limit": 2, "sample_seed": 42},
        "engine": {"kind": "modal-vllm", "model": "Qwen/Qwen3-8B-AWQ",
                   "vllm": {"max_model_len": 32768, "gpu_memory_utilization": 0.90,
                            "max_num_seqs": 16, "enable_prefix_caching": True, "enforce_eager": True,
                            "quantization": "awq_marlin", "kv_cache_dtype": "fp8",
                            "enable_thinking": False, "cudagraph_capture_sizes": [], "max_inputs": 32},
                   "modal": {"app": "sandbox-vllm-sand032", "gpu": gpu, "image_tag": "v0.29.0",
                             "scaledown_seconds": 120, "max_containers": 2, "min_containers": 2,
                             "prewarm": True}},
        "job": {"mode": "endpoint", "concurrency": 8, "cost_cap_usd": 0.15, "max_wall_seconds": 1800},
    }
    (root / "config" / "runs" / f"{rid}.yaml").write_text(yaml.safe_dump(spec))
    run = root / "data" / "runtime" / "runs" / rid
    run.mkdir(parents=True)
    items = [
        {"item_id": "DOC-1", "ok": True, "latency_ms": 1000, "prompt_tokens": 10, "completion_tokens": 5,
         "score": {"overall_extraction_score": 0.9, "extraction_f1": 0.5, "schema_valid": True}},
        {"item_id": "DOC-2", "ok": True, "latency_ms": 2000, "prompt_tokens": 20, "completion_tokens": 10,
         "score": {"overall_extraction_score": 0.8, "extraction_f1": 0.4, "schema_valid": True}},
    ]
    (run / "items.jsonl").write_text("\n".join(json.dumps(i) for i in items) + "\n")
    ds = [{"id": "DOC-1", "expected_subclass": "invoice"},
          {"id": "DOC-2", "expected_subclass": "letter"}]
    (run / "dataset.jsonl").write_text("\n".join(json.dumps(r) for r in ds) + "\n")
    (run / "spec.lock.json").write_text(json.dumps(
        {"git": {"commit": "deadbeef"}, "dataset": {"sha256": "a" * 64}, "spec_hash": "cafef00d"}))
    (run / "vllm_metrics_before.json").write_text(json.dumps({"replicas": {}}))
    (run / "vllm_metrics_after.json").write_text(json.dumps({"coverage": "1.0", "replicas": {}}))
    (run / "cold_boot.json").write_text(json.dumps({"cold_boot_seconds": 3.0}))
    grouped = root / "reports" / "serving" / "SAND-32"
    grouped.mkdir(parents=True)
    (grouped / f"{rid}.serving.json").write_text(json.dumps({"wall_seconds": 3600.0, "tokens_per_second": 12.0}))
    logs = root / "data" / "runtime" / "sand032" / "logs"
    logs.mkdir(parents=True)
    (logs / f"{rid}.times").write_text(
        '"deploy_start": 100\n"deploy_done": 130\n"ready": 150\n"stopped": 400\n')
    return rid


def _render(monkeypatch, tmp_path, report, gpu):
    monkeypatch.setattr(report, "ROOT", tmp_path)
    monkeypatch.setattr(report, "RUNS", tmp_path / "data" / "runtime" / "runs")
    monkeypatch.setattr(report, "RT", tmp_path / "data" / "runtime" / "sand032")
    monkeypatch.setattr(report, "SERVING", tmp_path / "reports" / "serving" / "SAND-32")
    rid = _build_run(tmp_path, gpu)
    out = report.run_report(rid)
    svg = (tmp_path / "reports" / "correspondence" / "figures" / f"{rid}-latency.svg").read_text()
    return out.read_text(), svg


# Frozen from the PRE-CHANGE renderer (hard-coded L4_USD_PER_HOUR = 0.80). Any diff here
# means the L4 report no longer matches the output it produced before this change.
GOLDEN_L4_REPORT = """\
# Run report — `sand032-l0-baseline`

SAND-032 Modal × vLLM specialist extract: **2 correspondence docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 8** on **2×L4** (MIN=MAX=2 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-l0-baseline` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel replicas) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=16 |
| engine flags | prefix_caching=on, enforce_eager=on, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=—, max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 2/2, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 2 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `aaaaaaaaaaaa` |
| git | `deadbeef` |
| spec_hash | `cafef00d` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **2 / 2** (errors 0) |
| **overall_extraction_score** | **0.8500** (sd 0.0500, min 0.8000, max 0.9000) |
| schema_valid_rate | 1.000 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 3600.000 s |
| concurrency | 8 (4 per replica) |
| cold boot — deploy→engine ready (driver stamps) | 20.0 s |
| preflight probe (engine answering) | 3.000 s |
| latency p50 / p95 / max | 1.50 / 2.00 / 2.00 s |
| prompt / completion tokens | 30 / 15 |
| throughput | 12.0 tok/s |
| GPU $ over busy wall (×2 L4 @ $0.8/h) | 1.600000 |
| **$ per doc (busy)** | **0.800000** |
| fleet window deploy→stop (upper est.) | 300 s → 0.1333 USD |
| cost cap | $0.15 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **1.0** (sampled through the Modal router; replica = vLLM process start time).

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 3.0 s over wall 3600.0 s = **0.00×** effective parallelism at c8 (0% of the ideal 8×).
- **Tail:** slowest doc `DOC-2` (letter) 2.0 s = 0% of wall — p95/p50 = 1.33×.
- **Decode budget:** mean completion 8 tok/doc, mean prompt 15 tok/doc.
- **Subclass spread:** best `invoice` 0.900 (n=1), worst `letter` 0.800 (n=1).
- **Field-level extraction:** 0/2 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.
- **Boot:** deploy→engine-ready 20 s (driver stamps); preflight probe measured 3.0 s once the engine answered.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-l0-baseline-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-l0-baseline-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| invoice | 1 | 0.9000 |
| letter | 1 | 0.8000 |
| **total** | **2** | **0.8500** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-1` | invoice | 0.9000 | 0.5000 | ✓ | 1.0 | 10 | 5 |  |
| 2 | `DOC-2` | letter | 0.8000 | 0.4000 | ✓ | 2.0 | 20 | 10 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-l0-baseline.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-l0-baseline
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-l0-baseline.yaml` | run spec |
| `reports/serving/sand032-l0-baseline.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-l0-baseline/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-l0-baseline/` | offline Braintrust-shaped rows — disposed after this report is committed |
"""


def test_l4_render_is_byte_identical_to_the_frozen_golden(monkeypatch, tmp_path):
    report = _report_module()
    text, svg = _render(monkeypatch, tmp_path, report, gpu="L4")
    assert text == GOLDEN_L4_REPORT
    # the figure subtitle is part of the L4 render too
    assert "on 2×L4 · wall" in svg


def test_a100_render_uses_the_a100_rate_and_label(monkeypatch, tmp_path):
    report = _report_module()
    text, svg = _render(monkeypatch, tmp_path, report, gpu="A100-40GB")
    assert "**2×A100**" in text
    assert "2× A100" in text
    assert "@ $2.1/h" in text
    assert "| 4.200000 |" in text  # 3600 s × 2.10 × 2 reps / 3600
    assert "on 2×A100 · wall" in svg
    assert text != GOLDEN_L4_REPORT
