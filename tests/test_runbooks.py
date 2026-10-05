"""SAND-031 — centralized operator runbook catalog."""

from __future__ import annotations

from mailroom_sandbox.cli import main
from mailroom_sandbox.job.runbooks import (
    REQUIRED_IDS,
    docs_are_current,
    env_exports,
    generated_dir,
    get_runbook,
    list_runbook_ids,
    load_catalog,
    render_markdown,
    render_shell,
    resolve_runbook_id,
    serving_knobs,
    verify_live_pins,
    write_docs,
)


def setup_function() -> None:
    load_catalog.cache_clear()


def test_catalog_has_required_runbooks():
    ids = list_runbook_ids()
    for rid in REQUIRED_IDS:
        assert rid in ids, rid
    assert list_runbook_ids(family="baseline")[0] == "l4-qwen3-8b"
    assert "improved-awq-c8" in list_runbook_ids(family="improved")


def test_aliases_resolve():
    assert resolve_runbook_id("l4") == "l4-qwen3-8b"
    assert resolve_runbook_id("singular") == "l4-qwen3-8b"
    assert resolve_runbook_id("awq-c8") == "improved-awq-c8"
    assert resolve_runbook_id("granite") == "improved-granite-fp8"
    assert resolve_runbook_id("track-a") == "l4-qwen3-8b-track-a"
    assert resolve_runbook_id("a100-sorter") == "a100-qwen3-14b-awq-sorter400"
    assert resolve_runbook_id("qwen3-14b-awq") == "a100-qwen3-14b-awq-sorter400"


def test_a100_sorter400_awq_14b_pins():
    knobs = serving_knobs("awq-14b-a100")
    assert knobs["model"] == "Qwen/Qwen3-14B-AWQ"
    assert knobs["gpu"] == "A100-40GB"
    assert knobs["quantization"] == "awq_marlin"
    assert int(knobs["max_model_len"]) == 32768
    assert int(knobs["max_num_seqs"]) == 32
    assert int(knobs["max_containers"]) == 1
    assert int(knobs["min_containers"]) == 1
    assert int(knobs["scaledown_seconds"]) == 600
    assert int(knobs["enforce_eager"]) == 0
    row = get_runbook("a100-qwen3-14b-awq-sorter400")
    assert row["skip_check"] is True
    md = render_markdown("a100-qwen3-14b-awq-sorter400")
    assert "Qwen/Qwen3-14B-AWQ" in md
    assert "A100-40GB" in md
    assert "sorter_v1" in md
    script = render_shell("a100-qwen3-14b-awq-sorter400")
    assert "run-400-sorter-qwen3-14b-awq-a100.yaml" in script
    assert "MODAL_VLLM_GPU=A100-40GB" in script
    assert "--strategy recreate" in script
    assert "modal-matrix env Qwen/Qwen3-14B-AWQ --gpu A100-40GB" in script
    assert "ONLY after this run" in script
    assert "ONLY after the this run" not in script
    env = env_exports(get_runbook("a100-qwen3-14b-awq-sorter400"))
    assert env["PHOENIX_TRACING"] == "disabled"


def test_baseline_serving_is_singular_l4_one_container_qwen():
    knobs = serving_knobs("baseline")
    assert knobs["model"] == "Qwen/Qwen3-8B"
    assert knobs["gpu"] == "L4"
    assert int(knobs["max_containers"]) == 1
    assert int(knobs["max_model_len"]) == 16384
    assert int(knobs["max_num_seqs"]) == 6
    assert knobs["image_tag"] == "v0.29.0"
    assert int(knobs["scaledown_seconds"]) == 120
    assert knobs["quantization"] in ("", None)


def test_improved_variants_keep_one_container():
    for variant in ("awq-16k", "awq-32k", "granite-fp8"):
        knobs = serving_knobs(variant)
        assert int(knobs["max_containers"]) == 1, variant
        assert knobs["gpu"] == "L4", variant
    second = serving_knobs("second-l4-dp")
    assert int(second["max_containers"]) == 2
    assert second["model"] == "Qwen/Qwen3-8B"


