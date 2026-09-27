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
    assert "granite_thinking_parser" in md
    assert "Deploy smoke" in md
    script = render_shell("improved-granite-fp8")
    assert "benchmark-check" not in script
    env = env_exports(get_runbook("improved-granite-fp8"))
    assert env["MODAL_VLLM_REASONING_PARSER"] == "granite_thinking_parser"
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
    errors = docs_are_current()
    assert errors == [], errors
    dest = generated_dir()
    assert (dest / "l4-qwen3-8b.md").is_file()
    assert (dest / "improved.md").is_file()
    text = (dest / "l4-qwen3-8b.md").read_text(encoding="utf-8")
    assert "Qwen/Qwen3-8B" in text
    assert "max_containers" in text
    improved = (dest / "improved.md").read_text(encoding="utf-8")
    assert "Qwen/Qwen3-8B-AWQ" in improved
    assert "ibm-granite/granite-4.2-8b-fp8" in improved


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
