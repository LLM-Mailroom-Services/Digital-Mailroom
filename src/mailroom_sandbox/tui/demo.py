"""Synthetic mailroom run for the watch dev server (`sandbox dev`, `watch --web --demo`).

Writes the same files a real SAND-032 run produces — driver ``.times`` stamps, run
store items, a serving record, a spend ledger, Modal-style boot/throughput log
lines — and advances one step per refresh, so every web panel (lifecycle, in-tray,
postage, scorecard, dispatch log) can be seen and browser-tested without Modal,
credentials, or spend. Loops back to a fresh run after the fleet "stops".
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.watch import LogBuffer

RUN_ID = "sand032-demo"
APP = "sandbox-vllm-demo"

# (tick offset within a cycle, log line) — lines match watch.BOOT_MARKERS / classify_log_line
_BOOT_LOGS = {
    0: "sandbox-vllm serve config: Qwen/Qwen3-8B-AWQ · awq_marlin · kv fp8 · seqs 16",
    2: "Loading weights took 11.20 seconds · model loading took 5.71 GiB",
    3: "GPU KV cache size: 190,464 tokens · Maximum concurrency 5.81x",
    4: "Capturing CUDA graphs (mixed prefill-decode): 100%|██████████| 5/5",
    5: "INFO: Application startup complete. vLLM ready on port 8000",
}


class DemoRun:
    """A deterministic, looping fake run rooted at ``root`` (a temp dir)."""

    def __init__(self, root: Path, *, n_docs: int = 12) -> None:
        self.root = Path(root)
        self.n_docs = n_docs
        self.times_dir = self.root / "logs"
        self.serving_dir = self.root / "serving"
        self.ledger = self.root / "spend.json"
        self.run_dir = self.root / "runs" / RUN_ID
        self.cycle = 0
        self._tick = 0
        self._spent = 0.0
        for d in (self.times_dir, self.serving_dir):
            d.mkdir(parents=True, exist_ok=True)
        self._reset_run()

    # ── public surface used by the web session / CLI ─────────────────────────
    def resolve(self) -> tuple[RunStore, str]:
        return RunStore(self.run_dir), APP

    def step(self, sink: LogBuffer, tick: int | None = None) -> None:
        """Advance the fake run by one tick (the web session calls this per refresh)."""
        t = self._tick if tick is None else tick
        self._tick = t + 1
        start = self.n_docs + 7  # run_end offset within a cycle
        span = start + 7  # stopped at +3, reset at +7
        c = t % span
        if t and c == 0:
            self.cycle += 1
            self._reset_run()
        store, _ = self.resolve()
        if c in _BOOT_LOGS:
            sink.append(_BOOT_LOGS[c])
        stamps = {0: "deploy_start", 1: "deploy_done", 5: "ready", 6: "run_start", start: "run_end", start + 3: "stopped"}
        if c in stamps:
            self._stamp(stamps[c])
        if c == 6:
            store.write_checkpoint(state="running", cursor=0, total=self.n_docs)
        if 7 <= c < start:
            i = c - 7
            ok = i != 1  # one returned doc so the in-tray error path is visible
            store.append_item(self._item(i, ok))
            store.write_checkpoint(state="running", cursor=i + 1, total=self.n_docs)
            sink.append(
                f"Engine 000: Avg prompt throughput: {1400 + 37 * i:.1f} tokens/s, "
                f"Avg generation throughput: {180 + 5 * i:.1f} tokens/s, Running: 8 reqs"
            )
            if not ok:
                sink.append("ERROR LengthFinishReasonError: completion hit max_tokens=4096")
        if c == start:
            store.write_checkpoint(state="done", cursor=self.n_docs, total=self.n_docs)
            self._write_serving()
        if c < start + 3:  # the fleet bills until it stops
            self._spent = round(self._spent + 0.0004, 4)
        self.ledger.write_text(json.dumps({"spent_usd": self._spent, "includes_live": True}))

    # ── internals ─────────────────────────────────────────────────────────────
    def _reset_run(self) -> None:
        shutil.rmtree(self.run_dir, ignore_errors=True)
        (self.times_dir / f"{RUN_ID}.times").write_text("")
        (self.serving_dir / f"{RUN_ID}.serving.json").unlink(missing_ok=True)
        store = RunStore(self.run_dir)
        store.write_lock(
            {
                "run_id": RUN_ID,
                "task": "correspondence_specialist",
                "engine": {
                    "model": "Qwen/Qwen3-8B-AWQ",
                    "vllm": {"kv_cache_dtype": "fp8", "quantization": "awq_marlin", "max_num_seqs": 16},
                    "modal": {"gpu": "L4", "max_containers": 2, "min_containers": 2, "app": APP},
                },
                "job": {"concurrency": 32},
            }
        )
        store.write_checkpoint(state="prepared", cursor=0, total=self.n_docs)

    def _stamp(self, key: str) -> None:
        with (self.times_dir / f"{RUN_ID}.times").open("a", encoding="utf-8") as fh:
            fh.write(f'"{key}": {time.time()},\n')

    def _item(self, i: int, ok: bool) -> dict[str, Any]:
        lat = 4200.0 + 650.0 * (i % 5)
        return {
            "item_id": f"DOC-demo-{self.cycle:02d}-{i:03d}",
            "ok": ok,
            "latency_ms": lat,
            "prompt_tokens": 2264 + 40 * i,
            "completion_tokens": 185 + 3 * i,
            "error": None if ok else "LengthFinishReasonError: completion hit max_tokens=4096",
            "score": (
                {"overall_extraction_score": round(0.24 + 0.03 * (i % 4), 4), "schema_valid": True, "parse_error": False}
                if ok
                else {}
            ),
        }

    def _write_serving(self) -> None:
        wall = 16.0 + 0.4 * self.n_docs
        # flat, like the real run_one.sh serving record that watch.scorecard_lines reads
        rec = {
            "n": self.n_docs,
            "wall_seconds": wall,
            "cold_boot_seconds": 216.0,
            "tokens_per_second": 7395.0,
            "latency_p50_seconds": 6.8,
            "latency_p95_seconds": 12.9,
            "gpu_cost_per_document": 0.000144,
            "estimated_gpu_cost_usd": round(0.000144 * self.n_docs, 6),
            "run_span_usd_lower_bound": round(wall / 3600 * 0.80 * 2, 6),
            "replicas": 2,
            "prompt_tokens": sum(2264 + 40 * i for i in range(self.n_docs)),
            "completion_tokens": sum(185 + 3 * i for i in range(self.n_docs)),
        }
        (self.serving_dir / f"{RUN_ID}.serving.json").write_text(json.dumps(rec))
