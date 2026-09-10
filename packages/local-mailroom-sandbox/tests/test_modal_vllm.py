"""Modal deploy app contract tests — network-free, `modal` SDK stubbed.

The real `modal` package is a deploy-time extra, never installed in the
runtime venv (same rule as llm-mailroom's
`src/tests/test_vllm_modal_capability.py`). These tests pin the deploy
surface: app/volume scoping, the vLLM argv builder (v0.28.0 flags), the
bearer-env mapping, the cost guards, the SDK-1.5.5 secret API
(``from_local`` was removed), and local compose <-> Modal argv parity.
"""

from __future__ import annotations

import importlib.util
import re
import sys
import types
from pathlib import Path

import pytest

from mailroom_sandbox.paths import repo_root

DEPLOY_APP = repo_root() / "deploy" / "modal_vllm.py"
COMPOSE = repo_root() / "deploy" / "docker-compose.yml"
PYPROJECT = repo_root() / "pyproject.toml"

KNOB_ENV = (
    "MODAL_VLLM_MODEL",
    "MODAL_VLLM_GPU",
    "MODAL_VLLM_QUANTIZATION",
    "MODAL_VLLM_MAX_MODEL_LEN",
    "MODAL_VLLM_GPU_MEMORY_UTILIZATION",
    "MODAL_VLLM_MAX_NUM_SEQS",
    "MODAL_VLLM_TP_SIZE",
    "MODAL_VLLM_IMAGE_TAG",
    "MODAL_VLLM_REVISION",
    "MODAL_VLLM_API_TOKEN",
    "MODAL_VLLM_SCALEDOWN_SECONDS",
    "MODAL_VLLM_MAX_CONTAINERS",
    "MODAL_VLLM_MIN_CONTAINERS",
    "MODAL_VLLM_STARTUP_TIMEOUT_SECONDS",
    "HF_TOKEN",
)


def _install_modal_stub() -> None:
    """Minimal stand-in for the `modal` surface used by the app (SDK 1.5.5)."""
    if "modal" in sys.modules:
        return
    stub = types.ModuleType("modal")

    class _Secret:
        calls: list[dict] = []

        @staticmethod
        def from_dict(env):
            _Secret.calls.append(dict(env))
            return ("secret", dict(env))

        # Deliberately no from_local: removed in SDK 1.5.x (regression guard).

    class _Volume:
        @staticmethod
        def from_name(name, create_if_missing=False):
            return ("volume", name)

    class _Image:
        def __init__(self, ref=None):
            self.ref = ref
            self.commands: list = []
            self.envs: dict = {}

        @staticmethod
        def from_registry(ref, add_python=None):
            img = _Image(ref)
            img.add_python = add_python
            return img

        @staticmethod
        def debian_slim(python_version=None):
            img = _Image("debian_slim")
            img.python_version = python_version
            return img

        def run_commands(self, *cmds):
            self.commands.extend(cmds)
            return self

        def uv_pip_install(self, *packages):
            self.commands.extend(packages)
            return self

        def env(self, mapping):
            self.envs.update(mapping)
            return self

    class _FunctionRecord:
        def __init__(self, fn, kwargs):
            self.fn = fn
            self.kwargs = kwargs
            self.web_server_kwargs = getattr(fn, "web_server_kwargs", None)

    class _App:
        def __init__(self, name, image=None, tags=None):
            self.name = name
            self.image = image
            self.tags = tags or {}

        def function(self, **kwargs):
            def deco(fn):
                return _FunctionRecord(fn, kwargs)

            return deco

        def local_entrypoint(self, fn=None):
            if fn is not None:
                return fn

            def deco(f):
                return f

            return deco

    def _web_server(port=None, *, startup_timeout=None, **kwargs):
        def deco(fn):
            fn.web_server_kwargs = {"port": port, "startup_timeout": startup_timeout}
            return fn

        return deco

    stub.Secret = _Secret
    stub.Volume = _Volume
    stub.Image = _Image
    stub.App = _App
    stub.web_server = _web_server
    sys.modules["modal"] = stub


