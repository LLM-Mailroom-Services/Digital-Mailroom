"""SAND-042 invariants: the four cells, the shared draw, the prompts, the telemetry.

Network-free. These are the checks that make the SAND-042 numbers survive
scrutiny — a drift in any of them invalidates the paired comparison, so each one
fails loudly rather than being inferred from the run cards after the fact.
"""

from __future__ import annotations

import json

import pytest
import yaml

from mailroom_sandbox.job import benchmark_check, container_telemetry, deploy_env, grid_cards, sand42_cards
from mailroom_sandbox.job import specialist_posture as posture
from mailroom_sandbox.job.spec import load_run_spec
from mailroom_sandbox.paths import repo_root

CELLS = ("1l4-c8", "1l4-c16", "2l4-c8", "2l4-c16")
CLASSES = ("correspondence", "insurance_claim", "corporate_record", "contract", "merger_agreement")
SLUGS = {
    "correspondence": "correspondence",
    "insurance_claim": "insurance-claims",
    "corporate_record": "corporate-records",
    "contract": "contracts",
    "merger_agreement": "merger",
}


def _config_path(cell: str, doc_class: str):
    rid = posture.sand42_run_id(cell, doc_class)
    return repo_root() / "config" / "runs" / f"{rid}.yaml"


def _raw(cell: str, doc_class: str) -> dict:
    return yaml.safe_load(_config_path(cell, doc_class).read_text(encoding="utf-8"))


# ── posture ──────────────────────────────────────────────────────────────────


def test_every_cell_class_pair_has_a_config_and_a_posture_row():
    # Five cells × five specialists. C32 is the SAND-047 saturation amendment —
    # 16 per replica, the engine's max_num_seqs — not one of the original four.
    assert len(posture.SAND42_RUNS) == 25
    for cell in CELLS:
        for doc_class in CLASSES:
            rid = posture.sand42_run_id(cell, doc_class)
            assert rid in posture.SPECIALIST_POSTURE, rid
            assert _config_path(cell, doc_class).is_file(), rid
            assert posture.expected_limit(rid) == 50


def test_posture_pins_the_1to1_specialist_and_the_cell_concurrency():
    for cell, (replicas, concurrency) in posture.SAND42_CELLS_BY_ID.items():
        for doc_class in CLASSES:
            rid = posture.sand42_run_id(cell, doc_class)
            row = posture.SPECIALIST_POSTURE[rid]
            assert row["doc_class"] == doc_class
            assert row["replicas"] == replicas
            assert row["concurrency"] == concurrency
            assert row["max_model_len"] == 32768
            assert row["max_num_seqs"] == 16
            # Merger's 6144 is the SAND-040 optimised long-document cap (see
            # _SAND42_CHUNKED); every other class decodes at 8192.
            assert row["max_tokens"] == (6144 if doc_class == "merger_agreement" else 8192)


def test_2l4_concurrency_splits_equally_across_replicas():
    """The operator rule: 2×L4 C8 → 4/replica, 2×L4 C16 → 8/replica."""
    for cell, (replicas, concurrency) in posture.SAND42_CELLS_BY_ID.items():
        assert concurrency % replicas == 0
    assert posture.SAND42_CELLS_BY_ID["2l4-c8"] == (2, 8)
    assert posture.SAND42_CELLS_BY_ID["2l4-c16"] == (2, 16)
    assert posture.SAND42_CELLS_BY_ID["2l4-c32"] == (2, 32)


def test_only_concurrency_and_replicas_differ_between_cells():
    """Same spec everywhere: a cell difference cannot come from engine or decode."""
    for doc_class in CLASSES:
        specs = [_raw(cell, doc_class) for cell in CELLS]

        def without_cell(spec: dict, key: str) -> dict:
            block = {k: v for k, v in spec[key].items() if k not in ("concurrency", "cost_cap_usd")}
            if key == "engine":
                block["modal"] = {
                    k: v for k, v in block["modal"].items()
                    if k not in ("max_containers", "min_containers")
                }
            if key == "trace":
                block.pop("tags", None)
            return block

        for key in ("engine", "job", "prompt", "dataset", "trace"):
            base = without_cell(specs[0], key)
            for spec in specs[1:]:
                assert without_cell(spec, key) == base, (doc_class, key)


def test_the_treatment_is_identical_in_every_cell():
    """The "consistent aligned approach to the mergers" — enforced, not folklore.

    All four cells resolve one single-sourced posture, so the ONLY legitimate
    cell-to-cell difference is the cell's own treatment (replicas, client
    concurrency) plus the abort cap that follows from the replica count. Any other
    divergence — a per-cell chunk size, output cap, or sampling knob — would make the
    four legs incomparable while still looking like one experiment. The config-level
    check above cannot see this: these keys are applied from the posture at run time.
    """
    treatment = {"concurrency", "replicas", "cost_cap_usd", "rationale"}
    for doc_class in CLASSES:
        rows = [
            {
                k: v
                for k, v in posture.SPECIALIST_POSTURE[
                    posture.sand42_run_id(cell, doc_class)
                ].items()
                if k not in treatment
            }
            for cell in CELLS
        ]
        assert all(r == rows[0] for r in rows[1:]), doc_class

    merger = posture.SPECIALIST_POSTURE[posture.sand42_run_id(CELLS[0], "merger_agreement")]
    assert merger["chunk_chars"] == 47_000  # SAND-040 optimised window
    assert merger["max_input_chars"] == 54_000
    assert merger["length_retries"] == 1


def test_deploy_knobs_are_identical_across_cells():
    for doc_class in CLASSES:
        knobs = []
        for cell in CELLS:
            spec = load_run_spec(_config_path(cell, doc_class))
            env = deploy_env.spec_env(spec)
            env.pop("MODAL_VLLM_MAX_CONTAINERS")
            env.pop("MODAL_VLLM_MIN_CONTAINERS")
            env.pop("MODAL_VLLM_TELEMETRY_LABEL")
            knobs.append(env)
        assert all(k == knobs[0] for k in knobs[1:]), doc_class


# ── prompts: v1 simplified only ──────────────────────────────────────────────


def test_every_sand42_prompt_is_a_simplified_stem():
    for rid in posture.SAND42_RUNS | posture.SAND42_CHECK_RUNS | {posture.SAND42_NOISE_FLOOR_RUN}:
        stem = posture.SPECIALIST_POSTURE[rid]["prompt_file"]
        assert stem.endswith("_simplified"), (rid, stem)
        assert (repo_root() / "config" / "prompts" / f"{stem}.txt").is_file(), stem


