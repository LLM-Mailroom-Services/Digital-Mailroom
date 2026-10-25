"""SAND-042: GPU hardware telemetry sampled inside the Modal serving replica.

The A100 cost cards carried ``gpu utilization % (min/max/n src=serving-replica
nvidia-smi)``, peak util, power draw, temperature and memory used. No L4 card
ever did — ``reports/SAND-37/SAND37_L4_cost_cards.md`` says "nvidia-smi not
sampled", and ``reports/dashboard/gpu_report.py`` recommends sampling it before
the next spend. SAND-042 closes that gap.

The container cannot expose a second HTTP port (Modal allows exactly one
``@modal.web_server`` per function — ``_PartialFunctionParams.update`` raises
"Cannot set `webhook_config` twice"), so the sampler runs *inside* ``serve()``,
appends one JSON line per sample to a Modal Volume, and this module reads that
volume from the operator machine and reduces it to the A100 card's fields.

Reading needs the Modal SDK (the ``[deploy]`` extra) and network. Nothing here
runs on the scoring path: a missing volume, a missing SDK or a missing file all
degrade to ``captured: False`` with a reason, never an exception.
"""

from __future__ import annotations

import json
import logging
import statistics
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

_log = logging.getLogger("mailroom_sandbox.job.container_telemetry")

SCHEMA = "sandbox.container-telemetry/v1"
DEFAULT_VOLUME = "sandbox-vllm-telemetry"
SRC = "serving-replica nvidia-smi"

# nvidia-smi prints "[N/A]" (or "N/A") for a metric the SKU does not report.
_NA = {"", "n/a", "[n/a]", "na", "[not supported]"}


