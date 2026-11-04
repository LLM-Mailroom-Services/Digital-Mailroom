"""Env template defaults to the Modal vLLM path; cloud keys stay opt-in."""

from mailroom_sandbox.paths import config_dir


def test_env_example_defaults_to_modal_vllm():
    text = (config_dir() / ".env.example").read_text(encoding="utf-8")
    assert "SANDBOX_PROFILE=modal-vllm" in text
    assert "DEFAULT_PROVIDER=vllm" in text
    assert "OBSERVABILITY_PROVIDER=langfuse" in text
    assert "LANGFUSE_INIT_ORG_ID=" in text
    assert "MAILROOM_TRACE_NAMES=document-pipeline" in text
    # The Modal endpoint only exists after `modal deploy`: a live localhost
    # default here would shadow the exported one and probe the wrong server.
    assert "\nVLLM_BASE_URL=http" not in text
    assert "# VLLM_BASE_URL=https://<workspace>--sandbox-vllm-serve.modal.run/v1" in text


def test_env_example_has_no_live_openrouter_key():
    text = (config_dir() / ".env.example").read_text(encoding="utf-8")
    # Cloud key is commented, not a placeholder that would authenticate.
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("OPENROUTER_API_KEY="):
            raise AssertionError("OPENROUTER_API_KEY must stay commented in the example")