def test_prompt_guard_rejects_a_non_simplified_stem():
    bad = {"correspondence": ("correspondence_specialist", "correspondence_specialist_production", 1, 1, 1)}
    with pytest.raises(ValueError):
        posture._assert_sand42_prompts(bad)


def test_config_pins_the_simplified_stem_as_a_local_prompt():
    for cell in CELLS:
        for doc_class in CLASSES:
            spec = load_run_spec(_config_path(cell, doc_class))
            row = posture.SPECIALIST_POSTURE[spec.run_id]
            agents = spec.prompt["agents"]
            assert set(agents) == {row["agent"]}  # 1:1 — no cross-agent pin
            ref = agents[row["agent"]]
            assert ref["source"] == "local"
            assert ref["file"] == row["prompt_file"]
            assert ref["file"].endswith("_simplified")


# ── the shared, stratified draw ──────────────────────────────────────────────


def test_every_class_stratum_sums_to_fifty_and_covers_every_subclass():
    for doc_class in CLASSES:
        strata = _raw("1l4-c8", doc_class)["dataset"]["strata"]["buckets"]
        assert len(strata) == 1
        bucket = strata[0]
        assert bucket["doc_class"] == doc_class
        subs = bucket["sub_buckets"]
        assert sum(s["count"] for s in subs) == 50
        assert all(s["count"] >= 1 for s in subs)
        assert len({s["subclass"] for s in subs}) == len(subs), "duplicate subclass quota"


def test_all_four_cells_share_one_identical_draw_per_class():
    """Pairing depends on it: byte-identical dataset blocks across the four cells."""
    for doc_class in CLASSES:
        blocks = [json.dumps(_raw(cell, doc_class)["dataset"], sort_keys=True) for cell in CELLS]
        assert len(set(blocks)) == 1, doc_class


def test_draw_is_pinned_and_seeded():
    for cell in CELLS:
        ds = _raw(cell, "contract")["dataset"]
        assert ds["repo"] == "Lucius-Morningstar/mailroom-dataset"
        assert ds["config"] == "ground_truth"
        assert ds["split"] == "all"  # train+test, both joined with ground truth
        assert ds["revision"] == "ed7576b676343e0b402ec5412cded301e629bdee"
        assert ds["sample_seed"] == 42
        assert ds["limit"] == 50


def _synthetic_corpus(doc_class: str, per_subclass: int = 60) -> list[dict]:
    """Rows shaped like the prepared corpus, enough for every quota of one class."""
    return [
        {
            "id": f"{doc_class}-{sb['subclass']}-{i}",
            "expected_doc_class": doc_class,
            "expected_subclass": sb["subclass"],
        }
        for sb in _raw("1l4-c8", doc_class)["dataset"]["strata"]["buckets"][0]["sub_buckets"]
        for i in range(per_subclass)
    ]


def test_draw_mechanics_yield_fifty_unique_docs_covering_every_subclass():
    """Exercise the real sampler against a synthetic corpus of the right shape."""
    from mailroom_sandbox.corpus import _draw_buckets, strata_draw_guard, strata_guard

    for cell in CELLS:
        for doc_class in CLASSES:
            rows = _synthetic_corpus(doc_class)
            strata = _raw(cell, doc_class)["dataset"]["strata"]
            strata_guard(rows, strata)  # requested strata exist
            drawn = _draw_buckets(rows, strata["buckets"], field="expected_doc_class", sample_seed=42)
            strata_draw_guard(drawn, strata)  # none dropped by the draw
            assert len(drawn) == 50, (cell, doc_class)
            assert len({r["id"] for r in drawn}) == 50, "duplicate document in the draw"
            got = {r["expected_subclass"] for r in drawn}
            want = {
                sb["subclass"]
                for sb in _raw(cell, doc_class)["dataset"]["strata"]["buckets"][0]["sub_buckets"]
            }
            assert got == want, (cell, doc_class, want - got)
            assert all(r["expected_doc_class"] == doc_class for r in drawn)


def test_draw_is_deterministic_so_the_four_cells_are_paired():
    from mailroom_sandbox.corpus import _draw_buckets

    rows = _synthetic_corpus("contract")
    buckets = _raw("1l4-c8", "contract")["dataset"]["strata"]["buckets"]
    a = [r["id"] for r in _draw_buckets(rows, buckets, field="expected_doc_class", sample_seed=42)]
    b = [r["id"] for r in _draw_buckets(rows, buckets, field="expected_doc_class", sample_seed=42)]
    assert a == b
    assert len(a) == 50
    assert len({r.split("-")[1] for r in a}) == 26  # every contract sub-type represented


def test_a_quota_above_availability_hard_fails_rather_than_truncating():
    from mailroom_sandbox.corpus import _draw_buckets

    rows = [
        {"id": f"contract-Supply-{i}", "expected_doc_class": "contract", "expected_subclass": "Supply"}
        for i in range(2)
    ]
    buckets = [{"doc_class": "contract", "count": 3, "sub_buckets": [{"subclass": "Supply", "count": 3}]}]
    with pytest.raises(ValueError, match="only 2 available"):
        _draw_buckets(rows, buckets, field="expected_doc_class", sample_seed=42)


def test_subclass_vocabulary_matches_the_corpus():
    """Quotas must name real sub-types, or the draw hard-fails at preflight."""
    expected = {
        "correspondence": {
            "email", "memo", "notice", "letter", "press_release", "demand",
            "meeting_request", "attorney_demand",
        },
        "insurance_claim": {"auto", "property", "carrier", "inpatient", "outpatient", "pde"},
        "corporate_record": {
            "charter_amendment", "articles_of_incorporation", "officer_certificate", "indenture",
            "subsidiary_list", "rights_instrument", "board_resolution", "powers_of_attorney",
            "bylaws", "other",
        },
        "merger_agreement": {
            "all_cash", "other", "all_stock", "mixed_cash_stock", "mixed_cash_stock_election",
        },
    }
    for doc_class, subs in expected.items():
        got = {
            s["subclass"]
            for s in _raw("1l4-c8", doc_class)["dataset"]["strata"]["buckets"][0]["sub_buckets"]
        }
        assert got == subs, doc_class
    # contracts: 26 sub-types, every one represented
    contracts = {
        s["subclass"]
        for s in _raw("1l4-c8", "contract")["dataset"]["strata"]["buckets"][0]["sub_buckets"]
    }
    assert len(contracts) == 26
    assert "Supply" in contracts and "Non_Compete_Non_Solicit" in contracts


