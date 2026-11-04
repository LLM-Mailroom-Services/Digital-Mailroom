"""Fake external CLIs (`modal`, `vllm`, `hf`, `ssh`, `docker`, `ollama`) for network-free tests.

Each shim is a tiny executable that appends ``{"tool": ..., "argv": [...]}`` to a JSONL
log and answers from a JSON rule file, so a test can change a tool's behaviour between
calls. The shims run under the current interpreter (absolute shebang), so the fixture
can set ``PATH`` to the shim directory *only*: a tool the test did not install is truly
missing, and a real ``hf``/``docker`` on the host can never be reached by accident.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

_ENV_KEYS = ("HF_HOME", "HF_TOKEN", "VLLM_API_KEY", "MODAL_VLLM_MODEL", "MODAL_VLLM_GPU", "MODAL_VLLM_QUANTIZATION", "MODAL_VLLM_TP_SIZE")

_SHIM = """#!{python}
import hashlib, json, os, sys, time
name = {name!r}
cfg = json.loads(open({cfg!r}, encoding="utf-8").read())
argv = sys.argv[1:]
with open({log!r}, "a", encoding="utf-8") as fh:
    env = {{k: os.environ[k] for k in {env_keys!r} if k in os.environ}}
    for key in ("HF_TOKEN", "VLLM_API_KEY"):
        if key in env:
            env[key] = "sha256:" + hashlib.sha256(env[key].encode()).hexdigest()
    fh.write(json.dumps({{"tool": name, "argv": argv, "env": env}}) + "\\n")
rule = cfg.get("default", {{}})
for candidate in cfg.get("rules", []):
    prefix = candidate["prefix"]
    if argv[: len(prefix)] == prefix:
        rule = candidate
        break
if rule.get("seq"):
    seen = 0
    for line in open({log!r}, encoding="utf-8"):
        row = json.loads(line)
        if row["tool"] == name and row["argv"][: len(rule["prefix"])] == rule["prefix"]:
            seen += 1
    rule = {{**rule, **rule["seq"][min(seen, len(rule["seq"])) - 1]}}
if rule.get("sleep"):
    time.sleep(rule["sleep"])
sys.stdout.write(rule.get("stdout", ""))
sys.stderr.write(rule.get("stderr", ""))
sys.exit(int(rule.get("rc", 0)))
"""


class FakeBin:
    """A directory of fake CLIs plus the log of every call made to them."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.log = root / "calls.jsonl"
        self.log.touch()

    def add(
        self,
        name: str,
        *,
        stdout: str = "",
        stderr: str = "",
        rc: int = 0,
        sleep: float = 0.0,
        rules: list[dict[str, Any]] | None = None,
    ) -> Path:
        """Install (or reconfigure) a fake ``name``.

        ``rules`` are matched in order on the argv prefix, e.g.
        ``{"prefix": ["app", "list"], "stdout": "[]"}``; a rule may carry ``"seq": [{...}, {...}]``
        to answer successive matching calls differently (the last entry repeats); the top-level keyword
        arguments are the default answer for anything no rule matches.
        """
        cfg = self.root / f"{name}.json"
        cfg.write_text(
            json.dumps(
                {"default": {"stdout": stdout, "stderr": stderr, "rc": rc, "sleep": sleep}, "rules": rules or []}
            ),
            encoding="utf-8",
        )
        path = self.root / name
        path.write_text(
            _SHIM.format(python=sys.executable, name=name, cfg=str(cfg), log=str(self.log), env_keys=_ENV_KEYS),
            encoding="utf-8",
        )
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return path

    def calls(self, tool: str | None = None) -> list[list[str]]:
        """The argv (without the tool name) of every recorded call, optionally for one tool."""
        rows = [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines() if line.strip()]
        return [row["argv"] for row in rows if tool is None or row["tool"] == tool]

    def envs(self, tool: str | None = None) -> list[dict[str, str]]:
        """The sandbox-relevant environment (``HF_HOME``, ``MODAL_VLLM_*`` …) each call saw."""
        rows = [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines() if line.strip()]
        return [row.get("env", {}) for row in rows if tool is None or row["tool"] == tool]

    def isolate_path(self, monkeypatch) -> None:
        """Make the shim directory the entire ``PATH``."""
        monkeypatch.setenv("PATH", os.fspath(self.root))
