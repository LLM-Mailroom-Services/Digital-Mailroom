"""Loud reproducibility checks for Modal L4 Qwen specialist benchmarks.

Fails closed when the Modal account / GPU posture / pins look wrong so a
cold-start tomorrow morning does not burn credits on a misconfigured deploy.
No secrets are printed — only profile names and path presence.

Spend posture (DMR-076/077): scaledown 120 attended, one warm app per track
(or all five for single-operator full), local specialist prompt pins, limit 30.
AWQ is optional only. Two-operator tracks use separate Modal accounts.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

from mailroom_sandbox.job.spec import (
    FAMILY_CORPUS_SIZE,
    FAMILY_HF_REVISION,
    HF_DEFAULT_REPO,
    RunSpec,
)
from mailroom_sandbox.modernbert import feeder_status

# Hermes Agent Gmail workspace profile (more credits). Never commit tokens —
# only the profile *name* belongs in docs / this check.
HERMES_MODAL_PROFILE = "hermes-agent-jjb"

# Default cost-eval suite (bf16). AWQ is accepted as an optional path when the
# engine model is explicitly Qwen/Qwen3-8B-AWQ (DMR-068 gate still operator-owned).
BENCHMARK_MODEL_BF16 = "Qwen/Qwen3-8B"
BENCHMARK_MODEL_AWQ = "Qwen/Qwen3-8B-AWQ"
BENCHMARK_ALLOWED_MODELS = frozenset({BENCHMARK_MODEL_BF16, BENCHMARK_MODEL_AWQ})

BENCHMARK_EXPECTED = {
    "model": BENCHMARK_MODEL_BF16,
    "gpu": "L4",
    "image_tag": "v0.29.0",
    "max_containers": 1,
    "min_containers": 0,
    "scaledown_seconds": 120,  # attended cost-saver (DMR-076); restore 600 unattended
    "concurrency": 4,
    "profile": "modal-vllm",
    "app": "sandbox-vllm",
    "revision": FAMILY_HF_REVISION,
    "repo": HF_DEFAULT_REPO,
    "limit": 30,
}

# DMR-074 / DMR-078: run-30 specialist YAMLs must pin local production prompt
# stems AND match specialist_posture concurrency / cost caps.
from mailroom_sandbox.job.specialist_posture import (
    SPECIALIST_POSTURE,
    expected_concurrency,
    posture_for_run,
)

SPECIALIST_LOCAL_PROMPTS: dict[str, dict[str, str]] = {
    run_id: {row["agent"]: row["prompt_file"]}
    for run_id, row in SPECIALIST_POSTURE.items()
}


def _read_modal_toml() -> str | None:
    path = Path.home() / ".modal.toml"
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def active_modal_profile_name() -> str | None:
    """Parse ``~/.modal.toml`` for the section with ``active = true``.

    Does not return or log token values.
    """
    text = _read_modal_toml()
    if not text:
        return None
    # Prefer CLI when available (fast-fail if hung — we only use toml parse).
    current: str | None = None
    active: str | None = None
    for line in text.splitlines():
        m = re.match(r"^\[([^\]]+)\]\s*$", line)
        if m:
            current = m.group(1).strip()
            continue
        if current and re.match(r"^active\s*=\s*true\b", line.strip(), re.I):
            active = current
    return active


def _modal_cli_ok() -> dict[str, Any]:
    if not shutil.which("modal"):
        return {"ok": False, "reason": "modal CLI not on PATH — pip install -e '.[deploy]'"}
    try:
        proc = subprocess.run(
            ["modal", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "reason": f"modal --version failed: {exc}"}
    if proc.returncode != 0:
        return {"ok": False, "reason": f"modal --version rc={proc.returncode}"}
    return {"ok": True, "version": (proc.stdout or proc.stderr or "").strip()}


def check_benchmark_posture(
    *,
    spec: RunSpec | None = None,
    require_hermes: bool = True,
    require_modernbert: bool = False,
    expected_modal_profile: str | None = None,
) -> dict[str, Any]:
    """Inventory Ready / Missing / Blocked for L4 Qwen specialist runs.

    ``ok`` is True only when there are zero ``errors`` (warnings allowed).

    ``expected_modal_profile`` (DMR-077): when set, the active Modal profile
    must match that name (Track B second account, or an explicit override).
    When unset and ``require_hermes``, Hermes ``hermes-agent-jjb`` is required.
    """
    errors: list[str] = []
    warnings: list[str] = []
    expected_profile = (expected_modal_profile or "").strip() or None
    checks: dict[str, Any] = {
        "expected": dict(BENCHMARK_EXPECTED),
        "family_corpus_size": FAMILY_CORPUS_SIZE,
        "hermes_profile_name": HERMES_MODAL_PROFILE,
        "expected_modal_profile": expected_profile,
        "spend_posture": {
            "warm_app_once": True,
            "teardown_only_after_last_in_track": True,
            "teardown_only_after_fifth": True,  # full-suite synonym
            "scaledown_seconds_attended": BENCHMARK_EXPECTED["scaledown_seconds"],
            "scaledown_seconds_unattended": 600,
            "awq_default": False,
        },
    }

    cli = _modal_cli_ok()
    checks["modal_cli"] = cli
    if not cli.get("ok"):
        errors.append(str(cli.get("reason")))

    profile = active_modal_profile_name()
    checks["active_modal_profile"] = profile
    if profile is None:
        hint = expected_profile or HERMES_MODAL_PROFILE
        errors.append(
            "~/.modal.toml missing or has no active profile — run "
            f"`modal profile activate {hint}` "
            "(never commit tokens; ~/.modal.toml stays local)"
        )
    elif expected_profile is not None:
        if profile != expected_profile:
            errors.append(
                f"active Modal profile is {profile!r}, expected "
                f"{expected_profile!r} for this suite/track — "
                f"`modal profile activate {expected_profile}` "
                "(do not share one Modal token across operators)"
            )
    elif require_hermes and profile != HERMES_MODAL_PROFILE:
        errors.append(
            f"active Modal profile is {profile!r}, expected Hermes "
            f"{HERMES_MODAL_PROFILE!r} — "
            f"`modal profile activate {HERMES_MODAL_PROFILE}` "
            "(do not commit tokens; ~/.modal.toml stays local)"
        )

    # Env posture (names only).
    env_bits = {
        "SANDBOX_PROFILE": os.environ.get("SANDBOX_PROFILE"),
        "MODAL_VLLM_MODEL": os.environ.get("MODAL_VLLM_MODEL"),
        "MODAL_VLLM_GPU": os.environ.get("MODAL_VLLM_GPU"),
        "MODAL_VLLM_IMAGE_TAG": os.environ.get("MODAL_VLLM_IMAGE_TAG"),
        "MODAL_VLLM_MAX_CONTAINERS": os.environ.get("MODAL_VLLM_MAX_CONTAINERS"),
        "MODAL_VLLM_MIN_CONTAINERS": os.environ.get("MODAL_VLLM_MIN_CONTAINERS"),
        "MODAL_VLLM_SCALEDOWN_SECONDS": os.environ.get("MODAL_VLLM_SCALEDOWN_SECONDS"),
        "VLLM_BASE_URL_set": bool((os.environ.get("VLLM_BASE_URL") or "").strip()),
        "VLLM_API_KEY_set": bool((os.environ.get("VLLM_API_KEY") or "").strip()),
        "HF_TOKEN_set": bool((os.environ.get("HF_TOKEN") or "").strip()),
        "MODAL_TOKEN_ID_set": bool((os.environ.get("MODAL_TOKEN_ID") or "").strip()),
    }
    checks["env"] = env_bits
    if env_bits.get("MODAL_VLLM_GPU") and env_bits["MODAL_VLLM_GPU"] != "L4":
        warnings.append(
            f"MODAL_VLLM_GPU={env_bits['MODAL_VLLM_GPU']!r} — specialist suite pins L4"
        )
    env_model = env_bits.get("MODAL_VLLM_MODEL")
    if env_model and env_model not in BENCHMARK_ALLOWED_MODELS:
        warnings.append(
            f"MODAL_VLLM_MODEL={env_model!r} — "
            f"expected {BENCHMARK_MODEL_BF16} (or optional {BENCHMARK_MODEL_AWQ})"
        )
    elif env_model == BENCHMARK_MODEL_AWQ:
        warnings.append(
            "MODAL_VLLM_MODEL is AWQ — optional cost-saver path; "
            "DMR-068 accuracy gate (≥98%) is operator-owned before defaulting"
        )
    sd_env = env_bits.get("MODAL_VLLM_SCALEDOWN_SECONDS")
    if sd_env:
        try:
            sd_val = int(sd_env)
        except ValueError:
            warnings.append(
                f"MODAL_VLLM_SCALEDOWN_SECONDS={sd_env!r} is not an int"
            )
        else:
            if sd_val != BENCHMARK_EXPECTED["scaledown_seconds"]:
                warnings.append(
                    f"MODAL_VLLM_SCALEDOWN_SECONDS={sd_val} "
                    f"(suite attended pin {BENCHMARK_EXPECTED['scaledown_seconds']}; "
                    "restore 600 for unattended/overnight)"
                )
    max_c = env_bits.get("MODAL_VLLM_MAX_CONTAINERS")
    if max_c and max_c != str(BENCHMARK_EXPECTED["max_containers"]):
        warnings.append(
            f"MODAL_VLLM_MAX_CONTAINERS={max_c!r} — specialist suite pins "
            f"{BENCHMARK_EXPECTED['max_containers']}"
        )

    if spec is not None:
        spec_errs = _check_spec_pins(spec)
        errors.extend(spec_errs["errors"])
        warnings.extend(spec_errs["warnings"])
        checks["spec"] = {
            "run_id": spec.run_id,
            "task": spec.task,
            "profile": spec.profile,
            "model": spec.engine.model,
            "gpu": spec.engine.modal.gpu if spec.engine.modal else None,
            "image_tag": spec.engine.modal.image_tag if spec.engine.modal else None,
            "scaledown_seconds": (
                spec.engine.modal.scaledown_seconds if spec.engine.modal else None
            ),
            "max_containers": (
                spec.engine.modal.max_containers if spec.engine.modal else None
            ),
            "min_containers": (
                spec.engine.modal.min_containers if spec.engine.modal else None
            ),
            "concurrency": spec.job.concurrency,
            "revision": spec.effective_revision(),
            "sample_seed": spec.dataset.sample_seed,
            "limit": spec.dataset.limit,
            "local_prompts": _prompt_agent_map(spec),
        }

    mb = feeder_status()
    checks["modernbert"] = {
        "ok": mb.get("ok"),
        "mailroom_ml_src": mb.get("mailroom_ml_src"),
        "modernbert_model_path": mb.get("modernbert_model_path"),
    }
    if require_modernbert and not mb.get("ok"):
        errors.append(
            "ModernBERT feeder incomplete — set MAILROOM_ML_SRC + "
            "MODERNBERT_MODEL_PATH (see sandbox modernbert status)"
        )
    elif not mb.get("ok"):
        warnings.append(
            "ModernBERT feeder not resolved (optional for specialist extract "
            "suite; required for sorter_vs_modernbert live)"
        )

    ok = len(errors) == 0
    return {
        "ok": ok,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
        "markdown": _format_md(ok, errors, warnings, checks),
    }


def _prompt_agent_map(spec: RunSpec) -> dict[str, str]:
    agents = spec.prompt.get("agents") if isinstance(spec.prompt, dict) else None
    if not isinstance(agents, dict):
        return {}
    out: dict[str, str] = {}
    for name, ref in agents.items():
        if not isinstance(ref, dict):
            continue
        if ref.get("source") == "local" and ref.get("file"):
            out[str(name)] = str(ref["file"])
    return out


def _check_spec_pins(spec: RunSpec) -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    exp = BENCHMARK_EXPECTED
    if spec.profile != exp["profile"]:
        errors.append(f"spec.profile={spec.profile!r} expected {exp['profile']!r}")

    model = spec.engine.model
    if model not in BENCHMARK_ALLOWED_MODELS:
        errors.append(
            f"spec.engine.model={model!r} expected {BENCHMARK_MODEL_BF16!r} "
            f"(or optional {BENCHMARK_MODEL_AWQ!r})"
        )
    elif model == BENCHMARK_MODEL_AWQ:
        warnings.append(
            "engine.model is AWQ — optional cost-saver; default suite stays "
            f"{BENCHMARK_MODEL_BF16} until DMR-068 accuracy gate is green"
        )

    modal = spec.engine.modal
    if modal is None:
        errors.append("spec.engine.modal missing — specialist suite requires Modal L4 pins")
    else:
        if modal.gpu.split(":")[0] != exp["gpu"]:
            errors.append(f"modal.gpu={modal.gpu!r} expected {exp['gpu']!r}")
        if modal.image_tag != exp["image_tag"]:
            errors.append(f"modal.image_tag={modal.image_tag!r} expected {exp['image_tag']!r}")
        if modal.max_containers != exp["max_containers"]:
            errors.append(
                f"modal.max_containers={modal.max_containers} expected {exp['max_containers']}"
            )
        if modal.min_containers != exp["min_containers"]:
            errors.append(
                f"modal.min_containers={modal.min_containers} expected {exp['min_containers']} "
                "(scale-to-zero cost guard)"
            )
        if modal.scaledown_seconds != exp["scaledown_seconds"]:
            errors.append(
                f"modal.scaledown_seconds={modal.scaledown_seconds} "
                f"expected {exp['scaledown_seconds']} "
                "(DMR-076 attended cost-saver; restore 600 for unattended/overnight)"
            )
        if modal.app != exp["app"]:
            warnings.append(f"modal.app={modal.app!r} (default {exp['app']!r})")

    if spec.job.concurrency < 2:
        errors.append("job.concurrency must be >= 2 for L4 throughput benchmarks")

    posture = posture_for_run(spec.run_id)
    if posture is not None:
        want_c = expected_concurrency(spec.run_id)
        if spec.job.concurrency != want_c:
            errors.append(
                f"job.concurrency={spec.job.concurrency} expected {want_c} "
                f"for {spec.run_id} (DMR-078 per-doc-type posture)"
            )
        if spec.task != posture["task"]:
            errors.append(
                f"spec.task={spec.task!r} expected {posture['task']!r} "
                f"(1:1 specialist map)"
            )
        cap = spec.job.cost_cap_usd
        want_cap = float(posture["cost_cap_usd"])
        if cap is None:
            errors.append(
                f"job.cost_cap_usd missing — expected {want_cap} "
                f"(DMR-078 cost guard for {spec.run_id})"
            )
        elif abs(float(cap) - want_cap) > 1e-9:
            errors.append(
                f"job.cost_cap_usd={cap} expected {want_cap} for {spec.run_id}"
            )
        wall = spec.job.max_wall_seconds
        want_wall = int(posture["max_wall_seconds"])
        if wall is None:
            errors.append(
                f"job.max_wall_seconds missing — expected {want_wall} "
                f"(DMR-078 wall guard for {spec.run_id})"
            )
        elif int(wall) != want_wall:
            errors.append(
                f"job.max_wall_seconds={wall} expected {want_wall} for {spec.run_id}"
            )
    elif spec.job.concurrency != exp["concurrency"]:
        # Non-suite runs still default to concurrency 4.
        errors.append(
            f"job.concurrency={spec.job.concurrency} expected {exp['concurrency']} "
            "(DMR-072: 1 starves continuous batching; >4 piles at 1×L4 proxy)"
        )

    rev = spec.effective_revision()
    if rev != exp["revision"]:
        errors.append(f"dataset revision={rev!r} expected pin {exp['revision']!r}")
    if spec.dataset.repo and spec.dataset.repo != exp["repo"]:
        warnings.append(f"dataset.repo={spec.dataset.repo!r}")
    if spec.dataset.sample_seed is None:
        warnings.append("dataset.sample_seed unset — strata draws may be non-reproducible")

    # Specialist 5×30 suite pins (limit + local prompts).
    if spec.run_id in SPECIALIST_LOCAL_PROMPTS or (
        isinstance(spec.run_id, str) and spec.run_id.startswith("run-30-") and "specialist" in spec.run_id
    ):
        if spec.dataset.limit != exp["limit"]:
            errors.append(
                f"dataset.limit={spec.dataset.limit} expected {exp['limit']} "
                "(specialist 5×30 strata)"
            )
        expected_prompts = SPECIALIST_LOCAL_PROMPTS.get(spec.run_id)
        if expected_prompts:
            if spec.task not in expected_prompts:
                errors.append(
                    f"task={spec.task!r} expected one of {sorted(expected_prompts)} "
                    "(1:1 specialist pin — merger must not ride contracts_specialist)"
                )
            actual = _prompt_agent_map(spec)
            for agent, stem in expected_prompts.items():
                got = actual.get(agent)
                if got is None:
                    errors.append(
                        f"prompt.agents.{agent} missing local pin "
                        f"(DMR-074 expected source=local file={stem})"
                    )
                elif got != stem:
                    errors.append(
                        f"prompt.agents.{agent}.file={got!r} "
                        f"expected {stem!r} (DMR-074 local production pin)"
                    )
        elif spec.run_id.startswith("run-30-") and "specialist" in spec.run_id:
            warnings.append(
                f"run_id={spec.run_id!r} looks like a specialist suite YAML "
                "but has no DMR-074 prompt pin map entry"
            )

    return {"errors": errors, "warnings": warnings}


def _format_md(
    ok: bool,
    errors: list[str],
    warnings: list[str],
    checks: Mapping[str, Any],
) -> str:
    spend = checks.get("spend_posture") or {}
    lines = [
        f"## Benchmark preflight — {'READY' if ok else 'BLOCKED'}",
        "",
        f"- Modal profile: `{checks.get('active_modal_profile')}` "
        f"(expected: `{checks.get('expected_modal_profile') or checks.get('hermes_profile_name')}`)",
        f"- Family corpus size pin: {checks.get('family_corpus_size')}",
        f"- Spend: one warm app → chain track configs → teardown after last; "
        f"scaledown attended={spend.get('scaledown_seconds_attended')}s "
        f"(unattended restore {spend.get('scaledown_seconds_unattended')}s); "
        f"AWQ default={spend.get('awq_default')}",
    ]
    if checks.get("spec"):
        s = checks["spec"]
        lines.append(
            f"- Spec: run_id={s.get('run_id')} task={s.get('task')} "
            f"model={s.get('model')} gpu={s.get('gpu')} "
            f"scaledown={s.get('scaledown_seconds')} "
            f"concurrency={s.get('concurrency')} limit={s.get('limit')} "
            f"revision={s.get('revision')}"
        )
        prompts = s.get("local_prompts") or {}
        if prompts:
            pinned = ", ".join(f"{a}={f}" for a, f in sorted(prompts.items()))
            lines.append(f"- Local prompts (DMR-074): {pinned}")
    mb = checks.get("modernbert") or {}
    lines.append(
        f"- ModernBERT: ok={mb.get('ok')} path={mb.get('modernbert_model_path')}"
    )
    if errors:
        lines += ["", "### Errors (must fix)"]
        lines.extend(f"- {e}" for e in errors)
    if warnings:
        lines += ["", "### Warnings"]
        lines.extend(f"- {w}" for w in warnings)
    return "\n".join(lines)


def check_suite_benchmark_posture(
    suite_name: str,
    *,
    require_hermes: bool = True,
    require_modernbert: bool = False,
) -> dict[str, Any]:
    """Run benchmark-check for every config in a suite track (DMR-077).

    Profile gate uses the suite's resolved Modal profile (Track A → Hermes
    default; Track B → ``SANDBOX_MODAL_PROFILE_TRACK_B``). Per-config checks
    still enforce L4 / scaledown 120 / per-doc-type concurrency (DMR-078) / local prompts.
    """
    from mailroom_sandbox.job.spec import load_run_spec
    from mailroom_sandbox.job.suite import load_suite

    suite = load_suite(suite_name)
    expected = suite.resolve_modal_profile()
    if expected is None and suite.modal_profile_env:
        return {
            "ok": False,
            "suite_id": suite.suite_id,
            "track": suite.track,
            "errors": [
                f"Modal profile unset — export {suite.modal_profile_env}=<profile> "
                "or set modal_profile_default in the suite YAML "
                "(never commit token values)"
            ],
            "configs": [],
            "markdown": (
                f"## Suite benchmark-check — BLOCKED\n\n"
                f"- suite: `{suite.suite_id}` track=`{suite.track}`\n"
                f"- set `{suite.modal_profile_env}` then re-run\n"
            ),
        }

    # When suite pins a non-Hermes profile, do not also require Hermes.
    use_hermes = bool(require_hermes) and (
        expected is None or expected == HERMES_MODAL_PROFILE
    )
    config_reports: list[dict[str, Any]] = []
    all_errors: list[str] = []
    for cfg in suite.configs:
        spec = load_run_spec(cfg)
        report = check_benchmark_posture(
            spec=spec,
            require_hermes=use_hermes,
            require_modernbert=require_modernbert,
            expected_modal_profile=expected,
        )
        config_reports.append(
            {
                "config": str(cfg),
                "run_id": spec.run_id,
                "ok": report.get("ok"),
                "errors": list(report.get("errors") or []),
                "warnings": list(report.get("warnings") or []),
            }
        )
        for err in report.get("errors") or []:
            all_errors.append(f"{spec.run_id}: {err}")

    ok = len(all_errors) == 0 and all(r.get("ok") for r in config_reports)
    lines = [
        f"## Suite benchmark-check — {'READY' if ok else 'BLOCKED'}",
        "",
        f"- suite: `{suite.suite_id}` track=`{suite.track}`",
        f"- expected Modal profile: `{expected}`",
        f"- configs: {len(config_reports)}",
        "",
        "| # | run_id | ok |",
        "| -: | --- | --- |",
    ]
    for i, row in enumerate(config_reports, 1):
        lines.append(f"| {i} | `{row['run_id']}` | {row['ok']} |")
    if all_errors:
        lines += ["", "### Errors"]
        lines.extend(f"- {e}" for e in all_errors)
    return {
        "ok": ok,
        "suite_id": suite.suite_id,
        "track": suite.track,
        "expected_modal_profile": expected,
        "configs": config_reports,
        "errors": all_errors,
        "markdown": "\n".join(lines),
    }