# ── benchmark-check accepts every cell ───────────────────────────────────────


@pytest.fixture
def _modal_host(monkeypatch):
    # The posture check also probes the operator's machine (modal CLI on PATH,
    # an active ~/.modal.toml profile). CI has neither; these tests pin the
    # run specs, so stub the host probes as the other gate tests do.
    monkeypatch.setattr(benchmark_check, "active_modal_profile_name", lambda: "hermes-agent-jjb")
    monkeypatch.setattr(benchmark_check, "_modal_cli_ok", lambda: {"ok": True, "version": "stub"})


@pytest.mark.parametrize("cell", CELLS)
def test_benchmark_check_accepts_every_config(cell, monkeypatch, _modal_host):
    for doc_class in CLASSES:
        spec = load_run_spec(_config_path(cell, doc_class))
        for key, val in deploy_env.spec_env(spec).items():
            monkeypatch.setenv(key, val)
        report = benchmark_check.check_benchmark_posture(
            spec=spec, require_hermes=False, require_modernbert=False
        )
        assert report["ok"], (spec.run_id, report["errors"])


def test_benchmark_check_accepts_the_noise_floor_leg(monkeypatch, _modal_host):
    spec = load_run_spec(
        repo_root() / "config" / "runs" / f"{posture.SAND42_NOISE_FLOOR_RUN}.yaml"
    )
    for key, val in deploy_env.spec_env(spec).items():
        monkeypatch.setenv(key, val)
    report = benchmark_check.check_benchmark_posture(
        spec=spec, require_hermes=False, require_modernbert=False
    )
    assert report["ok"], report["errors"]


def test_sand42_runs_are_in_the_two_and_one_gpu_allowlists():
    # 2×L4 cells: 2l4-c8, 2l4-c16, 2l4-c32 (5 each).
    assert len(posture.SAND42_TWO_GPU_RUNS) == 15
    # 10 one-GPU cell runs + the noise-floor leg + the two check legs (corporate smoke, merger probe).
    # Unchanged by the C32 amendment: C32 is a 2-GPU cell.
    assert len(posture.SAND42_ONE_GPU_RUNS) == 13
    assert posture.SAND42_TWO_GPU_RUNS <= posture.SAND42_RUNS
    extras = {posture.SAND42_NOISE_FLOOR_RUN, *posture.SAND42_CHECK_RUNS}
    assert posture.SAND42_ONE_GPU_RUNS - extras <= posture.SAND42_RUNS
    assert posture.SAND42_ONE_GPU_RUNS & posture.SAND42_TWO_GPU_RUNS == frozenset()
    for rid in posture.SAND42_TWO_GPU_RUNS:
        assert benchmark_check.TWO_GPU_RUNS >= {rid}
    for rid in posture.SAND42_ONE_GPU_RUNS:
        assert benchmark_check.PINNED_ONE_GPU_RUNS >= {rid}
    for rid in posture.SAND42_CHECK_RUNS:
        assert benchmark_check.SAND42_CHECK_RUNS >= {rid}


# ── noise floor ──────────────────────────────────────────────────────────────


def test_noise_floor_leg_is_the_same_spec_on_the_same_documents():
    twin = _raw("1l4-c8", "correspondence")
    floor = yaml.safe_load(
        (repo_root() / "config" / "runs" / f"{posture.SAND42_NOISE_FLOOR_RUN}.yaml").read_text()
    )
    assert floor["dataset"] == twin["dataset"]
    assert floor["prompt"] == twin["prompt"]
    assert floor["engine"] == twin["engine"]
    assert floor["job"] == twin["job"]
    assert floor["run_id"] != twin["run_id"]


def test_noise_floor_runbook_is_cleared_for_the_approved_rerun():
    """Spend was approved 2026-10-12, so the flag was dropped — and the mechanism still bites.

    The flag only ever gated the GENERATED script, never the config (the leg rode the
    1l4-c8 re-run's boot). Kept as a test so a future leg cannot be quietly unblocked
    without an approval recorded in its reason, and so the refusal path stays covered by
    a book that IS still blocked.
    """
    from mailroom_sandbox.job.runbooks import get_runbook, render_shell

    book = get_runbook("sand42-noise-floor")
    assert book.get("blocked") is False
    assert "approved" in str(book.get("blocked_reason") or "").lower()

    still_blocked = get_runbook("improved-correspondence-fp16-c8")
    assert still_blocked.get("blocked") is True
    shell = render_shell("improved-correspondence-fp16-c8")
    assert "BLOCKED" in shell and "refuse execution" in shell


# ── telemetry ────────────────────────────────────────────────────────────────


SMI = (
    "0, NVIDIA L4, 94, 23000, 23034, 56, 71.5\n"
    "1, NVIDIA L4, 0, 120, 23034, 41, [N/A]\n"
)


def test_parse_nvidia_smi_csv_handles_na_and_units():
    gpus = container_telemetry.parse_nvidia_smi_csv(SMI)
    assert len(gpus) == 2
    assert gpus[0]["utilization_gpu_perc"] == 94.0
    assert gpus[0]["power_draw_w"] == 71.5
    assert gpus[0]["temperature_c"] == 56.0
    assert gpus[1]["power_draw_w"] is None  # [N/A] is not zero
    assert gpus[1]["utilization_gpu_perc"] == 0.0


def test_summarize_reports_the_a100_card_fields():
    doc = {
        "label": "sand42-1l4-c8",
        "samples": [
            {"t": 1.0, "gpus": container_telemetry.parse_nvidia_smi_csv(SMI)},
            {"t": 2.0, "gpus": container_telemetry.parse_nvidia_smi_csv(SMI)},
        ],
        "replicas": {"host-a": {"samples": [{"t": 1.0, "gpus": [{"utilization_gpu_perc": 94.0}]}]}},
    }
    out = container_telemetry.summarize_samples(doc)
    assert out["captured"] is True
    assert out["samples"] == 2
    assert out["util_mean_perc"] == pytest.approx((94 + 0 + 94 + 0) / 4)
    assert out["util_peak_perc"] == 94.0
    assert out["power_draw_w"]["mean"] == pytest.approx(71.5)
    assert out["src"] == "serving-replica nvidia-smi"
    assert out["replicas"]["host-a"]["util_mean_perc"] == 94.0