def _load_app_module():
    _install_modal_stub()
    spec = importlib.util.spec_from_file_location("sandbox_modal_vllm", DEPLOY_APP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _clear_deploy_knobs(monkeypatch):
    """Deploy knobs come from the local env at import time — normalize them."""
    for name in KNOB_ENV:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def modal_stub():
    _install_modal_stub()
    stub = sys.modules["modal"]
    stub.Secret.calls = []
    return stub


class TestDeploySurface:
    def test_app_file_exists(self):
        assert DEPLOY_APP.is_file(), "deploy/modal_vllm.py missing"

    def test_sandbox_scoped_constants(self):
        mod = _load_app_module()
        assert mod.APP_NAME == "sandbox-vllm"
        assert mod.HF_CACHE_VOLUME_NAME == "sandbox-hf-cache"
        assert mod.VLLM_CACHE_VOLUME_NAME == "sandbox-vllm-cache"
        assert mod.SERVER_PORT == 8000

    def test_defaults_are_pinned_and_cost_guarded(self):
        mod = _load_app_module()
        assert mod.MODEL == "Qwen/Qwen3-8B"
        assert mod.GPU == "L4"
        assert mod.VLLM_IMAGE_TAG == "v0.28.0"  # never `latest`
        assert mod.MAX_MODEL_LEN == "32768"
        assert mod.GPU_MEMORY_UTILIZATION == "0.90"  # below vLLM's 0.92 default
        assert mod.MAX_NUM_SEQS == "256"  # vLLM's own L4/OpenAI-server default
        assert mod.SCALEDOWN_SECONDS == 15 * 60
        assert mod.MAX_CONTAINERS == 1  # a test sandbox must not fan out GPUs
        assert mod.MIN_CONTAINERS == 0  # scale-to-zero
        assert mod.STARTUP_TIMEOUT_SECONDS == 20 * 60

    def test_serve_function_config(self):
        mod = _load_app_module()
        kwargs = mod.serve.kwargs
        assert kwargs["gpu"] == "L4"
        assert kwargs["volumes"] == {
            "/root/.cache/huggingface": ("volume", "sandbox-hf-cache"),
            "/root/.cache/vllm": ("volume", "sandbox-vllm-cache"),
        }
        assert kwargs["max_containers"] == 1
        assert kwargs["min_containers"] == 0
        assert kwargs["scaledown_window"] == 15 * 60
        assert kwargs["startup_timeout"] == 20 * 60
        assert kwargs["timeout"] == 30 * 60
        assert mod.serve.web_server_kwargs == {
            "port": 8000,
            "startup_timeout": 20 * 60,
        }

    def test_app_tags_for_cost_allocation(self):
        mod = _load_app_module()
        assert mod.app.name == "sandbox-vllm"
        assert mod.app.tags["package"] == "local-mailroom-sandbox"
        assert mod.app.tags["purpose"] == "remote-gpu-testing"

    def test_image_pins_and_transfer_env(self):
        mod = _load_app_module()
        assert mod.image.ref == "vllm/vllm-openai:v0.28.0"
        assert mod.image.add_python == "3.12"
        assert mod.image.envs["HF_HUB_ENABLE_HF_TRANSFER"] == "1"
        assert mod.image.envs["HF_XET_HIGH_PERFORMANCE"] == "1"

    def test_download_model_prewarm_surface(self):
        mod = _load_app_module()
        kwargs = mod.download_model.kwargs
        assert kwargs["image"] is mod.download_image
        assert kwargs["volumes"] == {
            "/root/.cache/huggingface": ("volume", "sandbox-hf-cache")
        }
        assert mod.download_image.python_version == "3.12"


class TestCommandBuilder:
    def test_command_defaults(self):
        mod = _load_app_module()
        cmd = mod.build_vllm_command("Qwen/Qwen3-8B")
        assert cmd[:3] == ["vllm", "serve", "Qwen/Qwen3-8B"]
        assert "--host" in cmd and cmd[cmd.index("--host") + 1] == "0.0.0.0"
        assert "--port" in cmd and cmd[cmd.index("--port") + 1] == "8000"
        assert "--max-model-len" in cmd
        # Safe test-sandbox memory posture (v0.28.0 flags).
        assert cmd[cmd.index("--gpu-memory-utilization") + 1] == "0.90"
        assert cmd[cmd.index("--max-num-seqs") + 1] == "256"
        # fp16/bf16 default: no quantization or revision flag unless configured.
        assert "--quantization" not in cmd
        assert "--revision" not in cmd
        # v0.28.0 renamed the log flag (opt-in `--enable-log-requests`); the
        # explicit negation keeps request logging off, and the pre-0.28 flag
        # would make the server reject its own argv.
        assert "--no-enable-log-requests" in cmd
        assert "--disable-log-requests" not in cmd

    def test_memory_knobs_read_env_at_import(self, monkeypatch):
        monkeypatch.setenv("MODAL_VLLM_GPU_MEMORY_UTILIZATION", "0.85")
        monkeypatch.setenv("MODAL_VLLM_MAX_NUM_SEQS", "64")
        mod = _load_app_module()
        cmd = mod.build_vllm_command("Qwen/Qwen3-8B")
        assert cmd[cmd.index("--gpu-memory-utilization") + 1] == "0.85"
        assert cmd[cmd.index("--max-num-seqs") + 1] == "64"

    def test_quantization_flag_injected_when_configured(self):
        mod = _load_app_module()
        original = mod.QUANTIZATION
        try:
            mod.QUANTIZATION = "awq"
            cmd = mod.build_vllm_command("Qwen/Qwen3-14B")
            assert cmd[cmd.index("--quantization") + 1] == "awq"
        finally:
            mod.QUANTIZATION = original

    def test_revision_flag_injected_when_configured(self):
        mod = _load_app_module()
        original = mod.REVISION
        try:
            mod.REVISION = "abc123"
            cmd = mod.build_vllm_command("Qwen/Qwen3-8B")
            assert cmd[cmd.index("--revision") + 1] == "abc123"
        finally:
            mod.REVISION = original

    def test_tensor_parallel_defaults_to_1_single_gpu(self):
        """DMR-045: no TP flag on a single-GPU deploy (the default)."""
        mod = _load_app_module()
        cmd = mod.build_vllm_command("Qwen/Qwen3-8B")
        assert "--tensor-parallel-size" not in cmd
        assert mod.TP_SIZE == "1"

    def test_tensor_parallel_from_gpu_suffix(self, monkeypatch):
        """DMR-045: MODAL_VLLM_GPU='A100-80GB:2' must derive TP_SIZE=2."""
        monkeypatch.setenv("MODAL_VLLM_GPU", "A100-80GB:2")
        mod = _load_app_module()
        assert mod.TP_SIZE == "2"
        cmd = mod.build_vllm_command("meta-llama/Llama-3.3-70B-Instruct")
        assert cmd[cmd.index("--tensor-parallel-size") + 1] == "2"

    def test_tensor_parallel_explicit_override(self, monkeypatch):
        """DMR-045: explicit MODAL_VLLM_TP_SIZE beats the GPU-suffix default."""
        monkeypatch.setenv("MODAL_VLLM_GPU", "A100-80GB:2")
        monkeypatch.setenv("MODAL_VLLM_TP_SIZE", "1")
        mod = _load_app_module()
        assert mod.TP_SIZE == "1"
        cmd = mod.build_vllm_command("Qwen/Qwen3-32B")
        assert "--tensor-parallel-size" not in cmd

    def test_tensor_parallel_knob_travels_through_secret(self, modal_stub, monkeypatch):
        """DMR-045: TP_SIZE must reach the container via the deploy Secret."""
        monkeypatch.setenv("MODAL_VLLM_TP_SIZE", "2")
        monkeypatch.setenv("MODAL_VLLM_GPU", "A100-80GB:2")
        mod = _load_app_module()
        assert len(modal_stub.Secret.calls) == 2
        for call in modal_stub.Secret.calls:
            assert call["MODAL_VLLM_TP_SIZE"] == "2"
        assert "MODAL_VLLM_TP_SIZE" in mod.CONFIG_ENV_KEYS


class TestServerEnv:
    def test_api_token_maps_to_vllm_enforcement_var(self, monkeypatch):
        mod = _load_app_module()
        monkeypatch.setenv("MODAL_VLLM_API_TOKEN", "tok-abc123")
        assert mod._server_env()["VLLM_API_KEY"] == "tok-abc123"

    def test_no_token_means_keyless_server(self, monkeypatch):
        mod = _load_app_module()
        monkeypatch.delenv("MODAL_VLLM_API_TOKEN", raising=False)
        assert "VLLM_API_KEY" not in mod._server_env()

    def test_hf_token_passthrough_for_gated_repos(self, monkeypatch):
        mod = _load_app_module()
        monkeypatch.setenv("HF_TOKEN", "hf_xxx")
        assert mod._server_env()["HF_TOKEN"] == "hf_xxx"
        monkeypatch.delenv("HF_TOKEN")
        assert "HF_TOKEN" not in mod._server_env()


class TestSecretApi:
    """SDK 1.5.5 removed ``Secret.from_local``; optional knobs must survive."""

    def test_optional_knobs_use_from_dict_and_skip_missing(self, modal_stub, monkeypatch):
        monkeypatch.setenv("MODAL_VLLM_MODEL", "Qwen/Qwen3-14B")
        monkeypatch.setenv("HF_TOKEN", "hf_test")
        mod = _load_app_module()
        # One call per decorated function (serve + download_model).
        assert len(modal_stub.Secret.calls) == 2
        for call in modal_stub.Secret.calls:
            assert call == {"MODAL_VLLM_MODEL": "Qwen/Qwen3-14B", "HF_TOKEN": "hf_test"}
        assert len(mod.serve.kwargs["secrets"]) == 1

    def test_no_knobs_means_no_secret(self, modal_stub):
        mod = _load_app_module()
        assert modal_stub.Secret.calls == []
        assert mod.serve.kwargs["secrets"] == []

    def test_removed_from_local_api_is_not_used(self):
        text = DEPLOY_APP.read_text(encoding="utf-8")
        assert not re.search(r"\.from_local\s*\(", text), (
            "Secret.from_local was removed in Modal SDK 1.5.x — "
            "use from_dict / from_local_environ"
        )
        assert "Secret.from_dict" in text

    def test_engine_knobs_travel_through_secret(self, modal_stub, monkeypatch):
        """The container re-imports the module; argv knobs need the Secret."""
        monkeypatch.setenv("MODAL_VLLM_REVISION", "abc123")
        monkeypatch.setenv("MODAL_VLLM_GPU_MEMORY_UTILIZATION", "0.85")
        monkeypatch.setenv("MODAL_VLLM_MAX_NUM_SEQS", "64")
        mod = _load_app_module()
        assert len(modal_stub.Secret.calls) == 2
        for call in modal_stub.Secret.calls:
            assert call["MODAL_VLLM_REVISION"] == "abc123"
            assert call["MODAL_VLLM_GPU_MEMORY_UTILIZATION"] == "0.85"
            assert call["MODAL_VLLM_MAX_NUM_SEQS"] == "64"
        for name in (
            "MODAL_VLLM_REVISION",
            "MODAL_VLLM_GPU_MEMORY_UTILIZATION",
            "MODAL_VLLM_MAX_NUM_SEQS",
        ):
            assert name in mod.CONFIG_ENV_KEYS


class TestComposeParity:
    """Local compose and Modal must speak the same vLLM v0.28.0 argv."""

    @staticmethod
    def _vllm_service() -> dict:
        import yaml

        data = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
        return data["services"]["vllm"]

    def test_same_pinned_image(self):
        mod = _load_app_module()
        assert self._vllm_service()["image"] == mod.image.ref == "vllm/vllm-openai:v0.28.0"

    def test_command_parity(self):
        cmd = self._vllm_service()["command"]
        assert cmd[0] == "${VLLM_MODEL:-Qwen/Qwen3-8B}"
        assert cmd[cmd.index("--host") + 1] == "0.0.0.0"
        assert cmd[cmd.index("--port") + 1] == "8000"
        assert cmd[cmd.index("--max-model-len") + 1] == "${VLLM_MAX_MODEL_LEN:-32768}"
        assert (
            cmd[cmd.index("--gpu-memory-utilization") + 1]
            == "${VLLM_GPU_MEMORY_UTILIZATION:-0.90}"
        )
        assert cmd[cmd.index("--max-num-seqs") + 1] == "${VLLM_MAX_NUM_SEQS:-256}"
        assert cmd[-1] == "--no-enable-log-requests"

    def test_defaults_match_modal_constants(self):
        mod = _load_app_module()
        cmd = self._vllm_service()["command"]
        assert f"${{VLLM_MAX_MODEL_LEN:-{mod.MAX_MODEL_LEN}}}" in cmd
        assert f"${{VLLM_GPU_MEMORY_UTILIZATION:-{mod.GPU_MEMORY_UTILIZATION}}}" in cmd
        assert f"${{VLLM_MAX_NUM_SEQS:-{mod.MAX_NUM_SEQS}}}" in cmd

    def test_bearer_and_hf_env_contract(self):
        env = self._vllm_service()["environment"]
        assert env["VLLM_API_KEY"] == "${VLLM_API_KEY:-}"
        assert env["HF_TOKEN"] == "${HF_TOKEN:-}"

    def test_removed_log_flag_absent(self):
        # Comments may document the rename; the argv must never carry it.
        assert "--disable-log-requests" not in self._vllm_service()["command"]
        mod = _load_app_module()
        assert "--disable-log-requests" not in mod.build_vllm_command("Qwen/Qwen3-8B")


class TestVersionPins:
    def test_deploy_extra_pins_modal_sdk(self):
        import tomllib

        data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        deploy = data["project"]["optional-dependencies"]["deploy"]
        assert "modal==1.5.5" in deploy, "deploy extra must pin the verified SDK"
        core = data["project"]["dependencies"]
        assert all("modal" not in dep for dep in core), (
            "modal must stay a deploy-time extra (runtime venv stays clean)"
        )

    def test_app_file_records_sdk_version(self):
        text = DEPLOY_APP.read_text(encoding="utf-8")
        assert "1.5.5" in text
        assert "v0.28.0" in text
