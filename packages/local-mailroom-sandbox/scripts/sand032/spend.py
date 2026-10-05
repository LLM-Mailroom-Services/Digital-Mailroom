#!/usr/bin/env python3
"""SAND-032 spend ledger: GPU fleet windows (deploy → stop) × replicas × L4 rate.

This is the operator's UPPER estimate (a fleet bills from deploy until
`modal app stop`, including boot and idle gaps). The per-run serving records
carry the LOWER bound (run_span_usd_lower_bound). The Modal usage page is the
ground truth and is recorded by hand in reports/serving/SAND-32/SAND032-SPEND-LEDGER.md.

  spend.py open  <fleet-id> <replicas>   # at `modal deploy`
  spend.py close <fleet-id>              # at `modal app stop`
  spend.py write                         # refresh data/runtime/sand032/spend.json
  spend.py loop                          # refresh every 15 s (for `sandbox watch`)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "data" / "runtime" / "sand032"
FLEETS = ROOT / "fleets.json"
OUT = ROOT / "spend.json"
L4_USD_PER_HOUR = 0.80


def _load() -> dict:
    return json.loads(FLEETS.read_text()) if FLEETS.is_file() else {}


def _save(data: dict) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    FLEETS.write_text(json.dumps(data, indent=2, sort_keys=True))


def fleet_usd(f: dict, now: float) -> float:
    end = f.get("stop_ts") or now
    return max(0.0, end - f["deploy_ts"]) / 3600.0 * L4_USD_PER_HOUR * int(f["replicas"])


def write() -> dict:
    data, now = _load(), time.time()
    spent = sum(fleet_usd(f, now) for f in data.values())
    open_ = [k for k, f in data.items() if not f.get("stop_ts")]
    payload = {"spent_usd": round(spent, 4), "includes_live": True, "open_fleets": open_,
               "fleets": {k: round(fleet_usd(f, now), 4) for k, f in data.items()},
               "updated_ts": now}
    ROOT.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "write"
    data = _load()
    if cmd == "open":
        data[argv[1]] = {"deploy_ts": time.time(), "replicas": int(argv[2]), "stop_ts": None}
        _save(data)
    elif cmd == "close":
        data[argv[1]]["stop_ts"] = time.time()
        _save(data)
    elif cmd == "loop":
        while True:
            write()
            time.sleep(15)
    print(json.dumps(write()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