def test_summarize_adds_util_p95_and_sampling_coverage():
    """Issue #128's telemetry contract: p95 util, and a sampling-coverage gate."""
    doc = {
        "label": "sand42-1l4-c8",
        "start": 0.0,
        "end": 100.0,
        "samples": [
            {"t": float(t), "gpus": [{"utilization_gpu_perc": 90.0}]} for t in range(0, 101, 10)
        ],
        "replicas": {},
    }
    out = container_telemetry.summarize_samples(doc)
    assert out["util_p95_perc"] == 90.0
    assert out["sampling_coverage_pct"] == pytest.approx(100.0, abs=5)


def test_sampling_coverage_drops_when_the_sampler_drops_out():
    """A long gap lowers coverage — the sampler cannot redefine 'expected' to suit itself."""
    stamps = [float(t) for t in list(range(0, 41, 10)) + list(range(400, 441, 10))]
    doc = {
        "label": "x",
        "start": 0.0,
        "end": 440.0,
        "samples": [{"t": t, "gpus": [{"utilization_gpu_perc": 90.0}]} for t in stamps],
        "replicas": {},
    }
    out = container_telemetry.summarize_samples(doc)
    assert out["sampling_coverage_pct"] < 30  # 10 samples over a 440 s window at a 10 s cadence


def test_sampling_coverage_is_none_not_a_fabricated_hundred():
    assert container_telemetry._coverage_pct([], None, None) is None
    assert container_telemetry._coverage_pct([{"t": 1.0}], 0.0, 100.0) is None  # < 3 samples
    assert container_telemetry._coverage_pct([{"t": t} for t in (1.0, 2.0, 3.0)], None, 4.0) is None


def test_summarize_says_not_captured_rather_than_zero():
    out = container_telemetry.summarize_samples({"samples": [], "reason": "volume empty"})
    assert out["captured"] is False
    assert out["reason"] == "volume empty"
    assert "util_mean_perc" not in out


def test_slice_window_keeps_only_the_run_own_samples():
    samples = [{"t": t} for t in (1.0, 5.0, 9.0, 20.0)]
    kept = container_telemetry.slice_window(samples, start=5.0, end=9.0)
    assert [s["t"] for s in kept] == [5.0, 9.0]


def test_parse_jsonl_skips_malformed_lines():
    rows = container_telemetry.parse_jsonl('{"t": 1}\nnot json\n\n{"t": 2}\n')
    assert [r["t"] for r in rows] == [1, 2]


def test_pull_degrades_when_the_sdk_or_volume_is_unavailable(monkeypatch):
    def boom(*_a, **_k):
        raise ImportError("no modal")

    monkeypatch.setattr(container_telemetry, "_read_volume_files", boom)
    out = container_telemetry.pull("sand42-1l4-c8")
    assert out["samples"] == [] and out["errors"]
    assert "Modal telemetry volume" in out["reason"]


def test_read_file_drains_a_synchronous_generator():
    """Live bug: read_file is @live_method_gen, so it yields a SYNC generator
    outside async code; an `async for` raised "'async for' requires __aiter__"."""
    class _Vol:
        def read_file(self, path):
            return (chunk for chunk in [b'{"t": 1}\n', b'{"t": 2}\n'])

    assert container_telemetry._read_file(_Vol(), "x.jsonl") == '{"t": 1}\n{"t": 2}\n'


def test_volume_path_is_root_relative_not_the_container_mount(monkeypatch):
    """Live bug: /telemetry is the CONTAINER mount; the volume path is just <label>."""
    import sys
    import types

    seen: dict[str, str] = {}

    class _Vol:
        def listdir(self, path, recursive=False):
            seen["path"] = path
            return []

        def read_file(self, path):  # pragma: no cover - not reached
            return iter(())

    monkeypatch.setitem(
        sys.modules, "modal", types.SimpleNamespace(Volume=types.SimpleNamespace(from_name=lambda *a, **k: _Vol()))
    )
    container_telemetry._read_volume_files("sand42-1l4-c8")
    assert seen["path"] == "sand42-1l4-c8"  # NOT "telemetry/sand42-1l4-c8"


def test_pull_reads_a_real_shaped_volume(monkeypatch):
    """End-to-end over a fake volume: replicas keyed by the .jsonl stem."""
    import sys
    import types

    sample = '{"t": 10.0, "gpus": [{"utilization_gpu_perc": 91.0, "power_draw_w": 70.0}]}\n'

    class _Vol:
        def listdir(self, path, recursive=False):
            return [types.SimpleNamespace(path=f"{path}/1767000123.0.jsonl")]

        def read_file(self, path):
            return (chunk for chunk in [sample.encode()])

    monkeypatch.setitem(
        sys.modules, "modal", types.SimpleNamespace(Volume=types.SimpleNamespace(from_name=lambda *a, **k: _Vol()))
    )
    doc = container_telemetry.pull("sand42-1l4-c8", start=0.0, end=100.0)
    assert doc["errors"] == []
    assert list(doc["replicas"]) == ["1767000123.0"]
    out = container_telemetry.summarize_samples(doc)
    assert out["captured"] is True
    assert out["util_mean_perc"] == 91.0
    assert out["samples"] == 1


def test_card_md_renders_the_gpu_hardware_rows():
    """The JSON carried the GPU block but the markdown did not — the operator reads .md."""
    gpu = {
        "captured": True,
        "src": "serving-replica nvidia-smi",
        "samples": 4,
        "util_mean_perc": 49.0,
        "util_min_perc": 0.0,
        "util_peak_perc": 100.0,
        "util_p95_perc": 100.0,
        "sampling_coverage_pct": 96.0,
        "power_draw_w": {"mean": 52.4, "min": 31.9, "max": 72.9},
        "temperature_c": {"mean": 69.8, "min": 66.0, "max": 72.0},
        "memory_used_mib": {"mean": 20938.0, "min": 20764.0, "max": 20996.0},
    }
    rows = dict(grid_cards._gpu_rows(gpu))
    assert rows["**GPU hardware (nvidia-smi)**"] == "4 samples · serving-replica nvidia-smi"
    assert "49.0 %" in rows["GPU utilization"] and "peak 100.0" in rows["GPU utilization"]
    assert "p95 100.0" in rows["GPU utilization"]
    assert rows["Sampling coverage"] == "96.0 %"
    assert "52.4 W" in rows["GPU power draw"]
    assert "69.8 C" in rows["GPU temperature"]


