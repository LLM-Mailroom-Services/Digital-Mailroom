"""Two-operator (and full) specialist suite manifests (DMR-077).

Suite YAMLs under ``config/runs/suites/`` list ordered run configs plus Modal
profile env hints. Operators warm one ``sandbox-vllm`` app per track, chain
their configs without teardown between runs, then tear down after the last.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from mailroom_sandbox.paths import config_dir, repo_root

SUITE_SCHEMA = "sandbox.suite/v1"
SUITES_DIR_REL = "config/runs/suites"

# Short aliases for CLI: ``sandbox run suite --suite track-a``.
SUITE_ALIASES: dict[str, str] = {
    "track-a": "run-30-specialists-track-a",
    "a": "run-30-specialists-track-a",
    "track-b": "run-30-specialists-track-b",
    "b": "run-30-specialists-track-b",
    "full": "run-30-specialists-full",
    "all": "run-30-specialists-full",
    "run-30-specialists": "run-30-specialists-full",
    "run-30-specialists-full": "run-30-specialists-full",
    "run-30-specialists-track-a": "run-30-specialists-track-a",
    "run-30-specialists-track-b": "run-30-specialists-track-b",
}

# Env vars (names only — never commit token values).
MODAL_PROFILE_ENV_TRACK_A = "SANDBOX_MODAL_PROFILE_TRACK_A"
MODAL_PROFILE_ENV_TRACK_B = "SANDBOX_MODAL_PROFILE_TRACK_B"
DEFAULT_TRACK_A_PROFILE = "hermes-agent-jjb"


@dataclass(frozen=True)
class SuiteSpec:
    """Ordered specialist run track for one operator / one warm Modal app."""

    suite_id: str
    track: str
    title: str
    configs: tuple[Path, ...]
    scaledown_seconds: int = 120
    warm_once: bool = True
    modal_profile_env: str = ""
    modal_profile_default: str = ""
    rationale: str = ""
    source: Path | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def resolve_modal_profile(self) -> str | None:
        """Active profile name from env, then suite default; None if unset."""
        if self.modal_profile_env:
            raw = (os.environ.get(self.modal_profile_env) or "").strip()
            if raw:
                return raw
        default = (self.modal_profile_default or "").strip()
        return default or None

    def config_paths_rel(self) -> list[str]:
        root = repo_root()
        out: list[str] = []
        for p in self.configs:
            try:
                out.append(str(p.resolve().relative_to(root)))
            except ValueError:
                out.append(str(p))
        return out


def suites_dir() -> Path:
    return config_dir() / "runs" / "suites"


def list_suite_ids() -> list[str]:
    """Suite ids from YAML stems under ``config/runs/suites/``."""
    d = suites_dir()
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.yaml") if p.is_file())


def resolve_suite_path(name_or_path: str | Path) -> Path:
    """Resolve alias, suite id, or filesystem path to a suite YAML."""
    raw = str(name_or_path).strip()
    if not raw:
        raise ValueError("suite name/path is empty")
    path = Path(raw)
    if path.is_file():
        return path.resolve()
    # Relative to repo root
    cand = repo_root() / raw
    if cand.is_file():
        return cand.resolve()
    key = raw.lower().replace("_", "-")
    suite_id = SUITE_ALIASES.get(key, raw)
    # Strip .yaml if caller passed stem-like with extension
    if suite_id.endswith(".yaml"):
        suite_id = Path(suite_id).stem
    suite_path = suites_dir() / f"{suite_id}.yaml"
    if suite_path.is_file():
        return suite_path.resolve()
    known = list_suite_ids()
    raise FileNotFoundError(
        f"unknown suite {raw!r} — known ids: {known}; "
        f"aliases: {sorted(set(SUITE_ALIASES))}"
    )


def load_suite(name_or_path: str | Path) -> SuiteSpec:
    """Load and validate a ``sandbox.suite/v1`` manifest."""
    path = resolve_suite_path(name_or_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError(f"{path}: suite root must be a mapping")
    schema = str(data.get("schema") or "").strip()
    if schema and schema != SUITE_SCHEMA:
        raise ValueError(f"{path}: unsupported schema {schema!r} (want {SUITE_SCHEMA})")
    suite_id = str(data.get("suite_id") or path.stem).strip()
    track = str(data.get("track") or "").strip() or "unknown"
    title = str(data.get("title") or suite_id).strip()
    rationale = str(data.get("rationale") or "").strip()
    scaledown = int(data.get("scaledown_seconds") or 120)
    warm_once = bool(data.get("warm_once", True))
    modal_env = str(data.get("modal_profile_env") or "").strip()
    modal_default = str(data.get("modal_profile_default") or "").strip()
    raw_configs = data.get("configs")
    if not isinstance(raw_configs, list) or not raw_configs:
        raise ValueError(f"{path}: configs must be a non-empty list of run YAML paths")
    root = repo_root()
    configs: list[Path] = []
    for item in raw_configs:
        rel = str(item).strip()
        if not rel:
            raise ValueError(f"{path}: empty config path in configs")
        cfg = Path(rel)
        if not cfg.is_file():
            cfg = root / rel
        if not cfg.is_file():
            raise FileNotFoundError(f"{path}: missing run config {rel!r}")
        configs.append(cfg.resolve())
    known_keys = {
        "schema",
        "suite_id",
        "track",
        "title",
        "rationale",
        "scaledown_seconds",
        "warm_once",
        "modal_profile_env",
        "modal_profile_default",
        "configs",
    }
    extra = {k: v for k, v in data.items() if k not in known_keys}
    return SuiteSpec(
        suite_id=suite_id,
        track=track,
        title=title,
        configs=tuple(configs),
        scaledown_seconds=scaledown,
        warm_once=warm_once,
        modal_profile_env=modal_env,
        modal_profile_default=modal_default,
        rationale=rationale,
        source=path,
        extra=extra,
    )


def suite_shell_loop(suite: SuiteSpec, *, job_mode: str = "endpoint") -> str:
    """Emit a bash snippet: preflight+start each config, no teardown."""
    lines = [
        f"# Suite {suite.suite_id} ({suite.track}) — warm once, teardown after last",
        f"# scaledown={suite.scaledown_seconds}  warm_once={suite.warm_once}",
    ]
    profile = suite.resolve_modal_profile()
    if suite.modal_profile_env:
        lines.append(
            f"# Modal profile: ${{{suite.modal_profile_env}}}"
            + (f" or default {suite.modal_profile_default!r}" if suite.modal_profile_default else " (required)")
        )
    if profile:
        lines.append(f"modal profile activate {profile}")
        lines.append("modal profile current")
    lines.append("for cfg in \\")
    rels = suite.config_paths_rel()
    for i, rel in enumerate(rels):
        cont = " \\" if i < len(rels) - 1 else ""
        lines.append(f"  {rel}{cont}")
    lines.append("do")
    lines.append('  sandbox run preflight --config "$cfg" --live')
    lines.append(
        f'  sandbox run start --config "$cfg" --job-mode {job_mode} --watch'
    )
    lines.append("done")
    lines.append("./deploy/teardown_vllm.sh   # ONLY after the last config in this track")
    return "\n".join(lines)


def suite_runbook_md(suite: SuiteSpec) -> str:
    """Human-readable operator card for one track."""
    profile = suite.resolve_modal_profile()
    env_hint = suite.modal_profile_env or "(none)"
    lines = [
        f"## Suite `{suite.suite_id}` (track={suite.track})",
        "",
        suite.title,
        "",
    ]
    if suite.rationale:
        lines += ["### Why this split", "", suite.rationale, ""]
    lines += [
        "### Posture",
        "",
        f"- Warm once: `{suite.warm_once}` — one `sandbox-vllm` app for this track",
        f"- Scaledown: `{suite.scaledown_seconds}` s (attended; restore 600 unattended)",
        f"- Modal profile env: `{env_hint}`",
        f"- Resolved profile: `{profile or 'UNSET — set env or modal_profile_default'}`",
        "- Never share one Modal token / profile across operators",
        "",
        "### Ordered configs",
        "",
    ]
    for i, rel in enumerate(suite.config_paths_rel(), 1):
        lines.append(f"{i}. `{rel}`")
    lines += ["", "### Shell loop", "", "```bash", suite_shell_loop(suite), "```"]
    return "\n".join(lines)
