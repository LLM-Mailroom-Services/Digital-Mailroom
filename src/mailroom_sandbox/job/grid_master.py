"""Master score & cost card across the specialist-grid postures (SAND-037 / SAND-039 / SAND-040).

Renders the two-page executive ``reports/SAND-37/SAND-37-MASTER-SCORE-COST-CARD.md``
plus the detail ``reports/SAND-37/SAND-37-MASTER-APPENDIX.md`` from the committed
per-run ``*.card.json`` (same source of truth as the suite cards), so a later
leg populates both by re-running ``sandbox run card --master``::

    SAND-37 · 1×L4 · C8  · n=20   reports/SAND-37/1L4/<specialist>/grid-20-*-1l4*.card.json
    SAND-39 · 1×L4 · C8  · n=50   reports/SAND-37/1L4/<specialist>/grid-50-*-1l4*.card.json
    SAND-37 · 2×L4 · C32 · n=50   reports/SAND-37/2L4/<specialist>/grid-50-*-2l4*.card.json
    SAND-40 · 2×L4 · C32 · n=100  reports/SAND-37/2L4/<specialist>/sand40-*-2l4*.card.json
                                  (merger n=50 †)

The master card stays executive-length (postures, pooled efficiency, per-specialist
scorecard, merger † settings, key findings, metered cost). Everything else — per-cell
tables, clause scoring, engine telemetry, run conditions, token composition, full
findings, figures and dashboards — lives in the appendix. SAND-40 validation probes
are collected but never pooled or reported. A posture
with no cards yet renders as "pending". SAND-39 and the 2×L4 leg draw the identical
n=50 documents, so when both are present the scale-out finding is a matched-sample
comparison. Session-level Modal spend (cold boots, idle, pre-warm) is not in the
cards; it comes from ``metered-costs.json`` next to the card when the operator
has recorded it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from mailroom_sandbox.job.grid_cards import ROOT_REL, SCHEMA, SPECIALISTS, _read_json
from mailroom_sandbox.paths import repo_root

MASTER_STEM = "SAND-37-MASTER-SCORE-COST-CARD"
APPENDIX_STEM = "SAND-37-MASTER-APPENDIX"
METERED_FILE = "metered-costs.json"
PROBE_DIR = "probes"  # SAND-40 validation probes: collected, never pooled or reported
EXECUTIVE_MAX_LINES = 110  # two printed pages; the staleness test enforces it


@dataclass(frozen=True)
class Posture:
    key: str
    study: str
    shape_dir: str
    replicas: int
    concurrency: int
    n: int
    docs: str = ""
    n_by_folder: tuple[tuple[str, int], ...] = ()
    experiment: int = 0  # reader-facing id used on the record figures (Experiment 1-4)

    @property
    def label(self) -> str:
        return f"{self.replicas}×L4 C{self.concurrency} n={self.n}"

    @property
    def exp_label(self) -> str:
        return f"Experiment {self.experiment}"

    @property
    def documents(self) -> str:
        return self.docs or str(self.n)

    def expected_n(self, folder: str) -> int:
        return dict(self.n_by_folder).get(folder, self.n)


POSTURES: tuple[Posture, ...] = (
    Posture("s37-1l4-n20", "SAND-37", "1L4", 1, 8, 20, experiment=1),
    Posture("s39-1l4-n50", "SAND-39", "1L4", 1, 8, 50, experiment=2),
    Posture("s37-2l4-n50", "SAND-37", "2L4", 2, 32, 50, experiment=3),
    Posture(
        "s40-2l4",
        "SAND-40",
        "2L4",
        2,
        32,
        100,
        docs="100 (merger 50†)",
        n_by_folder=(("merger_agreement", 50),),
        experiment=4,
    ),
)
_ORDER = ("insurance_claims", "contracts", "corporate_records", "correspondence", "merger_agreement")
_LABEL = {folder: label for _, folder, label in SPECIALISTS}
_SUITE_FOLDERS = ("insurance_claims", "corporate_records", "correspondence")  # field score only
PENDING = "pending"
RECORD_FIG_DIR = "figures/record"  # one chart per PNG (figures/record/make_record_figures.py)
# Executive card: the three charts behind the three key findings. Everything else sits in the
# appendix section it illustrates (see APPENDIX_FIGURES).
MASTER_FIG_SECTIONS = ("efficiency", "merger")
RECORD_FIGURES: dict[str, tuple[tuple[str, str], ...]] = {
    # executive card
    "efficiency": (
        ("1x-vs-2xL4-throughput", "Throughput, 1x vs 2x L4 on the same 250 documents"),
        ("2xL4-n50-vs-n100-cost", "Cost per 1,000 ok documents on 2x L4, n=50 vs n=100"),
    ),
    "merger": (("merger-frozen-vs-dagger", "Merger agreements, frozen vs dagger settings"),),
    # appendix
    "appendix-serving": (
        ("1x-vs-2xL4-cost", "Cost per 1,000 ok documents, 1x vs 2x L4 on the same 250 documents"),
    ),
    "appendix-scores": (("cost-vs-score", "Cost vs score by specialist, same 250 documents"),),
    "posture-s39-1l4-n50": (
        ("1xL4-C8-n50-cost", "Cost per 1,000 ok documents, Experiment 2 (1x L4 C=8 n=50)"),
        ("1xL4-C8-n50-latency", "Latency p50 to p99, Experiment 2 (1x L4 C=8 n=50)"),
    ),
    "posture-s37-2l4-n50": (
        ("2xL4-C32-n50-cost", "Cost per 1,000 ok documents, Experiment 3 (2x L4 C=32 n=50)"),
        ("2xL4-C32-n50-latency", "Latency p50 to p99, Experiment 3 (2x L4 C=32 n=50)"),
    ),
    "posture-s40-2l4": (
        ("2xL4-C32-n100-cost", "Cost per 1,000 ok documents, Experiment 4 (2x L4 C=32 n=100)"),
        ("2xL4-C32-n100-latency", "Latency p50 to p99, Experiment 4 (2x L4 C=32 n=100)"),
    ),
}
PARITY = 0.03  # cost-per-document gap below which two postures are called equal


def master_paths(repo: Path | None = None) -> dict[str, Path]:
    base = (repo or repo_root()) / ROOT_REL
    return {
        "dir": base,
        "md": base / f"{MASTER_STEM}.md",
        "appendix": base / f"{APPENDIX_STEM}.md",
        "metered": base / METERED_FILE,
    }


def _cells_for(posture: Posture) -> frozenset[str]:
    from mailroom_sandbox.job.specialist_posture import GRID_CELLS, SAND40_CELLS

    if posture.key == "s40-2l4":
        return SAND40_CELLS
    return GRID_CELLS


def collect_master(repo: Path | None = None) -> dict[str, Any]:
    """Cards per posture and specialist folder, aligned grid cells only."""
    root = (repo or repo_root()) / ROOT_REL
    cards: dict[str, dict[str, dict[str, Any]]] = {p.key: {} for p in POSTURES}
    for p in POSTURES:
        aligned = _cells_for(p)
        for path in sorted((root / p.shape_dir).glob("*/*.card.json")):
            data = _read_json(path)
            if data.get("schema") != SCHEMA or data.get("run_id") not in aligned:
                continue
            cond = data.get("conditions") or {}
            if int(data.get("n") or 0) != p.expected_n(path.parent.name) or int(cond.get("replicas") or 0) != p.replicas:
                continue
            if int(cond.get("concurrency") or 0) != p.concurrency:
                continue
            cards[p.key][path.parent.name] = data
    probes: dict[str, dict[str, Any]] = {}
    for path in sorted((root / PROBE_DIR).glob("*/*.card.json")):
        data = _read_json(path)
        if data.get("schema") == SCHEMA and "-probe-" in str(data.get("run_id") or ""):
            probes[path.parent.name] = data
    metered = _read_json(master_paths(repo)["metered"])
    record = sorted(f.stem for f in (root / RECORD_FIG_DIR).glob("*.png"))
    return {"cards": cards, "probes": probes, "metered": metered, "record_figures": record}


def _record_figures(data: Mapping[str, Any], section: str) -> list[str]:
    """Embed the committed record figures for one executive section (only those on disk)."""
    have = set(data.get("record_figures") or ())
    out: list[str] = []
    for stem, alt in RECORD_FIGURES.get(section, ()):
        if stem in have:
            out += [f"![{alt}]({RECORD_FIG_DIR}/{stem}.png)", ""]
    return out


# ── formatting ───────────────────────────────────────────────────────────────


def _pct_change(new: float | None, old: float | None) -> str:
    if new is None or old is None or not old:
        return "—"
    pct = (new / old - 1) * 100
    return (f"{pct:+.1f}%" if abs(pct) < 1 else f"{pct:+.0f}%").replace("-", "−")


def _money(v: float | None, digits: int = 5) -> str:
    return "—" if v is None else f"${v:.{digits}f}"


def _rate(v: float | None) -> str:
    """Error rate as a percentage; two decimals below 1% so 1 in 400 reads 0.25%, not 0.2%."""
    if v is None:
        return "—"
    return f"{v * 100:.2f}%" if v * 100 < 1 else f"{v * 100:.1f}%"


def _num(v: float | None, digits: int = 2) -> str:
    if v is None:
        return "—"
    return f"{v:,.{digits}f}"


def _pooled(cards: Mapping[str, Mapping[str, Any]], replicas: int) -> dict[str, Any] | None:
    if not cards:
        return None
    vals = list(cards.values())
    docs = sum(c["quality"]["documents"] for c in vals)
    ok = sum(c["quality"]["ok"] for c in vals)
    errors = sum(c["quality"]["errors"] for c in vals)
    wall = sum(c["time"]["wall_seconds"] or 0.0 for c in vals)
    busy = sum(c["cost"]["busy_gpu_usd"] or 0.0 for c in vals)
    tokens = sum(c["tokens"]["total"] or 0 for c in vals)
    reps = [r for c in vals for r in (c.get("engine_telemetry") or {}).get("replicas") or []]
    return {
        "wall": wall,
        "prompt": sum(c["tokens"]["prompt"] or 0 for c in vals),
        "completion": sum(c["tokens"]["completion"] or 0 for c in vals),
        "length_finishes": sum(r.get("length_finishes") or 0 for r in reps),
        "preemptions": sum(r.get("preemptions") or 0 for r in reps),
        "cells": len(vals),
        "documents": docs,
        "ok": ok,
        "errors": errors,
        "error_rate": errors / docs if docs else None,
        "busy_usd": busy or None,
        "usd_per_document": busy / docs if busy and docs else None,
        "usd_per_mtok": busy / tokens * 1e6 if busy and tokens else None,
        "tps_per_gpu": tokens / wall / replicas if wall and tokens else None,
        "docs_per_minute": docs / wall * 60.0 if wall and docs else None,
    }


def _pooled_four(cards: Mapping[str, Mapping[str, Any]], replicas: int) -> dict[str, Any] | None:
    """Pooled metrics over the four specialists whose settings never changed (merger excluded)."""
    four = {k: v for k, v in cards.items() if k != "merger_agreement"}
    return _pooled(four, replicas) if len(four) == 4 else None


def _score(card: Mapping[str, Any] | None, *, mark: str = "") -> str:
    if not card:
        return PENDING + mark
    q = card["quality"]
    clause = q.get("clause") or {}
    if clause.get("kind") == "maud":
        return f"{clause.get('accuracy', 0):.3f} ({clause.get('coverage', 0) * 100:.0f}%){mark}"
    if clause.get("kind") == "cuad" and clause.get("f1") is not None:
        return f"{q['overall_mean']:.3f} ({clause['f1']:.3f}){mark}"
    return f"{q['overall_mean']:.3f}{mark}"


def _joined(values: list[str]) -> str:
    return " · ".join(values)


# ── findings (computed from the cards present) ───────────────────────────────


def _range(values: list[float], fmt: str = "{:.2f}") -> str:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return "—"
    lo, hi = fmt.format(vals[0]), fmt.format(vals[-1])
    return lo if lo == hi else f"{lo}–{hi}"


def _paired(a: Mapping[str, Any] | None, b: Mapping[str, Any] | None) -> dict[str, float] | None:
    """Per-document score change b − a over documents both cells scored, with a 95% t interval."""
    if not a or not b:
        return None
    ad = {d["item_id"]: d for d in a["documents"] if d["ok"] and d["score"] is not None}
    diffs = [d["score"] - ad[d["item_id"]]["score"] for d in b["documents"]
             if d["ok"] and d["score"] is not None and d["item_id"] in ad]
    if len(diffs) < 2:
        return None
    from statistics import mean, stdev

    from scipy.stats import t

    m = mean(diffs)
    half = t.ppf(0.975, len(diffs) - 1) * stdev(diffs) / len(diffs) ** 0.5
    return {
        "n": len(diffs), "mean": m, "lo": m - half, "hi": m + half, "half": half,
        "better": sum(x > 1e-9 for x in diffs), "worse": sum(x < -1e-9 for x in diffs),
        "same": sum(abs(x) <= 1e-9 for x in diffs),
    }


def _signed(v: float, digits: int = 3) -> str:
    return f"{v:+.{digits}f}".replace("-", "−")


def _findings(present: list[Posture], cards: dict, pooled: dict) -> list[str]:
    out: list[str] = []
    by_key = {p.key: p for p in present}
    one50, two50, one20 = by_key.get("s39-1l4-n50"), by_key.get("s37-2l4-n50"), by_key.get("s37-1l4-n20")

    # 1. scale-out economics: prefer the matched-sample pair.
    base = one50 or one20
    if base and two50:
        a, b = pooled[base.key], pooled[two50.key]
        lat, ttft_a, ttft_b = [], [], []
        for folder in _ORDER:
            ca, cb = cards[base.key].get(folder), cards[two50.key].get(folder)
            if ca and cb and ca["latency"]["p50"]:
                lat.append(cb["latency"]["p50"] / ca["latency"]["p50"])
            if ca and cb:
                ttft_a.append(_replica_weighted(ca, "ttft_mean_seconds"))
                ttft_b.append(_replica_weighted(cb, "ttft_mean_seconds"))
        basis = (
            f"identical {b['documents']} documents, {base.exp_label} · {base.label} vs {two50.exp_label} · {two50.label}"
            if base is one50
            else f"{base.label} vs {two50.label}; sample sizes differ, Experiment 2 pending"
        )
        ca, cb = a["usd_per_document"], b["usd_per_document"]
        parity = bool(ca and cb and abs(cb / ca - 1) < PARITY)
        dpm = _pct_change(b["docs_per_minute"], a["docs_per_minute"])
        if parity:
            head = (
                f"**Scaling out to {two50.replicas}×L4 at C{two50.concurrency} raises throughput by {dpm.lstrip('+')} "
                "at unchanged cost per document**"
            )
        else:
            cheaper = f"{two50.replicas}×L4 at C{two50.concurrency}" if (cb or 0) < (ca or 0) else f"{base.replicas}×L4 at C{base.concurrency}"
            head = f"**{cheaper} is the more cost-efficient posture**"
        per_a, per_b = base.concurrency // base.replicas, two50.concurrency // two50.replicas
        ttft = (
            f", and mean time to first token rises from {_range(ttft_a, '{:.1f}')} s to {_range(ttft_b, '{:.1f}')} s"
            if all(v is not None for v in ttft_a + ttft_b) and ttft_a
            else ""
        )
        out.append(
            f"{head} ({basis}). Cost per document changes by {_pct_change(cb, ca)} and tokens per second per GPU "
            f"by {_pct_change(b['tps_per_gpu'], a['tps_per_gpu'])}"
            + (", so per-GPU efficiency holds and capacity grows with GPU count" if parity else "")
            + f". GPU count and client concurrency changed together ({per_a} → about {per_b} in-flight requests per "
            "replica), so this comparison does not separate their effects. Median per-document latency rises "
            f"{_range(lat, '{:.1f}')}×{ttft}, consistent with requests queueing at the higher per-replica load."
        )

    # 1b. Experiment 4 (SAND-40) n = 100 on the four unchanged specialists (merger † excluded).
    s40 = by_key.get("s40-2l4")
    if s40 and two50:
        a, b = _pooled_four(cards[two50.key], two50.replicas), _pooled_four(cards[s40.key], s40.replicas)
        if a and b:
            out.append(
                f"**Running n = 100 per specialist instead of n = 50 lowers GPU cost per document by "
                f"{_pct_change(b['usd_per_document'], a['usd_per_document']).lstrip('−')} on the four unchanged "
                f"specialists** ({two50.exp_label} · {two50.label} vs {s40.exp_label} · {s40.label}, merger excluded; each "
                f"n = 100 draw contains the n = 50 documents). Tokens per second per GPU change by "
                f"{_pct_change(b['tps_per_gpu'], a['tps_per_gpu'])} and documents per minute by "
                f"{_pct_change(b['docs_per_minute'], a['docs_per_minute'])}. A likely contributor is that each "
                "cell's fixed ramp-up and drain time is spread over twice as many documents; the cards do not "
                f"measure that split directly. {b['errors']} of {b['documents']} documents failed "
                f"({_rate(b['error_rate'])})."
            )

    # 2. quality stability across postures, on matched documents first.
    deltas, cuad = [], []
    for folder in _SUITE_FOLDERS:
        vals = [cards[p.key][folder]["quality"]["overall_mean"] for p in present if folder in cards[p.key]]
        if len(vals) > 1:
            deltas.append(max(vals) - min(vals))
    kvals = [cards[p.key]["contracts"]["quality"]["overall_mean"] for p in present if "contracts" in cards[p.key]]
    if len(kvals) > 1:
        cuad.append(max(kvals) - min(kvals))
    pairs_a = [_paired(cards[one50.key].get(f), cards[two50.key].get(f)) for f in _ORDER] if one50 and two50 else []
    pairs_b = (
        [_paired(cards[two50.key].get(f), cards[s40.key].get(f)) for f in _ORDER if f != "merger_agreement"]
        if s40 and two50 else []
    )
    pairs_a, pairs_b = [x for x in pairs_a if x], [x for x in pairs_b if x]
    if pairs_a:
        def span(px: list[dict]) -> str:
            lo, hi = min(x["mean"] for x in px), max(x["mean"] for x in px)
            return f"{_signed(lo)} to {_signed(hi)}"

        allp = pairs_a + pairs_b
        zero = all(x["lo"] <= 0 <= x["hi"] for x in allp)
        widest = max(allp, key=lambda x: x["half"])
        text = (
            "**Serving posture has no detectable effect on extraction quality.** "
            if zero
            else "**Serving posture moves extraction quality for at least one specialist.** "
        )
        text += (
            f"On the {sum(x['n'] for x in pairs_a)} documents scored successfully under both {one50.exp_label} · "
            f"{one50.label} and {two50.exp_label} · {two50.label}, the mean per-document score change for each "
            f"specialist ranges from {span(pairs_a)}"
        )
        if pairs_b:
            text += (
                f"; on the {sum(x['n'] for x in pairs_b)} documents the four unchanged specialists share between "
                f"{two50.exp_label} (n = 50) and {s40.exp_label} (n = 100), it ranges from {span(pairs_b)}"
            )
        text += (
            (". Every 95% confidence interval includes zero" if zero else ". Not every 95% confidence interval includes zero")
            + f"; the widest is ±{widest['half']:.3f}, so smaller effects cannot be ruled out. "
            f"Unmatched means across all postures differ by at most {max(deltas):.3f} for field scores"
            + (f" and {max(cuad):.3f} for contracts CUAD F1" if cuad else "")
            + ". Contracts and merger sample at temperature 0.7, so their outputs vary from run to run."
        )
        out.append(text)
    elif deltas:
        out.append(
            f"**Extraction quality is stable across serving postures.** Field scores differ by at most "
            f"{max(deltas):.3f} across postures; no matched-sample pair is available yet."
        )

    # 3. error ledger.
    kinds: dict[str, int] = {}
    per_class: list[str] = []
    for folder in _ORDER:
        parts = []
        for p in present:
            card = cards[p.key].get(folder)
            if not card:
                continue
            for k, v in (card["quality"].get("error_kinds") or {}).items():
                kinds[k] = kinds.get(k, 0) + int(v)
            if card["quality"]["errors"]:
                parts.append(f"{card['quality']['errors']}/{card['n']}")
        if parts:
            per_class.append(f"{_LABEL[folder].lower()} {', '.join(parts)}")
    total = sum(kinds.values())
    if total:
        only_length = set(kinds) == {"LengthFinishReasonError"}
        what = (
            "output-cap truncations: the model reached the 8,192-token limit before closing the JSON"
            if only_length
            else "; ".join(f"{k} × {v}" for k, v in sorted(kinds.items()))
        )
        out.append(
            f"**All {total} errors are {what}** ({'; '.join(per_class)}; cells with errors, in posture order). No errors arose from "
            "infrastructure, authentication or JSON parsing. Failed documents are excluded from scores and "
            "token totals; the GPU time they used is included in cost."
        )

    # 4. merger: the frozen-settings gap, then what the † settings recover and what they cost.
    m = [
        cards[p.key]["merger_agreement"]["quality"].get("clause") or {}
        for p in present
        if "merger_agreement" in cards[p.key] and p.key != "s40-2l4"
    ]
    after = (cards.get("s40-2l4") or {}).get("merger_agreement")
    if m:
        size = ""
        chars = sorted(d["input_chars"] for d in (after or {}).get("documents") or [] if d.get("input_chars"))
        if chars:
            med = chars[len(chars) // 2] if len(chars) % 2 else (chars[len(chars) // 2 - 1] + chars[len(chars) // 2]) / 2
            size = (
                f"The median agreement is {med:,.0f} characters, about {med / 30000:.0f}× the 30,000-character "
                "input cap (head plus tail), so the frozen settings read under a tenth of a typical agreement. "
                if med / 30000 >= 10
                else f"The median agreement is {med:,.0f} characters against a 30,000-character input cap (head plus tail). "
            )
        out.append(
            "**Merger agreements are the principal quality gap on the frozen settings.** " + size
            + f"The model answers only {_range([c.get('coverage') for c in m], '{:.0%}')} of labeled MAUD "
            f"questions, with {_range([c.get('precision_answered') for c in m], '{:.0%}')} precision on those "
            "answered, and serving posture does not change that."
        )
    before = (cards.get("s37-2l4-n50") or {}).get("merger_agreement")
    if before and after:
        cb, ca = before["quality"].get("clause") or {}, after["quality"].get("clause") or {}
        pair = _paired(before, after)
        reps = (after.get("engine_telemetry") or {}).get("replicas") or []
        capped = sum(r.get("length_finishes") or 0 for r in reps)
        pre = sum(r.get("preemptions") or 0 for r in reps)
        requests = sum(r.get("requests") or 0 for r in reps)

        def per_ok_prompt(card: Mapping[str, Any]) -> float:
            return (card["tokens"]["prompt"] or 0) / max(1, card["quality"]["ok"])

        cost_b, cost_a = before["cost"]["usd_per_ok_document"], after["cost"]["usd_per_ok_document"]
        acc_b, acc_a = cb.get("accuracy") or 0.0, ca.get("accuracy") or 0.0
        text = (
            f"**The † merger settings raise MAUD accuracy from {acc_b:.3f} to {acc_a:.3f} on the same "
            f"{after['n']} agreements.** Question coverage rises {cb.get('coverage', 0):.0%} → "
            f"{ca.get('coverage', 0):.0%} and precision on answered questions {cb.get('precision_answered', 0):.0%} → "
            f"{ca.get('precision_answered', 0):.0%}; {after['quality']['ok']} of {after['n']} agreements return a "
            f"result ({before['quality']['ok']} before). "
        )
        if pair:
            text += (
                f"On the {pair['n']} agreements scored under both, the mean per-agreement score changes by "
                f"{_signed(pair['mean'])} (95% CI {_signed(pair['lo'])} to {_signed(pair['hi'])}; {pair['better']} "
                f"better, {pair['worse']} worse, {pair['same']} unchanged). This is the like-for-like figure: the "
                f"pooled accuracies use different denominators ({cb.get('questions')} vs {ca.get('questions')} "
                "labeled questions) because the frozen settings lost agreements to the output cap. "
            )
        text += (
            "The † cell changes input, prompt, sampling, output cap and re-sampling together, so this run does "
            "not attribute the gain to any one of them. The cost: prompt tokens per agreement rise "
            f"{per_ok_prompt(after) / max(per_ok_prompt(before), 1.0):.0f}×, GPU cost per agreement "
            f"${cost_b:.4f} → ${cost_a:.4f} ({cost_a / cost_b:.1f}×) and median latency "
            f"{before['latency']['p50']:.0f} s → {after['latency']['p50']:,.0f} s. vLLM recorded {capped:.0f} "
            f"length-capped finishes over {requests:,.0f} requests and {pre:.0f} preemptions; the preemptions "
            "indicate KV-cache pressure from ~50,000-character sections at C32. Those two are the first places "
            "to look for cost and latency savings."
        )
        out.append(text)

    # 4c. token composition: fixed instruction overhead dominates the short classes.
    shares = []
    for folder in ("correspondence", "insurance_claims"):
        card = (cards.get("s40-2l4") or {}).get(folder)
        sp = (card or {}).get("tokens", {}).get("split") if card else None
        if sp:
            per = sp["per_document"]
            shares.append((folder, per["instruction"] / (per["instruction"] + per["document"] + per["completion"]),
                           sp["instruction_per_call"], _replica_weighted(card, "prefix_cache_hit_rate")))
    if len(shares) == 2:
        hits = [s[3] for s in shares if s[3] is not None]
        out.append(
            "**Fixed instructions, not document text, account for most tokens in the short classes.** By the "
            f"estimate in *Token composition*, the instructions and template are {shares[0][1]:.0%} of a "
            f"correspondence document's tokens and {shares[1][1]:.0%} of an insurance claim's "
            f"({shares[0][2]:,.0f} and {shares[1][2]:,.0f} tokens per call). Prefix caching already reuses part "
            "of that prefix"
            + (f" (hit rate {_range(hits, '{:.0%}')} in Experiment 4)" if hits else "")
            + ". A shorter template, or several short documents per call, would cut these classes' token cost; "
            "neither has been tested."
        )

    # 5. correspondence.
    c = [cards[p.key]["correspondence"]["quality"] for p in present if "correspondence" in cards[p.key]]
    if c:
        out.append(
            f"**Correspondence scores are low and widely spread** (mean {_range([q['overall_mean'] for q in c])}, "
            f"standard deviation {_range([q['overall_sd'] for q in c])}, across all postures). The score does "
            "not move with serving posture, so the cause most likely sits in the prompt, the ground truth or the "
            "scorer. It has not been diagnosed yet and is the next item to review."
        )

    # 6. schema conformance.
    ins = [cards[p.key]["insurance_claims"]["quality"]["schema_valid_rate"] for p in present if "insurance_claims" in cards[p.key]]
    corp = [cards[p.key]["corporate_records"]["quality"]["schema_valid_rate"] for p in present if "corporate_records" in cards[p.key]]
    ins_score = [cards[p.key]["insurance_claims"]["quality"]["overall_mean"] for p in present if "insurance_claims" in cards[p.key]]
    if ins and min(ins) < 0.9:
        out.append(
            f"**Most insurance-claims outputs fail strict schema validation** (schema-valid rate {_range(ins)}; "
            f"corporate records {_range(corp)}; contracts, merger and correspondence 1.00), although insurance "
            f"claims has the highest field score of the field-scored classes ({_range(ins_score)}). A "
            f"strict-schema consumer would reject {1 - max(ins):.0%}–{1 - min(ins):.0%} of these outputs. "
            "Contracts and merger request structured output against their JSON schema (LangChain "
            "`with_structured_output`) and validate at 1.00; moving insurance claims to the same call mode is the "
            "likely fix and has not been tested."
        )
    return out


# ── detail sections ──────────────────────────────────────────────────────────


def _f(v: float | None, digits: int = 2, suffix: str = "") -> str:
    return "—" if v is None else f"{v:,.{digits}f}{suffix}"


def _replica_sum(card: Mapping[str, Any], key: str) -> float | None:
    reps = (card.get("engine_telemetry") or {}).get("replicas") or []
    vals = [r.get(key) for r in reps if r.get(key) is not None]
    return sum(vals) if vals else None


def _replica_weighted(card: Mapping[str, Any], key: str) -> float | None:
    """Request-weighted mean of a per-replica rate (prefix-cache hit rate, mean TTFT)."""
    reps = [r for r in (card.get("engine_telemetry") or {}).get("replicas") or [] if r.get(key) is not None]
    weight = sum(r.get("requests") or 0 for r in reps)
    if not reps or not weight:
        return None
    return sum(r[key] * (r.get("requests") or 0) for r in reps) / weight


def _errors_text(q: Mapping[str, Any]) -> str:
    kinds = q.get("error_kinds") or {}
    if not kinds:
        return "0"
    short = {"LengthFinishReasonError": "length"}
    return f"{q['errors']} (" + ", ".join(f"{short.get(k, k)} {v}" for k, v in sorted(kinds.items())) + ")"


def _detail_sections(present: list[Posture], cards: dict, data: Mapping[str, Any] | None = None) -> list[str]:
    out = [
        "## Per-cell detail",
        "",
        "One table per posture. Latency, tokens per document and completion p95 / max cover successful "
        "documents (the run store records no token counts for a failed document); busy GPU $ is the cell's "
        "busy wall × GPUs × $0.80 per GPU-hour and includes the time failed documents used.",
        "",
    ]
    for p in present:
        out += [
            f"### {p.exp_label} · {p.label}",
            "",
            "| Specialist | ok / n | Errors | Schema-valid | Score (sd) | p50 / p95 latency (s) | Tokens per doc "
            "| Completion p95 / max | Wall (s) | Busy GPU $ | $ per ok doc | $ per 1M tokens | Tokens/s/GPU |",
            "| --- | :---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for folder in _ORDER:
            c = cards[p.key].get(folder)
            if not c:
                out.append(f"| {_LABEL[folder]} | {PENDING} |" + " |" * 11)
                continue
            q, lat, tok, cost = c["quality"], c["latency"], c["tokens"], c["cost"]
            score = q["overall_mean"]
            clause = q.get("clause") or {}
            if clause.get("kind") == "maud":
                score = clause.get("accuracy")
            out.append(
                f"| {_LABEL[folder]} | {q['ok']}/{c['n']} | {_errors_text(q)} | {_f(q['schema_valid_rate'])} "
                f"| {_f(score, 3)} ({_f(q['overall_sd'], 3)}) | {_f(lat['p50'], 1)} / {_f(lat['p95'], 1)} "
                f"| {_f(tok['per_document'], 0)} | {_f(tok['completion_p95'], 0)} / {_f(tok['completion_max'], 0)} "
                f"| {_f(c['time']['wall_seconds'], 1)} | {_money(cost['busy_gpu_usd'], 4)} "
                f"| {_money(cost['usd_per_ok_document'])} | {_money(cost['usd_per_million_tokens'], 3)} "
                f"| {_f(c['throughput']['tokens_per_second_per_gpu'], 0)} |"
            )
        out.append("")
        if data is not None:
            out += _record_figures(data, f"posture-{p.key}")
    out += ["Merger score is MAUD micro-accuracy; its sd is over per-document scores.", ""]

    # clause scoring
    out += [
        "## Clause scoring detail",
        "",
        "| Posture | Contracts: CUAD-labeled docs | Precision | Recall | Micro F1 | Labeled-doc mean F1 "
        "| Value accuracy | Merger: MAUD questions | Answered (coverage) | Correct | Accuracy | Precision on answered |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for p in present:
        k = cards[p.key].get("contracts")
        m = cards[p.key].get("merger_agreement")
        kc = (k["quality"].get("clause") or {}) if k else {}
        mc = (m["quality"].get("clause") or {}) if m else {}
        val = (
            f"{kc['value_correct']}/{kc['value_checked']} ({kc['value_correct'] / kc['value_checked']:.0%})"
            if kc.get("value_checked")
            else "—"
        )
        out.append(
            f"| {p.exp_label} · {p.label} | {kc.get('docs_labeled', '—')} of {k['quality']['ok'] if k else '—'} ok "
            f"| {_f(kc.get('precision'), 3)} | {_f(kc.get('recall'), 3)} | {_f(kc.get('f1'), 3)} "
            f"| {_f(k['quality']['overall_mean'] if k else None, 3)} | {val} "
            f"| {mc.get('questions', '—')} | {mc.get('answered', '—')} ({_f((mc.get('coverage') or 0) * 100, 0)}%) "
            f"| {mc.get('correct', '—')} | {_f(mc.get('accuracy'), 3)} | {_f(mc.get('precision_answered'), 3)} |"
        )
    out += [
        "",
        "Clause counts cover successful documents only, so two postures on the same draw can differ slightly "
        "in labeled documents and MAUD questions when different documents hit the output cap.",
        "",
    ]

    # engine telemetry
    out += [
        "## Engine telemetry (vLLM /metrics, this run's delta)",
        "",
        "Requests, length-capped finishes and preemptions are summed over replicas; prefix-cache hit rate and "
        "mean time to first token are request-weighted across replicas. A chunked or re-sampled document "
        "issues more than one request.",
        "",
        "| Specialist | Requests | Length-capped finishes | Preemptions | Prefix-cache hit rate | Mean TTFT (s) |",
        "| --- | :---: | :---: | :---: | :---: | :---: |",
    ]
    for folder in _ORDER:
        per = [cards[p.key].get(folder) for p in present]

        def col(fn, per=per):
            return _joined([fn(c) if c else PENDING for c in per])

        out.append(
            f"| {_LABEL[folder]} "
            f"| {col(lambda c: _f(_replica_sum(c, 'requests'), 0))} "
            f"| {col(lambda c: _f(_replica_sum(c, 'length_finishes'), 0))} "
            f"| {col(lambda c: _f(_replica_sum(c, 'preemptions'), 0))} "
            f"| {col(lambda c: _f((_replica_weighted(c, 'prefix_cache_hit_rate') or 0) * 100, 0, '%'))} "
            f"| {col(lambda c: _f(_replica_weighted(c, 'ttft_mean_seconds'), 1))} |"
        )
    out += ["", f"Columns follow the posture order ({' · '.join(p.label for p in present)}).", ""]

    # conditions
    out += [
        "## Run conditions by specialist",
        "",
        "Identical across the postures above unless a cell lists more than one value.",
        "",
        "| Specialist | Prompt | Input cap (chars) | Output cap (tokens) | Temperature | Retries |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for folder in _ORDER:
        conds = [cards[p.key][folder]["conditions"] for p in present if folder in cards[p.key]]
        if not conds:
            continue

        def uniq(key, conds=conds):
            vals = []
            for c in conds:
                if c.get(key) not in vals:
                    vals.append(c.get(key))
            return " / ".join(f"{v:,}" if isinstance(v, int) and not isinstance(v, bool) else str(v) for v in vals)

        out.append(
            f"| {_LABEL[folder]} | `{uniq('prompt')}` | {uniq('max_input_chars')} | {uniq('max_tokens')} "
            f"| {uniq('temperature')} | {uniq('max_retries')} |"
        )
    out.append("")
    return out


_SETTINGS_RUNS = (
    ("Experiments 1–3 merger", "grid-50-merger-specialist-awq-2l4"),
    ("Experiment 4 merger †", "sand40-50-merger-specialist-awq-2l4"),
)


def _input_text(row: Mapping[str, Any]) -> str:
    if row.get("chunk_chars"):
        from mailroom_sandbox.eval.agents import chunk_window

        window, overlap = chunk_window(
            int(row["max_input_chars"]), int(row["chunk_chars"]), int(row.get("overlap_chars") or 0)
        )
        return (
            f"whole agreement, chunked: {window:,}-char windows + {overlap:,}-char overlap "
            f"(≤ {int(row['max_input_chars']):,} chars per call), merged"
        )
    return f"head + tail, {int(row['max_input_chars']):,} chars (rest of the agreement unread)"


def _sampling_text(row: Mapping[str, Any]) -> str:
    parts = [f"temperature {row.get('temperature', 0.1)}"]
    for key in ("top_p", "top_k", "presence_penalty"):
        if row.get(key) is not None:
            parts.append(f"{key} {row[key]}")
    if len(parts) == 1:
        parts.append("other sampling at vLLM defaults")
    return ", ".join(parts)


def _maud_result(card: Mapping[str, Any] | None) -> str:
    if not card:
        return PENDING
    c = card["quality"].get("clause") or {}
    return (
        f"MAUD accuracy {c.get('accuracy', 0):.3f}, coverage {c.get('coverage', 0):.0%}, "
        f"{card['quality']['ok']}/{card['n']} ok, ${card['cost']['usd_per_ok_document']:.4f} per agreement"
    )


def _matched_merger(
    before: Mapping[str, Any] | None, after: Mapping[str, Any] | None
) -> tuple[float, int, int, int] | None:
    """Mean per-agreement score change, n, better, worse over agreements both cells scored."""
    if not before or not after:
        return None
    bd = {d["item_id"]: d for d in before["documents"]}
    both = [
        (d["score"], bd[d["item_id"]]["score"])
        for d in after["documents"]
        if d["item_id"] in bd
        and d["ok"]
        and bd[d["item_id"]]["ok"]
        and d["score"] is not None
        and bd[d["item_id"]]["score"] is not None
    ]
    if not both:
        return None
    delta = sum(a - b for a, b in both) / len(both)
    return delta, len(both), sum(a > b for a, b in both), sum(a < b for a, b in both)


def _scale_check_section(cards: dict) -> list[str]:
    """SAND-37 2×L4 n=50 vs SAND-40 n=100 on the four specialists whose settings never changed."""
    a = _pooled_four(cards.get("s37-2l4-n50") or {}, 2)
    b = _pooled_four(cards.get("s40-2l4") or {}, 2)
    if not a or not b:
        return []
    rows = (
        ("Documents ok / total", lambda q: f"{q['ok']} / {q['documents']}", None),
        ("Error rate", lambda q: _rate(q["error_rate"]), None),
        ("Throughput (documents per minute)", lambda q: _num(q["docs_per_minute"]), "docs_per_minute"),
        ("Throughput (tokens per second per GPU)", lambda q: _num(q["tps_per_gpu"], 0), "tps_per_gpu"),
        ("GPU cost per document", lambda q: _money(q["usd_per_document"]), "usd_per_document"),
        ("GPU cost per 1M tokens", lambda q: _money(q["usd_per_mtok"], 3), "usd_per_mtok"),
        ("Length-capped finishes (vLLM)", lambda q: f"{q['length_finishes']:.0f}", None),
    )
    out = [
        "### Scale check: four unchanged specialists (merger excluded)",
        "",
        "| Metric | Experiment 3 · 2×L4 C32 n=50 | Experiment 4 · 2×L4 C32 n=100 | Change |",
        "| --- | ---: | ---: | ---: |",
    ]
    for label, fn, key in rows:
        out.append(f"| {label} | {fn(a)} | {fn(b)} | {_pct_change(b[key], a[key]) if key else '—'} |")
    out.append("")
    return out


def _token_section(cards: dict) -> list[str]:
    """Per-document token composition: instructions + template, document text, output."""
    rows = []
    s40, s37 = cards.get("s40-2l4") or {}, cards.get("s37-2l4-n50") or {}
    for folder in _ORDER:
        if folder == "merger_agreement":
            for label, card in (("Merger Agreements (frozen, Experiment 3)", s37.get(folder)),
                                ("Merger Agreements † (Experiment 4)", s40.get(folder))):
                if card:
                    rows.append((label, card))
        else:
            card = s40.get(folder) or s37.get(folder)
            if card:
                rows.append((_LABEL[folder], card))
    rows = [(label, card) for label, card in rows if (card.get("tokens") or {}).get("split")]
    if not rows:
        return []
    out = [
        "## Token composition",
        "",
        "Prompt tokens split into the instructions and template (system prompt, schema, field list; resent "
        "on every model call) and the document text the model reads, plus the output. The split is fitted per "
        "run across documents of different lengths (`prompt = I × calls + characters ÷ r`); where every "
        "document is cut to the same cap, or a chunked run's re-samples blur the call count, document tokens "
        "use 4.5 characters per token (the contracts fits measure 4.4–4.6) and instructions are the remainder.",
        "",
        "| Specialist | Instructions + template | Document text | Output | Tokens per document | Calls per document | Instructions per call | Basis |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for label, card in rows:
        sp = card["tokens"]["split"]
        per = sp["per_document"]
        total = per["instruction"] + per["document"] + per["completion"]
        basis = f"fit, {sp['chars_per_token']:.2f} chars/token" if sp["method"] == "fit" else "4.5 chars/token"
        out.append(
            f"| {label} | {per['instruction']:,.0f} ({per['instruction'] / total:.0%}) | "
            f"{per['document']:,.0f} ({per['document'] / total:.0%}) | {per['completion']:,.0f} ({per['completion'] / total:.0%}) | "
            f"{total:,.0f} | {sp['calls'] / sp['documents']:.1f} | {sp['instruction_per_call']:,.0f} | {basis} |"
        )
    out.append("")
    return out


def _merger_settings_section(cards: dict) -> list[str]:
    """What the † merger cell changes, row by row, and the measured effect once it exists."""
    from mailroom_sandbox.job.specialist_posture import posture_for_run

    rows = [(label, posture_for_run(rid) or {}) for label, rid in _SETTINGS_RUNS]
    if not all(r for _, r in rows):
        return []
    (base_label, base), (opt_label, opt) = rows
    table = (
        ("Serving window", lambda r: f"{int(r['max_model_len']):,} tokens"),
        ("Input", _input_text),
        ("Prompt", lambda r: f"`{r['prompt_file']}`"),
        ("Sampling", _sampling_text),
        ("Output cap", lambda r: f"{int(r['max_tokens']):,} tokens"),
        ("Re-sample on a length-capped output", lambda r: str(r["length_retries"]) if r.get("length_retries") else "none"),
    )
    out = [
        "## Merger † settings",
        "",
        "Same 50 agreements (seed 42) and 2×L4 engine as Experiment 3; only the settings below change.",
        "",
        f"| Setting | {base_label} | {opt_label} |",
        "| --- | --- | --- |",
    ]
    for label, fn in table:
        a, b = fn(base), fn(opt)
        if a != b:
            out.append(f"| {label} | {a} | {b} |")
    before = (cards.get("s37-2l4-n50") or {}).get("merger_agreement")
    after = (cards.get("s40-2l4") or {}).get("merger_agreement")
    out.append(f"| Result | {_maud_result(before)} | {_maud_result(after)} |")
    matched = _matched_merger(before, after)
    if matched:
        delta, n, better, worse = matched
        out.append(
            f"| Matched agreements | — | {delta:+.3f} mean per-agreement score over {n} agreements "
            f"({better} better / {worse} worse) |"
        )
    out.append("")
    return out


def _executive_findings(present: list[Posture], cards: dict, pooled: dict) -> list[str]:
    """Vital bullets for the two-page master; the full analysis lives in the appendix."""
    out: list[str] = []
    by_key = {p.key: p for p in present}
    one50, two50, one20 = by_key.get("s39-1l4-n50"), by_key.get("s37-2l4-n50"), by_key.get("s37-1l4-n20")
    s40 = by_key.get("s40-2l4")
    base = one50 or one20
    if base and two50:
        a, b = pooled[base.key], pooled[two50.key]
        lat = []
        for folder in _ORDER:
            ca, cb = cards[base.key].get(folder), cards[two50.key].get(folder)
            if ca and cb and ca["latency"]["p50"]:
                lat.append(cb["latency"]["p50"] / ca["latency"]["p50"])
        basis = (
            f"identical {b['documents']} documents, {base.exp_label} → {two50.exp_label}"
            if base is one50
            else f"sample sizes differ, Experiment 2 pending"
        )
        out.append(
            f"**2×L4 at C32 raises throughput {_pct_change(b['docs_per_minute'], a['docs_per_minute'])} at "
            f"{_pct_change(b['usd_per_document'], a['usd_per_document'])} cost per document** ({basis}); "
            f"median latency rises ×{_range(lat, '{:.1f}')}. GPU count and client concurrency changed "
            "together, so this does not separate their effects."
        )
    if s40 and two50:
        a, b = _pooled_four(cards[two50.key], two50.replicas), _pooled_four(cards[s40.key], s40.replicas)
        if a and b:
            out.append(
                f"**Larger runs cost less per document.** Running n = 100 per specialist instead of n = 50 cuts GPU cost "
                f"per document {_pct_change(b['usd_per_document'], a['usd_per_document']).lstrip('−')} on the four "
                f"unchanged specialists ({two50.exp_label} → {s40.exp_label}); {b['errors']} of {b['documents']} failed "
                f"({_rate(b['error_rate'])})."
            )
    before = (cards.get("s37-2l4-n50") or {}).get("merger_agreement")
    after = (cards.get("s40-2l4") or {}).get("merger_agreement")
    frozen = [
        cards[p.key]["merger_agreement"]["quality"].get("clause") or {}
        for p in present
        if "merger_agreement" in cards[p.key] and p.key != "s40-2l4"
    ]
    if before and after:
        cb, ca = before["quality"].get("clause") or {}, after["quality"].get("clause") or {}
        cost_x = after["cost"]["usd_per_ok_document"] / before["cost"]["usd_per_ok_document"]
        out.append(
            f"**Merger is the quality gap; the † settings narrow it.** They raise MAUD "
            f"accuracy {cb.get('accuracy') or 0:.3f} → {ca.get('accuracy') or 0:.3f} and coverage "
            f"{cb.get('coverage', 0):.0%} → {ca.get('coverage', 0):.0%} on the same {after['n']} agreements "
            "(Experiment 3 → Experiment 4), "
            f"at {cost_x:.1f}× the GPU cost per agreement."
        )
    elif frozen:
        out.append(
            f"**Merger is the quality gap.** Frozen settings answer only "
            f"{_range([c.get('coverage') for c in frozen], '{:.0%}')} of labeled MAUD questions because agreements "
            "exceed the 30,000-char input window."
        )
    return out


EXECUTIVE_POOLED_ROWS = (
    ("Error rate", lambda q: _rate(q["error_rate"])),
    ("Documents per minute", lambda q: _num(q["docs_per_minute"])),
    ("Tokens per second per GPU", lambda q: _num(q["tps_per_gpu"], 0)),
    ("GPU cost per document", lambda q: _money(q["usd_per_document"])),
)


def render_master_md(data: Mapping[str, Any]) -> str:
    """Executive card: key findings first, then postures, pooled efficiency, scorecard, merger † settings, cost."""
    cards: dict[str, dict[str, Any]] = data["cards"]
    metered: Mapping[str, Any] = data.get("metered") or {}
    present = [p for p in POSTURES if cards[p.key]]
    pooled = {p.key: _pooled(cards[p.key], p.replicas) for p in POSTURES}
    first = next((c for p in present for c in cards[p.key].values()), None)

    lines = ["# L4 Specialist Grid (Experiments 1–4): Results and Cost Summary", "", "## Key findings", ""]
    key = _executive_findings(present, cards, pooled)
    lines += [f"{i}. {text}" for i, text in enumerate(key, 1)] or ["No cells reported yet."]
    lines.append("")
    if first:
        cond, ds = first["conditions"], first["conditions"]["dataset"]
        lines += [
            f"**Setup:** {cond['model']} on vLLM {cond['image_tag']}, NVIDIA {cond['gpu']} at "
            f"${cond['gpu_usd_per_hour']:.2f}/GPU-hr; `{ds['repo']}` @ `{ds['revision']}`, seed {ds['seed']}, "
            "smaller draws nested in larger ones. Frozen v1 prompts and an 8,192-token output cap except the "
            "† merger cell.",
            "",
        ]
    lines += [
        f"Method, detail tables and figures: [appendix](./{APPENDIX_STEM}.md).",
        "",
        "| Experiment | Posture | GPUs | Client concurrency | Documents per class | Status |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for p in POSTURES:
        status = f"{len(cards[p.key])} of 5 cells" if cards[p.key] else PENDING
        lines.append(
            f"| {p.exp_label} | {p.label} | {p.replicas} | {p.concurrency} | {p.documents} | {status} |"
        )
    lines.append("")

    heads = " | ".join(f"{p.exp_label} · {p.label}" for p in POSTURES)
    lines += [
        "## Serving efficiency (pooled across the five specialists)",
        "",
        f"| Metric | {heads} |",
        "| --- |" + " ---: |" * len(POSTURES),
    ]
    for label, fn in EXECUTIVE_POOLED_ROWS:
        vals = [fn(pooled[p.key]) if pooled[p.key] else PENDING for p in POSTURES]
        lines.append(f"| {label} | " + " | ".join(vals) + " |")
    if pooled.get("s40-2l4") and cards["s40-2l4"].get("merger_agreement"):
        lines += [
            "",
            "Experiment 4 includes the † merger cell's whole-agreement reads; the like-for-like check is in the "
            "appendix.",
        ]
    lines.append("")
    lines += _record_figures(data, "efficiency")
    if lines[-1] == "":
        lines.pop()
    lines += [
        "",
        "## Quality and cost by specialist",
        "",
        f"Cell order: {' · '.join(p.exp_label for p in POSTURES)}. Contracts: CUAD F1 (micro). "
        "Merger: MAUD accuracy (coverage), a different scale. † = optimized merger.",
        "",
        "| Specialist | Score | ok / n | p50 latency (s) | $ per ok document |",
        "| --- | :---: | :---: | :---: | :---: |",
    ]
    for folder in _ORDER:
        per = [cards[p.key].get(folder) for p in POSTURES]
        marks = ["†" if p.key == "s40-2l4" and folder == "merger_agreement" else "" for p in POSTURES]
        lines.append(
            f"| {_LABEL[folder]} | "
            + _joined([_score(c, mark=m) for c, m in zip(per, marks, strict=True)]) + " | "
            + _joined([f"{c['quality']['ok']}/{c['n']}" if c else PENDING for c in per]) + " | "
            + _joined([f"{c['latency']['p50']:.1f}" if c else PENDING for c in per]) + " | "
            + _joined([f"{c['cost']['usd_per_ok_document']:.5f}" if c else PENDING for c in per]) + " |"
        )
    lines.append("")
    merger = _merger_settings_section(cards)
    if merger:
        lines += merger + _record_figures(data, "merger")
    lines += ["## Cost", ""]
    lines += _cost_table(present, pooled, metered)
    unrecorded = [s for s in dict.fromkeys(p.study for p in present) if s not in metered]
    if unrecorded:
        lines.append(
            f"- **{' and '.join(_session_label(u, present) for u in unrecorded)} metered Modal total:** not yet recorded."
        )
    lines += [
        "- **Teardown** to zero warm containers is part of every posture's runbook; the metered totals come "
        "from its spend check.",
        "",
    ]
    return "\n".join(lines)


def _cost_table(present: list[Posture], pooled: Mapping[str, Any], metered: Mapping[str, Any]) -> list[str]:
    """Metered session spend per study, reconciled against the busy-window GPU cost of its cells."""
    studies = [s for s in dict.fromkeys(p.study for p in present) if isinstance(metered.get(s), Mapping)]
    if not studies:
        return []
    lines = [
        "Busy-window GPU = the cells' own GPU time (the efficiency table above). Metered = the study's whole "
        "Modal session (cold boots, gates, warm idle, teardown) from the billing report.",
        "",
        "| Session | Documents | Busy-window GPU | Metered session | Busy share | Metered per document | Billed |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    tot = {"docs": 0, "busy": 0.0, "metered": 0.0, "billed": 0.0}
    for study in studies:
        legs = [pooled[p.key] for p in present if p.study == study and pooled.get(p.key)]
        docs = sum(leg["documents"] for leg in legs)
        busy = sum(leg["busy_usd"] or 0.0 for leg in legs)
        rec = metered[study]
        m, b = float(rec.get("metered_usd", 0)), float(rec.get("billed_usd", 0))
        for k, v in (("docs", docs), ("busy", busy), ("metered", m), ("billed", b)):
            tot[k] += v
        lines.append(_cost_row(_session_label(study, present), docs, busy, m, b))
    if len(studies) > 1:
        lines.append(_cost_row("**Total**", tot["docs"], tot["busy"], tot["metered"], tot["billed"]))
    lines.append("")
    return lines


def _session_label(study: str, postures: list[Posture]) -> str:
    """A billed Modal session named by the experiments it ran (one session can run several)."""
    exps = [str(p.experiment) for p in postures if p.study == study] or [
        str(p.experiment) for p in POSTURES if p.study == study
    ]
    return ("Experiments " + " + ".join(exps)) if len(exps) > 1 else f"Experiment {exps[0]}"


def _cost_row(label: str, docs: int, busy: float, metered: float, billed: float) -> str:
    share = f"{busy / metered:.0%}" if metered else "—"
    per_doc = f"${metered / docs:.5f}" if docs else "—"
    return f"| {label} | {docs:,} | ${busy:.2f} | ${metered:.2f} | {share} | {per_doc} | ${billed:.2f} |"


def render_appendix_md(data: Mapping[str, Any]) -> str:
    """Method detail the executive card omits: full findings, detail tables, run conditions, figures."""
    cards: dict[str, dict[str, Any]] = data["cards"]
    metered: Mapping[str, Any] = data.get("metered") or {}
    present = [p for p in POSTURES if cards[p.key]]
    pooled = {p.key: _pooled(cards[p.key], p.replicas) for p in POSTURES}
    first = next((c for p in present for c in cards[p.key].values()), None)

    lines = [
        "# Appendix: L4 Specialist Grid (Experiments 1–4)",
        "",
        f"Full findings, detail tables, method and figures behind the [executive summary](./{MASTER_STEM}.md). "
        "Regenerate both with `sandbox run card --master`.",
        "",
    ]
    if first:
        cond, ds = first["conditions"], first["conditions"]["dataset"]
        lines += [
            f"**Model:** {cond['model']} on vLLM {cond['image_tag']} · **GPU:** NVIDIA {cond['gpu']} at "
            f"${cond['gpu_usd_per_hour']:.2f} per GPU-hour  ",
            f"**Data:** public `{ds['repo']}` {ds['config']} @ `{ds['revision']}`, seed {ds['seed']}; "
            "the n = 20 draw is nested in the n = 50 draw, and every n = 50 posture scores the identical documents.  ",
            "**Engine (Experiments 1–3):** AWQ-Marlin, fp8 KV cache, CUDA graphs, prefix caching, thinking "
            "disabled, 8,192-token output cap, frozen prompts (see *Run conditions by specialist*); temperature 0.7 for contracts and merger, "
            "0.1 otherwise.  ",
            "**Experiment 4:** one 32K deploy of the same 2×L4 engine at C32. Four specialists run n = 100 on unchanged "
            "settings (the n = 50 draw nested inside); merger runs the same 50 agreements as Experiment 3 with the "
            "optimized settings marked † (see *Merger † settings* on the executive card).",
            "",
        ]
    lines += [
        "| Experiment | Posture | GPUs | Client concurrency | Documents per class | Status |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for p in POSTURES:
        status = f"{len(cards[p.key])} of 5 cells" if cards[p.key] else PENDING
        lines.append(
            f"| {p.exp_label} | {p.label} | {p.replicas} | {p.concurrency} | {p.documents} | {status} |"
        )
    lines += ["", "## Findings (full)", ""]
    findings = _findings(present, cards, pooled)
    lines += [f"{i}. {text}" for i, text in enumerate(findings, 1)] or ["No cells reported yet."]
    lines.append("")

    heads = " | ".join(f"{p.exp_label} · {p.label}" for p in POSTURES)
    lines += [
        "## Serving efficiency (pooled across the five specialists)",
        "",
        f"| Metric | {heads} |",
        "| --- |" + " ---: |" * len(POSTURES),
    ]
    rows = (
        ("Documents ok / total", lambda q: f"{q['ok']} / {q['documents']}"),
        ("Error rate", lambda q: _rate(q["error_rate"])),
        ("Throughput (documents per minute)", lambda q: _num(q["docs_per_minute"])),
        ("Throughput (tokens per second per GPU)", lambda q: _num(q["tps_per_gpu"], 0)),
        ("GPU cost per document", lambda q: _money(q["usd_per_document"])),
        ("GPU cost per 1M tokens", lambda q: _money(q["usd_per_mtok"], 3)),
        ("Busy-window GPU cost", lambda q: _money(q["busy_usd"], 3)),
        ("Busy wall time (sum of cells)", lambda q: f"{_num(q['wall'], 0)} s"),
        ("Tokens processed (prompt / completion)", lambda q: f"{q['prompt']:,} / {q['completion']:,}"),
        ("Length-capped finishes (vLLM)", lambda q: f"{q['length_finishes']:.0f}"),
        ("Preemptions (vLLM)", lambda q: f"{q['preemptions']:.0f}"),
    )
    for label, fn in rows:
        vals = [fn(pooled[p.key]) if pooled[p.key] else PENDING for p in POSTURES]
        lines.append(f"| {label} | " + " | ".join(vals) + " |")
    lines.append("")
    failed = sum(q["errors"] for q in pooled.values() if q)
    if failed:
        lines += [
            f"Token counts cover successful documents only. The {failed} failed documents (see *Findings*) are in "
            "busy time and cost but not in token totals, so tokens per second read slightly low and cost per 1M "
            "tokens slightly high for postures with failures.",
            "",
        ]
    lines += _record_figures(data, "appendix-serving")
    if pooled.get("s40-2l4") and cards["s40-2l4"].get("merger_agreement"):
        lines += [
            "The Experiment 4 column includes the † merger cell, which reads whole agreements and takes most of the "
            "posture's busy time, so its pooled throughput and cost per document are not a serving comparison. "
            "The like-for-like check is below.",
            "",
        ]
        lines += _scale_check_section(cards)

    lines += [
        "## Score definitions",
        "",
        "Field scores (insurance claims, corporate records, correspondence) are the mean suite extraction "
        "score against ground truth over successful documents. Contracts ground truth is CUAD clause labels, "
        "so its score is the per-document CUAD clause-presence F1 averaged over the successful documents "
        "that carry CUAD labels (see *Clause scoring detail* for counts), with the pooled micro F1 in "
        "parentheses; the committed run reports count unlabeled documents as 0 and so read lower. Merger is "
        "micro-accuracy over labeled MAUD questions, with question coverage in parentheses, a different "
        "scale from the field scores. † marks the optimized merger cell (settings on the executive card).",
        "",
    ]
    lines += _record_figures(data, "appendix-scores")
    lines += _token_section(cards)
    lines += _detail_sections(present, cards, data)
    lines += _figure_md(data, "comparison", "## Figures: posture comparison")
    lines += ["", "## Cost accounting and run integrity", ""]
    for study, rec in metered.items():
        if not isinstance(rec, Mapping):
            continue
        note = f" {rec['note']}" if rec.get("note") else ""
        lines.append(
            f"- **{_session_label(study, present)} metered Modal total:** ${float(rec.get('metered_usd', 0)):.2f} "
            f"(${float(rec.get('billed_usd', 0)):.2f} billed after credits).{note}"
        )
    unrecorded = [s for s in dict.fromkeys(p.study for p in present) if s not in metered]
    if unrecorded:
        lines.append(
            f"- **{' and '.join(_session_label(u, present) for u in unrecorded)} metered Modal total:** not yet recorded; the busy-window GPU cost "
            "under *Serving efficiency* is the cost of the cells themselves."
        )
    lines += [
        "- **Teardown** to zero warm containers is part of every posture's runbook; the metered totals above "
        "come from the teardown spend check.",
        "- **Comparability:** Experiments 2 and 3 score identical n = 50 documents and "
        "differ only in GPU count and client concurrency; Experiment 1 is a nested n = 20 subset. "
        "Experiment 4 runs the same 2×L4 engine as Experiment 3; its n = 100 draws contain the n = 50 documents, and its merger "
        "cell scores the same 50 agreements with the † settings.",
        "",
        "**Source data:** per-cell score and cost cards, run reports and vLLM serving telemetry under "
        "`1L4/<specialist>/` and `2L4/<specialist>/`; posture suite cards `1L4/L4x1-SCORE-COST-CARD.md` "
        "and `2L4/L4x2-SCORE-COST-CARD.md`. Regenerate with `sandbox run card --master`.",
        "",
    ]
    lines += _figure_md(data, "posture", "## Appendix: posture dashboards")
    return "\n".join(lines)


def _figure_md(data: Mapping[str, Any], section: str, heading: str) -> list[str]:
    from mailroom_sandbox.job.grid_figures import figure_specs

    specs = [s for s in figure_specs(data) if s["section"] == section]
    if not specs:
        return []
    out = ["", heading, ""]
    for i, spec in enumerate(specs, 1):
        tag = "Figure" if section == "comparison" else "Dashboard"
        out += [f"![{tag} {i}]({spec['path']})", "", f"*{tag} {i}. {spec['caption']}*", ""]
    return out


def write_master(repo: Path | None = None) -> dict[str, Path]:
    paths = master_paths(repo)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    data = collect_master(repo)
    from mailroom_sandbox.job.grid_figures import write_figures

    write_figures(data, repo)
    paths["md"].write_text(render_master_md(data), encoding="utf-8")
    paths["appendix"].write_text(render_appendix_md(data), encoding="utf-8")
    return paths


def record_metered(study: str, metered_usd: float, billed_usd: float, note: str = "", *, repo: Path | None = None) -> Path:
    """Record a study's session-level Modal spend (from the teardown spend check)."""
    path = master_paths(repo)["metered"]
    data = _read_json(path)
    data[study] = {"metered_usd": round(float(metered_usd), 2), "billed_usd": round(float(billed_usd), 2)}
    if note:
        data[study]["note"] = note
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