def test_card_flags_a_cell_below_the_issue_128_coverage_gate():
    """#128 rejects a cell below 90% sampling coverage — the card must say so, not hide it."""
    gpu = {
        "captured": True,
        "src": "serving-replica nvidia-smi",
        "samples": 30,
        "util_mean_perc": 49.0,
        "util_min_perc": 0.0,
        "util_peak_perc": 100.0,
        "util_p95_perc": 100.0,
        "sampling_coverage_pct": 61.0,
    }
    assert "below the 90% gate" in dict(grid_cards._gpu_rows(gpu))["Sampling coverage"]
    assert "gate" not in dict(grid_cards._gpu_rows({**gpu, "sampling_coverage_pct": 96.0}))["Sampling coverage"]


def test_gpu_rows_say_not_captured_rather_than_zero():
    assert grid_cards._gpu_rows(None) == [("**GPU hardware (nvidia-smi)**", "not captured")]
    assert grid_cards._gpu_rows({"captured": False})[0][1] == "not captured"


def test_card_md_renders_the_gpu_block(monkeypatch):
    monkeypatch.setattr(grid_cards, "_read_json", lambda p: {"samples": [{"t": 1.0, "gpus": [
        {"utilization_gpu_perc": 88.0, "power_draw_w": 70.0, "temperature_c": 55.0,
         "memory_used_mib": 23000.0, "memory_total_mib": 23034.0}]}], "replicas": {}})

    class _Store:
        dir = repo_root()

    block = grid_cards._container_telemetry(_Store())
    assert block["captured"] is True and block["util_mean_perc"] == 88.0


def test_deploy_env_carries_the_cell_label():
    for cell in CELLS:
        spec = load_run_spec(_config_path(cell, "correspondence"))
        assert deploy_env.spec_env(spec)["MODAL_VLLM_TELEMETRY_LABEL"] == f"sand42-{cell}"
    # non-SAND42 runs leave the sampler on the deploy default label
    other = load_run_spec(repo_root() / "config" / "runs" / "sand037" / "grid-50-correspondence-specialist-awq-1l4.yaml")
    assert deploy_env.spec_env(other)["MODAL_VLLM_TELEMETRY_LABEL"] == ""


def test_cell_label_is_shared_by_all_five_configs_of_a_cell():
    for cell in CELLS:
        labels = {posture.sand42_cell_label(posture.sand42_run_id(cell, c)) for c in CLASSES}
        assert labels == {f"sand42-{cell}"}
    assert posture.sand42_cell_label("grid-50-contracts-specialist-awq-1l4") == ""


# ── reports ──────────────────────────────────────────────────────────────────


def test_sand42_cards_route_to_the_sand42_study_folder():
    assert grid_cards.study_for_run("sand42-50-contracts-specialist-awq-1l4-c8") == "SAND42"
    assert grid_cards.study_for_run("grid-50-contracts-specialist-awq-1l4") == "SAND-37"
    assert grid_cards.study_for_run(None) == "SAND-37"
    paths = grid_cards.card_paths(
        "sand42-50-contracts-specialist-awq-1l4-c8", "contracts_specialist", 1
    )
    # one folder per experimental condition, then per specialist
    assert paths["md"].parent == repo_root() / "reports" / "SAND42" / "1L4-c8" / "contracts"
    two = grid_cards.card_paths(
        "sand42-50-contracts-specialist-awq-2l4-c16", "contracts_specialist", 2
    )
    assert two["md"].parent == repo_root() / "reports" / "SAND42" / "2L4-c16" / "contracts"


def test_condition_folders_separate_the_four_cells():
    assert grid_cards.condition_dir("sand42-x-1l4-c8", 1) == "1L4-c8"
    assert grid_cards.condition_dir("sand42-x-1l4-c16", 1) == "1L4-c16"
    assert grid_cards.condition_dir("sand42-x-2l4-c8", 2) == "2L4-c8"
    assert grid_cards.condition_dir("sand42-x-2l4-c16", 2) == "2L4-c16"
    # SAND-037 runs keep their two-folder layout
    assert grid_cards.condition_dir("grid-50-contracts-specialist-awq-1l4", 1) == "1L4"
    assert grid_cards.condition_dir("grid-50-contracts-specialist-awq-2l4", 2) == "2L4"


def test_every_cell_has_a_suite_stem_and_a_runbook():
    from mailroom_sandbox.job.runbooks import get_runbook

    for cell in sand42_cards.CELL_ORDER:
        assert cell in sand42_cards.CELL_STEMS
        assert cell in sand42_cards.CELLS
        assert get_runbook(f"sand42-{cell}")["id"] == f"sand42-{cell}"
        paths = sand42_cards.cell_paths(cell)
        assert paths["md"].name.startswith("SAND42-")


def test_cell_card_renders_without_any_run_cards(tmp_path):
    """Pre-run the card must render (all "not run"), not crash.

    Reads an empty repo root on purpose: pointing at the live ``reports/`` tree made
    this test pass or fail depending on whether a cell happened to be mid-run.
    """
    data = sand42_cards.collect_cell("1l4-c8", repo=tmp_path)
    assert data["cells_reported"] == 0
    md = sand42_cards.render_cell_md(data)
    assert "1× L4 · client concurrency 8" in md
    assert md.count("not run") >= 5


def test_no_two_edge_kv_row_can_come_back(tmp_path):
    """The drained-edge KV row must not return, in either rendered artifact.

    ``vllm:kv_cache_usage_perc`` is a gauge of live sequences, and the before/after scrapes
    fire at the run's two drained edges — so a row built from them read 0 in all 58
    preserved readings across every cell. It could not distinguish one cell from another,
    and it sat directly above the row that could, which is why it was deleted. Deleting it
    is only durable if the suite refuses its return, so this pins both artifacts to a single
    KV row — the mid-run maximum — and pins the module to not carrying the helper at all.
    """
    cell = sand42_cards.render_cell_md(sand42_cards.collect_cell("1l4-c8", repo=tmp_path))
    master = sand42_cards.render_master_report_md(sand42_cards.collect_master(repo=tmp_path))

    for name, md in (("cell card", cell), ("master report", master)):
        assert "KV cache use (%)" not in md, f"{name} has the drained-edge KV row back"
        kv_rows = [ln for ln in md.splitlines() if ln.startswith("|") and "KV cache" in ln]
        assert kv_rows, f"{name} lost its KV row entirely"
        assert all("mid-run (max %)" in ln for ln in kv_rows), f"{name}: {kv_rows}"

    # The helper had no other caller, so its absence is the same guarantee at the source.
    assert not hasattr(sand42_cards, "_kv_text")
    assert not hasattr(sand42_cards, "_kv_max")


