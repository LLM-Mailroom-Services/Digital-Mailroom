"""QWEN-flash tracked cost ledger (issue #40)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_API_EVALS = Path(__file__).resolve().parent.parent / "api-evals"
if str(_API_EVALS) not in sys.path:
    sys.path.insert(0, str(_API_EVALS))

from api_evals.cost import item_cost_usd  # noqa: E402
from api_evals.ledger import ledger_path, ledger_to_results, load_ledger, price_pin  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PRICES = (0.03, 0.13)


def test_ledger_path_exists():
    path = ledger_path(ROOT)
    assert path.is_file()
    ledger = load_ledger(path)
    assert len(ledger["records"]) == 3
    assert price_pin(ledger) == PRICES


def test_real_api_totals_match_issue_40():
    ledger = load_ledger(ledger_path(ROOT))
    results = ledger_to_results(ledger, prices=PRICES)
    costs = [r["cost"]["cost_usd"] for r in results]
    assert costs[0] == round(item_cost_usd(12158, 997, PRICES), 8)
    assert sum(costs) == pytest.approx(0.01207616, rel=1e-4)
    proxies = sum(r["ledger"]["estimated_gpu_cost_usd"] for r in results)
    assert proxies == pytest.approx(0.018558, rel=1e-4)


def test_report_from_ledger_cli_offline():
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "api-evals" / "run_api_evals.py"),
            "report",
            "--from-ledger",
            "--prices",
            "0.03",
            "0.13",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "api-evals report" in proc.stdout


def test_report_from_log_missing_points_at_ledger():
    """On a clean checkout the gitignored log is absent — CLI must point at the ledger."""
    log = ROOT / "reports" / "experiment_log.jsonl"
    if log.is_file():
        pytest.skip("local experiment_log.jsonl present — absence path not testable")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "api-evals" / "run_api_evals.py"), "report", "--from-log"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 1
    assert "qwen-flash-cost-source.json" in proc.stderr
    assert "--from-ledger" in proc.stderr
