"""Resolve what `sandbox watch` / `sandbox web` should follow.

One positional TARGET replaces the old `--config` / `--follow` bookkeeping:

* nothing           -> the SAND-032 current run if one is published, else the
                       most recently active run, re-evaluated every frame so a
                       newly started run is picked up live;
* a run ID          -> ``data/runtime/runs/<id>``;
* a run directory   -> that directory;
* a run YAML        -> its run (``run_id`` from the spec; a spec without one
                       follows its newest auto-named run);
* a run name        -> ``config/runs/<name>.yaml``;
* an experiment     -> ``experiment.yaml`` or its folder: follows the
                       campaign's current-run marker with the campaign panel.

Resolvers never probe a provider. They may write the experiment marker that
``sandbox experiment watch`` already writes; run discovery may create the runs
root; and watching an explicit ``run_id`` from a run YAML before it starts
creates its empty run directory (as ``RunStore`` always has). A bare run ID or
run directory that does not exist is never created.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from mailroom_sandbox.job import spec as spec_mod
from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.services._exec import ServiceError

DEFAULT_APP = "sandbox-vllm"
_ACTIVITY_FILES = ("events.jsonl", "items.jsonl", "nodes.jsonl", "checkpoint.json", "spec.lock.json")


class WaitingForRun(ServiceError):
    """No run to show yet; the web watcher keeps polling instead of exiting."""


@dataclass
class WatchTarget:
    resolve: Callable[[], tuple[RunStore, str]]
    describe: str
    campaign: Callable[[str], Path | None] = field(default=lambda _rid: None)
    follow: Path | None = None  # marker file, when following one


def _activity(directory: Path) -> float:
    stamps = [directory.stat().st_mtime]
    for name in _ACTIVITY_FILES:
        try:
            stamps.append((directory / name).stat().st_mtime)
        except OSError:
            pass
    return max(stamps)


def run_dirs(root: Path | None = None, *, prefix: str = "") -> list[Path]:
    """Run directories under ``root``, most recently active first."""
    root = root or spec_mod.runs_root()
    if not root.is_dir():
        return []
    found = []
    for child in root.iterdir():
        if not child.is_dir() or not child.name.startswith(prefix) or child.name.startswith("."):
            continue
        if not any((child / name).is_file() for name in _ACTIVITY_FILES):
            continue
        try:
            found.append((_activity(child), child.name, child))
        except OSError:  # removed between listing and stat
            continue
    return [path for _, _, path in sorted(found, reverse=True)]


def latest_run(root: Path | None = None, *, prefix: str = "") -> Path | None:
    dirs = run_dirs(root, prefix=prefix)
    return dirs[0] if dirs else None


def store_and_app(directory: Path, app: str | None = None) -> tuple[RunStore, str]:
    """Open an existing run directory; the Modal app comes from its lock."""
    if not directory.is_dir():
        raise WaitingForRun(f"run {directory.name} has not started yet ({directory} does not exist)")
    store = RunStore(directory)
    try:
        lock = store.read_lock() if store.lock_path.is_file() else {}
    except Exception:  # noqa: BLE001 — a torn/invalid lock must not kill the watcher
        lock = {}
    lock = lock if isinstance(lock, dict) else {}
    modal = (lock.get("engine") or {}).get("modal") if isinstance(lock.get("engine"), dict) else None
    return store, app or ((modal or {}).get("app") if isinstance(modal, dict) else None) or DEFAULT_APP


def _spec_store(cfg: Path, app: str | None) -> tuple[RunStore, str]:
    spec = spec_mod.load_run_spec(cfg)
    app = app or (spec.engine.modal.app if spec.engine.modal else None)
    if spec.run_id:
        # An explicit run may be watched before it starts: the store (and its
        # directory) is created empty and fills in as the run writes to it.
        directory = spec_mod.run_dir(spec_mod.resolve_run_id(spec))
        if not directory.is_dir():
            return RunStore(directory), app or DEFAULT_APP
        return store_and_app(directory, app)
    # resolve_run_id() would mint a fresh timestamp on every frame; follow the
    # newest run this exact spec auto-named instead. The name only encodes task
    # and model, so a candidate must also carry this spec's locked spec_hash.
    prefix = f"{spec_mod._slug(spec.task)}-{spec_mod._slug(spec.engine.model.split('/')[-1])}-"
    want = spec.spec_hash()
    for directory in run_dirs(prefix=prefix):
        if _locked_hash(directory) == want:
            return store_and_app(directory, app)
    raise WaitingForRun(f"{cfg} has no run_id and no run of this spec ({prefix}*, spec_hash {want[:12]}) has started yet")


def _locked_hash(directory: Path) -> str | None:
    try:
        import json

        lock = json.loads((directory / "spec.lock.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return lock.get("spec_hash") if isinstance(lock, dict) else None


def _experiment_dirs() -> list[Path]:
    from mailroom_sandbox.paths import repo_root

    root = repo_root() / "config" / "experiments"
    return sorted(p.parent for p in root.glob("*/experiment.yaml")) if root.is_dir() else []


def campaign_for_run(run_id: str, _cache: dict[str, Path | None] | None = None) -> Path | None:
    """experiment.yaml whose plan contains ``run_id`` (cached per run ID)."""
    from mailroom_sandbox.experiments import _load

    if _cache is not None and run_id in _cache:
        return _cache[run_id]
    hit = None
    for folder in _experiment_dirs():
        try:
            _, _, runs = _load(folder / "experiment.yaml")
        except Exception:  # noqa: BLE001 — one malformed study must not hide the rest
            continue
        if any(spec.run_id == run_id for _, spec in runs):
            hit = folder / "experiment.yaml"
            break
    if _cache is not None:
        _cache[run_id] = hit
    return hit


def experiment_marker(path: Path) -> Path:
    """The campaign's current-run marker, seeded with its first run (as `experiment watch` does)."""
    from mailroom_sandbox.experiments import _atomic_write, _load

    path, _plan, runs = _load(path)
    marker = path.parent / "current-run"
    if not marker.is_file():
        if not runs:
            raise ServiceError(f"{path} lists no runs")
        _atomic_write(marker, runs[0][1].run_id + "\n")
    return marker


