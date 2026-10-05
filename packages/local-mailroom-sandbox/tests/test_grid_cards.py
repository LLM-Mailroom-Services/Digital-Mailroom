"""SAND-037 score & cost cards under reports/SAND-37/<shape>/<specialist>/."""

from __future__ import annotations

import json

from mailroom_sandbox.job import grid_cards
from mailroom_sandbox.job.checkpoint import RunStore


def _store(tmp_path, run_id="grid-50-contracts-specialist-awq-2l4-rerun", *, task="contracts_specialist",
           replicas=2, concurrency=32, limit=3) -> RunStore:
    store = RunStore(tmp_path / "runs" / run_id)
    store.write_lock(
        {
            "run_id": run_id,
            "task": task,
            "profile": "modal-vllm",
            "engine": {
                "model": "Qwen/Qwen3-8B-AWQ",
                "vllm": {
                    "max_model_len": 32768,
                    "max_num_seqs": 16,
                    "enforce_eager": False,
                    "quantization": "awq_marlin",
                    "kv_cache_dtype": "fp8",
                    "enable_thinking": False,
                    "cudagraph_capture_sizes": [1, 2, 4, 8, 16],
                    "max_inputs": 32,
                    "enable_prefix_caching": True,
                },
                "modal": {"gpu": "L4", "max_containers": replicas, "min_containers": replicas,
                          "app": "sandbox-vllm", "image_tag": "v0.29.0"},
            },
            "job": {"mock": False, "concurrency": concurrency, "mode": "endpoint", "max_retries": 2},
            "dataset": {"repo": "Lucius-Morningstar/mailroom-dataset", "config": "ground_truth",
                        "split": "all", "revision": "ed7576b676343e0b", "sample_seed": 42, "limit": limit},
            "prompt": {"agents": {task: {"source": "local", "file": "contracts_specialist_v33_simplified"}}},
        }
    )
    cuad = {"scoring_method": "suite+cuad", "schema_valid": True, "cuad_tp": 3, "cuad_fp": 1, "cuad_fn": 1,
            "cuad_presence_f1": 0.75, "cuad_value_correct": 2, "cuad_value_checked": 3,
            "suite_overall_extraction_score": 0.0}
    store.append_item({"item_id": "DOC-1", "index": 0, "ok": True, "latency_ms": 60000.0, "prompt_tokens": 8000,
                       "completion_tokens": 1500, "ts": "2026-10-01T00:00:10.000+00:00",
                       "score": {**cuad, "overall_extraction_score": 0.75}})
    store.append_item({"item_id": "DOC-2", "index": 1, "ok": True, "latency_ms": 90000.0, "prompt_tokens": 7000,
                       "completion_tokens": 2500, "ts": "2026-10-01T00:00:40.000+00:00",
                       "score": {**cuad, "overall_extraction_score": 0.5}})
    store.append_item({"item_id": "DOC-3", "index": 2, "ok": False, "latency_ms": 120000.0,
                       "ts": "2026-10-01T00:01:10.000+00:00",
                       "error": "LengthFinishReasonError: Could not parse response content as the length limit was reached"})
    reps_before = {"a": {"requests": 10, "preemptions": 0, "length_finishes": 1},
                   "b": {"requests": 4, "preemptions": 0, "length_finishes": 0}}
    reps_after = {"a": {"requests": 12, "preemptions": 0, "length_finishes": 2, "ttft_mean_seconds": 0.8,
                        "prefix_cache_hit_rate": 0.6},
                  "b": {"requests": 5, "preemptions": 0, "length_finishes": 0, "ttft_mean_seconds": 1.2,
                        "prefix_cache_hit_rate": 0.4}}
    (store.dir / "vllm_metrics_before.json").write_text(json.dumps({"replicas": reps_before}))
    (store.dir / "vllm_metrics_after.json").write_text(
        json.dumps({"coverage": "replicas observed: 2 of 2", "replicas": reps_after, "errors": []}))
    return store


def test_card_lands_under_shape_and_specialist(tmp_path):
    store = _store(tmp_path)
    paths = grid_cards.write_card(store, repo=tmp_path, wall_seconds=150.0)
    base = tmp_path / "reports" / "SAND-37" / "2L4" / "contracts"
    assert paths["md"] == base / "grid-50-contracts-specialist-awq-2l4-rerun.card.md"
    assert paths["json"].is_file()