def test_maybe_write_card_accepts_the_smoke_leg(monkeypatch):
    """The runner hook must auto-write the smoke card too, not only --config."""
    from mailroom_sandbox.job import grid_cards as gc

    class _Store:
        run_id = posture.SAND42_CHECK_RUN

        def read_lock(self):
            return {"run_id": posture.SAND42_CHECK_RUN}

        def load_items(self):
            return [{"id": "DOC-x"}]

    called: dict[str, str] = {}
    monkeypatch.setattr(
        gc, "write_card", lambda store, **kw: called.setdefault("run_id", store.run_id) and {}
    )
    gc.maybe_write_card(_Store())
    assert called["run_id"] == posture.SAND42_CHECK_RUN


def test_master_paths_live_at_the_study_root():
    paths = sand42_cards.master_paths()
    assert paths["card_md"].parent == repo_root() / "reports" / "SAND42"
    assert paths["card_md"].name == "SAND42-MASTER-SCORE-COST-CARD.md"
    assert paths["report_md"].name == "SAND42-MASTER-REPORT.md"
    assert paths["metered"].name == "metered-costs.json"


def test_master_card_and_report_render_before_any_run(tmp_path):
    """Reads an empty repo root on purpose: pointing at the live ``reports/`` tree made
    this pass or fail depending on how many cells had already been run."""
    data = sand42_cards.collect_master(repo=tmp_path)
    card = sand42_cards.render_master_card_md(data)
    report = sand42_cards.render_master_report_md(data)
    assert f"Conditions measured:** 0 of {len(sand42_cards.CELL_ORDER)}" in card
    assert "Pending — condition cards report" in card
    assert "master report" in report
    # every condition gets a section, and the comparison + method come with it
    for cell in sand42_cards.CELL_ORDER:
        assert f"sand42-{cell}" in card
    assert "## Method" in report and "## Open items" in report


def test_metered_spend_is_recorded_under_the_sand42_root(tmp_path):
    import json

    path = sand42_cards.write_metered("SAND-42", 1.23, 0.0, repo=tmp_path)
    assert path == tmp_path / "reports" / "SAND42" / "metered-costs.json"
    assert json.loads(path.read_text())["SAND-42"] == {"metered_usd": 1.23, "billed_usd": 0.0}


# ── statistics ───────────────────────────────────────────────────────────────


def test_wilson_brackets_the_point_estimate():
    lo, hi = sand42_cards.wilson(46, 50)
    assert lo < 46 / 50 < hi
    assert lo > 0.8
    assert sand42_cards.wilson(0, 0) is None


def test_bootstrap_ci_is_deterministic_and_brackets_the_mean():
    values = [0.1, 0.2, 0.3, 0.4, 0.5] * 10
    a = sand42_cards.bootstrap_mean_ci(values, iters=500, seed=7)
    b = sand42_cards.bootstrap_mean_ci(values, iters=500, seed=7)
    assert a == b
    mean, lo, hi = a
    assert lo <= mean <= hi


def test_paired_delta_pairs_on_item_id_and_reports_better_worse():
    a = {"documents": [{"item_id": "x", "score": 0.2}, {"item_id": "y", "score": 0.5}]}
    b = {"documents": [{"item_id": "x", "score": 0.4}, {"item_id": "y", "score": 0.4},
                       {"item_id": "z", "score": 0.9}]}
    d = sand42_cards.paired_delta(a, b, iters=200, seed=1)
    assert d["paired_documents"] == 2  # z is not paired
    assert d["delta_mean"] == pytest.approx((0.2 + -0.1) / 2)
    assert (d["better"], d["worse"], d["tie"]) == (1, 1, 0)


def test_paired_n_matches_the_program_formula():
    # BENCHMARK-PROGRAM §3: n ≈ (2.8 × SD_diff / Δ)²
    assert sand42_cards.paired_n_for(0.05, 0.077) == 19   # corporate records
    assert sand42_cards.paired_n_for(0.05, 0.122) == 47   # contracts
    # contracts at Δ=0.03: the formula gives 130; the program doc prints 131
    # (its own rounding), so allow either.
    assert sand42_cards.paired_n_for(0.03, 0.122) in (130, 131)
    assert sand42_cards.paired_n_for(0.0, 0.1) is None


def test_goodput_zeroes_a_run_that_misses_the_class_slo():
    card = {
        "conditions": {"replicas": 2},
        "time": {"wall_seconds": 600.0},
        "quality": {"documents": 50},
        "latency": {"p95": 400.0},
    }
    slow = sand42_cards._goodput(card, "contracts_specialist")   # SLO 300 s
    assert slow["meets_slo"] is False
    assert slow["goodput_documents_per_minute_per_gpu"] == 0.0
    fast = sand42_cards._goodput({**card, "latency": {"p95": 100.0}}, "contracts_specialist")
    assert fast["meets_slo"] is True
    assert fast["goodput_documents_per_minute_per_gpu"] > 0


def test_cost_per_usable_record_uses_both_denominators():
    card = {
        "cost": {"busy_gpu_usd": 1.0},
        "quality": {"documents": 100, "ok": 50, "schema_valid_rate": 0.25},
        "documents": [],
    }
    out = sand42_cards._cost_per_usable(card)
    assert out["usd_per_1k_ok"] == pytest.approx(20.0)              # 1.0 / 50 × 1000
    assert out["usd_per_1k_schema_valid"] == pytest.approx(40.0)    # 1.0 / 25 × 1000


# ── no collateral damage ─────────────────────────────────────────────────────


def test_sand42_rows_do_not_pollute_the_global_agent_budgets():
    """AGENT_GENERATION_BUDGETS is last-writer-wins; SAND-042 must stay out of it.

    Pinned to the values the five specialists carried before SAND-042 existed —
    the SAND-042 posture rows use 8192 with their own input caps, so a leak would
    move every one of these.
    """
    assert posture.AGENT_GENERATION_BUDGETS["correspondence_specialist"] == {
        "max_tokens": 2048, "max_input_chars": 12000,
    }
    assert posture.AGENT_GENERATION_BUDGETS["insurance_claims_specialist"] == {
        "max_tokens": 3072, "max_input_chars": 13500,
    }
    assert posture.AGENT_GENERATION_BUDGETS["corporate_records_specialist"] == {
        "max_tokens": 4096, "max_input_chars": 15000,
    }
    assert posture.AGENT_GENERATION_BUDGETS["contracts_specialist"] == {
        "max_tokens": 8192, "max_input_chars": 24000,
    }
    assert posture.AGENT_GENERATION_BUDGETS["merger_agreement_specialist"] == {
        "max_tokens": 4096, "max_input_chars": 19891,
    }


