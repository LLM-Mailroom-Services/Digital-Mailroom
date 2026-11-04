#!/usr/bin/env python3
"""Offline pre-flight for an experiment day (SAND-081): no provider, deploy or spend.

Runs three mock campaigns end to end — the five specialists, the paired sand42
grid and the full connected pipeline — through ``sandbox experiment create →
preflight → launch → report`` on the pinned dataset, then checks the reports:

* every run completes with every document successful;
* paired cells share identical dataset bytes;
* the mock oracle (``mock_llm.oracle_extraction``) scores an extraction
  headline of 1.0 on every run, and the pipeline classifies every document
  correctly, so the Dojo scorers still receive ground truth and predictions in
  the shape they read. Pipeline stage is reported, not gated (see SAND-081).

Run stores go to a temporary ``MAILROOM_BASE_DIR`` (``--keep DIR`` keeps them);
the dataset is read from the ``sandbox datasets pull`` cache, or ``--local-dataset``.

    python scripts/smoke_campaign.py
    python scripts/smoke_campaign.py --samples 5 --keep /tmp/smoke
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path


def _campaigns(samples: int) -> list[tuple[str, list[str]]]:
    return [
        ("specialists", ["--samples", str(samples)]),
        ("sand42", ["--design", "sand42", "--doc-class", "contract", "--doc-class", "merger_agreement",
                    "--samples", str(samples)]),
        ("pipeline", ["--task", "pipeline", "--samples", str(samples)]),
    ]


def _run(cli, argv: list[str], log: Path) -> int:
    with open(log, "a", encoding="utf-8") as fh, contextlib.redirect_stdout(fh), contextlib.redirect_stderr(fh):
        print("$ sandbox " + " ".join(argv))
        try:
            return cli.main(argv)
        except SystemExit as exc:  # argparse errors
            return int(exc.code or 1)


def _check(name: str, report: dict) -> list[str]:
    problems = []
    if not report.get("complete"):
        problems.append("not every run completed with every document successful")
    if not report.get("paired_dataset_bytes"):
        problems.append("paired cells drew different dataset bytes")
    for run in report.get("runs", []):
        means = run.get("stored_score_means") or {}
        headline = means.get("overall_extraction_score")
        if headline != 1.0:
            problems.append(f"{run['run_id']}: oracle extraction headline {headline} (expected 1.0)")
        # Pipeline stage is not gated: llm-mailroom's extraction coverage check parks
        # every contract and merger agreement at review even for a perfect answer (SAND-081).
        if name == "pipeline" and means.get("class_correct") != 1.0:
            problems.append(f"{run['run_id']}: class_correct {means.get('class_correct')} (expected 1.0)")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--samples", type=int, default=3, help="documents per class (default 3)")
    parser.add_argument("--local-dataset", help="local JSONL instead of the pulled Hub cache")
    parser.add_argument("--keep", help="keep run stores and campaign files in this directory")
    args = parser.parse_args()

    work = Path(args.keep).resolve() if args.keep else Path(tempfile.mkdtemp(prefix="smoke-campaign-"))
    work.mkdir(parents=True, exist_ok=True)
    os.environ["MAILROOM_BASE_DIR"] = str(work / "data")  # isolate run stores from data/runtime
    os.environ.setdefault("OBSERVABILITY_PROVIDER", "none")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from mailroom_sandbox import cli

    stamp = time.strftime("%H%M%S")
    log = work / "smoke.log"
    failures = 0
    print(f"smoke campaigns in {work} (log: {log})")
    for name, options in _campaigns(args.samples):
        study = f"smoke-{name[:6]}-{stamp}"
        config = work / study / "experiment.yaml"
        extra = ["--local-dataset", args.local_dataset] if args.local_dataset else []
        steps = [["experiment", "create", study, "--mock", "--trace-sink", "none", *options, *extra,
                  "--output", str(config.parent)],
                 ["experiment", "preflight", "--config", str(config)],
                 ["experiment", "launch", "--config", str(config)]]
        started = time.monotonic()
        rc = 0
        for argv in steps:
            rc = _run(cli, argv, log)
            if rc:
                break
        if rc:
            failures += 1
            print(f"FAIL {name}: `sandbox {' '.join(argv[:2])}` exited {rc}; see {log}")
            if argv[1] == "preflight" and not args.local_dataset:
                print("     (no cached dataset? run `sandbox datasets pull` once, or pass --local-dataset)")
            continue
        report = json.loads((config.parent / "report.json").read_text())
        problems = _check(name, report)
        failures += bool(problems)
        status = "FAIL" if problems else "ok  "
        print(f"{status} {name}: {len(report['runs'])} run(s) in {time.monotonic() - started:.0f}s · "
              f"{config.parent / 'report.md'}")
        for problem in problems:
            print(f"     - {problem}")
    print("all campaigns passed" if not failures else f"{failures} campaign(s) failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
