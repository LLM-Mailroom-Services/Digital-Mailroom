"""Environment precedence and CLI startup, using synthetic credentials only."""

import os
from types import SimpleNamespace

from mailroom_sandbox import agent_routes, cli, runtime
from mailroom_sandbox.job.spec import AgentRoute


def test_cli_loads_files_before_parser_and_custom_route_validation(monkeypatch, tmp_path):
    root_file = tmp_path / ".env"
    config_file = tmp_path / "config" / ".env"
    config_file.parent.mkdir()
    root_file.write_text("ROOT_ONLY=root\nSHARED=root\nEXPORTED=file\nCUSTOM_ROUTE_KEY=fake-route-key\n")
    config_file.write_text("CONFIG_ONLY=config\nSHARED=config\n")
    env = {"EXPORTED": "shell"}
    monkeypatch.setattr(os, "environ", env)
    monkeypatch.delenv("SANDBOX_SKIP_DOTENV", raising=False)
    monkeypatch.setattr(runtime, "dotenv_files", lambda: [root_file, config_file])
    monkeypatch.setattr(agent_routes, "known_agents", lambda: {"sorter"})
    route = AgentRoute(provider="api", model="example", base_url="https://example.test/v1", api_key_env="CUSTOM_ROUTE_KEY")

    def build_parser():
        assert env == {"EXPORTED": "shell", "ROOT_ONLY": "root", "SHARED": "root",
                       "CUSTOM_ROUTE_KEY": "fake-route-key", "CONFIG_ONLY": "config"}
        agent_routes.validate({"sorter": route}, credentials=True)
        return SimpleNamespace(parse_args=lambda argv: SimpleNamespace(handler=lambda args: 0))

    monkeypatch.setattr(cli, "build_parser", build_parser)
    assert cli.main([]) == 0


def test_missing_env_files_are_optional(monkeypatch):
    monkeypatch.setattr(os, "environ", {})
    monkeypatch.delenv("SANDBOX_SKIP_DOTENV", raising=False)
    monkeypatch.setattr(runtime, "dotenv_files", lambda: [])
    runtime.load_env_file()
    assert not os.environ
