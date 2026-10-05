#!/opt/homebrew/Cellar/modal/1.5.5/libexec/bin/python
"""Scale the WARM sandbox-vllm-sand032 fleet in place (no redeploy, no restart).

  scale.py <replicas> <segment-id>

Updates the deployed `serve` function's autoscaler to MIN=MAX=<replicas>; the
running replica keeps serving and only the new GPU(s) cold-boot. Closes the
open spend segment and opens a new one at the new replica count.
"""
import subprocess
import sys
from pathlib import Path

import modal

n, seg = int(sys.argv[1]), sys.argv[2]
fn = modal.Function.from_name("sandbox-vllm-sand032", "serve")
fn.update_autoscaler(min_containers=n, max_containers=n)
spend = Path(__file__).with_name("spend.py")
fleets = Path(__file__).resolve().parents[2] / "data/runtime/sand032/fleets.json"
import json  # noqa: E402

open_ = [k for k, v in json.loads(fleets.read_text()).items() if not v.get("stop_ts")]
for k in open_:
    subprocess.run(["python3", str(spend), "close", k], check=True, capture_output=True)
subprocess.run(["python3", str(spend), "open", seg, str(n)], check=True, capture_output=True)
print(f"autoscaler → min=max={n}; spend segment {seg} opened ×{n}")