def test_existing_grid_cells_are_untouched():
    assert posture.GRID_CELLS
    for rid in ("grid-50-contracts-specialist-awq-1l4", "grid-50-merger-specialist-awq-2l4"):
        assert rid in posture.GRID_CELLS
        assert posture.SPECIALIST_POSTURE[rid]["max_tokens"] == 8192


def test_contracts_process_the_whole_document_chunked():
    """The 24,000-char cap dropped 62 % of contract text — the middle, where the
    operative clauses are. Contracts must run the chunked pass, not head+tail."""
    from mailroom_sandbox.eval.agents import chunk_window

    rows = [r for r in posture.SAND42_RUNS if "contracts" in r]
    assert rows, "no contracts rows"
    for rid in sorted(rows):
        row = posture.SPECIALIST_POSTURE[rid]
        assert row.get("chunk_chars"), f"{rid}: contracts must be chunked"
        assert row.get("overlap_chars"), f"{rid}: contracts need an overlap window"
        assert posture.context_fit_ok(
            row["max_tokens"], row["max_input_chars"], row["max_model_len"]
        ), f"{rid}: input cap + decode must fit the 32K window"

        # The knobs must actually reach the agent, and no chunk may be truncated.
        knobs = posture.agent_knobs_for_run(rid)[row["agent"]]
        assert knobs["chunk_chars"] == row["chunk_chars"]
        window, overlap = chunk_window(
            knobs["max_input_chars"], knobs["chunk_chars"], knobs["overlap_chars"]
        )
        assert window + overlap <= knobs["max_input_chars"], rid


def test_short_classes_keep_their_single_pass_cap():
    """Chunking must not spread to classes whose documents fit one window.

    Contracts and merger are chunked on purpose: their real draws exceed one window
    many times over (62 % and 93 % of text was being dropped). The three short classes
    fit, and chunking them would add calls for no coverage gain.
    """
    for slug in ("correspondence", "insurance-claims", "corporate-records"):
        rid = f"sand42-50-{slug}-specialist-awq-1l4-c8"
        assert posture.SPECIALIST_POSTURE[rid].get("chunk_chars") is None, rid


def test_merger_runs_the_sand040_optimised_whole_document_posture():
    """Merger's 93 %-dropped input is replaced by our most efficient whole-document
    method: the SAND-040 optimised posture. It also fixes the 3/50 hard
    LengthFinishReasonError failures, via the 6144 cap plus one re-sample."""
    rows = [r for r in posture.SAND42_RUNS if "merger" in r]
    assert rows, "no merger rows"
    for rid in sorted(rows):
        row = posture.SPECIALIST_POSTURE[rid]
        assert row["chunk_chars"] == 47000 and row["overlap_chars"] == 6500, rid
        assert row["max_tokens"] == 6144, rid
        assert row["top_p"] == 0.8 and row["presence_penalty"] == 1.0, rid
        assert row["length_retries"] == 1, rid
        assert posture.context_fit_ok(
            row["max_tokens"], row["max_input_chars"], row["max_model_len"]
        ), rid


# ── cost is computed from the run/session, never scraped ─────────────────────


def test_cell_fleet_cost_is_computed_from_the_recorded_window(tmp_path):
    """`min_containers=1` bills the whole warm window, so the cell's cost is the fleet
    window x replicas x rate — computed from the session, not from the billing CLI
    (whose figures are credits-based and workspace-wide, not per cell)."""
    d = sand42_cards._cell_dir("2l4-c16", repo=tmp_path)
    d.mkdir(parents=True, exist_ok=True)
    (d / "fleet_window.json").write_text(json.dumps({
        "cell": "2l4-c16", "gpu": "L4", "replicas": 2,
        "deploy_ts": 1000.0, "ready_ts": 1130.0, "teardown_ts": 4000.0,
    }))
    fleet = sand42_cards.fleet_cost("2l4-c16", repo=tmp_path)
    assert fleet["measured"] is True
    assert fleet["fleet_seconds"] == 3000.0
    assert fleet["cold_boot_seconds"] == 130.0
    assert fleet["fleet_gpu_hours"] == round(3000.0 * 2 / 3600, 4)
    assert fleet["fleet_gpu_usd"] == round(3000.0 * 2 * 0.80 / 3600, 4)


def test_cell_fleet_cost_says_so_rather_than_guessing(tmp_path):
    """An unclosed or absent window must report `measured: False`, never a number."""
    d = sand42_cards._cell_dir("1l4-c8", repo=tmp_path)
    d.mkdir(parents=True, exist_ok=True)
    (d / "fleet_window.json").write_text(
        json.dumps({"cell": "1l4-c8", "replicas": 1, "deploy_ts": 5.0})
    )
    fleet = sand42_cards.fleet_cost("1l4-c8", repo=tmp_path)
    assert fleet["measured"] is False and "not closed" in fleet["reason"]

    empty = sand42_cards.fleet_cost("1l4-c8", repo=tmp_path / "elsewhere")
    assert empty["measured"] is False and "no fleet_window.json" in empty["reason"]


def test_cell_card_renders_the_computed_fleet_cost(tmp_path):
    cell_data = {
        "cell": "1l4-c8", "replicas": 1, "concurrency": 8, "concurrency_per_replica": 8,
        "runbook": "sand42-1l4-c8", "cells_reported": 0, "specialists": [], "cards": {},
        "generated_at": "2026-10-12T00:00:00+00:00",
        "fleet": {"measured": True, "replicas": 1, "gpu": "L4", "gpu_usd_per_hour": 0.80,
                  "cold_boot_seconds": 130.0, "fleet_seconds": 7200.0,
                  "fleet_gpu_hours": 2.0, "fleet_gpu_usd": 1.60},
    }
    md = sand42_cards.render_cell_md(cell_data)
    assert "## Cost (computed from the session)" in md
    assert "**$1.6000**" in md and "7,200.0 s" in md


# ── the SAND42 master must never touch another study's master ────────────────