def test_l4_runbook_shell_is_complete():
    script = render_shell("l4-qwen3-8b")
    assert "MODAL_VLLM_MODEL=Qwen/Qwen3-8B" in script
    assert "MODAL_VLLM_GPU=L4" in script
    assert "MODAL_VLLM_MAX_CONTAINERS=1" in script
    assert "MODAL_VLLM_GPU_MEMORY_UTILIZATION=0.90" in script
    assert "modal run deploy/modal_vllm.py::download_model" in script
    assert "modal deploy deploy/modal_vllm.py" in script
    assert "--strategy recreate" not in script
    assert "sandbox run suite --suite full" in script
    assert "run-30-contracts-specialist.yaml" in script
    assert "teardown_vllm.sh" in script
    assert "sandbox cutover --profile modal-vllm" in script


def test_track_b_requires_second_profile():
    script = render_shell("l4-qwen3-8b-track-b")
    assert "SANDBOX_MODAL_PROFILE_TRACK_B" in script
    assert "run-30-merger-specialist.yaml" in script
    assert "--allow-non-hermes" in script


def test_improved_awq_c8_recreates_and_sets_knobs():
    script = render_shell("improved-awq-c8")
    assert "Qwen/Qwen3-8B-AWQ" in script
    assert "MODAL_VLLM_MAX_MODEL_LEN=32768" in script
    assert "MODAL_VLLM_MAX_CONTAINERS=1" in script
    assert "--strategy recreate" in script
    assert "SANDBOX_AGENT_KNOBS=" in script
    assert "run-20-contracts-awq-c8.yaml" in script


def test_fp16_twin_is_blocked():
    row = get_runbook("improved-correspondence-fp16-c8")
    assert row["blocked"] is True
    script = render_shell("improved-correspondence-fp16-c8")
    assert "BLOCKED" in script
    assert "run-20-correspondence-fp16-c8.yaml" in script


def test_granite_runbook_documents_smoke_and_skips_qwen_check():
    md = render_markdown("improved-granite-fp8")
    assert "ibm-granite/granite-4.2-8b-fp8" in md
    # The runbook must explain why the newer parser is NOT used: vLLM v0.29.0
    # (the pinned image) has no `granite_thinking_parser` and crash-loops on
    # boot, so the verified pin is the native `granite` parser.
    assert "granite_thinking_parser" in md
    assert "Deploy smoke" in md
    script = render_shell("improved-granite-fp8")
    assert "benchmark-check" not in script
    env = env_exports(get_runbook("improved-granite-fp8"))
    assert env["MODAL_VLLM_REASONING_PARSER"] == "granite"
    assert int(env["MODAL_VLLM_MAX_CONTAINERS"]) == 1


def test_markdown_notes_are_strings():
    md = render_markdown("l4-qwen3-8b")
    assert "{'Attended" not in md
    assert "Unattended/overnight" in md


def test_markdown_includes_live_posture():
    md = render_markdown("l4-qwen3-8b")
    assert "run-30-merger-specialist" in md
    assert "merger_agreement_specialist" in md
    assert "contracts_specialist_v1" in md or "contracts_specialist_v33_simplified" in md


def test_verify_live_pins_clean():
    errors = verify_live_pins()
    assert errors == [], errors


def test_generated_docs_match_renderer():
    """Generated runbook and family docs match the renderer, including catalog depths."""
    errors = docs_are_current()
    assert errors == [], errors
    dest = generated_dir()
    generated = load_catalog()["generated_docs"]
    l4_doc = dest / generated["runbooks"]["l4-qwen3-8b"]
    improved_doc = dest / generated["families"]["improved"]
    grid_family = dest / generated["families"]["grid"]
    assert l4_doc.is_file()
    assert improved_doc.is_file()
    text = l4_doc.read_text(encoding="utf-8")
    assert "Qwen/Qwen3-8B" in text
    assert "max_containers" in text
    assert "../../../../../config/runbooks/catalog.yaml" in text
    improved = improved_doc.read_text(encoding="utf-8")
    assert "Qwen/Qwen3-8B-AWQ" in improved
    assert "ibm-granite/granite-4.2-8b-fp8" in improved
    # Family rollups sit at a different depth than nested cards; catalog links
    # must be rewritten for the family file, not copied from the nested path.
    assert improved.count("](../../../../config/runbooks/catalog.yaml)") >= 8
    assert "](../../../config/runbooks/catalog.yaml)" not in grid_family.read_text(
        encoding="utf-8"
    )
    assert "docs/pretty-logging/mailroom-themed-logging.md" in (
        dest / generated["runbooks"]["a100-qwen3-14b-awq-sorter400"]
    ).read_text(encoding="utf-8")


