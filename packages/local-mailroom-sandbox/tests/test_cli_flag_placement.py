"""`--profile/--model/--prompt/--agent-model` work before OR after the subcommand.

The shared flags used to be attached to the root parser and to every leaf with a real
default, so `sandbox --profile ollama health` was silently overwritten by the leaf's
default (`modal-vllm`), and the `tunnel` and `run` leaves rejected the flags outright.
"""

from __future__ import annotations

import pytest

from mailroom_sandbox.cli import build_parser

# (argv without the shared flag, the flag/value to inject, attribute that must carry it)
COMMANDS = [
    ["health"],
    ["eval", "sorter"],
    ["profiles"],
    ["cutover"],
    ["tunnel", "plan"],
    ["tunnel", "status"],
    ["tunnel", "up"],
    ["run", "status", "--run-id", "x"],
    ["run", "preflight", "--config", "x.yaml"],
    ["run", "start", "--config", "x.yaml"],
    ["metrics", "compare", "--runs", "a,b"],
]


def _placements(command: list[str], flag: list[str]) -> list[list[str]]:
    """Every position a flag can reasonably take: before the group, between group and leaf, after the leaf."""
    out = [flag + command, command + flag]
    if len(command) > 1:
        out.append([command[0]] + flag + command[1:])
    return out


@pytest.fixture(autouse=True)
def _no_ambient_profile(monkeypatch):
    monkeypatch.setattr("mailroom_sandbox.paths.dotenv_files", lambda: [])
    monkeypatch.delenv("SANDBOX_PROFILE", raising=False)


@pytest.mark.parametrize("command", COMMANDS, ids=lambda c: " ".join(c))
def test_profile_flag_is_honoured_in_every_placement(command):
    parser = build_parser()
    for argv in _placements(command, ["--profile", "ollama"]):
        assert parser.parse_args(argv).profile == "ollama", argv


@pytest.mark.parametrize("command", COMMANDS, ids=lambda c: " ".join(c))
def test_profile_defaults_to_modal_vllm_when_absent(command):
    assert build_parser().parse_args(command).profile == "modal-vllm"


def test_env_profile_is_the_default_for_every_placement(monkeypatch):
    monkeypatch.setenv("SANDBOX_PROFILE", "vllm-local")
    parser = build_parser()
    assert parser.parse_args(["tunnel", "status"]).profile == "vllm-local"
    assert parser.parse_args(["run", "status", "--run-id", "x"]).profile == "vllm-local"
    assert parser.parse_args(["--profile", "ollama", "tunnel", "status"]).profile == "ollama"


@pytest.mark.parametrize("flag", [["--model", "Qwen/Qwen3-8B"], ["--prompt", "sorter_local_v0"]])
def test_model_and_prompt_flags_survive_a_leading_position(flag):
    parser = build_parser()
    attr = flag[0].lstrip("-")
    for argv in _placements(["eval", "sorter"], flag):
        assert getattr(parser.parse_args(argv), attr) == flag[1], argv


def test_agent_model_flag_survives_a_leading_position():
    parser = build_parser()
    for argv in _placements(["eval", "sorter"], ["--agent-model", "sorter=qwen3:8b"]):
        assert parser.parse_args(argv).agent_models == ["sorter=qwen3:8b"], argv


def test_a_flag_after_the_subcommand_overrides_one_before_it():
    args = build_parser().parse_args(["--profile", "ollama", "health", "--profile", "vllm-local"])
    assert args.profile == "vllm-local"