def _follow(marker: Path, app: str | None, fallback: str | None = None) -> tuple[RunStore, str]:
    try:
        value = marker.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise WaitingForRun(f"follow marker {marker} is unreadable: {exc}") from exc
    value = value or (fallback or "")
    if not value:
        raise ServiceError("watch follow marker is empty and no --config fallback was provided")
    if Path(value).is_file():
        return _spec_store(Path(value), app)
    try:
        directory = spec_mod.run_dir(value)
    except ValueError as exc:
        raise ServiceError(f"follow marker must contain an existing run YAML or valid run ID: {exc}") from exc
    return store_and_app(directory, app)


def _is_experiment(path: Path) -> bool:
    if path.is_dir():
        return (path / "experiment.yaml").is_file()
    if path.name == "experiment.yaml":
        return True
    try:
        head = path.read_text(encoding="utf-8")[:4096]
    except OSError:
        return False
    return "sandbox.experiment/v1" in head


def _suggest() -> str:
    recent = [p.name for p in run_dirs()[:5]]
    return ("recent runs: " + ", ".join(recent)) if recent else "no runs under data/runtime/runs yet"


def resolve_target(
    target: str | None = None,
    *,
    config: str | None = None,
    follow: str | None = None,
    app: str | None = None,
    sand032_current: Path | None = None,
) -> WatchTarget:
    """Turn the CLI's TARGET / --config / --follow into a live resolver."""
    from mailroom_sandbox.paths import repo_root

    cache: dict[str, Path | None] = {}
    auto_campaign = lambda rid: campaign_for_run(rid, cache)  # noqa: E731

    if follow:
        marker = Path(follow)
        beside = marker.resolve().parent / "experiment.yaml"
        return WatchTarget(lambda: _follow(marker, app, config), f"following {marker}",
                           (lambda _rid: beside) if beside.is_file() else auto_campaign, marker)
    if target is None and config:
        target = config
    if target is None:
        if sand032_current is not None and sand032_current.is_file():
            return WatchTarget(lambda: _follow(sand032_current, app), f"following the SAND-032 current run ({sand032_current})",
                               auto_campaign, sand032_current)

        def newest() -> tuple[RunStore, str]:
            directory = latest_run()
            if directory is None:
                raise WaitingForRun("waiting for a run: none under data/runtime/runs yet "
                                    "(start one, or try `sandbox web --demo`)")
            return store_and_app(directory, app)

        return WatchTarget(newest, "the most recently active run (switches when a newer run starts)", auto_campaign)

    path = Path(target).expanduser()
    if not path.exists() and not path.suffix:
        for candidate in (repo_root() / "config" / "runs" / f"{target}.yaml",
                          repo_root() / "config" / "experiments" / target):
            if candidate.exists():
                path = candidate
                break
    if path.exists():
        if _is_experiment(path):
            yaml_path = path / "experiment.yaml" if path.is_dir() else path
            marker = experiment_marker(yaml_path)
            return WatchTarget(lambda: _follow(marker, app), f"experiment {yaml_path.parent.name} (current run)",
                               lambda _rid: yaml_path, marker)
        if path.is_dir():
            directory = path.resolve()
            return WatchTarget(lambda: store_and_app(directory, app), f"run {directory.name}", auto_campaign)
        if path.suffix in {".yaml", ".yml"}:
            try:
                spec_mod.load_run_spec(path)  # fail fast on a malformed spec
            except (TypeError, ValueError, OSError, yaml.YAMLError) as exc:  # pydantic errors are ValueErrors
                raise ServiceError(f"{path}: not a valid run YAML: {exc}") from exc
            return WatchTarget(lambda: _spec_store(path, app), f"run spec {path}", auto_campaign)
        raise ServiceError(f"{target}: not a run YAML, experiment or run directory")
    try:
        directory = spec_mod.run_dir(target)
    except ValueError as exc:
        raise ServiceError(f"{target!r} is not a run ID, run YAML, run name or experiment; {_suggest()}") from exc
    if not directory.is_dir():
        raise ServiceError(f"no run {target!r} under {directory.parent}; {_suggest()}")
    return WatchTarget(lambda: store_and_app(directory, app), f"run {target}", auto_campaign)