def test_card_measures_cost_tokens_engine_and_quality(tmp_path):
    store = _store(tmp_path)
    card = json.loads(grid_cards.write_card(store, repo=tmp_path, wall_seconds=150.0)["json"].read_text())
    # cost: 150 s × 2 L4 × $0.80/hr
    assert abs(card["cost"]["busy_gpu_usd"] - 150 * 2 * 0.80 / 3600) < 1e-9
    assert abs(card["cost"]["usd_per_document"] - card["cost"]["busy_gpu_usd"] / 3) < 1e-12
    assert card["tokens"]["total"] == 19000 and card["tokens"]["completion_max"] == 2500
    assert abs(card["throughput"]["tokens_per_second_per_gpu"] - 19000 / 150 / 2) < 1e-9
    assert abs(card["concurrency"]["parallelism"] - 270 / 150) < 1e-9
    # per-replica deltas from the before/after scrapes
    reps = {r["replica"]: r for r in card["engine_telemetry"]["replicas"]}
    assert reps["a"]["requests"] == 2 and reps["a"]["length_finishes"] == 1
    assert card["quality"]["error_kinds"] == {"LengthFinishReasonError": 1}
    assert card["quality"]["clause"]["kind"] == "cuad"
    assert abs(card["quality"]["clause"]["f1"] - 0.75) < 1e-9
    assert card["conditions"]["engine"]["quantization"] == "awq_marlin"
    assert card["conditions"]["temperature"] == 0.7  # contracts grid posture
    assert card["conditions"]["max_tokens"] == 8192


def test_card_markdown_follows_template(tmp_path):
    md = grid_cards.write_card(_store(tmp_path), repo=tmp_path, wall_seconds=150.0)["md"].read_text()
    for heading in ("## Conditions", "## Score & cost card", "## Errors", "## Per-document results"):
        assert heading in md
    for section in ("**Run**", "**Time**", "**Cost**", "**Tokens**", "**Throughput**",
                    "**Latency (per document, ok rows)**", "**Engine (vLLM /metrics)**", "**Quality**",
                    "**Clause scoring (CUAD)**"):
        assert f"| {section} |" in md
    assert "| Temperature | 0.7 (posture knob) |" in md
    assert "| Length-capped finishes per replica (this run) | 1 / 0 |" in md
    assert "| `DOC-3` | no |" in md


def test_rerender_without_wall_reuses_the_runner_wall(tmp_path):
    store = _store(tmp_path)
    grid_cards.write_card(store, repo=tmp_path, wall_seconds=150.0)
    again = json.loads(grid_cards.write_card(store, repo=tmp_path)["json"].read_text())
    assert again["time"]["wall_seconds"] == 150.0


def test_missing_scrapes_render_as_not_captured(tmp_path):
    store = _store(tmp_path)
    (store.dir / "vllm_metrics_after.json").unlink()
    md = grid_cards.write_card(store, repo=tmp_path, wall_seconds=150.0)["md"].read_text()
    assert "| Coverage | not captured |" in md


def test_suite_card_rolls_up_cards_and_marks_missing_cells(tmp_path):
    grid_cards.write_card(_store(tmp_path), repo=tmp_path, wall_seconds=150.0)
    other = _store(tmp_path, "grid-20-contracts-specialist-awq-2l4", limit=3)
    grid_cards.write_card(other, repo=tmp_path, wall_seconds=50.0)
    paths = grid_cards.write_suite(2, repo=tmp_path)
    assert paths["md"] == tmp_path / "reports" / "SAND-37" / "2L4" / "L4x2-SCORE-COST-CARD.md"
    suite = json.loads(paths["json"].read_text())
    assert len(suite["cells"]) == 10
    assert sum(c["reported"] for c in suite["cells"]) == 2
    pooled = suite["pooled"]["all"]
    assert pooled["documents"] == 6 and pooled["errors"] == 2
    assert abs(pooled["busy_gpu_usd"] - (200 * 2 * 0.80 / 3600)) < 1e-9
    md = paths["md"].read_text()
    assert "Cells reported:** 2 of 10" in md
    assert "## Per specialist · n = 20" in md and "## Per specialist · n = 50" in md
    assert "not run" in md
    assert "[grid-50-contracts-specialist-awq-2l4-rerun.card.md](contracts/" in md


def test_sand40_probe_card_records_optimized_settings(tmp_path):
    store = _store(
        tmp_path,
        "sand40-probe-20-merger-specialist-awq-2l4-64k",
        task="merger_agreement_specialist",
        limit=20,
    )
    lock = json.loads(store.lock_path.read_text())
    lock["engine"]["vllm"]["max_model_len"] = 65536
    lock["engine"]["vllm"]["hf_overrides"] = {
        "rope_parameters": {"rope_type": "yarn", "factor": 2.0, "original_max_position_embeddings": 32768, "rope_theta": 1000000}
    }
    lock["prompt"]["agents"] = {
        "merger_agreement_specialist": {"source": "local", "file": "merger_agreement_specialist_maud_v1"}
    }
    store.lock_path.write_text(json.dumps(lock))
    paths = grid_cards.maybe_write_card(store, wall_seconds=10.0, repo=tmp_path)
    assert paths["md"] == (
        tmp_path / "reports" / "SAND-37" / "probes" / "merger_agreement" / "sand40-probe-20-merger-specialist-awq-2l4-64k.card.md"
    )
    card = json.loads(paths["json"].read_text())
    cond = card["conditions"]
    assert cond["top_p"] == 0.8 and cond["top_k"] == 20
    assert cond["presence_penalty"] == 1.0 and cond["length_retries"] == 1
    assert cond["chunk_chars"] == 120000 and cond["optimized"] is True
    assert cond["hf_overrides"]["rope_parameters"]["rope_type"] == "yarn"
    md = paths["md"].read_text()
    assert "top_p" in md and "hf_overrides" in md