def _f(value: Any) -> float | None:
    """Parse one nvidia-smi CSV cell, tolerating units and ``[N/A]``."""
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in _NA:
        return None
    for suffix in ("%", "W", "C", "MiB", "MHz"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    try:
        return float(text)
    except ValueError:
        return None


def parse_nvidia_smi_csv(text: str) -> list[dict[str, Any]]:
    """One nvidia-smi query output → one dict per GPU.

    Expects ``--format=csv,noheader,nounits`` with the column order
    ``index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,
    utilization.memory,power.limit,clocks.sm`` — the same query the in-container
    sampler uses (``deploy/modal_vllm.py::TELEMETRY_QUERY``). Columns past the 7th are
    optional so a 7-column capture still parses.
    """
    gpus: list[dict[str, Any]] = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 7:
            continue

        def at(idx: int):
            return _f(parts[idx]) if len(parts) > idx else None

        gpus.append(
            {
                "index": parts[0],
                "name": parts[1],
                "utilization_gpu_perc": at(2),
                "memory_used_mib": at(3),
                "memory_total_mib": at(4),
                "temperature_c": at(5),
                "power_draw_w": at(6),
                "utilization_memory_perc": at(7),
                "power_limit_w": at(8),
                "clocks_sm_mhz": at(9),
            }
        )
    return gpus


def parse_jsonl(text: str) -> list[dict[str, Any]]:
    """Sampler JSONL → samples; a malformed line is skipped, never fatal."""
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def slice_window(
    samples: Sequence[Mapping[str, Any]], *, start: float | None, end: float | None
) -> list[dict[str, Any]]:
    """Samples whose ``t`` falls inside the run's own scrape window."""
    out: list[dict[str, Any]] = []
    for s in samples:
        t = s.get("t")
        if not isinstance(t, (int, float)):
            continue
        if start is not None and float(t) < float(start):
            continue
        if end is not None and float(t) > float(end):
            continue
        out.append(dict(s))
    return out


def _flat_gpus(samples: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in samples:
        for g in s.get("gpus") or []:
            if isinstance(g, dict):
                out.append(g)
    return out


def _stat(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    return {
        "mean": statistics.fmean(values),
        "min": min(values),
        "max": max(values),
        "p95": _p95(values),
        "n": len(values),
    }


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
    return ordered[idx]


def _coverage_pct(
    samples: Sequence[Mapping[str, Any]], start: Any, end: Any
) -> float | None:
    """Fraction of the run window covered by *contiguous* sampling — #128's gate.

    Not ``observed / expected``: the sampler's cadence is bimodal (a fixed 5 s sleep
    plus the ``nvidia-smi`` call's own ~2-3 s), so a median-based expected count
    swings 76 %→99 % across equally healthy series, and a mean-based one absorbs the
    very dropout it is meant to catch. Instead, a gap longer than twice the normal
    cadence is treated as uncovered time (the sampler dropped out); ordinary jitter
    and the few seconds of window beyond the first/last sample are not penalised.

    #128 rejects a cell below 90%. Returns ``None`` when the window or the cadence
    cannot be established — a missing number, never a fabricated 100%.
    """
    stamps = sorted(t for t in (_num(s.get("t")) for s in samples) if t is not None)
    lo, hi = _num(start), _num(end)
    if len(stamps) < 3 or lo is None or hi is None or hi <= lo:
        return None
    gaps = [b - a for a, b in zip(stamps, stamps[1:]) if b > a]
    if not gaps:
        return None
    cadence = statistics.median(gaps)
    if cadence <= 0:
        return None
    tolerance = 2.0 * cadence
    excess = sum(
        max(0.0, g - tolerance) for g in [*gaps, stamps[0] - lo, hi - stamps[-1]]
    )
    span = hi - lo
    return round(max(0.0, min(100.0, 100.0 * (1.0 - excess / span))), 1)


def summarize_samples(doc: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce a pulled telemetry doc to the A100 cost-card GPU fields.

    ``doc`` is what ``pull`` writes: ``{"samples": [...], "replicas": {...}}``.
    Every field is ``None`` when the metric was never reported, so a card can say
    "not captured" instead of printing a fabricated 0.
    """
    samples = [s for s in (doc.get("samples") or []) if isinstance(s, dict)]
    gpus = _flat_gpus(samples)
    if not gpus:
        return {
            "captured": False,
            "src": SRC,
            "samples": len(samples),
            # Still report coverage: it separates "the sampler never ran" from
            # "the sampler ran but nvidia-smi returned no GPU rows".
            "sampling_coverage_pct": _coverage_pct(samples, doc.get("start"), doc.get("end")),
            "util_p95_perc": None,
            "reason": doc.get("reason") or "no GPU samples in the telemetry window",
            "errors": list(doc.get("errors") or []),
        }

    def collect(key: str) -> list[float]:
        return [v for v in (_num(g.get(key)) for g in gpus) if v is not None]

    util = collect("utilization_gpu_perc")
    replicas: dict[str, Any] = {}
    for name, rep in sorted((doc.get("replicas") or {}).items()):
        rep_gpus = _flat_gpus(
            [s for s in (rep.get("samples") or []) if isinstance(s, dict)]
        )
        rep_util = [v for v in (_num(g.get("utilization_gpu_perc")) for g in rep_gpus) if v is not None]
        replicas[str(name)] = {
            "samples": len(rep.get("samples") or []),
            "util_mean_perc": statistics.fmean(rep_util) if rep_util else None,
            "util_max_perc": max(rep_util) if rep_util else None,
        }

    return {
        "captured": True,
        "schema": SCHEMA,
        "src": doc.get("src") or SRC,
        "label": doc.get("label"),
        "samples": len(samples),
        "gpus_observed": len(gpus),
        "util_mean_perc": statistics.fmean(util) if util else None,
        "util_min_perc": min(util) if util else None,
        "util_max_perc": max(util) if util else None,
        "util_peak_perc": max(util) if util else None,
        "util_p95_perc": _p95(util) if util else None,
        "sampling_coverage_pct": _coverage_pct(samples, doc.get("start"), doc.get("end")),
        "power_draw_w": _stat(collect("power_draw_w")),
        "power_limit_w": _stat(collect("power_limit_w")),
        "utilization_memory_perc": _stat(collect("utilization_memory_perc")),
        "clocks_sm_mhz": _stat(collect("clocks_sm_mhz")),
        "temperature_c": _stat(collect("temperature_c")),
        "memory_used_mib": _stat(collect("memory_used_mib")),
        "memory_total_mib": _stat(collect("memory_total_mib")),
        "replicas": replicas,
        "errors": list(doc.get("errors") or []),
    }


def _num(value: Any) -> float | None:
    return value if isinstance(value, (int, float)) else None


# ── volume pull ──────────────────────────────────────────────────────────────


def _read_volume_files(
    label: str, *, volume_name: str = DEFAULT_VOLUME
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    """``{replica: samples}`` from ``<label>/<replica>.jsonl`` in the volume.

    The volume is mounted at ``/telemetry`` *inside the container*; from the
    volume's own perspective the sampler's files live at the volume root under
    ``<label>/``. Do not prefix the container mount here.
    """
    import modal  # local import: [deploy] extra, network + auth required

    errors: list[str] = []
    out: dict[str, list[dict[str, Any]]] = {}
    vol = modal.Volume.from_name(volume_name)
    prefix = label.strip("/")

    entries = _listdir(vol, prefix, errors)
    for entry in entries:
        path = str(getattr(entry, "path", "") or "")
        if not path.endswith(".jsonl"):
            continue
        replica = Path(path).name[: -len(".jsonl")]
        try:
            chunks = _read_file(vol, path)
        except Exception as exc:  # noqa: BLE001 — report, never crash the run
            errors.append(f"read {path}: {type(exc).__name__}: {str(exc)[:120]}")
            continue
        out[replica] = parse_jsonl(chunks)
    if not entries:
        errors.append(f"no telemetry under {prefix}/ in volume {volume_name!r}")
    return out, errors


def _listdir(vol: Any, prefix: str, errors: list[str]) -> list[Any]:
    try:
        return list(vol.listdir(prefix))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"listdir {prefix}: {type(exc).__name__}: {str(exc)[:120]}")
        return []


def _read_file(vol: Any, path: str) -> str:
    """Drain ``Volume.read_file``.

    ``read_file`` is decorated ``@live_method_gen``, so outside async code it
    returns a *synchronous* generator (the SDK's own docstring iterates it with a
    plain ``for``); an ``async for`` raises "'async for' requires an object with
    __aiter__ method, got generator".
    """
    return b"".join(vol.read_file(path)).decode("utf-8", errors="replace")


def billed_seconds(doc: Mapping[str, Any]) -> float | None:
    """Wall seconds the run's containers were observed, from the run's OWN window.

    ``pull`` records the window it was asked for: the runbook's ``before`` scrape
    opens it and the ``after`` scrape closes it, so it brackets the run. That makes
    it the billed interval, and it is derived from the run's own telemetry rather
    than from a billing-CLI scrape.

    It is also the honest replacement for the item-``ts`` span (``metrics.
    infer_wall_seconds_from_items``), which runs FIRST completion -> last completion
    and therefore drops the whole first wave: measured 100.3 s against a true 438 s
    on the 5-document merger probe (4.4x), and ~1/waves at n=50.
    """
    start, end = _num(doc.get("start")), _num(doc.get("end"))
    if start is not None and end is not None and end > start:
        return round(end - start, 3)
    stamps = _stamps(doc.get("samples") or [])
    if len(stamps) < 2:
        return None
    return round(stamps[-1] - stamps[0], 3)


def fleet_gpu_seconds(doc: Mapping[str, Any]) -> float | None:
    """Per-replica alive seconds, summed = GPU-seconds the fleet billed.

    One telemetry file per container (``<label>/<process_start_time_seconds>.jsonl``),
    so each replica's own first->last sample is its container lifetime. With
    ``min_containers=1`` the fleet is pinned warm from deploy to teardown, so this
    sum — not the sum of the five run windows — is what Modal meters for a cell.
    """
    spans = []
    for rep in (doc.get("replicas") or {}).values():
        stamps = _stamps(rep.get("samples") or [])
        if len(stamps) >= 2:
            spans.append(stamps[-1] - stamps[0])
    return round(sum(spans), 3) if spans else None


def _stamps(samples: Sequence[Mapping[str, Any]]) -> list[float]:
    return sorted(t for t in (_num(s.get("t")) for s in samples) if t is not None)


def pull(
    label: str,
    *,
    volume_name: str = DEFAULT_VOLUME,
    start: float | None = None,
    end: float | None = None,
) -> dict[str, Any]:
    """Read one cell's telemetry out of the Modal Volume, sliced to the run window."""
    try:
        replicas_raw, errors = _read_volume_files(label, volume_name=volume_name)
    except Exception as exc:  # noqa: BLE001 — no SDK / no auth / volume absent
        return {
            "schema": SCHEMA,
            "label": label,
            "src": SRC,
            "samples": [],
            "replicas": {},
            "errors": [f"{type(exc).__name__}: {str(exc)[:160]}"],
            "reason": (
                "could not read the Modal telemetry volume "
                f"(is the [deploy] extra installed and `modal` authenticated?)"
            ),
        }

    replicas: dict[str, Any] = {}
    flat: list[dict[str, Any]] = []
    for replica, samples in replicas_raw.items():
        windowed = slice_window(samples, start=start, end=end)
        replicas[replica] = {"samples": windowed}
        flat.extend(windowed)
    return {
        "schema": SCHEMA,
        "label": label,
        "src": SRC,
        "volume": volume_name,
        "start": start,
        "end": end,
        "samples": flat,
        "replicas": replicas,
        "errors": errors,
    }
