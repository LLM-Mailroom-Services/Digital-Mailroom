"""Overlay merge, model map, and profile loading (network-free)."""

from __future__ import annotations

from mailroom_sandbox.overlay import (
    build_merged_taxonomy,
    deep_merge,
    list_profiles,
    load_profile,
    map_model,
    rewrite_agents,
    serving_family,
)
from mailroom_sandbox.providers import MAILROOM_PROVIDER_KEYS, endpoints_for, load_endpoints


def test_deep_merge_nested():
    base = {"a": 1, "b": {"x": 1, "y": 2}}
    overlay = {"b": {"y": 9}, "c": 3}
    assert deep_merge(base, overlay) == {"a": 1, "b": {"x": 1, "y": 9}, "c": 3}


def test_profiles_exist():
    names = list_profiles()
    for required in ("ollama", "vllm-local", "vllm-remote", "modal-vllm", "llamacpp", "lmstudio", "openrouter"):
        assert required in names


def test_ollama_profile_is_local_first():
    profile = load_profile("ollama")
    assert profile["provider"] == "ollama"
    assert profile["default_model"] == "qwen3:8b"
    assert not profile.get("requires_api_key")
    assert profile["provider"] in MAILROOM_PROVIDER_KEYS


def test_openrouter_is_opt_in():
    profile = load_profile("openrouter")
    assert profile.get("requires_api_key") is True
    assert profile["provider"] == "openrouter"


def test_map_qwen_flash_to_ollama():
    assert map_model("qwen/qwen3.7-flash", "ollama") == "qwen3:8b"
    assert map_model("deepseek/deepseek-v4-flash", "ollama") == "deepseek-r1:8b"
    assert map_model("qwen/qwen3.7-flash", "vllm") == "Qwen/Qwen3-8B"


def test_rewrite_agents_uses_local_tags():
    profile = load_profile("ollama")
    taxonomy = build_merged_taxonomy(profile)
    agents = taxonomy["agents"]
    assert agents["sorter"]["provider"] == "ollama"
    assert agents["sorter"]["model"] == "qwen3:8b"
    assert agents["judge"]["provider"] == "ollama"
    assert "/" not in agents["sorter"]["model"] or agents["sorter"]["model"].startswith("qwen")


def test_model_override():
    profile = load_profile("ollama")
    taxonomy = build_merged_taxonomy(profile, model_override="llama3.1:8b")
    assert taxonomy["agents"]["sorter"]["model"] == "llama3.1:8b"
    assert taxonomy["agents"]["contracts_specialist"]["model"] == "llama3.1:8b"


def test_agent_model_surgical_override():
    from mailroom_sandbox.overlay import parse_agent_models

    profile = load_profile("ollama")
    taxonomy = build_merged_taxonomy(
        profile, agent_models=parse_agent_models(["judge=qwen3:14b", "sorter=llama3.1:8b"])
    )
    assert taxonomy["agents"]["sorter"]["model"] == "llama3.1:8b"
    assert taxonomy["agents"]["judge"]["model"] == "qwen3:14b"
    assert taxonomy["agents"]["contracts_specialist"]["model"] == "qwen3:8b"
    assert taxonomy["agents"]["sorter"]["temperature"] == 0.1


def test_parse_agent_models_rejects_bare_name():
    from mailroom_sandbox.overlay import parse_agent_models

    try:
        parse_agent_models(["sorter"])
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_serving_family():
    assert serving_family(load_profile("vllm-local")) == "vllm"
    assert serving_family(load_profile("modal-vllm")) == "vllm"
    assert serving_family(load_profile("llamacpp")) == "llamacpp"


def test_endpoints_urls():
    ep = load_endpoints("ollama")
    assert ep.base_url == "http://localhost:11434/v1"
    assert ep.models_url.endswith("/models")
    assert ep.chat_url.endswith("/chat/completions")
    assert "/v1/v1" not in ep.models_url

    vllm = endpoints_for(load_profile("vllm-local"))
    assert vllm.base_url == "http://localhost:8000/v1"

    llama = load_endpoints("llamacpp")
    assert llama.mailroom_provider == "generic"
    assert ":8080" in llama.base_url

    lm = load_endpoints("lmstudio")
    assert ":1234" in lm.base_url


def test_live_extract_classes_map_one_to_one_specialists():
    """sandbox#9: merger_agreement has its own specialist, not contracts."""
    taxonomy = build_merged_taxonomy(load_profile("ollama"))
    expected = {
        "contract": "contracts_specialist",
        "merger_agreement": "merger_agreement_specialist",
        "corporate_record": "corporate_records_specialist",
        "correspondence": "correspondence_specialist",
        "insurance_claim": "insurance_claims_specialist",
    }
    classes = {row["key"]: row["specialist"] for row in taxonomy["doc_classes"]}
    for key, specialist in expected.items():
        assert classes[key] == specialist, key
    assert "merger_agreement_specialist" in taxonomy["agents"]
    assert taxonomy["agents"]["merger_agreement_specialist"]["model"] == "qwen3:8b"


def test_taxonomy_yaml_agent_keys_are_unique():
    """PyYAML last-key-wins; a merge leftover duplicate would silently
    regress DMR-078 L4 budgets (8192/100k over 4096/36008)."""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for rel in (
        "config/mailroom.taxonomy.base.yaml",
        "config/taxonomy.overlay.yaml",
    ):
        text = (root / rel).read_text(encoding="utf-8")
        in_agents = False
        seen: dict[str, int] = {}
        for i, line in enumerate(text.splitlines(), 1):
            if re.match(r"^agents:\s*$", line):
                in_agents = True
                seen = {}
                continue
            if not in_agents:
                continue
            if line and not line[0].isspace():
                in_agents = False
                continue
            match = re.match(r"^  ([A-Za-z0-9_]+):\s*$", line)
            if match:
                key = match.group(1)
                assert key not in seen, (
                    f"duplicate agents.{key} in {rel}:{seen[key]} and {i}"
                )
                seen[key] = i
        assert "merger_agreement_specialist" in seen, rel


def test_modal_profile_merge_sorter_vllm_and_timeout_600():
    """DMR-072/078: the modal-vllm profile rewrite must point the sorter at the
    vLLM endpoint AND the merged run_limits must carry the 600s per-call
    timeout (the vendored 120s default cannot hold an L4 generation)."""
    from mailroom_sandbox.overlay import build_merged_taxonomy, load_profile

    t = build_merged_taxonomy(load_profile("modal-vllm"))
    assert t["agents"]["sorter"]["provider"] == "vllm"
    assert t["agents"]["sorter"]["model"] == "Qwen/Qwen3-8B"
    assert t["run_limits"]["llm_call_timeout_seconds"] == 600
    # DMR-078: specialist budgets fit Qwen L4 16k
    assert t["agents"]["contracts_specialist"]["max_tokens"] == 4096
    assert t["agents"]["merger_agreement_specialist"]["max_tokens"] == 4096
    assert t["agents"]["correspondence_specialist"]["max_tokens"] == 2048
