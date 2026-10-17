#!/usr/bin/env python
"""SAND-042 coverage ledger: prove the designed metric matrix landed, per cell.

A card only rewrites at the END of its leg, so a capture that silently stopped halfway
stays invisible for hours. This reads the run stores directly and reports, per cell, the
things the re-run campaign exists to capture — plus the contract draw — and exits non-zero
if anything is missing.

    .venv/bin/python scripts/sand42/coverage-ledger.py            # all five cells
    .venv/bin/python scripts/sand42/coverage-ledger.py 1l4-c8     # one cell, as it stands

Columns: runs found · stores at 50 docs · verbatim before/mid/after · mid series ·
mid-run KV in the card · nvidia-smi samples in the card · draw loaded · fleet ready_ts.
"""

from __future__ import annotations

import glob
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
RUNS = REPO / "data" / "runtime" / "runs"
CELLS = ("1l4-c8", "1l4-c16", "2l4-c8", "2l4-c16", "2l4-c32")
FAMILY = re.compile(r"^vllm:", re.M)


def folder(cell: str) -> str:
    return cell.replace("l4-c", "L4-c").upper().replace("L4-C", "L4-c")


def _json(p: pathlib.Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _lines(rid: str, name: str) -> int:
    p = RUNS / rid / name
    if not p.is_file():
        return 0
    return sum(1 for x in p.read_text(encoding="utf-8").splitlines() if x.strip())


def _card_fresh(rid: str) -> bool:
    """True when the newest card is at least as new as the run's store.

    The reruns reuse run ids, so a card left over from a previous run of the same id sits
    beside the new store. Reading its numbers would report a stale paired n and stale
    mid-run KV as if they described the run on disk.
    """
    cards = _cards(rid)
    store = RUNS / rid / "items.jsonl"
    if not cards or not store.is_file():
        return False
    return max(c.stat().st_mtime for c in cards) >= store.stat().st_mtime


def _run_health(rid: str) -> tuple[int, dict[str, int], list[str]]:
    """Documents run, error kinds, and which documents failed.

    A failed row still counts in ``items.jsonl``, so a store can read 50/50 while a document
    produced no score at all — that is exactly how an error hides inside a "complete" capture
    and quietly deflates the paired n. The card records it (``quality.errors``) but nothing
    failed on it before this.
    """
    p = RUNS / rid / "items.jsonl"
    if not p.is_file():
        return 0, {}, []
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    bad = [r for r in rows if r.get("ok") is False or r.get("error")]
    kinds: dict[str, int] = {}
    for r in bad:
        k = str(r.get("error") or "unknown").split(":")[0].strip()[:60]
        kinds[k] = kinds.get(k, 0) + 1
    return len(rows), kinds, [str(r.get("item_id")) for r in bad]


def _cards(rid: str) -> list[pathlib.Path]:
    return [pathlib.Path(x) for x in glob.glob(
        str(REPO / "reports" / "SAND42" / "*" / "*" / f"{rid}.card.json"))]


def _midrun(rid: str) -> dict:
    for c in _cards(rid):
        et = _json(c).get("engine_telemetry") or {}
        if et.get("midrun"):
            return et["midrun"]
    return {}


def _bw_samples(rid: str) -> int:
    """nvidia-smi samples behind the card's 'GPU mem bandwidth (mean)' row.

    That row renders from `utilization_memory_perc` (the nvidia-smi memory-bandwidth gauge)
    in the summarized telemetry, so this checks exactly that field and nothing looser — a
    per-replica sample count would report positive on cards whose bandwidth row still reads
    "not captured".
    """
    for c in _cards(rid):
        et = _json(c).get("engine_telemetry") or {}
        n = ((et.get("gpu") or {}).get("utilization_memory_perc") or {}).get("n")
        if n:
            return int(n)
    return 0


def check_run(rid: str, gaps: list[str], ok: list[str]) -> None:
    d = RUNS / rid
    if not d.is_dir():
        gaps.append(f"{rid}: no run store")
        return
    items = _lines(rid, "items.jsonl")
    if items < 50:
        gaps.append(f"{rid}: store {items}/50 documents")

    # A row that failed still counts as a document in the store, so check the outcomes too:
    # "50/50 items" with one error is a paired n of 49, not a complete capture.
    n_rows, kinds, bad_ids = _run_health(rid)
    if kinds:
        n_err = sum(kinds.values())
        gaps.append(f"{rid}: {n_err} document(s) errored ({kinds}) — paired n "
                    f"{n_rows - n_err}/{n_rows}, not 50; failed: {bad_ids[:4]}")

    if "contract" in rid and _card_fresh(rid):
        labeled = None
        for c in _cards(rid):
            cl = (_json(c).get("quality") or {}).get("clause") or {}
            if isinstance(cl.get("docs_labeled"), int):
                labeled = cl["docs_labeled"]
                break
        if labeled is not None and labeled < 50:
            gaps.append(f"{rid}: paired n {labeled}/50 — the CUAD metric scores only "
                        f"{labeled} of the 50 drawn")
        elif labeled == 50:
            ok.append(f"{rid}: paired n 50/50")

    for lbl in ("before", "mid", "after"):
        j, t = d / f"vllm_metrics_{lbl}.json", d / f"vllm_metrics_{lbl}.txt"
        if not j.is_file() or not t.is_file():
            gaps.append(f"{rid}: {lbl} scrape missing ({j.name}{'' if j.is_file() else ' MISSING'} / "
                        f"{t.name}{'' if t.is_file() else ' MISSING'})")
        elif not FAMILY.search(t.read_text(encoding="utf-8", errors="replace")):
            gaps.append(f"{rid}: {lbl} text carries no vllm: family (verbatim not preserved)")

    if _lines(rid, "vllm_metrics_mid.series.jsonl") < 1:
        gaps.append(f"{rid}: no mid-run SERIES — the card's mid max has no source")

    if not _cards(rid):
        gaps.append(f"{rid}: no card written")
    elif not _card_fresh(rid):
        gaps.append(f"{rid}: card predates this run's store (run in flight, or the card was "
                    f"not rebuilt) — its mid-run KV and paired n would be the PREVIOUS run's")
    else:
        cm = (_midrun(rid).get("cell_max") or {})
        if cm.get("kv_cache_usage_perc") is None:
            gaps.append(f"{rid}: card has no mid-run kv_cache_usage_perc")
        if _bw_samples(rid) == 0:
            gaps.append(f"{rid}: card carries no GPU memory-bandwidth samples "
                        f"(utilization_memory_perc) — the bandwidth row stays empty")

    rows = [json.loads(x) for x in
            (d / "dataset.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()] \
        if (d / "dataset.jsonl").is_file() else []
    if len(rows) != 50:
        gaps.append(f"{rid}: draw is {len(rows)} documents, expected 50")
    if "contract" in rid:
        blank = [r.get("id") for r in rows
                 if not str((r.get("expected_fields") or {}).get("cuad_clause_labels") or "").strip()]
        if blank:
            gaps.append(f"{rid}: {len(blank)} drawn contract(s) carry no cuad_clause_labels "
                        f"— the CUAD metric cannot score them: {blank[:4]}")
        else:
            ok.append(f"{rid}: draw 50/50 annotated (CUAD-scorable)")


def draw_identity(cells: list[str], gaps: list[str], ok: list[str]) -> None:
    """Every cell must score the same documents — the campaign's whole premise.

    The cards record a dataset fingerprint and the master's prose asserts the identical 250
    documents, but nothing compared them, so a draw that drifted between cells would have
    produced a comparison of different documents under a sentence claiming otherwise. This
    reads each run's own ``dataset.jsonl``, so it is true of the artifacts rather than of the
    configs that were supposed to produce them.

    Only meaningful across cells, so it runs in the all-cells mode, not in a per-leg gate: a
    leg legitimately re-draws its own cell while its siblings still hold the previous draw.
    """
    by_cell = {}
    for cell in cells:
        draws = {}
        for p in sorted(glob.glob(str(REPO / "config" / "runs" / f"sand42-50-*-awq-{cell}.yaml"))):
            rid = pathlib.Path(p).stem
            store = RUNS / rid / "dataset.jsonl"
            if store.is_file():
                draws[rid.split("-specialist-awq-")[0]] = [
                    json.loads(x)["id"] for x in store.read_text(encoding="utf-8").splitlines() if x.strip()]
        by_cell[cell] = draws

    print()
    print("draw identity (all cells must score the same documents):")
    for cls in sorted({k for d in by_cell.values() for k in d}):
        have = {c: set(d[cls]) for c, d in by_cell.items() if cls in d}
        if len(have) < 2:
            print(f"  {cls:<24} only {len(have)} cell(s) have a draw on disk — nothing to compare yet")
            continue
        shapes = {}
        for c, ids in have.items():
            shapes.setdefault(frozenset(ids), []).append(c)
        if len(shapes) == 1:
            print(f"  {cls:<24} {len(have)} cells share one draw of {len(next(iter(have.values())))} "
                  f"documents — IDENTICAL")
            ok.append(f"{cls}: one draw across {len(have)} cells")
        else:
            groups = " | ".join(f"{sorted(cs)} ({len(ids)} docs)" for ids, cs in shapes.items())
            gaps.append(f"draw identity: `{cls}` differs across cells — {groups}. Those cells "
                        f"compare DIFFERENT documents; the identical-250 claim is false until "
                        f"every cell re-runs on one draw.")
            print(f"  {cls:<24} ** DIFFERS ** {groups}")


def main(argv: list[str]) -> int:
    cells = [c for c in argv if c in CELLS] or list(CELLS)
    gaps: list[str] = []
    ok: list[str] = []
    print(f"{'cell':<8} {'runs':>4} {'store':>7} {'clean':>7} {'verbatim':>9} {'series':>7} "
          f"{'midKV':>6} {'bw':>6} {'draw':>6} {'fleet':>5}  verdict")
    print("-" * 74)
    for cell in cells:
        reps = sorted(pathlib.Path(p).stem for p in
                      glob.glob(str(REPO / "config" / "runs" / f"sand42-*-awq-{cell}.yaml"))
                      if not pathlib.Path(p).name.startswith("sand42-check-"))
        if not reps:
            print(f"{cell:<8}    -  no configs found")
            continue
        before = len(gaps)
        for rid in reps:
            check_run(rid, gaps, ok)
        fw = REPO / "reports" / "SAND42" / folder(cell) / "fleet_window.json"
        ready = bool(_json(fw).get("ready_ts"))
        if not ready:
            gaps.append(f"{cell}: fleet_window.json missing/incomplete ready_ts")

        t = len(reps)
        store = sum(1 for r in reps if _lines(r, "items.jsonl") >= 50)
        clean = sum(1 for r in reps if not _run_health(r)[1])
        verb = sum(1 for r in reps if all((RUNS / r / f"vllm_metrics_{l}.{e}").is_file()
                                          for l in ("before", "mid", "after") for e in ("json", "txt")))
        ser = sum(1 for r in reps if _lines(r, "vllm_metrics_mid.series.jsonl") >= 1)
        mid = sum(1 for r in reps
                  if (_midrun(r).get("cell_max") or {}).get("kv_cache_usage_perc") is not None)
        gpu = sum(1 for r in reps if _bw_samples(r) > 0)
        draw = sum(1 for r in reps if _lines(r, "dataset.jsonl") == 50)
        here = len(gaps) - before
        print(f"{cell:<8} {t:>4} {store:>4}/{t} {clean:>4}/{t} {verb:>6}/{t} {ser:>4}/{t} "
              f"{mid:>3}/{t} {gpu:>3}/{t} {draw:>3}/{t} {('yes' if ready else 'NO'):>5}  "
              f"{'ALL CAPTURES' if here == 0 else f'{here} gap(s)'}")
    if len(cells) > 1:
        draw_identity(cells, gaps, ok)
    print()
    if gaps:
        print(f"GAPS ({len(gaps)}):")
        for g in gaps:
            print(f"  - {g}")
        return 1
    print(f"COVERAGE COMPLETE for {', '.join(cells)} ({len(ok)} positive draw checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