def test_sand42_master_is_a_separate_file_from_the_sand37_master():
    """`--runbook sand42` must never overwrite the SAND-37 master.

    `--master` is the SAND-37 writer (`grid_master.write_master`, which also emits
    SAND-39 / SAND-40 postures into reports/SAND-37/); `--runbook sand42` is the SAND42
    writer (`sand42_cards.write_all`). Different flags, different outputs — this pins
    that the two path sets can never collide.
    """
    from mailroom_sandbox.job import grid_master

    sand42 = {p.resolve() for p in sand42_cards.master_paths().values()}
    sand37 = {p.resolve() for p in grid_master.master_paths().values()}
    assert sand42 and sand37
    assert not (sand42 & sand37), f"master paths collide: {sand42 & sand37}"
    for p in sand42:
        assert "SAND42" in p.parts and "SAND-37" not in p.parts, p
    for p in sand37:
        assert "SAND-37" in p.parts, p


def test_write_all_writes_only_under_the_sand42_study_root(tmp_path):
    """Every artifact `--runbook sand42` emits stays inside reports/SAND42/."""
    written = sand42_cards.write_all(repo=tmp_path)
    assert written, "write_all emitted nothing"
    root = (tmp_path / "reports" / "SAND42").resolve()
    for label, path in written.items():
        assert path.resolve().is_relative_to(root), f"{label} escaped the study root: {path}"
    assert not (tmp_path / "reports" / "SAND-37").exists(), "wrote into reports/SAND-37/"


def test_master_report_per_run_links_resolve_from_the_study_root(tmp_path):
    """The master report embeds each cell's markdown one level ABOVE the cell folder,
    so per-run links must be rebased with the condition folder. Unrebased they point at
    `correspondence/…` from reports/SAND42/, where no such path exists — every link 404s.

    Seeds one reported leg, because an empty repo emits no links at all and would let
    the bug through.
    """
    import re

    rid = "sand42-50-correspondence-specialist-awq-1l4-c8"
    folder = sand42_cards._cell_dir("1l4-c8", repo=tmp_path) / "correspondence"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{rid}.card.md").write_text("# card\n", encoding="utf-8")
    (folder / f"{rid}.card.json").write_text(
        json.dumps({
            "run_id": rid, "n": 2, "documents": [{"score": 0.5}, {"score": 0.7}],
            "quality": {"ok": 2, "documents": 2, "schema_valid_rate": 1.0, "errors": 0,
                        "error_kinds": {}},
            "latency": {"p50": 1.0, "p95": 2.0}, "time": {"wall_seconds": 10.0},
            "cost": {"billed_gpu_usd": 0.01, "billed_seconds": 10.0, "busy_gpu_usd": 0.01},
        }),
        encoding="utf-8",
    )

    sand42_cards.write_all(repo=tmp_path)
    master = tmp_path / "reports" / "SAND42" / "SAND42-MASTER-REPORT.md"
    links = [
        t for t in re.findall(r"\]\(([^)]+)\)", master.read_text(encoding="utf-8"))
        if t.endswith(".card.md")
    ]
    assert links, "master report has no per-run card links to check"
    for target in links:
        assert target.startswith("1L4-c8/"), f"link not rebased with the condition folder: {target}"
        assert (master.parent / target).exists(), f"master report link 404s: {target}"


# ── the L4-comparable GPU extras (memory bandwidth / power cap / SM clock) ────


def test_nvidia_smi_parse_captures_the_l4_comparable_extras():
    """These three are exposed on every NVIDIA datacentre GPU, so the same query is
    valid on an A100 — they are the closest comparable columns we were missing."""
    row = container_telemetry.parse_nvidia_smi_csv(
        "0, NVIDIA L4, 97, 21026, 23034, 73, 71.4, 12, 72.00, 1710"
    )[0]
    assert row["utilization_memory_perc"] == 12.0   # memory BANDWIDTH, not capacity
    assert row["power_limit_w"] == 72.0             # the cap, to normalise power draw
    assert row["clocks_sm_mhz"] == 1710.0           # throttling evidence


def test_nvidia_smi_parse_still_accepts_a_seven_column_capture():
    """A container running the older query must still parse and report the extras as
    absent — never drop the whole sample over a missing optional column."""
    row = container_telemetry.parse_nvidia_smi_csv(
        "0, NVIDIA L4, 97, 21026, 23034, 73, 71.4"
    )[0]
    assert row["utilization_gpu_perc"] == 97.0
    assert row["utilization_memory_perc"] is None
    assert row["power_limit_w"] is None
    assert row["clocks_sm_mhz"] is None


def test_summarize_reports_the_extra_gpu_stats():
    doc = {
        "start": 0.0,
        "end": 30.0,
        "samples": [
            {"t": t, "gpus": [{"utilization_gpu_perc": 95, "utilization_memory_perc": mb,
                               "power_limit_w": 72.0, "clocks_sm_mhz": 1700}]}
            for t, mb in ((5.0, 10.0), (12.0, 20.0), (20.0, 30.0))
        ],
        "replicas": {},
    }
    s = container_telemetry.summarize_samples(doc)
    assert s["utilization_memory_perc"]["mean"] == 20.0
    assert s["power_limit_w"]["mean"] == 72.0
    assert s["clocks_sm_mhz"]["mean"] == 1700.0


def test_report_lock_serializes_and_atomic_write_lands(tmp_path, monkeypatch):
    """Two builders (parallel fleets + the driver) must not tear the master.

    The lock is what keeps the master report / comparison / figures from being
    rewritten while another process reads them; the temp+replace keeps a reader
    from ever seeing a half-written file.
    """
    import fcntl

    from mailroom_sandbox.job import sand42_cards

    root = tmp_path / "SAND42"
    monkeypatch.setattr(sand42_cards, "study_root", lambda *a, **k: root)

    with sand42_cards.report_lock(timeout_s=2):
        held = open(root / ".report.lock", "w", encoding="utf-8")
        with pytest.raises(OSError):
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        held.close()

    # Released: a fresh exclusive acquire succeeds.
    after = open(root / ".report.lock", "w", encoding="utf-8")
    fcntl.flock(after, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fcntl.flock(after, fcntl.LOCK_UN)
    after.close()

    target = root / "SAND42-MASTER-REPORT.md"
    sand42_cards._atomic_text(target, "master\n")
    assert target.read_text(encoding="utf-8") == "master\n"
    assert not list(root.glob(".SAND42-MASTER-REPORT.md.tmp*")), "temp file left behind"