def test_runbook_writer_preserves_unmanaged_markdown(tmp_path):
    """write_docs leaves handwritten markdown beside generated cards."""
    keep = tmp_path / "handwritten.md"
    keep.write_text("User-authored note.\n", encoding="utf-8")
    write_docs(dest=tmp_path)
    assert keep.read_text(encoding="utf-8") == "User-authored note.\n"


def test_cli_list_show_check(capsys, tmp_path):
    rc = main(["runbook", "list"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "l4-qwen3-8b" in out
    assert "improved-awq-c8" in out

    rc = main(["runbook", "show", "l4", "--shell"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "MODAL_VLLM_MAX_CONTAINERS=1" in out

    rc = main(["runbook", "check", "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    assert '"ok": true' in out


def test_catalog_how_to_edit_present():
    cat = load_catalog()
    assert "sandbox runbook write" in str(cat.get("how_to_edit"))
    assert cat["ops"]["app"] == "sandbox-vllm"


# ── SAND-037 specialist grid runbooks ─────────────────────────────────────


def test_grid_runbooks_cover_every_aligned_cell_once():
    from pathlib import Path

    from mailroom_sandbox.job.specialist_posture import GRID_CELLS

    seen: list[str] = []
    for rid, shape in (("grid-1l4", "1l4"), ("grid-2l4", "2l4")):
        ids = [Path(rel).stem for rel in get_runbook(rid)["configs"]]
        assert all(f"-awq-{shape}" in i for i in ids), ids
        seen += ids
    assert sorted(seen) == sorted(GRID_CELLS)
    assert len(seen) == 20


def test_grid_runbook_configs_share_one_deploy_env():
    from mailroom_sandbox.job.runbooks import deploy_env_drift

    for rid in ("grid-1l4", "grid-2l4"):
        assert deploy_env_drift(get_runbook(rid)) == [], rid


def test_grid_deploy_env_drift_is_detected():
    from mailroom_sandbox.job.runbooks import deploy_env_drift

    wrong = dict(get_runbook("grid-1l4"), serving="grid-awq-2l4")
    errors = deploy_env_drift(wrong)
    assert any("MODAL_VLLM_MAX_CONTAINERS" in e for e in errors)
    assert any("MODAL_VLLM_MIN_CONTAINERS" in e for e in errors)


def test_grid_shapes_differ_only_in_replicas():
    one = env_exports(get_runbook("grid-1l4"))
    two = env_exports(get_runbook("grid-2l4"))
    diff = {k for k in set(one) | set(two) if one.get(k) != two.get(k)}
    assert diff == {"MODAL_VLLM_MAX_CONTAINERS", "MODAL_VLLM_MIN_CONTAINERS"}
    assert one["MODAL_VLLM_QUANTIZATION"] == "awq_marlin"
    assert one["MODAL_VLLM_KV_CACHE_DTYPE"] == "fp8"
    assert one["MODAL_VLLM_MAX_INPUTS"] == "32"
    assert one["MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS"] == '{"enable_thinking": false}'


def test_grid_shell_relocks_1l4_and_leaves_decode_to_posture():
    sh = render_shell("grid-1l4")
    assert 'sandbox run preflight --config "$cfg" --live --force' in sh
    assert "grid-20-merger-specialist-awq-1l4-rerun.yaml" in sh
    assert "SANDBOX_AGENT_KNOBS" not in sh  # decode comes from the posture row at start
    sh2 = render_shell("grid-2l4")
    assert "config/runs/grid-50-contracts-specialist-awq-2l4-rerun.yaml" in sh2
    assert "config/runs/grid-50-contracts-specialist-awq-2l4.yaml" not in sh2


def test_grid_family_renders():
    assert set(list_runbook_ids(family="grid")) == {
        "grid-1l4",
        "grid-2l4",
        "sand39-1l4-n50",
        "sand40-probe",
        "sand40",
    }
    md = render_markdown("grid-1l4")
    assert "## Per-cell posture (live)" in md
    assert "`grid-50-merger-specialist-awq-1l4` | `merger_agreement_specialist` | 8 | 8192" in md
    grid_doc = load_catalog()["generated_docs"]["families"]["grid"]
    assert (generated_dir() / grid_doc).is_file()


def test_grid_runbooks_scrape_and_export_cards():
    for rid, stem in (("grid-1l4", "grid-1l4"), ("grid-2l4", "grid-2l4")):
        sh = render_shell(rid)
        loop = sh[sh.index("do\n"):sh.index("\ndone")]
        order = [
            'sandbox run preflight --config "$cfg"',
            'sandbox run scrape-metrics --config "$cfg" --label before',
            'sandbox run start --config "$cfg"',
            'sandbox run scrape-metrics --config "$cfg" --label after',
            'sandbox run card --config "$cfg"',
        ]
        positions = [loop.index(step) for step in order]
        assert positions == sorted(positions), rid
        assert f"sandbox run card --runbook {stem}" in sh
    # other runbooks keep their two-line loop
    assert "scrape-metrics" not in render_shell("improved-scale-matrix")


# ── SAND-039: 1×L4 · C8 · n=50 inverse leg of the SAND-37 2×L4 scale-out ──────


def test_sand39_runs_the_five_1l4_n50_cells_matched_to_2l4():
    from pathlib import Path

    from mailroom_sandbox.job.runbooks import deploy_env_drift
    from mailroom_sandbox.job.specialist_posture import GRID_CELLS, posture_for_run

    rb = get_runbook("sand39")
    ids = [Path(rel).stem for rel in rb["configs"]]
    assert len(ids) == 5 and all(i.startswith("grid-50-") and i.endswith("-awq-1l4") for i in ids)
    assert set(ids) <= set(Path(r).stem for r in get_runbook("grid-1l4")["configs"])
    assert set(ids) <= GRID_CELLS
    assert {posture_for_run(i)["concurrency"] for i in ids} == {8}
    assert {posture_for_run(i)["replicas"] for i in ids} == {1}
    assert deploy_env_drift(rb) == []


def test_sand40_runs_on_one_32k_deploy_behind_a_merger_chunk_gate():
    from pathlib import Path

    from mailroom_sandbox.job.runbooks import deploy_env_drift
    from mailroom_sandbox.job.specialist_posture import SAND40_CELLS, SAND40_CHECK_CELLS

    rb = get_runbook("sand40")
    assert {Path(rel).stem for rel in rb["configs"]} == SAND40_CELLS
    assert {Path(rb["gate"]["config"]).stem} == SAND40_CHECK_CELLS
    sh = render_shell("sand40")
    assert sh.count("modal deploy deploy/modal_vllm.py") == 1
    assert "MODAL_VLLM_MAX_MODEL_LEN=32768" in sh
    assert "65536" not in sh and "MODAL_VLLM_HF_OVERRIDES=" not in sh
    gate = sh.index("--gate; then")
    assert sh.index("sand40-check-5-merger-specialist-awq-2l4.yaml --job-mode") < gate < sh.index("for cfg in")
    failure = sh[gate:sh.index("fi", gate)]
    assert "./deploy/teardown_vllm.sh" in failure and "exit 1" in failure
    assert sh.index("sand40-50-merger-specialist-awq-2l4.yaml") > sh.index("sand40-100-contracts-specialist-awq-2l4.yaml")
    assert sh.index("sandbox run card --master") > sh.rindex("teardown_vllm.sh")
    assert deploy_env_drift(rb) == []
    assert deploy_env_drift(get_runbook("sand40-probe")) == []
    assert "MODAL_VLLM_MAX_MODEL_LEN=65536" in render_shell("sand40-probe")
    assert "Gate, runs first" in render_markdown("sand40")


def test_sand39_shell_relocks_scrapes_and_writes_master_card():
    sh = render_shell("sand39-1l4-n50")
    assert 'sandbox run preflight --config "$cfg" --live --force' in sh
    assert 'sandbox run card --config "$cfg"' in sh
    assert "sandbox run card --runbook grid-1l4" in sh
    assert "--master" in sh
    assert "grid-20-" not in sh
