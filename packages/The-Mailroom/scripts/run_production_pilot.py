#!/usr/bin/env python3
"""Orchestrate a production Langfuse-traced HF subset pilot.

1. Require sibling ``llm-mailroom`` (``MAILROOM_PIPELINE_ROOT`` or
   ``../llm-mailroom``).
2. Run ``src/scripts/run_hf_pilot.py --real`` there (Qwen 3.7-Flash, vision
   off, stratified ``Lucius-Morningstar/mailroom-dataset`` subset).
3. Score the resulting traces with ``scripts/eval_pipeline.py``.

Keys stay in gitignored ``.env`` (Langfuse + OpenRouter + HF). Never printed.

Usage:
    python scripts/run_production_pilot.py --check
    python scripts/run_production_pilot.py --real --per-class 1
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mailroom_ui.producer import pipeline_checkout


def _pipeline_root() -> Path | None:
    return pipeline_checkout()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--per-class", type=int, default=1)
    parser.add_argument("--split", default="train")
    parser.add_argument("--max-chars", type=int, default=25000)
    parser.add_argument("--target-chars", type=int, default=6000)
    args = parser.parse_args()
    if not args.real and not args.check:
        parser.error("choose --check or --real")

    pipe = _pipeline_root()
    if pipe is None:
        sys.exit(
            "llm-mailroom not found. Clone it next to this repo or set "
            "MAILROOM_PIPELINE_ROOT. Intake + run_hf_pilot live in that repo."
        )
    runner = pipe / "src" / "scripts" / "run_hf_pilot.py"
    if not runner.is_file():
        sys.exit(f"run_hf_pilot.py missing in {pipe} — pull the intake/HF-pilot branch")

    env = os.environ.copy()
    # Copy keys from The-Mailroom .env if the sibling has none.
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    load_dotenv(pipe / ".env")
    for key in (
        "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST",
        "LANGFUSE_BASE_URL", "OPENROUTER_API_KEY", "HF_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
    ):
        val = os.environ.get(key)
        if val:
            env[key] = val
    env.setdefault("OBSERVABILITY_PROVIDER", "langfuse")
    env.setdefault("OBSERVABILITY_ENVIRONMENT", "pilot")
    env.setdefault("MAILROOM_VISION_ENABLED", "0")
    env.setdefault("MAILROOM_PILOT_COST_ABORT", "2.00")
    env.setdefault("DEFAULT_PROVIDER", "openrouter")

    cmd = [sys.executable, str(runner)]
    if args.check:
        cmd.append("--check")
    else:
        cmd.append("--real")
    cmd += ["--per-class", str(args.per_class), "--split", args.split,
            "--max-chars", str(args.max_chars),
            "--target-chars", str(args.target_chars)]
    print(f"pipeline {pipe}")
    print(" ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(pipe), env={**env, "PYTHONPATH": str(pipe / "src")})
    if args.check:
        # local scorer contract
        eval_cmd = [sys.executable, str(ROOT / "scripts" / "eval_pipeline.py"), "--check"]
        ev = subprocess.run(eval_cmd, cwd=str(ROOT))
        return proc.returncode or ev.returncode
    if proc.returncode not in (0, 1):
        return proc.returncode
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_json = ROOT / "docs" / "reports" / "evaluations" / f"hf-pilot-{stamp}.json"
    out_md = ROOT / "docs" / "reports" / "evaluations" / f"hf-pilot-{stamp}.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    eval_cmd = [sys.executable, str(ROOT / "scripts" / "eval_pipeline.py"),
                "--environment", "pilot", "--since", "7200",
                "--out", str(out_json), "--md", str(out_md)]
    reports = sorted((pipe / "data" / "hf_pilot").glob("*/report.json"))
    if reports:
        try:
            session = json.loads(reports[-1].read_text(encoding="utf-8")).get("session_id")
        except Exception:
            session = None
        if session:
            eval_cmd += ["--session", session]
            print(f"eval session {session}")
        eval_cmd += ["--manifest", str(reports[-1])]
    ev = subprocess.run(eval_cmd, cwd=str(ROOT), env=env)
    return ev.returncode


if __name__ == "__main__":
    raise SystemExit(main())
