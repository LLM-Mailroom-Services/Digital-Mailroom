"""Central operator runbooks (SAND-031).

Edit ``config/runbooks/catalog.yaml``, then::

    sandbox runbook check
    sandbox runbook write
    sandbox runbook show l4-qwen3-8b

Serving numbers in the catalog are verified against deploy defaults,
``config/models.yaml``, and cited run YAMLs. Per-class concurrency / caps
come from ``specialist_posture``; suite order comes from ``config/runs/suites/``.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import yaml

from mailroom_sandbox.paths import config_dir, repo_root

SCHEMA = "sandbox.runbook/v1"
CATALOG_REL = "config/runbooks/catalog.yaml"
GENERATED_REL = "docs/runbooks"
GENERATED_HEADER = (
    "<!-- Generated from config/runbooks/catalog.yaml. "
    "Edit the catalog, then: sandbox runbook write -->"
)

ENV_FIELDS: tuple[tuple[str, str], ...] = (
    ("model", "MODAL_VLLM_MODEL"),
    ("gpu", "MODAL_VLLM_GPU"),
    ("image_tag", "MODAL_VLLM_IMAGE_TAG"),
    ("max_model_len", "MODAL_VLLM_MAX_MODEL_LEN"),
    ("max_num_seqs", "MODAL_VLLM_MAX_NUM_SEQS"),
    ("gpu_memory_utilization", "MODAL_VLLM_GPU_MEMORY_UTILIZATION"),
    ("enable_prefix_caching", "MODAL_VLLM_ENABLE_PREFIX_CACHING"),
    ("enforce_eager", "MODAL_VLLM_ENFORCE_EAGER"),
    ("max_containers", "MODAL_VLLM_MAX_CONTAINERS"),
    ("min_containers", "MODAL_VLLM_MIN_CONTAINERS"),
    ("scaledown_seconds", "MODAL_VLLM_SCALEDOWN_SECONDS"),
    ("quantization", "MODAL_VLLM_QUANTIZATION"),
    ("tp_size", "MODAL_VLLM_TP_SIZE"),
)

REQUIRED_IDS: tuple[str, ...] = (
    "l4-qwen3-8b",
    "l4-qwen3-8b-track-a",
    "l4-qwen3-8b-track-b",
    "l4-qwen3-8b-n20",
    "improved-awq",
    "improved-awq-c8",
    "improved-correspondence-awq",
    "improved-correspondence-awq-c8",
    "improved-correspondence-fp16-c8",
    "improved-granite-fp8",
    "improved-second-l4",
    "improved-scale-matrix",
)

_DEPLOY_DEFAULT_RE = {
    "model": re.compile(r'MODEL = os\.environ\.get\("MODAL_VLLM_MODEL", "([^"]+)"\)'),
    "gpu": re.compile(r'GPU = os\.environ\.get\("MODAL_VLLM_GPU", "([^"]+)"\)'),
    "max_model_len": re.compile(
        r'MAX_MODEL_LEN = os\.environ\.get\("MODAL_VLLM_MAX_MODEL_LEN", "([^"]+)"\)'
    ),
    "max_num_seqs": re.compile(
        r'MAX_NUM_SEQS = os\.environ\.get\("MODAL_VLLM_MAX_NUM_SEQS", "([^"]+)"\)'
    ),
    "image_tag": re.compile(
        r'VLLM_IMAGE_TAG = os\.environ\.get\("MODAL_VLLM_IMAGE_TAG", "([^"]+)"\)'
    ),
    "scaledown_seconds": re.compile(
        r"SCALEDOWN_SECONDS = int\(os\.environ\.get\(\"MODAL_VLLM_SCALEDOWN_SECONDS\", (\d+)\)\)"
    ),
    "max_containers": re.compile(
        r"MAX_CONTAINERS = int\(os\.environ\.get\(\"MODAL_VLLM_MAX_CONTAINERS\", (\d+)\)\)"
    ),
    "min_containers": re.compile(
        r"MIN_CONTAINERS = int\(os\.environ\.get\(\"MODAL_VLLM_MIN_CONTAINERS\", (\d+)\)\)"
    ),
}


def catalog_path() -> Path:
    return config_dir() / "runbooks" / "catalog.yaml"


def generated_dir() -> Path:
    return repo_root() / GENERATED_REL


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    path = catalog_path()
    if not path.is_file():
        raise FileNotFoundError(f"missing runbook catalog {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError(f"{path}: catalog root must be a mapping")
    schema = str(data.get("schema") or "").strip()
    if schema != SCHEMA:
        raise ValueError(f"{path}: unsupported schema {schema!r} (want {SCHEMA})")
    runbooks = data.get("runbooks")
    if not isinstance(runbooks, Mapping) or not runbooks:
        raise ValueError(f"{path}: runbooks must be a non-empty mapping")
    serving = data.get("serving")
    if not isinstance(serving, Mapping) or not isinstance(serving.get("baseline"), Mapping):
        raise ValueError(f"{path}: serving.baseline is required")
    return dict(data)


def _aliases() -> dict[str, str]:
    raw = load_catalog().get("aliases") or {}
    if not isinstance(raw, Mapping):
        return {}
    return {str(k).lower(): str(v) for k, v in raw.items()}


def list_runbook_ids(*, family: str | None = None) -> list[str]:
    rows = load_catalog()["runbooks"]
    ids = list(rows)
    if family:
        want = family.strip().lower()
        ids = [
            rid
            for rid in ids
            if str((rows[rid] or {}).get("family") or "").lower() == want
        ]
    return ids


def resolve_runbook_id(name: str) -> str:
    raw = (name or "").strip()
    if not raw:
        raise ValueError("runbook id is empty")
    key = raw.lower().replace("_", "-")
    aliases = _aliases()
    rid = aliases.get(key, raw)
    rows = load_catalog()["runbooks"]
    if rid in rows:
        return str(rid)
    if key in rows:
        return key
    known = list_runbook_ids()
    raise KeyError(
        f"unknown runbook {name!r} — known: {known}; aliases: {sorted(aliases)}"
    )


def get_runbook(name: str) -> dict[str, Any]:
    rid = resolve_runbook_id(name)
    row = dict(load_catalog()["runbooks"][rid])
    row["id"] = rid
    return row


def serving_knobs(variant: str | None = None) -> dict[str, Any]:
    """Resolved serving knobs (baseline overlayed with a named variant)."""
    serving = load_catalog()["serving"]
    knobs = dict(serving["baseline"])
    extra: dict[str, str] = {}
    raw_extra = knobs.pop("extra_env", None)
    if isinstance(raw_extra, Mapping):
        extra.update({str(k): str(v) for k, v in raw_extra.items()})
    variant_name = (variant or "baseline").strip() or "baseline"
    if variant_name != "baseline":
        variants = serving.get("variants") or {}
        if variant_name not in variants:
            raise KeyError(
                f"unknown serving variant {variant_name!r} — "
                f"have: baseline, {', '.join(sorted(variants))}"
            )
        overlay = dict(variants[variant_name] or {})
        overlay_extra = overlay.pop("extra_env", None)
        knobs.update(overlay)
        if isinstance(overlay_extra, Mapping):
            extra.update({str(k): str(v) for k, v in overlay_extra.items()})
    knobs["extra_env"] = extra
    knobs["variant"] = variant_name
    return knobs


def _shell_quote(value: str) -> str:
    if value == "":
        return '""'
    if all(c.isalnum() or c in "/._-:+" for c in value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _env_value(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bool):
        return "1" if raw else "0"
    return str(raw)


def env_exports(runbook: Mapping[str, Any]) -> dict[str, str]:
    knobs = serving_knobs(str(runbook.get("serving") or "baseline"))
    out: dict[str, str] = {"SANDBOX_PROFILE": str(load_catalog()["ops"]["profile"])}
    for field, env_key in ENV_FIELDS:
        if field in knobs:
            out[env_key] = _env_value(knobs[field])
    extra = dict(knobs.get("extra_env") or {})
    extra.update(
        {str(k): str(v) for k, v in (runbook.get("extra_env") or {}).items()}
    )
    out.update(extra)
    return out


def env_script(runbook: Mapping[str, Any], *, include_token: bool = True) -> str:
    lines = [
        f"# serving variant: {runbook.get('serving') or 'baseline'}",
        f"# runbook: {runbook.get('id')}",
    ]
    env = env_exports(runbook)
    for key, val in env.items():
        lines.append(f"export {key}={_shell_quote(val)}")
    if include_token:
        lines.append('export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"')
    return "\n".join(lines)


def _ops() -> dict[str, Any]:
    ops = load_catalog().get("ops") or {}
    return dict(ops) if isinstance(ops, Mapping) else {}


def _profile_activate(runbook: Mapping[str, Any]) -> list[str]:
    ops = _ops()
    which = str(runbook.get("modal_profile") or "track-a")
    lines: list[str] = []
    if which == "track-b":
        env = str(ops.get("track_b_profile_env") or "SANDBOX_MODAL_PROFILE_TRACK_B")
        lines.append(f'if [ -z "${{{env}:-}}" ]; then')
        lines.append(f'  echo "error: set {env} to the second Modal profile name" >&2')
        lines.append("  exit 1")
        lines.append("fi")
        lines.append(f'modal profile activate "${{{env}}}"')
        lines.append("modal profile current   # must NOT print hermes-agent-jjb if A uses Hermes")
    else:
        env = str(ops.get("track_a_profile_env") or "SANDBOX_MODAL_PROFILE_TRACK_A")
        default = str(ops.get("track_a_profile_default") or "hermes-agent-jjb")
        lines.append(f'modal profile activate "${{{env}:-{default}}}"')
        lines.append("modal profile current")
    return lines


def _config_paths(runbook: Mapping[str, Any]) -> list[str]:
    raw = runbook.get("configs") or []
    if isinstance(raw, list) and raw:
        return [str(p) for p in raw]
    suite_name = str(runbook.get("suite") or "").strip()
    if not suite_name:
        return []
    from mailroom_sandbox.job.suite import load_suite

    return load_suite(suite_name).config_paths_rel()


def _check_cmd(runbook: Mapping[str, Any]) -> str | None:
    if runbook.get("skip_check"):
        return None
    allow = " --allow-non-hermes" if runbook.get("allow_non_hermes") else ""
    suite_name = str(runbook.get("suite") or "").strip()
    configs = [str(p) for p in (runbook.get("configs") or [])]
    if suite_name:
        return f"sandbox run benchmark-check --suite {suite_name}{allow}"
    if configs:
        return f"sandbox run benchmark-check --config {configs[0]}{allow}"
    return None


def _estimate_cmd(runbook: Mapping[str, Any]) -> str | None:
    suite_name = str(runbook.get("suite") or "").strip()
    if not suite_name:
        return None
    return f"sandbox metrics estimate-suite --suite {suite_name}"


def render_shell(name: str) -> str:
    """Copy-pasteable operator script (no secrets)."""
    runbook = get_runbook(name)
    ops = _ops()
    job_mode = str(ops.get("job_mode") or "endpoint")
    deploy = str(ops.get("deploy") or "modal deploy deploy/modal_vllm.py")
    if str(runbook.get("deploy_strategy") or "") == "recreate":
        deploy = f"{deploy} --strategy recreate"
    prewarm = str(ops.get("prewarm") or "modal run deploy/modal_vllm.py::download_model")
    teardown = str(ops.get("teardown") or "./deploy/teardown_vllm.sh")
    start_force = " --force" if runbook.get("start_force") else ""
    lines: list[str] = [
        f"# {runbook.get('title') or runbook['id']}",
        f"# sandbox runbook show {runbook['id']}",
        "set -euo pipefail",
    ]
    if runbook.get("blocked"):
        reason = str(runbook.get("blocked_reason") or "blocked")
        lines += [
            f'echo "BLOCKED: {reason}" >&2',
            "false   # refuse execution until spend/auth are approved",
        ]

    step_set = {str(s) for s in (runbook.get("steps") or [])}
    for step in runbook.get("steps") or []:
        kind = str(step)
        if kind == "env":
            lines += ["", env_script(runbook)]
        elif kind == "extra_env":
            extra = runbook.get("extra_env") or {}
            if extra:
                lines.append("# runbook extra_env (already in the export block above)")
        elif kind == "activate_profile":
            lines += ["", *_profile_activate(runbook)]
        elif kind == "matrix_hint":
            mid = str(runbook.get("modal_matrix") or "").strip()
            if mid:
                lines += [
                    "",
                    f'# equivalent: eval "$(sandbox modal-matrix env {mid})"',
                ]
        elif kind == "estimate":
            cmd = _estimate_cmd(runbook)
            if cmd:
                lines += ["", cmd]
        elif kind == "check":
            cmd = _check_cmd(runbook)
            if cmd:
                lines += ["", cmd]
        elif kind == "prewarm":
            lines += ["", prewarm]
        elif kind == "deploy":
            lines += ["", deploy]
        elif kind == "cutover":
            lines += [
                "",
                "# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN",
                "sandbox cutover --profile modal-vllm",
            ]
        elif kind == "health":
            lines.append("sandbox health --profile modal-vllm")
        elif kind == "smoke":
            for item in runbook.get("smoke") or []:
                lines.append(f"# smoke: {item}")
        elif kind == "suite":
            suite_name = str(runbook.get("suite") or "").strip()
            if suite_name:
                lines += [
                    "",
                    f"sandbox run suite --suite {suite_name}",
                    f"# sandbox run suite --suite {suite_name} --execute --job-mode {job_mode}",
                ]
            rels = _config_paths(runbook)
            if rels:
                lines.append("for cfg in \\")
                for i, rel in enumerate(rels):
                    cont = " \\" if i < len(rels) - 1 else ""
                    lines.append(f"  {rel}{cont}")
                lines += [
                    "do",
                    '  sandbox run preflight --config "$cfg" --live',
                    f'  sandbox run start --config "$cfg" --job-mode {job_mode} --watch{start_force}',
                    "done",
                ]
        elif kind == "configs":
            rels = _config_paths(runbook)
            if not rels:
                continue
            lines.append("")
            if len(rels) == 1:
                cfg = rels[0]
                lines.append(f'sandbox run preflight --config {cfg} --live')
                lines.append(
                    f"sandbox run start --config {cfg} --job-mode {job_mode} --watch{start_force}"
                )
            else:
                lines.append("for cfg in \\")
                for i, rel in enumerate(rels):
                    cont = " \\" if i < len(rels) - 1 else ""
                    lines.append(f"  {rel}{cont}")
                lines += [
                    "do",
                    '  sandbox run preflight --config "$cfg" --live',
                    f'  sandbox run start --config "$cfg" --job-mode {job_mode} --watch{start_force}',
                    "done",
                ]
        elif kind == "teardown":
            last = "last config in this track" if "suite" in step_set else "this run"
            lines += ["", f"{teardown}   # ONLY after the {last}"]
        elif kind == "after":
            after = runbook.get("after") or []
            if after:
                lines.append("")
                lines.extend(str(cmd) for cmd in after)
    return "\n".join(lines).rstrip() + "\n"


def _note_text(item: Any) -> str:
    if isinstance(item, Mapping):
        return "; ".join(f"{k}: {v}" for k, v in item.items())
    return str(item)


def _posture_table(*, run_prefix: str | None = None) -> str:
    from mailroom_sandbox.job.specialist_posture import summarize_posture

    rows = summarize_posture()
    if run_prefix:
        rows = [row for row in rows if str(row["run_id"]).startswith(run_prefix)]
    lines = [
        "| Run | Task | Conc. | max_tokens | max_input_chars | cost_cap | max_wall |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['run_id']}` | `{row['task']}` | {row['concurrency']} | "
            f"{row['max_tokens']} | {row['max_input_chars']} | "
            f"${row['cost_cap_usd']:.2f} | {row['max_wall_seconds']}s |"
        )
    lines.append("")
    lines.append("Source: `src/mailroom_sandbox/job/specialist_posture.py`.")
    return "\n".join(lines)


def _prompt_table() -> str:
    from mailroom_sandbox.eval_environment_lineage import eval_environment_key_for
    from mailroom_sandbox.job.specialist_posture import SPECIALIST_POSTURE

    lines = [
        "| Run | Agent | Local stem | eval-environment key |",
        "| --- | --- | --- | --- |",
    ]
    seen: set[str] = set()
    for run_id, row in SPECIALIST_POSTURE.items():
        if not str(run_id).startswith("run-30-"):
            continue
        agent = str(row["agent"])
        if agent in seen:
            continue
        seen.add(agent)
        stem = str(row["prompt_file"])
        key = eval_environment_key_for(agent=agent) or "—"
        lines.append(f"| `{run_id}` | `{agent}` | `{stem}` | `{key}` |")
    return "\n".join(lines)


def _pin_table(runbook: Mapping[str, Any]) -> str:
    knobs = serving_knobs(str(runbook.get("serving") or "baseline"))
    rows = [
        ("Model", knobs.get("model")),
        ("GPU", knobs.get("gpu")),
        ("Image", knobs.get("image_tag")),
        ("max_model_len", knobs.get("max_model_len")),
        ("max_num_seqs", knobs.get("max_num_seqs")),
        ("max_containers", knobs.get("max_containers")),
        ("min_containers", knobs.get("min_containers")),
        ("scaledown_seconds", knobs.get("scaledown_seconds")),
        ("quantization", knobs.get("quantization") or "(none)"),
        ("prefix caching / eager", f"{knobs.get('enable_prefix_caching')} / {knobs.get('enforce_eager')}"),
    ]
    lines = ["| Knob | Value |", "| --- | --- |"]
    for label, value in rows:
        lines.append(f"| {label} | `{value}` |")
    return "\n".join(lines)


def render_markdown(name: str) -> str:
    runbook = get_runbook(name)
    ops = _ops()
    family = str(runbook.get("family") or "")
    lines = [
        GENERATED_HEADER,
        "",
        f"# {runbook.get('title') or runbook['id']}",
        "",
        f"**id:** `{runbook['id']}` · **family:** `{family}` · "
        f"**serving:** `{runbook.get('serving') or 'baseline'}`",
        "",
        str(runbook.get("summary") or "").strip(),
        "",
        "Edit [`config/runbooks/catalog.yaml`](../../config/runbooks/catalog.yaml), "
        f"then `sandbox runbook write`. Print this card: `sandbox runbook show {runbook['id']}`.",
        "",
    ]
    if runbook.get("blocked"):
        lines += [
            f"> **BLOCKED:** {runbook.get('blocked_reason')}",
            "",
        ]
    lines += ["## Pins (from catalog serving variant)", "", _pin_table(runbook), ""]
    suite_name = str(runbook.get("suite") or "").strip()
    if suite_name:
        from mailroom_sandbox.job.suite import load_suite

        suite = load_suite(suite_name)
        lines += [
            f"## Suite `{suite.suite_id}` (track={suite.track})",
            "",
            suite.title,
            "",
        ]
        if suite.rationale:
            lines += [suite.rationale.strip(), ""]
        lines.append("Ordered configs:")
        lines.append("")
        for i, rel in enumerate(suite.config_paths_rel(), 1):
            lines.append(f"{i}. `{rel}`")
        lines.append("")
    configs = [str(p) for p in (runbook.get("configs") or [])]
    if configs and not suite_name:
        lines += ["## Configs", ""]
        for rel in configs:
            lines.append(f"- `{rel}`")
        lines.append("")
    if family == "baseline" or str(runbook["id"]).startswith("l4-qwen3-8b"):
        prefix = "run-20-contracts-specialist" if runbook["id"] == "l4-qwen3-8b-n20" else "run-30-"
        lines += ["## Per-doc-type posture (live)", "", _posture_table(run_prefix=prefix), ""]
        lines += ["## Specialist prompts (eval-environment frozen v1)", "", _prompt_table(), ""]
    smoke = runbook.get("smoke") or []
    if smoke:
        lines += ["## Deploy smoke", ""]
        for item in smoke:
            lines.append(f"- {item}")
        lines.append("")
    notes = runbook.get("notes") or []
    if notes:
        lines += ["## Notes", ""]
        for note in notes:
            lines.append(f"- {_note_text(note)}")
        lines.append("")
    never = ops.get("never") or []
    if never:
        lines += ["## Do not", ""]
        for item in never:
            lines.append(f"- {item}")
        lines.append("")
    lines += ["## Operator script", "", "```bash", render_shell(runbook["id"]).rstrip(), "```", ""]
    return "\n".join(lines).rstrip() + "\n"


def render_index() -> str:
    cat = load_catalog()
    lines = [
        GENERATED_HEADER,
        "",
        f"# {cat.get('title') or 'Operator runbooks'}",
        "",
        str(cat.get("how_to_edit") or "").strip(),
        "",
        "```bash",
        "sandbox runbook list",
        "sandbox runbook show l4-qwen3-8b          # singular 1×L4 / 1-container Qwen3-8B",
        "sandbox runbook show l4-qwen3-8b-track-a  # Operator A",
        "sandbox runbook show improved-awq-c8      # improved config",
        "sandbox runbook check                     # catalog vs live pins",
        "sandbox runbook write                     # regenerate this directory",
        "```",
        "",
        "Source of truth: [`config/runbooks/catalog.yaml`](../../config/runbooks/catalog.yaml).",
        "",
    ]
    for family, heading in (("baseline", "Singular L4 / 1-container Qwen3-8B"), ("improved", "Improved run configurations")):
        lines += [f"## {heading}", ""]
        for rid in list_runbook_ids(family=family):
            row = get_runbook(rid)
            blocked = " — **BLOCKED**" if row.get("blocked") else ""
            lines.append(f"- [`{rid}`]({rid}.md) — {row.get('title')}{blocked}")
        lines.append("")
    anti = cat.get("anti_patterns") or []
    if anti:
        lines += [
            "## Anti-patterns",
            "",
            "| Anti-pattern | Cost | Instead |",
            "| --- | --- | --- |",
        ]
        for row in anti:
            if not isinstance(row, Mapping):
                continue
            lines.append(
                f"| {row.get('anti')} | {row.get('cost')} | {row.get('instead')} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_family(family: str) -> str:
    heading = {
        "baseline": "Singular 1×L4 / 1-container Qwen3-8B",
        "improved": "Improved run configurations",
    }.get(family, family)
    chunks = [
        GENERATED_HEADER,
        "",
        f"# {heading}",
        "",
        "Generated family rollup. Canonical per-id cards live beside this file.",
        "",
    ]
    for rid in list_runbook_ids(family=family):
        body = render_markdown(rid)
        # Drop the generated header from nested cards.
        nested = "\n".join(
            line for line in body.splitlines() if line != GENERATED_HEADER
        ).strip()
        chunks += [nested, "", "---", ""]
    return "\n".join(chunks).rstrip() + "\n"


def generated_files() -> dict[str, str]:
    files = {
        "README.md": render_index(),
        "baseline.md": render_family("baseline"),
        "improved.md": render_family("improved"),
    }
    for rid in list_runbook_ids():
        files[f"{rid}.md"] = render_markdown(rid)
    return files


def write_docs(*, dest: Path | None = None) -> list[Path]:
    load_catalog.cache_clear()
    target = dest or generated_dir()
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    wanted = generated_files()
    for name, text in wanted.items():
        path = target / name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    keep = set(wanted)
    for existing in target.glob("*.md"):
        if existing.name not in keep:
            existing.unlink()
    return written


def docs_are_current() -> list[str]:
    errors: list[str] = []
    target = generated_dir()
    wanted = generated_files()
    if not target.is_dir():
        return [f"missing generated runbook dir {target}"]
    on_disk = {p.name for p in target.glob("*.md")}
    extra = sorted(on_disk - set(wanted))
    missing = sorted(set(wanted) - on_disk)
    if extra:
        errors.append(f"stale generated files: {extra} (run sandbox runbook write)")
    if missing:
        errors.append(f"missing generated files: {missing} (run sandbox runbook write)")
    for name, text in wanted.items():
        path = target / name
        if not path.is_file():
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != text:
            errors.append(f"{path.relative_to(repo_root())} is stale — run sandbox runbook write")
    return errors


def _load_run_yaml(rel: str) -> dict[str, Any]:
    path = repo_root() / rel
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError(f"{rel}: not a mapping")
    return dict(data)


def _deploy_defaults() -> dict[str, str]:
    text = (repo_root() / "deploy" / "modal_vllm.py").read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for key, pattern in _DEPLOY_DEFAULT_RE.items():
        match = pattern.search(text)
        if not match:
            raise ValueError(f"deploy/modal_vllm.py: could not parse default for {key}")
        out[key] = match.group(1)
    return out


def verify_live_pins() -> list[str]:
    """Return errors if the catalog drifted from live deploy / YAML / models."""
    load_catalog.cache_clear()
    errors: list[str] = []
    cat = load_catalog()
    for rid in REQUIRED_IDS:
        if rid not in cat["runbooks"]:
            errors.append(f"catalog missing required runbook {rid}")
    baseline = serving_knobs("baseline")
    deploy = _deploy_defaults()
    for key in (
        "model",
        "gpu",
        "max_model_len",
        "max_num_seqs",
        "image_tag",
        "scaledown_seconds",
        "max_containers",
        "min_containers",
    ):
        left = str(baseline.get(key))
        right = str(deploy.get(key))
        if left != right:
            errors.append(
                f"serving.baseline.{key}={left!r} != deploy/modal_vllm.py default {right!r}"
            )

    from mailroom_sandbox.job.specialist_posture import BENCHMARK_MODEL, MAX_MODEL_LEN
    from mailroom_sandbox.modal_matrix import DEFAULT_MODAL_GPU, DEFAULT_MODAL_MODEL, modal_models

    if str(baseline.get("model")) != BENCHMARK_MODEL:
        errors.append(
            f"serving.baseline.model={baseline.get('model')!r} != specialist_posture.BENCHMARK_MODEL={BENCHMARK_MODEL!r}"
        )
    if int(baseline.get("max_model_len")) != int(MAX_MODEL_LEN):
        errors.append("serving.baseline.max_model_len != specialist_posture.MAX_MODEL_LEN")
    if str(baseline.get("model")) != DEFAULT_MODAL_MODEL:
        errors.append("serving.baseline.model != modal_matrix.DEFAULT_MODAL_MODEL")
    if str(baseline.get("gpu")) != DEFAULT_MODAL_GPU:
        errors.append("serving.baseline.gpu != modal_matrix.DEFAULT_MODAL_GPU")

    models = modal_models()
    expected_matrix = {
        "baseline": str(baseline.get("model")),
        "awq-16k": "Qwen/Qwen3-8B-AWQ",
        "awq-32k": "Qwen/Qwen3-8B-AWQ",
        "granite-fp8": "ibm-granite/granite-4.2-8b-fp8",
    }
    for variant, model_id in expected_matrix.items():
        knobs = serving_knobs(variant)
        if str(knobs.get("model")) != model_id:
            errors.append(f"variant {variant} model {knobs.get('model')!r} != {model_id!r}")
        row = models.get(model_id)
        if not row:
            errors.append(f"config/models.yaml missing modal_models row {model_id}")
            continue
        if str(row.get("gpu") or "") != str(knobs.get("gpu")):
            errors.append(
                f"{model_id} gpu {row.get('gpu')!r} != catalog {knobs.get('gpu')!r}"
            )
        if int(row.get("max_model_len") or 0) != int(knobs.get("max_model_len") or 0) and variant != "awq-16k":
            # awq-16k is the older contracts YAML window; matrix default is 32768.
            errors.append(
                f"{model_id} max_model_len {row.get('max_model_len')!r} != catalog variant {variant} {knobs.get('max_model_len')!r}"
            )

    from mailroom_sandbox.job.suite import load_suite

    for rid in list_runbook_ids():
        runbook = get_runbook(rid)
        suite_name = str(runbook.get("suite") or "").strip()
        if suite_name:
            try:
                suite = load_suite(suite_name)
            except (FileNotFoundError, ValueError) as exc:
                errors.append(f"{rid}: suite {suite_name!r}: {exc}")
                continue
            if not suite.configs:
                errors.append(f"{rid}: suite {suite_name} has no configs")
        for rel in runbook.get("configs") or []:
            path = repo_root() / str(rel)
            if not path.is_file():
                errors.append(f"{rid}: missing config {rel}")
        if not runbook.get("assert_engine"):
            continue
        rels = list(runbook.get("configs") or [])
        if not rels and suite_name:
            rels = load_suite(suite_name).config_paths_rel()
        if not rels:
            errors.append(f"{rid}: assert_engine set but no configs")
            continue
        knobs = serving_knobs(str(runbook.get("serving") or "baseline"))
        spec = _load_run_yaml(str(rels[0]))
        engine = spec.get("engine") or {}
        modal = engine.get("modal") or {}
        vllm = engine.get("vllm") or {}
        if str(engine.get("model")) != str(knobs.get("model")):
            errors.append(
                f"{rid}: {rels[0]} engine.model={engine.get('model')!r} "
                f"!= serving {knobs.get('model')!r}"
            )
        if str(modal.get("gpu")) != str(knobs.get("gpu")):
            errors.append(f"{rid}: {rels[0]} modal.gpu != {knobs.get('gpu')}")
        if int(modal.get("max_containers") or 0) != int(knobs.get("max_containers") or 0):
            errors.append(
                f"{rid}: {rels[0]} max_containers={modal.get('max_containers')!r} "
                f"!= {knobs.get('max_containers')}"
            )
        if int(vllm.get("max_model_len") or 0) != int(knobs.get("max_model_len") or 0):
            errors.append(
                f"{rid}: {rels[0]} max_model_len={vllm.get('max_model_len')!r} "
                f"!= {knobs.get('max_model_len')}"
            )
        catalog_q = str(knobs.get("quantization") or "")
        yaml_q = str(vllm.get("quantization") or "")
        if catalog_q != yaml_q:
            errors.append(
                f"{rid}: {rels[0]} quantization={yaml_q!r} != serving {catalog_q!r}"
            )
    return errors