def test_sand40_probe_card_is_outside_the_scorecard_tree(tmp_path):
    store = _store(
        tmp_path,
        "sand40-probe-20-contracts-specialist-awq-2l4-64k",
        task="contracts_specialist",
        limit=20,
    )
    paths = grid_cards.maybe_write_card(store, wall_seconds=10.0, repo=tmp_path)
    assert paths["md"] == (
        tmp_path
        / "reports"
        / "SAND-37"
        / "probes"
        / "contracts"
        / "sand40-probe-20-contracts-specialist-awq-2l4-64k.card.md"
    )
    assert not (tmp_path / "reports" / "SAND-37" / "2L4").exists()
    from mailroom_sandbox.job.grid_master import collect_master

    master = collect_master(tmp_path)
    assert master["cards"]["s40-2l4"] == {}
    assert master["cards"]["s37-2l4-n50"] == {}


def test_runner_hook_skips_non_grid_runs(tmp_path):
    store = _store(tmp_path, "run-20-contracts-awq-c8", replicas=1, concurrency=8)
    assert grid_cards.maybe_write_card(store, wall_seconds=10.0) == {}


def test_sand40_scale_cells_land_under_2l4(tmp_path):
    store = _store(tmp_path, "sand40-100-contracts-specialist-awq-2l4", limit=3)
    paths = grid_cards.maybe_write_card(store, wall_seconds=10.0, repo=tmp_path)
    assert paths["md"] == tmp_path / "reports/SAND-37/2L4/contracts/sand40-100-contracts-specialist-awq-2l4.card.md"
    cond = json.loads(paths["json"].read_text())["conditions"]
    assert cond["max_tokens"] == 8192 and not cond.get("chunk_chars")

    store = _store(tmp_path, "sand40-50-merger-specialist-awq-2l4", task="merger_agreement_specialist", limit=3)
    paths = grid_cards.maybe_write_card(store, wall_seconds=10.0, repo=tmp_path)
    assert paths["md"] == tmp_path / "reports/SAND-37/2L4/merger_agreement/sand40-50-merger-specialist-awq-2l4.card.md"
    cond = json.loads(paths["json"].read_text())["conditions"]
    assert cond["chunk_chars"] == 47000 and cond["max_tokens"] == 6144 and cond["optimized"] is True


def _gate_store(tmp_path, *, requests, length_finishes=0, ok=True):
    run_id = "sand40-check-5-merger-specialist-awq-2l4"
    store = _store(tmp_path, run_id, task="merger_agreement_specialist", limit=2)
    store.dir.joinpath("items.jsonl").unlink(missing_ok=True)
    store = RunStore(store.dir)
    for i in range(2):
        store.append_item({"item_id": f"DOC-{i}", "index": i, "ok": ok or i == 0, "latency_ms": 1000.0,
                           "prompt_tokens": 100, "completion_tokens": 10, "ts": "2026-10-01T00:00:10.000+00:00",
                           "score": {"overall_extraction_score": 0.1},
                           **({} if ok or i == 0 else {"error": "LengthFinishReasonError: cap"})})
    store.write_dataset([{"id": "DOC-0", "doc_text": "a" * 10}, {"id": "DOC-1", "doc_text": "b" * 10}])
    half = requests / 2
    reps = {"a": {"requests": half, "length_finishes": length_finishes, "preemptions": 0},
            "b": {"requests": half, "length_finishes": 0, "preemptions": 0}}
    zero = {k: {"requests": 0, "length_finishes": 0, "preemptions": 0} for k in reps}
    (store.dir / "vllm_metrics_before.json").write_text(json.dumps({"replicas": zero}))
    (store.dir / "vllm_metrics_after.json").write_text(json.dumps({"coverage": "replicas observed: 2 of 2", "replicas": reps, "errors": []}))
    return store


def _three_chunks(text, window, overlap):
    return ["x"] * 3


def test_chunk_gate_passes_when_every_chunk_reached_vllm(tmp_path):
    store = _gate_store(tmp_path, requests=7, length_finishes=1)
    assert grid_cards.chunk_gate(store, split=_three_chunks) == []


def test_chunk_gate_fails_on_lost_chunks_or_failed_documents(tmp_path):
    lost = grid_cards.chunk_gate(_gate_store(tmp_path / "a", requests=6, length_finishes=1), split=_three_chunks)
    assert any("need 6 chunk calls" in e for e in lost)
    failed = grid_cards.chunk_gate(_gate_store(tmp_path / "b", requests=6, ok=False), split=_three_chunks)
    assert any("documents ok 1/2" in e for e in failed)
