"""CLI: sandbox up/down/health/pilot/eval/matrix/..."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from mailroom_sandbox.overlay import list_profiles, load_profile
from mailroom_sandbox.paths import repo_root, vendor_dir
from mailroom_sandbox.runtime import activate, resolve_dojo_src, resolve_mailroom_src



def _activation_model(spec, cli_model):
    """SAND-032: graph tasks (sorter) must call the model the run YAML serves.

    Activating with only the profile default sent `Qwen/Qwen3-8B` to an AWQ
    fleet (vLLM 404 on every request). An explicit --model still wins.
    """
    return cli_model or (spec.engine.model if getattr(spec, "engine", None) else None)


def _activation_knobs(spec):
    """Apply posture decode budget (grid cells: 8192, above the 4096 JSON cap)."""
    import json

    from mailroom_sandbox.job.specialist_posture import agent_knobs_for_run

    knobs = agent_knobs_for_run(getattr(spec, "run_id", None))
    if knobs:
        os.environ["SANDBOX_AGENT_KNOBS"] = json.dumps(knobs)
    return knobs

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 0
    try:
        return int(args.handler(args) or 0)
    except subprocess.CalledProcessError as exc:
        # Docker/ollama/ssh failures surface the tool's own message; don't
        # dump a Python traceback for a missing daemon/container (DMR-058).
        print(f"command failed ({exc.returncode}): {' '.join(exc.cmd[:3])} …", file=sys.stderr)
        if exc.stderr:
            print(exc.stderr.decode() if isinstance(exc.stderr, bytes) else exc.stderr, end="", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"command unavailable: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--profile", default=os.environ.get("SANDBOX_PROFILE") or "ollama")
    shared.add_argument("--model", default=None, help="Override every agent's model tag")
    shared.add_argument("--prompt", default=None, help="Local prompt variant stem (e.g. sorter_local_v0)")
    shared.add_argument(
        "--agent-model",
        action="append",
        default=[],
        dest="agent_models",
        metavar="NAME=TAG",
        help="Surgical per-agent model override (repeatable)",
    )

    parser = argparse.ArgumentParser(
        prog="sandbox",
        description="Local-first LLM-Mailroom experiment sandbox.",
        parents=[shared],
    )
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("up", help="Start compose profiles (langfuse + provider)", parents=[shared])
    p.add_argument("--compose-profile", action="append", dest="compose_profiles")
    # hub#56: -d opts in to detached mode; the default is foreground (the old
    # action='store_true', default=True made -d a permanent no-op and `sandbox
    # up` could NEVER run in the foreground).
    p.add_argument("-d", "--detach", action="store_true", default=False)
    p.set_defaults(handler=_cmd_up)

    p = sub.add_parser("down", help="Stop compose stack", parents=[shared])
    p.add_argument("--compose-profile", action="append", dest="compose_profiles")
    p.set_defaults(handler=_cmd_down)

    p = sub.add_parser("health", help="Probe the active provider + Langfuse", parents=[shared])
    p.set_defaults(handler=_cmd_health)

    p = sub.add_parser("pull-models", help="Pull Ollama (or listed) weights", parents=[shared])
    p.add_argument("models", nargs="*")
    p.set_defaults(handler=_cmd_pull_models)

    p = sub.add_parser(
        "fetch-deps",
        help="Refresh tracked vendor snapshots (llm-mailroom v0.7.1, llm-dojo-scoring v0.15.0) from pinned tags",
        parents=[shared],
    )
    p.add_argument("--visualizer", action="store_true", help="Also clone The-Mailroom (Langfuse observer)")
    p.set_defaults(handler=_cmd_fetch_deps)

    p = sub.add_parser("cutover", help="Show effective agent→provider/model assignments", parents=[shared])
    p.set_defaults(handler=_cmd_cutover)

    agents_p = sub.add_parser("agents", help="List or show pipeline agents", parents=[shared])
    agents_sub = agents_p.add_subparsers(dest="agents_cmd")
    al = agents_sub.add_parser("list", parents=[shared])
    al.set_defaults(handler=_cmd_agents_list)
    ash = agents_sub.add_parser("show", parents=[shared])
    ash.add_argument("name")
    ash.set_defaults(handler=_cmd_agents_show)
    agents_p.set_defaults(handler=_cmd_agents_list)

    subagents_p = sub.add_parser(
        "subagents",
        help="Central coding subagent roster (Cursor + OpenCode adapters)",
        parents=[shared],
    )
    subagents_sub = subagents_p.add_subparsers(dest="subagents_cmd")
    sa_list = subagents_sub.add_parser("list", parents=[shared])
    sa_list.add_argument("--json", action="store_true")
    sa_list.add_argument(
        "--package",
        default=None,
        help="Family package filter (default: local-mailroom-sandbox or SUBAGENT_PACKAGE)",
    )
    sa_list.set_defaults(handler=_cmd_subagents_list)
    sa_pkgs = subagents_sub.add_parser("packages", parents=[shared])
    sa_pkgs.add_argument("--json", action="store_true")
    sa_pkgs.set_defaults(handler=_cmd_subagents_packages)
    sa_show = subagents_sub.add_parser("show", parents=[shared])
    sa_show.add_argument("id")
    sa_show.add_argument("--json", action="store_true")
    sa_show.add_argument("--package", default=None)
    sa_show.set_defaults(handler=_cmd_subagents_show)
    sa_sync = subagents_sub.add_parser("sync", parents=[shared])
    sa_sync.add_argument(
        "--harness",
        default="all",
        choices=("cursor", "opencode", "opencode-global", "all"),
        help="Harness adapter(s); default syncs OpenCode + Cursor + ~/.config/opencode/agents",
    )
    sa_sync.add_argument(
        "--package",
        default=None,
        help="Family package filter for roster entries",
    )
    sa_sync.add_argument(
        "--root",
        default=None,
        help="Checkout root to write into (default: this repo)",
    )
    sa_sync.add_argument("--dry-run", action="store_true")
    sa_sync.set_defaults(handler=_cmd_subagents_sync)
    sa_doc = subagents_sub.add_parser(
        "doctor",
        help="Audit harness health (OpenCode global, roster sync, framework v2)",
        parents=[shared],
    )
    sa_doc.add_argument(
        "--root",
        default=None,
        help="Family checkout root (default: this repo)",
    )
    sa_doc.add_argument("--json", action="store_true")
    sa_doc.add_argument(
        "--no-global",
        action="store_true",
        help="Skip ~/.config/opencode checks",
    )
    sa_doc.add_argument("--package", default=None, help="Filter roster entries by package id")
    sa_doc.add_argument(
        "--also-root",
        action="append",
        default=None,
        metavar="PATH",
        help="Additional checkout to audit (repeatable)",
    )
    sa_doc.add_argument(
        "--apply-framework",
        action="store_true",
        help="Append Agent framework (v2) to roster + global profile agents missing it",
    )
    sa_doc.add_argument("--dry-run", action="store_true")
    sa_doc.set_defaults(handler=_cmd_subagents_doctor)
    sa_mat = subagents_sub.add_parser(
        "materialize",
        help="Copy family-roster.yaml + missing prompts into another package checkout",
        parents=[shared],
    )
    sa_mat.add_argument(
        "--package",
        required=True,
        help="Target package id (llm-mailroom, digital-mailroom, …)",
    )
    sa_mat.add_argument(
        "--root",
        required=True,
        help="Destination checkout root (e.g. monorepo packages/llm-mailroom)",
    )
    sa_mat.add_argument(
        "--source-root",
        default=None,
        help="Prompt source checkout (default: this sandbox repo)",
    )
    sa_mat.add_argument("--dry-run", action="store_true")
    sa_mat.set_defaults(handler=_cmd_subagents_materialize)
    sa_prop = subagents_sub.add_parser(
        "propagate",
        help="Materialize + sync all mapped family checkouts",
        parents=[shared],
    )
    sa_prop.add_argument(
        "--monorepo-root",
        default=None,
        help="Digital-Mailroom root (DIGITAL_MAILROOM_ROOT / MONOREPO_ROOT)",
    )
    sa_prop.add_argument("--package", action="append", dest="packages", default=None)
    sa_prop.add_argument("--dry-run", action="store_true")
    sa_prop.add_argument("--json", action="store_true")
    sa_prop.set_defaults(handler=_cmd_subagents_propagate)
    subagents_p.set_defaults(handler=_cmd_subagents_list)

    pipe = sub.add_parser("pipeline", help="Run mailroom inbox watcher or API (not the Tray TUI watch)", parents=[shared])
    pipe_sub = pipe.add_subparsers(dest="pipeline_cmd")
    w = pipe_sub.add_parser("watcher", parents=[shared])
    w.set_defaults(handler=_cmd_watcher)
    a = pipe_sub.add_parser("api", parents=[shared])
    a.set_defaults(handler=_cmd_api)

    p = sub.add_parser("pilot", help="Run the fixture pilot (--mock or --local)", parents=[shared])
    g = p.add_mutually_exclusive_group()
    g.add_argument("--mock", action="store_true", default=False)
    g.add_argument("--local", action="store_true", default=False)
    p.add_argument("--sample", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(handler=_cmd_pilot)

    p = sub.add_parser("hf-pilot", help="HF docclass mini-pilot", parents=[shared])
    g = p.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true")
    g.add_argument("--mock", action="store_true")
    g.add_argument("--local", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(handler=_cmd_hf_pilot)

    p = sub.add_parser("legalbench", help="LegalBench Yes/No fixture harness", parents=[shared])
    p.add_argument("--task", default="contract_qa", choices=("contract_qa", "family_classification"))
    p.add_argument("--mock", action="store_true")
    p.add_argument("--local", action="store_true")
    p.add_argument("--n", type=int, default=None, help="seeded sample size (never first-N)")
    p.add_argument("--seed", type=int, default=42, help="sample seed (recorded in the experiment log)")
    p.add_argument("--suite", action="store_true", help="use the vendored llm-mailroom suite (needs data/cuad)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(handler=_cmd_legalbench)

    from mailroom_sandbox.eval.agents import EVAL_TASKS

    p = sub.add_parser("eval", help="Run a scoring eval (isolated agent or connected pipeline)", parents=[shared])
    p.add_argument("task", choices=tuple(EVAL_TASKS))
    p.add_argument("--mock", action="store_true", default=False)
    p.add_argument("--local", action="store_true", default=False)
    p.add_argument("--sample", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--name", dest="experiment_name")
    p.add_argument(
        "--connected",
        action="store_true",
        default=False,
        help="Score class + stage + extraction + routing (pipeline default; flag is accepted on pipeline)",
    )
    p.add_argument(
        "--from-log",
        action="store_true",
        dest="from_log",
        help="For local_vs_api / sorter_vs_modernbert: compare experiment_log.jsonl instead of fixtures",
    )
    p.set_defaults(handler=_cmd_eval)

    p = sub.add_parser("matrix", help="provider × model × prompt grid", parents=[shared])
    p.add_argument("--task", default="sorter")
    p.add_argument("--providers", default="ollama")
    p.add_argument("--models", default="qwen3:8b")
    p.add_argument("--prompts", default="mailroom-default")
    p.add_argument("--sample", type=int, default=10)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--mock", action="store_true")
    p.add_argument("--local", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(handler=_cmd_matrix)

    p = sub.add_parser("datasets", help="Dataset helpers", parents=[shared])
    ds = p.add_subparsers(dest="datasets_cmd")
    pull = ds.add_parser("pull", parents=[shared], help="Live pinned Hub pull of the FULL ground_truth corpus into data/cache (network)")
    pull.add_argument("--dataset", default="Lucius-Morningstar/mailroom-dataset")
    pull.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help="Cap rows after the draw (0 = full corpus; default). Legacy tiny slices used 50.",
    )
    pull.add_argument(
        "--revision",
        default="",
        help="Hub revision (default: the pinned FAMILY_HF_REVISION snapshot)",
    )
    pull.add_argument(
        "--config",
        default="ground_truth",
        choices=("ground_truth", "default", ""),
        help="parquet config: ground_truth (labels merged with blind text, the default) or 'default'/'' (blind)",
    )
    pull.add_argument(
        "--split",
        default="all",
        help="parquet split: all (train+test, default — required for 40/100-per-class) | train | test",
    )
    pull.add_argument(
        "--per-class",
        type=int,
        default=0,
        help="Also draw N rows per live doc type (20/40/100…) from the pulled corpus",
    )
    pull.add_argument(
        "--seed",
        type=int,
        default=42,
        dest="sample_seed",
        help="sample_seed for --per-class draws (default 42)",
    )
    pull.set_defaults(handler=_cmd_datasets_pull)
    sample = ds.add_parser(
        "sample",
        parents=[shared],
        help="Offline per-class draw from the cached full corpus (no network)",
    )
    sample.add_argument("--per-class", type=int, required=True, help="rows per live doc type (20/40/100…)")
    sample.add_argument("--seed", type=int, default=42, dest="sample_seed")
    sample.add_argument(
        "--classes",
        default="",
        help="comma-separated live classes (default: all five)",
    )
    sample.add_argument("--from", dest="source", default="", help="source JSONL (default: cached full pull)")
    sample.add_argument("--out", default="", help="destination JSONL")
    sample.set_defaults(handler=_cmd_datasets_sample)
    prep = ds.add_parser(
        "prepare",
        help="Load/clean fixtures into data/runtime/prepared/ (offline, no network)",
        parents=[shared],
    )
    prep.set_defaults(handler=_cmd_datasets_prepare)
    p.set_defaults(handler=_cmd_datasets_help)

    p = sub.add_parser("traces", help="Trace helpers", parents=[shared])
    tr = p.add_subparsers(dest="traces_cmd")
    exp = tr.add_parser("export", parents=[shared])
    exp.set_defaults(handler=_cmd_traces_export)
    pk = tr.add_parser(
        "pack",
        help="Zip a run's local span mirror (Parquet), copy it to --dest and verify; --prune deletes local copies",
        parents=[shared],
    )
    pk.add_argument("run_id")
    pk.add_argument("--experiment", help="experiment label for the zip name (default: run_id prefix)")
    pk.add_argument("--runner", help="who ran it: claude | axios (default: claude inside Claude Code, else axios)")
    pk.add_argument(
        "--dest",
        default=os.environ.get("SANDBOX_TRACE_UPLOAD_DIR"),
        help="synced upload folder, e.g. the Drive LOGS folder (env SANDBOX_TRACE_UPLOAD_DIR); a <date>/ subfolder is added",
    )
    pk.add_argument("--date", help="date subfolder YYYY-MM-DD (default: today UTC)")
    pk.add_argument("--prune", action="store_true", help="after a verified copy, delete the local mirror and local zip")
    pk.set_defaults(handler=_cmd_traces_pack)
    p.set_defaults(handler=_cmd_traces_help)

    p = sub.add_parser("profiles", help="List provider profiles", parents=[shared])
    p.set_defaults(handler=_cmd_profiles)

    tun = sub.add_parser(
        "tunnel",
        help="SSH local port forward for remote-serving profiles (plan/up/status/down)",
        parents=[shared],
    )
    tun_sub = tun.add_subparsers(dest="tunnel_cmd")
    # NOTE: the leaf parsers deliberately omit parents=[shared] — a leaf-level
    # --profile default would clobber the value parsed at the tunnel level.
    tp = tun_sub.add_parser("plan", help="Print the exact ssh forward command")
    tp.set_defaults(handler=_cmd_tunnel_plan)
    tu = tun_sub.add_parser("up", help="Start the detached forward (pidfile under data/runtime/)")
    tu.set_defaults(handler=_cmd_tunnel_up)
    ts = tun_sub.add_parser("status", help="Is the forward port answering / pid recorded?")
    ts.set_defaults(handler=_cmd_tunnel_status)
    td = tun_sub.add_parser("down", help="Stop the recorded forward")
    td.set_defaults(handler=_cmd_tunnel_down)
    tun.set_defaults(handler=_cmd_tunnel_help)

    _run_parser(sub, shared)

    watch_p = sub.add_parser(
        "watch",
        help="Tray TUI: live in-tray + spend + Modal dispatch log for any locked run",
        parents=[shared],
    )
    watch_p.add_argument("--config", default=None, help="run YAML to watch")
    watch_p.add_argument(
        "--follow", default=None,
        help="file holding the CURRENT run YAML path; re-read every frame",
    )
    watch_p.add_argument("--app", default=None, help="Modal serve app override (default: engine.modal.app; modal job mode also tails sandbox-job)")
    watch_p.add_argument("--ledger", default=None, help="spend ledger JSON ({spent_usd})")
    watch_p.add_argument("--cap-usd", type=float, default=5.0)
    watch_p.add_argument("--interval", type=float, default=1.0, help="max seconds between redraws (logs and run-store changes redraw immediately)")
    watch_p.add_argument("--no-bell", action="store_true", help="do not ring the terminal bell on a new critical watchdog alert")
    watch_p.add_argument("--once", action="store_true", help="render one frame and exit")
    watch_p.add_argument("--no-logs", action="store_true", help="do not follow Modal dispatch logs (serve + worker); job events still shown")
    watch_p.add_argument(
        "--web",
        action="store_true",
        help="Tray TUI in the browser on localhost (SSE); frees the terminal tab",
    )
    watch_p.add_argument(
        "--host",
        default=None,
        help="web UI bind host (default 127.0.0.1; only with --web)",
    )
    watch_p.add_argument(
        "--port",
        type=int,
        default=None,
        help="web UI port (default 8765; 0 = ephemeral; only with --web)",
    )
    watch_p.add_argument(
        "--no-browser",
        action="store_true",
        help="do not open a browser tab (only with --web; also NO_BROWSER=1)",
    )
    watch_p.add_argument(
        "--demo",
        action="store_true",
        help="with --web: serve a synthetic looping run (dev server; no Modal, no spend)",
    )
    watch_p.set_defaults(handler=_cmd_watch)

    dev_p = sub.add_parser(
        "dev",
        help="Tray TUI dev server: themed browser UI on a synthetic run (= watch --web --demo)",
        parents=[shared],
    )
    dev_p.add_argument("--host", default=None, help="bind host (default 127.0.0.1)")
    dev_p.add_argument("--port", type=int, default=None, help="port (default 8765; 0 = ephemeral)")
    dev_p.add_argument("--interval", type=float, default=1.0, help="seconds per demo tick")
    dev_p.add_argument("--no-browser", action="store_true", help="do not open a browser tab")
    dev_p.set_defaults(handler=_cmd_dev)

    board_p = sub.add_parser(
        "board",
        help="persistent mailroom job board: every beacon job in the package family (browser; --tui for terminal)",
        parents=[shared],
    )
    board_p.add_argument("--root", default=None, help="beacon dir (default $MAILROOM_BEACON_DIR or ~/.mailroom/jobs)")
    board_p.add_argument("--tui", action="store_true", help="terminal TUI instead of the browser page")
    board_p.add_argument("--once", action="store_true", help="with --tui: render one frame and exit")
    board_p.add_argument("--host", default=None, help="bind host (default 127.0.0.1)")
    board_p.add_argument("--port", type=int, default=None, help="port (default 8767; 0 = ephemeral)")
    board_p.add_argument("--no-browser", action="store_true", help="do not open a browser tab")
    board_p.add_argument("--stale-s", type=float, default=120.0, help="heartbeat age that marks a running job stalled")
    board_p.add_argument("--interval", type=float, default=1.0, help="refresh seconds")
    board_p.add_argument("--demo", action="store_true", help="also run synthetic demo jobs (dev server; no Modal)")
    board_p.set_defaults(handler=_cmd_board)

    beacon_p = sub.add_parser("beacon", help="publish a mailroom.beacon/v1 heartbeat (shell jobs)", parents=[shared])
    beacon_sub = beacon_p.add_subparsers(dest="beacon_cmd", required=True)
    bu = beacon_sub.add_parser("update", help="create/update a job heartbeat", parents=[shared])
    bu.add_argument("--job", required=True)
    bu.add_argument("--package", required=True)
    bu.add_argument("--title", default="")
    bu.add_argument("--phase", default=None)
    bu.add_argument("--done", type=int, default=None)
    bu.add_argument("--total", type=int, default=None)
    bu.add_argument("--ok", type=int, default=None)
    bu.add_argument("--errors", type=int, default=None)
    bu.add_argument("--metric", action="append", default=[], help="key=value (repeatable)")
    bu.add_argument("--log", default=None, help="append one log line")
    bu.add_argument("--finish", choices=("done", "failed"), default=None)
    bu.add_argument("--root", default=None)
    bu.set_defaults(handler=_cmd_beacon_update)

    score_p = sub.add_parser(
        "scorecard",
        help="mailroom TUI scorecard for a finished run (SAND-032)",
        parents=[shared],
    )
    score_p.add_argument("--run", dest="run_id", required=True, help="run id (e.g. sand032-l0-baseline)")
    score_p.add_argument("--serving-dir", default=None, help="default: reports/serving (nested SAND trees and legacy flat exports)")
    score_p.set_defaults(handler=_cmd_scorecard)

    rb = sub.add_parser(
        "runbook",
        help="Operator runbooks (catalog → show / check / write)",
        parents=[shared],
    )
    rb_sub = rb.add_subparsers(dest="runbook_cmd")
    rb_list = rb_sub.add_parser("list", parents=[shared], help="list catalog ids")
    rb_list.add_argument("--family", choices=["baseline", "improved"], default=None)
    rb_list.add_argument("--json", action="store_true")
    rb_list.set_defaults(handler=_cmd_runbook_list)
    rb_show = rb_sub.add_parser("show", parents=[shared], help="print one operator card")
    rb_show.add_argument("name", help="runbook id or alias (l4-qwen3-8b, awq-c8, granite…)")
    rb_show.add_argument("--shell", action="store_true", help="print the bash script only")
    rb_show.add_argument("--json", action="store_true")
    rb_show.set_defaults(handler=_cmd_runbook_show)
    rb_check = rb_sub.add_parser(
        "check",
        parents=[shared],
        help="catalog vs live pins + generated docs freshness",
    )
    rb_check.add_argument("--json", action="store_true")
    rb_check.set_defaults(handler=_cmd_runbook_check)
    rb_write = rb_sub.add_parser(
        "write",
        parents=[shared],
        help="regenerate docs/runbooks/ from the catalog",
    )
    rb_write.set_defaults(handler=_cmd_runbook_write)
    rb.set_defaults(handler=_cmd_runbook_help)

    prom = sub.add_parser("prompts", help="Pipeline-agent prompt surface (local + Langfuse)", parents=[shared])
    prom_sub = prom.add_subparsers(dest="prompts_cmd")
    plug_list = prom_sub.add_parser("list", parents=[shared])
    plug_list.set_defaults(handler=_cmd_prompts_list)
    plug_show = prom_sub.add_parser("show", parents=[shared])
    plug_show.add_argument("name", help="agent name (or --all)")
    plug_show.add_argument("--variant", default=None, help="local variant stem")
    plug_show.add_argument("--json", action="store_true")
    plug_show.set_defaults(handler=_cmd_prompts_show)
    prom.set_defaults(handler=_cmd_prompts_help)

    mp = sub.add_parser("metrics", help="serving metrics compare (local vs Modal vs API)", parents=[shared])
    metrics_sub = mp.add_subparsers(dest="metrics_cmd")
    mcomp = metrics_sub.add_parser("compare", parents=[shared])
    mcomp.add_argument("--runs", default="", help="comma-separated run-ids")
    mcomp.add_argument("--log", action="store_true", help="read experiments from the log instead")
    mcomp.add_argument(
        "--fixture",
        action="store_true",
        help="offline Grant-style local/Modal/API cost-compare fixture (no GPU)",
    )
    mcomp.add_argument(
        "--sorter-vs-modernbert",
        action="store_true",
        help="compare LLM sorter vs ModernBERT (fixtures, or --runs sorter,modernbert)",
    )
    mcomp.add_argument("--json", action="store_true")
    mcomp.set_defaults(handler=_cmd_metrics_compare)
    mext = metrics_sub.add_parser(
        "extrapolate",
        parents=[shared],
        help="extrapolate run cost/doc to full corpus / docs-per-day",
    )
    mext.add_argument("--run", dest="run_id", required=True, help="run-id with a lock + items")
    mext.add_argument(
        "--corpus-size",
        type=int,
        default=None,
        help="target N (default: FAMILY_CORPUS_SIZE=3302)",
    )
    mext.add_argument("--docs-per-day", type=float, default=None)
    mext.add_argument("--docs-per-month", type=float, default=None)
    mext.add_argument("--cold-start-seconds", type=float, default=120.0)
    mext.add_argument("--scaledown-seconds", type=float, default=120.0)
    mext.add_argument("--concurrency", type=int, default=4)
    mext.add_argument("--json", action="store_true")
    mext.set_defaults(handler=_cmd_metrics_extrapolate)
    mserv = metrics_sub.add_parser(
        "serving-record",
        parents=[shared],
        help="write a serving export under the canonical reports/serving tree",
    )
    mserv.add_argument("--run", dest="run_id", required=True, help="run-id with lock + items")
    mserv.add_argument(
        "--wall-seconds",
        type=float,
        default=None,
        help="override wall clock when item timestamps are absent",
    )
    mserv.add_argument(
        "--out",
        default="",
        help="output path (default: canonical nested reports/serving path for this run)",
    )
    mserv.add_argument("--json", action="store_true", help="print the record to stdout")
    mserv.set_defaults(handler=_cmd_metrics_serving_record)
    mest = metrics_sub.add_parser(
        "estimate-suite",
        parents=[shared],
        help="pre-flight GPU $/wall estimate from run YAML(s) (no Modal spend)",
    )
    mest.add_argument(
        "--configs",
        default="",
        help="comma-separated run YAML paths (default: five run-30-*-specialist.yaml)",
    )
    mest.add_argument(
        "--suite",
        default="",
        help="suite id/alias (track-a|track-b|full) — overrides default five; "
        "see config/runs/suites/",
    )
    mest.add_argument(
        "config_paths",
        nargs="*",
        help="optional run YAML paths (positional); overrides default suite when set",
    )
    mest.add_argument(
        "--sec-per-doc",
        type=float,
        default=None,
        help="override busy seconds/doc for every run (skips class defaults)",
    )
    mest.add_argument(
        "--gen-tok-per-s",
        type=float,
        default=None,
        help="derive sec/doc from assumed completion tokens ÷ gen rate",
    )
    mest.add_argument(
        "--gpu-usd-per-hour",
        type=float,
        default=None,
        help="override L4 rate (default $0.80 or MODAL_GPU_USD_PER_HOUR)",
    )
    mest.add_argument("--cold-start-seconds", type=float, default=120.0)
    mest.add_argument(
        "--scaledown-seconds",
        type=float,
        default=None,
        help="suite teardown scaledown (default: max from YAMLs, usually 120 attended)",
    )
    mest.add_argument(
        "--inter-run-gap-seconds",
        type=float,
        default=60.0,
        help="warm idle between classes (preflight) while app stays up",
    )
    mest.add_argument(
        "--corpus-size",
        type=int,
        default=None,
        help="also print linear extrapolation (default: FAMILY_CORPUS_SIZE)",
    )
    mest.add_argument(
        "--no-corpus",
        action="store_true",
        help="skip full-corpus extrapolation block",
    )
    mest.add_argument("--json", action="store_true")
    mest.set_defaults(handler=_cmd_metrics_estimate_suite)
    mp.set_defaults(handler=_cmd_metrics_help)

    mb = sub.add_parser(
        "modernbert",
        help="mailroom-ml ModernBERT feeder (path status + live eval)",
        parents=[shared],
    )
    mb_sub = mb.add_subparsers(dest="modernbert_cmd")
    mb_status = mb_sub.add_parser("status", parents=[shared], help="resolve MAILROOM_ML_SRC + checkpoint")
    mb_status.set_defaults(handler=_cmd_modernbert_status)
    mb_eval = mb_sub.add_parser("eval", parents=[shared], help="run mailroom-ml eval_modernbert.py")
    mb_eval.add_argument("--sample", type=int, default=50)
    mb_eval.add_argument("--seed", type=int, default=42)
    mb_eval.add_argument(
        "--subset",
        default="test",
        choices=["test", "train", "all", "heldout-plus"],
        help="eval pool (test=323 held-out; all=finetune corpus for large "
        "samples; heldout-plus=1323 extended set, mailroom-ml "
        "training/build_heldout_plus.py)",
    )
    mb_eval.add_argument("--checkpoint", default=None, help="override MODERNBERT_MODEL_PATH")
    mb_eval.add_argument(
        "--append-log",
        action="store_true",
        help="append serving record to reports/experiment_log.jsonl",
    )
    mb_eval.add_argument("--json", action="store_true")
    mb_eval.set_defaults(handler=_cmd_modernbert_eval)
    mb.set_defaults(handler=_cmd_modernbert_help)

    mm = sub.add_parser(
        "modal-matrix",
        help="list/apply Modal+vLLM model/GPU rows from config/models.yaml",
        parents=[shared],
    )
    mm_sub = mm.add_subparsers(dest="modal_matrix_cmd")
    mm_list = mm_sub.add_parser("list", parents=[shared], help="catalog rows (default marked)")
    mm_list.add_argument("--json", action="store_true")
    mm_list.set_defaults(handler=_cmd_modal_matrix_list)
    mm_show = mm_sub.add_parser("show", parents=[shared], help="one row + cutover hints")
    mm_show.add_argument("model", help="HF id (e.g. Qwen/Qwen3-8B or Qwen/Qwen3-8B-AWQ)")
    mm_show.add_argument("--gpu", default=None, help="override matrix GPU (e.g. A100-40GB:2)")
    mm_show.add_argument("--json", action="store_true")
    mm_show.set_defaults(handler=_cmd_modal_matrix_show)
    mm_env = mm_sub.add_parser(
        "env",
        parents=[shared],
        help='print export lines for eval "$(sandbox modal-matrix env …)"',
    )
    mm_env.add_argument("model", nargs="?", default=None, help="HF id (default: Qwen/Qwen3-8B)")
    mm_env.add_argument("--gpu", default=None, help="override matrix GPU")
    mm_env.set_defaults(handler=_cmd_modal_matrix_env)
    mm.set_defaults(handler=_cmd_modal_matrix_help)

    return parser


def _run_parser(sub, shared):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default=None)
    common.add_argument("--run-id", default=None)
    common.add_argument("--offline", action="store_true")
    common.add_argument("--force", action="store_true")
    common.add_argument("--dry-run", action="store_true")
    common.add_argument("--live", action="store_true")
    common.add_argument("--json", action="store_true")
    common.add_argument("--watch", action="store_true")
    common.add_argument("--job-mode", dest="mode", choices=["endpoint", "modal"], default=None)
    common.add_argument("--max-items", type=int, default=None)
    common.add_argument(
        "--suite",
        default=None,
        help="suite id/alias (track-a|track-b|full) for suite / benchmark-check",
    )
    common.add_argument(
        "--require-hermes",
        action="store_true",
        default=True,
        help="benchmark-check: require Hermes Modal profile (default on)",
    )
    common.add_argument(
        "--modal-profile",
        default=None,
        help="benchmark-check: required active Modal profile (e.g. exios66); overrides Hermes",
    )
    common.add_argument(
        "--allow-non-hermes",
        action="store_true",
        help="benchmark-check: skip Hermes profile requirement",
    )
    g = common.add_mutually_exclusive_group()
    g.add_argument("--mock", action="store_true", default=None)
    g.add_argument("--local", action="store_true", default=None)

    run = sub.add_parser("run", help="Spec-driven job lifecycle (DMR-027)", parents=[shared])
    run_sub = run.add_subparsers(dest="run_cmd")
    pre = run_sub.add_parser("preflight", parents=[common])
    pre.set_defaults(handler=_cmd_run_preflight)
    start = run_sub.add_parser("start", parents=[common])
    start.set_defaults(handler=_cmd_run_start)
    status = run_sub.add_parser("status", parents=[common])
    status.set_defaults(handler=_cmd_run_status)
    resume = run_sub.add_parser("resume", parents=[common])
    resume.set_defaults(handler=_cmd_run_resume)
    cancel = run_sub.add_parser("cancel", parents=[common])
    cancel.set_defaults(handler=_cmd_run_cancel)
    runlist = run_sub.add_parser("list", parents=[common])
    runlist.set_defaults(handler=_cmd_run_list)
    bcheck = run_sub.add_parser(
        "benchmark-check",
        parents=[common],
        help="loud Modal L4 Qwen reproducibility gate (Hermes profile, pins)",
    )
    bcheck.set_defaults(handler=_cmd_run_benchmark_check)
    denv = run_sub.add_parser(
        "deploy-env",
        parents=[common],
        help="print the MODAL_VLLM_* exports a run YAML implies (SAND-032)",
    )
    denv.set_defaults(handler=_cmd_run_deploy_env)
    scrape_p = run_sub.add_parser(
        "scrape-metrics",
        parents=[common],
        help="sample vLLM /metrics per replica into the run dir (SAND-032)",
    )
    scrape_p.add_argument("--label", choices=["before", "after"], required=True)
    scrape_p.set_defaults(handler=_cmd_run_scrape_metrics)
    card_p = run_sub.add_parser(
        "card",
        parents=[common],
        help="SAND-037 score & cost card: --config (one run) or --runbook grid-1l4|grid-2l4 (suite)",
    )
    card_p.add_argument(
        "--runbook",
        default=None,
        choices=["grid-1l4", "grid-2l4"],
        help="write the finalized L4x1 / L4x2 suite card from the per-run cards",
    )
    card_p.add_argument(
        "--master",
        action="store_true",
        help="write reports/SAND-37/SAND-37-MASTER-SCORE-COST-CARD.md (two-page executive) + SAND-37-MASTER-APPENDIX.md across SAND-37 / SAND-39 / SAND-40 postures",
    )
    card_p.add_argument(
        "--gate",
        action="store_true",
        help="SAND-040 chunked cell: exit 1 unless every document is ok and every expected chunk reached vLLM",
    )
    card_p.add_argument(
        "--record-metered",
        nargs=3,
        metavar=("STUDY", "METERED_USD", "BILLED_USD"),
        default=None,
        help="record a study's session Modal spend (teardown spend check) for the master card, e.g. SAND-39 0.62 0.00",
    )
    card_p.set_defaults(handler=_cmd_run_card)
    export_bt = run_sub.add_parser(
        "export-bt",
        parents=[common],
        help="write offline Braintrust-Experiment-shaped rows (gitignored; SAND-032)",
    )
    export_bt.set_defaults(handler=_cmd_run_export_bt)
    dispose_p = run_sub.add_parser(
        "dispose",
        parents=[common],
        help="delete a run's offline BT rows once its report is tracked in git",
    )
    dispose_p.add_argument("--report", required=True)
    dispose_p.set_defaults(handler=_cmd_run_dispose)
    suite_p = run_sub.add_parser(
        "suite",
        parents=[common],
        help="two-operator / full specialist suite runbook (DMR-077)",
    )
    suite_p.add_argument(
        "--list",
        action="store_true",
        help="list suite ids under config/runs/suites/",
    )
    suite_p.add_argument(
        "--check",
        action="store_true",
        help="run benchmark-check on every config in the suite",
    )
    suite_p.add_argument(
        "--print-loop",
        action="store_true",
        help="print bash preflight+start loop only",
    )
    suite_p.add_argument(
        "--execute",
        action="store_true",
        help="chain preflight+start --watch for each config (no teardown)",
    )
    suite_p.set_defaults(handler=_cmd_run_suite)
    run.set_defaults(handler=_cmd_run_help)
    return common


def _agent_models(args: argparse.Namespace) -> dict[str, str]:
    from mailroom_sandbox.overlay import parse_agent_models

    return parse_agent_models(getattr(args, "agent_models", None) or [])


def _print(obj: object) -> None:
    if isinstance(obj, (dict, list)):
        print(json.dumps(obj, indent=2, default=str))
    else:
        print(obj)


def _cmd_up(args: argparse.Namespace) -> int:
    from mailroom_sandbox.compose import default_profiles_for, run_compose

    profiles = args.compose_profiles or default_profiles_for(args.profile)
    extra = ["up", "-d"] if args.detach else ["up"]
    run_compose(profiles, *extra)
    return 0


def _cmd_down(args: argparse.Namespace) -> int:
    from mailroom_sandbox.compose import default_profiles_for, run_compose

    profiles = args.compose_profiles or default_profiles_for(args.profile)
    run_compose(profiles, "down")
    return 0


def _cmd_health(args: argparse.Namespace) -> int:
    from mailroom_sandbox.health import health_check, probe_models
    from mailroom_sandbox.overlay import load_profile as _lp
    from mailroom_sandbox.runtime import load_env_file

    # `.env` may carry VLLM_BASE_URL/VLLM_API_KEY for a deployed Modal endpoint
    # — without it the probe reports on localhost (DMR-048).
    load_env_file()
    result = health_check(args.profile)
    host = (
        os.environ.get("LANGFUSE_HOST")
        or os.environ.get("LANGFUSE_BASE_URL")
        or "http://localhost:3000"
    )
    langfuse = probe_models(
        {
            "name": "langfuse",
            "base_url": host,
            "health": {"models_url": f"{host.rstrip('/')}/api/public/health"},
        }
    )
    result["langfuse"] = langfuse.as_dict()
    phoenix = probe_models(
        {
            "name": "phoenix",
            "base_url": os.environ.get("PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces").rsplit("/v1", 1)[0],
            # hub#56: derive the healthz URL from the resolved Phoenix base —
            # the old hardcoded localhost:6006/healthz probed the wrong server
            # whenever PHOENIX_ENDPOINT pointed at a remote Phoenix.
            "health": {"models_url": (os.environ.get("PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces").rsplit("/v1", 1)[0]) + "/healthz"},
        }
    )
    result["phoenix"] = phoenix.as_dict()
    _print(result)
    return 0 if result.get("ok") else 1


def _cmd_pull_models(args: argparse.Namespace) -> int:
    from mailroom_sandbox.compose import pull_ollama_models
    from mailroom_sandbox.overlay import serving_family

    profile = load_profile(args.profile)
    models = list(args.models) or list(profile.get("pull_models") or [])
    family = serving_family(profile)
    if family == "vllm":
        # vLLM weights live in the HF cache — `ollama pull` would be wrong.
        # Modal: pre-warm the HF Volume; local compose: first serve downloads.
        name = str(profile.get("name") or "")
        model = models[0] if models else str(profile.get("default_model") or "Qwen/Qwen3-8B")
        if "modal" in name:
            print(
                "vLLM profile is Modal-backed — weights are cached on the Modal Volume.\n"
                f"Pre-warm:  MODAL_VLLM_MODEL={model} modal run deploy/modal_vllm.py::download_model\n"
                "(requires the [deploy] extra + `modal token new`; run from the package root)"
            )
        else:
            print(
                "vLLM profile serves weights from the HF cache — no pull step.\n"
                f"First boot downloads {model} into the compose hf_cache volume; "
                "pre-warm with `docker compose --profile vllm up vllm`."
            )
        return 0
    return pull_ollama_models(models)


def _cmd_fetch_deps(args: argparse.Namespace) -> int:
    """Refresh the TRACKED vendor snapshots (DMR-057/DMR-070).

    The family code ships in-repo (DMR-057), so a fresh checkout needs no
    network. Refresh order (DMR-070 rework): when the sandbox checkout lives
    inside the Digital-Mailroom monorepo, the workspace package is the
    development source of truth and the vendor tree MIRRORS it — carrying
    BOTH content updates AND deletions (a copy-only refresh is how the
    removed docclass-era compliance files survived their upstream deletion).
    Standalone clones fall back to the tag-based clone refresh, with a loud
    warning that tags can lag removals (the v0.7.1 tag predates 59c47401).
    """
    print(
        "vendor trees are tracked snapshots (self-contained); fetch-deps "
        "refreshes them — workspace mirror first (offline, carries "
        "deletions), tag-based clone fallback for standalone clones"
    )
    rc = 0
    for name, tag, url in _VENDOR_PINS:
        ws = _monorepo_workspace_pkg(name)
        if ws is not None:
            rc = rc or _refresh_vendor_from_workspace(name, ws)
        else:
            print(
                f"== {name}: no monorepo workspace detected — falling back to the "
                f"tag-based refresh ({tag}); NOTE tags can lag removals — prefer "
                "the monorepo workspace as the source of truth",
                file=sys.stderr,
            )
            rc = rc or _refresh_vendor(name, tag, url)
    if getattr(args, "visualizer", False):
        dest = vendor_dir() / "The-Mailroom"
        if dest.is_dir() and (dest / ".git").exists():
            pull = subprocess.run(
                ["git", "-C", str(dest), "pull", "--ff-only"],
                capture_output=True,
                text=True,
                check=False,
            )
            if pull.returncode != 0:
                print(
                    f"!! visualizer refresh (git pull --ff-only) failed: "
                    f"{pull.stderr.strip() or pull.stdout.strip()}",
                    file=sys.stderr,
                )
                rc = rc or 1
        else:
            rc = rc or subprocess.run(
                ["git", "clone", "--depth", "1", "https://github.com/Exios66/The-Mailroom.git", str(dest)]
            ).returncode
    return rc


# (vendor name, pinned tag, upstream url) — STANDALONE-clone fallback pins.
# In the monorepo, fetch-deps ignores these and mirrors the workspace package
# instead (DMR-057/070): tags can lag removals — the v0.7.1 tag predates the
# five-class taxonomy removal (59c47401), so a tag-based refresh of
# llm-mailroom would resurrect the deleted docclass-era files.
_VENDOR_PINS: tuple[tuple[str, str, str], ...] = (
    ("llm-mailroom", "v0.7.1", "https://github.com/Exios66/llm-mailroom.git"),
    ("llm-dojo-scoring", "v0.15.0", "https://github.com/Exios66/llm-dojo-scoring.git"),
)


def _monorepo_workspace_pkg(name: str):
    """Locate the monorepo workspace package for a vendored family member.

    Returns the package dir to mirror (llm-mailroom: its ``src/``;
    llm-dojo-scoring: its root-level ``llm_dojo_scoring/`` package dir), or
    ``None`` when the sandbox checkout is standalone (no monorepo sibling).
    """
    mono = repo_root().parents[1]  # packages/<sandbox> -> monorepo root
    pkg = mono / "packages" / name
    if (pkg / "llm_dojo_scoring").is_dir():
        return pkg / "llm_dojo_scoring"
    if (pkg / "src").is_dir():
        return pkg / "src"
    return None


# Mirror exclusions — keep in sync with scripts/sync_vendor.py (monorepo)
# and tests/test_vendor_drift.py.
_VENDOR_EXCLUDE_NAMES = {"__pycache__"}
_VENDOR_EXCLUDE_SUFFIXES = {".pyc"}
_VENDOR_EXCLUDE_REL_PREFIXES = {"legalbench/reports"}
_VENDOR_EXCLUDE_TOP_LEVEL_DIRS = {"tests"}


def _vendor_rel_excluded(rel: Path) -> bool:
    if any(part in _VENDOR_EXCLUDE_NAMES for part in rel.parts):
        return True
    if rel.parts and rel.parts[0] in _VENDOR_EXCLUDE_TOP_LEVEL_DIRS:
        return True
    if any(part.endswith(".egg-info") for part in rel.parts):
        return True
    if rel.suffix in _VENDOR_EXCLUDE_SUFFIXES:
        return True
    if any("/".join(rel.parts).startswith(p) for p in _VENDOR_EXCLUDE_REL_PREFIXES):
        return True
    return False


def _refresh_vendor_from_workspace(name: str, ws_root: Path) -> int:
    """Mirror the monorepo workspace package onto ``vendor/<name>`` (DMR-070).

    Deletion-carrying exact mirror: after a run the vendored tree is an exact
    image of the workspace package (minus the shared exclusions), so a
    subsequent drift-guard run (tests/test_vendor_drift.py) passes. VENDOR.md
    lives OUTSIDE the mirrored ``src`` root and is never touched.
    """
    import shutil

    dest_root = vendor_dir() / name / "src"
    if ws_root.name != "src":
        # llm-dojo-scoring layout: the package dir relocates under src/
        # (mirrors the tag-based path's DMR-058 normalization).
        dest_root = dest_root / ws_root.name
    dest_root.parent.mkdir(parents=True, exist_ok=True)

    wanted: set[str] = set()
    for path in sorted(ws_root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ws_root)
        if _vendor_rel_excluded(rel):
            continue
        wanted.add(str(rel))
        dst = dest_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
    removed = 0
    if dest_root.is_dir():
        for path in sorted(dest_root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            rel = path.relative_to(dest_root)
            if path.is_file():
                if str(rel) not in wanted:
                    path.unlink()
                    removed += 1
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
    print(
        f"== mirrored vendor/{name} from the monorepo workspace "
        f"({ws_root}) — {len(wanted)} file(s), {removed} deleted; commit the diff"
    )
    return 0


def _package_src_dir(clone_root: Path) -> Path | None:
    """Locate the package dir in a vendored-family clone (DMR-058).

    llm-mailroom keeps ``src/``; llm-dojo-scoring ships the package at the
    repo root (``llm_dojo_scoring/``) and the snapshot normalizes it under
    ``src/``. Returns None when the layout is unrecognized — the caller must
    NOT touch the tracked tree in that case.
    """
    for candidate in ("src", "llm_dojo_scoring", "llm_mailroom"):
        p = clone_root / candidate
        if p.is_dir():
            return p
    return None


def _refresh_vendor(name: str, tag: str, url: str) -> int:
    import shutil

    stamp = subprocess.run(
        ["git", "ls-remote", "--tags", url, tag],
        capture_output=True,
        text=True,
        check=False,
    )
    if stamp.returncode != 0 or not stamp.stdout.strip():
        print(f"!! could not resolve {tag} of {url}", file=sys.stderr)
        return 1
    work = vendor_dir() / ".refresh" / name
    if work.is_dir():
        shutil.rmtree(work)
    work.parent.mkdir(parents=True, exist_ok=True)
    clone = subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", tag, url, str(work)],
        capture_output=True,
        text=True,
        check=False,
    )
    if clone.returncode != 0:
        print(f"!! clone {name}@{tag} failed: {clone.stderr.strip()}", file=sys.stderr)
        return 1
    dest = vendor_dir() / name
    dest.mkdir(parents=True, exist_ok=True)
    # Mirror the committed layout — llm-mailroom keeps src/; llm-dojo-scoring
    # ships the package at the repo ROOT (llm_dojo_scoring/) and the snapshot
    # normalizes it under src/. Validate the source BEFORE touching dest so a
    # layout surprise can never half-wipe the tracked tree (DMR-058).
    package_src = _package_src_dir(work)
    if package_src is None:
        print(
            f"!! unexpected layout in {name}@{tag} clone (no src/, llm_dojo_scoring/, "
            f"or llm_mailroom/ at root) — vendor/{name} left untouched",
            file=sys.stderr,
        )
        shutil.rmtree(work, ignore_errors=True)
        return 1
    shutil.rmtree(dest / "src", ignore_errors=True)
    # The tracked layout is vendor/<name>/src/<pkgdir> for BOTH trees:
    # llm-mailroom already ships src/<pkgdir>, llm-dojo-scoring ships the
    # package at the clone root and gets normalized under src/ (DMR-058).
    dest_src = dest / "src" / package_src.name if package_src.name != "src" else dest / "src"
    shutil.copytree(package_src, dest_src, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"))
    head_proc = subprocess.run(
        ["git", "-C", str(work), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if head_proc.returncode != 0:
        head = "unknown"
        print(
            f"!! could not read the refreshed {name} commit: "
            f"{head_proc.stderr.strip() or head_proc.stdout.strip()}",
            file=sys.stderr,
        )
    else:
        head = head_proc.stdout.strip()
    shutil.rmtree(work, ignore_errors=True)
    print(f"== refreshed vendor/{name} @ {tag} (commit {head[:12]}) — commit the diff")
    return 0


def _cmd_cutover(args: argparse.Namespace) -> int:
    activation = activate(
        args.profile,
        model=args.model,
        prompt_variant=args.prompt,
        agent_models=_agent_models(args),
    )
    print(f"profile={activation.profile_name} taxonomy={activation.taxonomy_path}")
    print(f"{'Agent':<35} {'Provider':<15} {'Model'}")
    print("-" * 80)
    for name, provider, model in activation.assignments:
        print(f"{name:<35} {provider:<15} {model}")
    return 0


def _cmd_agents_list(args: argparse.Namespace) -> int:
    from mailroom_sandbox.eval.agents import RETIRED_AGENTS, SPECS
    from mailroom_sandbox.overlay import agent_roster, load_yaml

    activation = activate(
        args.profile,
        model=args.model,
        prompt_variant=args.prompt,
        agent_models=_agent_models(args),
    )
    roster = agent_roster(load_yaml(activation.taxonomy_path))
    evals = sorted(SPECS)
    _print(
        {
            "profile": activation.profile_name,
            "agents": roster,
            "eval_tasks": evals,
            "retired": list(RETIRED_AGENTS),
        }
    )
    return 0


def _cmd_subagents_packages(args: argparse.Namespace) -> int:
    from mailroom_sandbox.subagents import list_packages
    from mailroom_sandbox.subagents.family import load_family_document

    doc = load_family_document()
    payload = {"packages": doc.get("packages") or {}}
    if getattr(args, "json", False):
        _print(payload)
    else:
        for name in list_packages():
            role = (payload["packages"].get(name) or {}).get("role") or ""
            print(f"{name:28} {role}")
    return 0


def _cmd_subagents_list(args: argparse.Namespace) -> int:
    from mailroom_sandbox.subagents import load_roster

    package = getattr(args, "package", None)
    rows = []
    for entry in load_roster(package=package):
        rows.append(
            {
                "id": entry.id,
                "title": entry.title,
                "tags": list(entry.tags),
                "harnesses": list(entry.harnesses),
                "home_package": entry.home_package,
                "family_source": entry.family_source,
                "opencode": str(entry.opencode_path()),
                "cursor": str(entry.cursor_path()),
            }
        )
    if getattr(args, "json", False):
        _print({"subagents": rows})
    else:
        for row in rows:
            tags = ",".join(row["tags"]) or "-"
            print(f"{row['id']:24} {row['title']:32} [{tags}]")
    return 0


def _cmd_subagents_show(args: argparse.Namespace) -> int:
    from mailroom_sandbox.subagents.parse_opencode import parse_opencode_markdown
    from mailroom_sandbox.subagents.roster import get_subagent

    entry = get_subagent(args.id, package=getattr(args, "package", None))
    if entry is None:
        print(f"unknown subagent: {args.id}", file=sys.stderr)
        return 1
    doc = parse_opencode_markdown(entry.opencode_path().read_text(encoding="utf-8"))
    payload = {
        "id": entry.id,
        "title": entry.title,
        "tags": list(entry.tags),
        "harnesses": list(entry.harnesses),
        "home_package": entry.home_package,
        "family_source": entry.family_source,
        "cursor_invoke_hint": entry.cursor_invoke_hint,
        "opencode_frontmatter": doc.frontmatter,
        "opencode_path": str(entry.opencode_path()),
        "cursor_path": str(entry.cursor_path()),
    }
    if getattr(args, "json", False):
        _print(payload)
    else:
        _print(payload)
        print("\n--- prompt preview (first 40 lines) ---")
        lines = doc.body.splitlines()
        for line in lines[:40]:
            print(line)
        if len(lines) > 40:
            print(f"... ({len(lines) - 40} more lines)")
    return 0


def _cmd_subagents_doctor(args: argparse.Namespace) -> int:
    from mailroom_sandbox.subagents.doctor import (
        apply_framework_to_agents,
        apply_framework_to_global_profiles,
        findings_to_dict,
        run_doctor,
    )

    root = Path(args.root).expanduser().resolve() if args.root else None
    if args.apply_framework:
        roster_written = apply_framework_to_agents(
            root=root,
            package=getattr(args, "package", None),
            dry_run=bool(args.dry_run),
        )
        global_written = apply_framework_to_global_profiles(dry_run=bool(args.dry_run))
        payload = {
            "apply_framework": True,
            "dry_run": bool(args.dry_run),
            "roster_paths": [str(p) for p in roster_written],
            "global_profile_paths": [str(p) for p in global_written],
        }
        if args.json:
            _print(payload)
        else:
            for p in roster_written + global_written:
                print(p)
        return 0

    extra = tuple(
        Path(p).expanduser().resolve() for p in (args.also_root or []) if p
    )
    report = run_doctor(
        root=root,
        package=getattr(args, "package", None),
        include_global=not args.no_global,
        extra_roots=extra,
    )
    payload = findings_to_dict(report)
    if args.json:
        _print(payload)
    else:
        for f in report.findings:
            loc = f" ({f.path})" if f.path else ""
            hint = f" — {f.hint}" if f.hint else ""
            print(f"[{f.severity}] {f.code}: {f.message}{loc}{hint}")
        s = payload["summary"]
        print(f"\nSummary: {s['fail']} fail, {s['warn']} warn")
    return 1 if payload["summary"]["fail"] else 0


def _cmd_subagents_sync(args: argparse.Namespace) -> int:
    from mailroom_sandbox.subagents import sync_harness

    root = Path(args.root).expanduser().resolve() if args.root else None
    result = sync_harness(
        args.harness,
        root=root,
        package=getattr(args, "package", None),
        dry_run=bool(args.dry_run),
    )
    if isinstance(result, list):
        _print(
            {
                "harness": args.harness,
                "dry_run": bool(args.dry_run),
                "results": [
                    {
                        "harness": r.harness,
                        "written": [str(p) for p in r.written],
                        "skipped": r.skipped,
                    }
                    for r in result
                ],
            }
        )
    else:
        _print(
            {
                "harness": result.harness,
                "dry_run": bool(args.dry_run),
                "written": [str(p) for p in result.written],
                "skipped": result.skipped,
            }
        )
    return 0


def _cmd_subagents_materialize(args: argparse.Namespace) -> int:
    from mailroom_sandbox.subagents import materialize_package

    dest = Path(args.root).expanduser().resolve()
    source = Path(args.source_root).expanduser().resolve() if args.source_root else None
    result = materialize_package(
        args.package,
        dest_root=dest,
        source_root=source,
        dry_run=bool(args.dry_run),
    )
    _print(
        {
            "package": result.package,
            "dry_run": bool(args.dry_run),
            "family_roster": str(result.family_roster_written) if result.family_roster_written else None,
            "prompts_copied": [str(p) for p in result.prompts_copied],
        }
    )
    return 0


def _cmd_subagents_propagate(args: argparse.Namespace) -> int:
    from mailroom_sandbox.subagents import propagate_family_checkouts

    mono = Path(args.monorepo_root).expanduser().resolve() if args.monorepo_root else None
    result = propagate_family_checkouts(
        monorepo_root=mono,
        packages=getattr(args, "packages", None),
        dry_run=bool(args.dry_run),
    )
    payload = {
        "source_root": str(result.source_root),
        "monorepo_root": str(result.monorepo_root) if result.monorepo_root else None,
        "dry_run": bool(args.dry_run),
        "packages": [
            {
                "package": row.package,
                "dest_root": str(row.dest_root),
                "materialized": row.materialized,
                "sync_written": row.sync_written,
                "skipped": row.skipped,
                "error": row.error,
            }
            for row in result.packages
        ],
    }
    if getattr(args, "json", False):
        _print(payload)
    else:
        _print(payload)
    return 1 if any(row.error for row in result.packages) else 0


def _cmd_agents_show(args: argparse.Namespace) -> int:
    from mailroom_sandbox.eval.agents import SPECS
    from mailroom_sandbox.overlay import agent_roster, load_yaml

    activation = activate(
        args.profile,
        model=args.model,
        prompt_variant=args.prompt,
        agent_models=_agent_models(args),
    )
    roster = {row["agent"]: row for row in agent_roster(load_yaml(activation.taxonomy_path))}
    spec = SPECS.get(args.name)
    payload = roster.get(args.name, {"agent": args.name, "enabled": False})
    if spec:
        payload["observation"] = spec.observation
        payload["eval_task"] = spec.name
        payload["dojo_profile"] = spec.dojo_profile
    _print(payload)
    return 0


def _mailroom_env() -> dict[str, str]:
    env = os.environ.copy()
    parts = [str(repo_root() / "src")]
    for src in (resolve_mailroom_src(), resolve_dojo_src()):
        if src is not None:
            parts.insert(0, str(src))
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(parts + ([existing] if existing else []))
    env.setdefault("OBSERVABILITY_ENVIRONMENT", os.environ.get("OBSERVABILITY_ENVIRONMENT") or "pilot")
    return env


def _cmd_watcher(args: argparse.Namespace) -> int:
    activate(args.profile, model=args.model, prompt_variant=args.prompt, agent_models=_agent_models(args))
    return subprocess.call([sys.executable, "-m", "pipeline.watcher"], env=_mailroom_env())


def _cmd_api(args: argparse.Namespace) -> int:
    activate(args.profile, model=args.model, prompt_variant=args.prompt, agent_models=_agent_models(args))
    return subprocess.call([sys.executable, "-m", "api.main"], env=_mailroom_env())


def _mock_for(args: argparse.Namespace, *, subcommand: str) -> bool:
    """Resolve the mock flag; warn when a vLLM/Modal profile would silently mock.

    Live-or-loud (DMR-048): a vLLM/Modal profile without --local (and without
    an explicit --mock) used to run a mock that looks like a real eval. The
    warning keeps smoke runs working while surfacing the hazard.
    """
    from mailroom_sandbox.overlay import serving_family

    explicit_mock = bool(getattr(args, "mock", False))
    mock = explicit_mock or not bool(getattr(args, "local", False))
    if mock and not explicit_mock and serving_family(load_profile(args.profile)) == "vllm":
        print(
            f"warning: {subcommand} would run MOCK against the vLLM profile "
            f"{args.profile!r} — pass --local for a live run, or --mock to make "
            "the mock explicit (DMR-048 live-or-loud)"
        )
    return mock


def _cmd_pilot(args: argparse.Namespace) -> int:
    from mailroom_sandbox.eval.runners import run_pipeline_eval

    mock = _mock_for(args, subcommand="pilot")
    os.environ["SANDBOX_RUN_MODE"] = "mock" if mock else "local"
    result = run_pipeline_eval(
        mock=mock,
        sample=args.sample,
        dry_run=args.dry_run,
        experiment_name="sandbox_pilot",
        profile=args.profile,
        model=args.model,
        prompt_version=args.prompt,
    )
    _print(result)
    return 0


def _cmd_hf_pilot(args: argparse.Namespace) -> int:
    from mailroom_sandbox.datasets import load_hf_fixtures

    rows = load_hf_fixtures()
    if args.check or args.dry_run:
        _print({"ok": True, "n": len(rows), "classes": sorted({r.get("doc_type") for r in rows})})
        return 0 if rows else 1
    from mailroom_sandbox.eval.runners import run_sorter_eval

    mock = _mock_for(args, subcommand="eval")
    result = run_sorter_eval(
        mock=mock,
        sample=len(rows) or None,
        experiment_name="sandbox_hf_pilot",
        profile=args.profile,
        model=args.model,
        prompt_version=args.prompt,
    )
    _print(result)
    return 0


def _cmd_legalbench(args: argparse.Namespace) -> int:
    from mailroom_sandbox.eval.runners import run_legalbench_eval

    mock = _mock_for(args, subcommand="legalbench")
    name = f"sandbox_legalbench_{args.task}"
    if args.suite:
        name += f"_n{args.n or 0}_s{args.seed}"
    try:
        result = run_legalbench_eval(
            mock=mock,
            sample=args.n,
            seed=args.seed,
            task=args.task,
            suite=args.suite,
            dry_run=args.dry_run,
            experiment_name=name,
            profile=args.profile,
            model=args.model,
        )
    except ValueError as exc:
        # Loud guard (unwired task / suite without --n / empty rows): clean
        # one-liner, not a traceback (DMR-058).
        print(f"error: {exc}")
        return 1
    except Exception as exc:  # live-or-loud (DMR-049/058): CorpusUnavailable &
        # missing-corpus keep naming the fetch command, without a traceback.
        print(f"error: {type(exc).__name__}: {exc}")
        return 1
    _print(result)
    return 0


def _cmd_eval(args: argparse.Namespace) -> int:
    from mailroom_sandbox.eval import runners
    from mailroom_sandbox.eval.agents import SPECS
    from mailroom_sandbox.tui.session import MailroomConsole

    mock = _mock_for(args, subcommand="eval")
    os.environ["SANDBOX_RUN_MODE"] = "mock" if mock else "local"
    console = MailroomConsole()
    exp = args.experiment_name or f"sandbox_{args.task}"
    console.run_banner(run_id=exp, task=args.task, subtitle="sandbox eval")
    console.phase("EVAL", "mock" if mock else args.profile or "local")
    kwargs = {
        "mock": mock,
        "sample": args.sample,
        "dry_run": args.dry_run,
        "experiment_name": args.experiment_name or f"sandbox_{args.task}",
        "profile": args.profile,
        "model": args.model,
        "agent_models": _agent_models(args),
    }
    def _eval_progress(done: int, total: int, ok: int, errors: int) -> None:
        console.progress(done, total, ok=ok, errors=errors)

    if args.task in SPECS:
        result = runners.run_isolated_eval(
            args.task, prompt_version=args.prompt, progress_cb=_eval_progress, **kwargs
        )
    elif args.task == "pipeline":
        result = runners.run_pipeline_eval(
            prompt_version=args.prompt, connected=True, **kwargs
        )
    elif args.task == "extract":
        result = runners.run_extract_eval(prompt_version=args.prompt, **kwargs)
    elif args.task == "chained":
        result = runners.run_chained_eval(prompt_version=args.prompt, **kwargs)
    elif args.task == "local_vs_api":
        result = runners.run_local_vs_api_eval(
            prompt_version=args.prompt,
            from_log=bool(getattr(args, "from_log", False)),
            **kwargs,
        )
    elif args.task == "sorter_vs_modernbert":
        result = runners.run_sorter_vs_modernbert_eval(
            prompt_version=args.prompt,
            from_log=bool(getattr(args, "from_log", False)),
            **kwargs,
        )
    elif args.task == "legalbench":
        result = runners.run_legalbench_eval(**kwargs)
    else:
        # DMR-056: never fall through to the LegalBench runner for an unknown
        # task — a future composite registered without its own arm would have
        # been silently misrouted (scorecard pollution).
        raise SystemExit(f"error: task {args.task!r} has no dispatch arm in _cmd_eval")
    scores = result.get("scores") if isinstance(result, dict) else None
    summary = ""
    if isinstance(scores, dict) and scores.get("accuracy") is not None:
        summary = f"accuracy {scores['accuracy']}"
    elif isinstance(result, dict) and result.get("n") is not None:
        summary = f"n={result['n']}"
    console.complete(state="done", summary=summary or exp)
    _print(result)
    return 0


def _cmd_matrix(args: argparse.Namespace) -> int:
    from mailroom_sandbox.eval.matrix import run_matrix
    from mailroom_sandbox.tui.session import MailroomConsole

    mock = _mock_for(args, subcommand="matrix")
    console = MailroomConsole()
    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    console.run_banner(
        run_id=f"matrix_{args.task}",
        task=args.task,
        subtitle=f"{len(providers)} providers × {len(models)} models",
    )
    result = run_matrix(
        task=args.task,
        providers=providers,
        models=models,
        prompts=[x.strip() for x in args.prompts.split(",") if x.strip()],
        sample=args.sample,
        seed=args.seed,
        mock=mock,
        dry_run=args.dry_run,
        console=console,
    )
    if args.dry_run:
        console.complete(state="prepared", summary=f"{result.get('n', 0)} cells planned")
    else:
        console.complete(state="done", summary=f"{len(result.get('results') or [])} cells")
    _print(result)
    return 0


def _cmd_datasets_help(args: argparse.Namespace) -> int:
    print("Use: sandbox datasets pull | sandbox datasets sample | sandbox datasets prepare")
    return 0


def _cmd_datasets_pull(args: argparse.Namespace) -> int:
    from mailroom_sandbox.datasets import pull_hf_dataset

    try:
        pull_hf_dataset(
            args.dataset,
            split=args.split,
            max_rows=args.max_rows,
            revision=args.revision,
            config=args.config,
            per_class=getattr(args, "per_class", 0) or None,
            sample_seed=getattr(args, "sample_seed", 42),
        )
    except ModuleNotFoundError as exc:
        # The Hub client lives in the [hf]/[dev] extras (offline-first base
        # install) — say how to get it instead of a bare traceback (DMR-058).
        print(f"error: {type(exc).__name__}: {exc}\n(hint: pip install -e \".[hf]\" — or -e \".[dev]\")")
        return 1
    except Exception as exc:  # live-or-loud (DMR-056): a failed pull is exit 1
        print(f"error: {type(exc).__name__}: {exc}")
        return 1
    return 0


def _cmd_datasets_sample(args: argparse.Namespace) -> int:
    from pathlib import Path

    from mailroom_sandbox.datasets import sample_cached_corpus

    classes = [c.strip() for c in (args.classes or "").split(",") if c.strip()]
    source = Path(args.source) if args.source else None
    dest = Path(args.out) if args.out else None
    try:
        sample_cached_corpus(
            args.per_class,
            sample_seed=args.sample_seed,
            source=source,
            dest=dest,
            classes=classes or None,
        )
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}")
        return 1
    return 0


def _cmd_datasets_prepare(args: argparse.Namespace) -> int:
    from mailroom_sandbox.prep import prepare_offline_datasets

    activate(args.profile, model=args.model, prompt_variant=args.prompt, agent_models=_agent_models(args))
    summary = prepare_offline_datasets()
    _print(summary)
    return 0 if summary.get("counts", {}).get("fixtures", 0) else 1


def _cmd_traces_help(args: argparse.Namespace) -> int:
    print("Use: sandbox traces export | sandbox traces pack RUN_ID [--dest DIR] [--prune]")
    return 0


def _cmd_traces_pack(args: argparse.Namespace) -> int:
    from mailroom_sandbox.job import trace_pack

    if args.prune and not args.dest:
        print("error: --prune needs --dest (or SANDBOX_TRACE_UPLOAD_DIR): local copies go only after a verified upload")
        return 2
    try:
        result = trace_pack.pack(
            args.run_id,
            experiment=args.experiment,
            runner=args.runner,
            dest=Path(args.dest).expanduser() if args.dest else None,
            date=args.date,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}")
        return 1
    if args.dest and not result["verified"]:
        _print(result)
        print("error: uploaded copy did not verify; nothing pruned")
        return 1
    if args.prune:
        result["pruned"] = trace_pack.prune(result)
    _print(result)
    return 0


def _cmd_traces_export(args: argparse.Namespace) -> int:
    from mailroom_sandbox.eval.tracing import export_traces

    print(export_traces())
    return 0


def _cmd_profiles(args: argparse.Namespace) -> int:
    _print(list_profiles())
    return 0


def _tunnel_spec(args: argparse.Namespace):
    from mailroom_sandbox.overlay import load_profile
    from mailroom_sandbox.tunnel import TunnelError, tunnel_spec

    try:
        return tunnel_spec(load_profile(args.profile))
    except TunnelError as exc:
        print(f"ERROR {exc}")
        raise SystemExit(1) from exc


def _cmd_tunnel_help(args: argparse.Namespace) -> int:
    print("Use: sandbox tunnel plan | up | status | down")
    return 0


def _cmd_tunnel_plan(args: argparse.Namespace) -> int:
    from mailroom_sandbox.tunnel import build_ssh_argv

    spec = _tunnel_spec(args)
    print(" ".join(build_ssh_argv(spec)))
    print(f"# sandbox side: SANDBOX_PROFILE={spec.profile} (base_url {spec.base_url})")
    return 0


def _cmd_tunnel_up(args: argparse.Namespace) -> int:
    from mailroom_sandbox.tunnel import spawn

    spec = _tunnel_spec(args)
    pid = spawn(spec)
    print(f"tunnel up: pid {pid} forwarding localhost:{spec.local_port} -> {spec.destination}:{spec.remote_port}")
    print(f"stop with: sandbox tunnel --profile {spec.profile} down")
    return 0


def _cmd_tunnel_status(args: argparse.Namespace) -> int:
    from mailroom_sandbox.tunnel import is_up, read_pid

    spec = _tunnel_spec(args)
    _print(
        {
            "profile": spec.profile,
            "local_port": spec.local_port,
            "destination": spec.destination,
            "port_answering": is_up(spec.local_port),
            "pid": read_pid(spec.profile),
        }
    )
    return 0


def _cmd_tunnel_down(args: argparse.Namespace) -> int:
    from mailroom_sandbox.tunnel import terminate

    spec = _tunnel_spec(args)
    pid = terminate(spec)
    if pid is None:
        print(f"no recorded tunnel for profile '{spec.profile}'")
        return 0
    print(f"tunnel down: killed pid {pid}")
    return 0


def _cmd_run_help(args):
    print(
        "Use: sandbox run preflight | start | status | resume | cancel | list | "
        "benchmark-check | suite  --config <run.yaml> | --suite track-a|track-b|full"
    )
    return 0


def _cmd_run_benchmark_check(args) -> int:
    """Loud Modal L4 Qwen + Modal profile gate before specialist suite."""
    from mailroom_sandbox.job.benchmark_check import (
        check_benchmark_posture,
        check_suite_benchmark_posture,
    )
    from mailroom_sandbox.job.spec import load_run_spec

    suite_name = (getattr(args, "suite", None) or "").strip()
    modal_profile = (getattr(args, "modal_profile", None) or "").strip() or None
    require_hermes = not bool(getattr(args, "allow_non_hermes", False)) and modal_profile is None
    if suite_name:
        report = check_suite_benchmark_posture(
            suite_name,
            require_hermes=require_hermes,
            require_modernbert=False,
        )  # suite YAML carries its own Modal profile (sand032-sweep → exios66)
    else:
        spec = None
        if getattr(args, "config", None):
            spec = load_run_spec(args.config)
        report = check_benchmark_posture(
            spec=spec,
            require_hermes=require_hermes,
            require_modernbert=False,
            expected_modal_profile=modal_profile,
        )
    if getattr(args, "json", False):
        _print(report)
    else:
        print(report.get("markdown", ""))
        for err in report.get("errors") or []:
            print(f"ERROR: {err}", file=sys.stderr)
    return 0 if report.get("ok") else 1


def _cmd_run_deploy_env(args) -> int:
    """SAND-032: YAML is the source of truth for deploy knobs — render it."""
    from mailroom_sandbox.job.deploy_env import render_exports
    from mailroom_sandbox.job.spec import load_run_spec

    if not getattr(args, "config", None):
        print("ERROR: --config required", file=sys.stderr)
        return 2
    sys.stdout.write(render_exports(load_run_spec(args.config)))
    return 0


def _cmd_run_scrape_metrics(args) -> int:
    """SAND-032: per-replica vLLM /metrics snapshot (measured TTFT, KV, preemptions)."""
    from mailroom_sandbox.job import spec as spec_mod
    from mailroom_sandbox.job import vllm_metrics

    if not getattr(args, "config", None):
        print("ERROR: --config required", file=sys.stderr)
        return 2
    spec = spec_mod.load_run_spec(args.config)
    expected = spec.engine.modal.max_containers if spec.engine.modal else 1
    result = vllm_metrics.scrape(
        spec_mod.engine_base_url(spec),
        os.environ.get("VLLM_API_KEY", "").strip(),
        expected=expected,
    )
    dest = spec_mod.runs_root() / spec_mod.resolve_run_id(spec) / f"vllm_metrics_{args.label}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(f"{result['coverage']} → {dest}")
    for err in result.get("errors") or []:
        print(f"WARN: scrape error: {err}", file=sys.stderr)
    return 0


def _cmd_run_card(args) -> int:
    """SAND-037: per-run card under reports/SAND-37/<shape>/<specialist>/, or the suite card."""
    from mailroom_sandbox.job import grid_cards

    if getattr(args, "record_metered", None):
        from mailroom_sandbox.job.grid_master import record_metered

        study, metered, billed = args.record_metered
        print(f"metered spend → {record_metered(study, float(metered), float(billed))}")
        if not getattr(args, "master", False):
            return 0
    if getattr(args, "master", False):
        from mailroom_sandbox.job.grid_master import write_master

        from mailroom_sandbox.job.grid_reader import write_reader

        paths = write_master()
        print(f"master card → {paths['md']} (+ appendix {paths['appendix']})")
        reader = write_reader()
        print(f"reader report → {reader['md']} (+ notebook {reader['ipynb']})")
        if reader["pdf"]:
            print(f"reader PDF → {reader['pdf']}")
        else:
            print("reader PDF skipped: Chrome not found (set SANDBOX_CHROME); READER-REPORT.pdf is now stale")
        return 0
    if getattr(args, "runbook", None):
        replicas = 1 if args.runbook == "grid-1l4" else 2
        paths = grid_cards.write_suite(replicas)
        print(f"suite card → {paths['md']}")
        return 0
    if not getattr(args, "config", None):
        print("ERROR: --config or --runbook required", file=sys.stderr)
        return 2
    from mailroom_sandbox.job import spec as spec_mod
    from mailroom_sandbox.job.checkpoint import RunStore

    spec = spec_mod.load_run_spec(args.config)
    store = RunStore(spec_mod.runs_root() / spec_mod.resolve_run_id(spec))
    if not store.load_items():
        print(f"ERROR: no items for {store.run_id} — run it first", file=sys.stderr)
        return 2
    paths = grid_cards.write_card(store)
    print(f"run card → {paths['md']}")
    if getattr(args, "gate", False):
        problems = grid_cards.chunk_gate(store)
        for line in problems:
            print(f"GATE FAIL: {line}", file=sys.stderr)
        if problems:
            return 1
        print(f"gate passed: every chunk of {store.run_id} reached vLLM")
    return 0


def _bt_run_context(args):
    from mailroom_sandbox import paths
    from mailroom_sandbox.job import spec as spec_mod

    spec = spec_mod.load_run_spec(args.config)
    run_id = spec_mod.resolve_run_id(spec)
    return run_id, spec_mod.runs_root() / run_id, paths.runtime_dir() / "bt_experiments"


def _cmd_run_export_bt(args) -> int:
    """SAND-032: offline evidence rows for one run (never uploaded)."""
    from mailroom_sandbox.job import bt_offline
    from mailroom_sandbox.job.checkpoint import RunStore

    if not getattr(args, "config", None):
        print("ERROR: --config required", file=sys.stderr)
        return 2
    run_id, store_dir, out_root = _bt_run_context(args)
    if not (store_dir / "items.jsonl").is_file():
        print(f"ERROR: run {run_id} has no items.jsonl at {store_dir}", file=sys.stderr)
        return 1
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    out = bt_offline.write_experiment(RunStore(store_dir), out_root=out_root, git_commit=commit)
    print(f"offline BT rows → {out}")
    return 0


def _cmd_run_dispose(args) -> int:
    """SAND-032: remove offline rows only after the run's report is committed."""
    from mailroom_sandbox.job import bt_offline

    if not getattr(args, "config", None):
        print("ERROR: --config required", file=sys.stderr)
        return 2
    run_id, _store_dir, out_root = _bt_run_context(args)
    try:
        removed = bt_offline.dispose(
            run_id,
            out_root=out_root,
            report=Path(args.report),
            is_tracked=lambda p: bt_offline.git_tracked(p),
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"disposed {run_id}" if removed else f"nothing to dispose for {run_id}")
    return 0


def _cmd_watch(args) -> int:
    from mailroom_sandbox import watch as watch_mod
    from mailroom_sandbox.job import spec as spec_mod
    from mailroom_sandbox.job.checkpoint import RunStore

    from mailroom_sandbox import paths

    if getattr(args, "demo", False):
        return _serve_demo(args)
    sand032 = paths.runtime_dir() / "sand032"
    if not args.config and not args.follow and (sand032 / "current").is_file():
        # Bare `sandbox watch`: follow the current SAND-032 run with its ledger.
        args.follow = str(sand032 / "current")
        if not args.ledger and (sand032 / "spend.json").is_file():
            args.ledger = str(sand032 / "spend.json")
    if not args.config and not args.follow:
        print("ERROR: --config or --follow required", file=sys.stderr)
        return 2

    def resolve():
        cfg = args.config
        if args.follow:
            cfg = Path(args.follow).read_text(encoding="utf-8").strip() or args.config
        spec = spec_mod.load_run_spec(cfg)
        app = args.app or (spec.engine.modal.app if spec.engine.modal else "sandbox-vllm")
        return RunStore(spec_mod.runs_root() / spec_mod.resolve_run_id(spec)), app

    common = dict(
        resolve=resolve,
        ledger=Path(args.ledger) if args.ledger else None,
        cap_usd=args.cap_usd,
        logs=not args.no_logs,
        interval=args.interval,
        sand032_root=sand032 if sand032.is_dir() else None,
    )
    if getattr(args, "web", False):
        from mailroom_sandbox.tui import web as web_mod

        host = args.host or web_mod.DEFAULT_HOST
        port = web_mod.DEFAULT_PORT if args.port is None else args.port
        open_browser = False if args.no_browser else None
        return web_mod.serve_watch_web(**common, host=host, port=port, open_browser=open_browser)
    return watch_mod.watch(**common, once=args.once, bell=not getattr(args, "no_bell", False))


def _serve_demo(args) -> int:
    """Dev server: the web watch UI driven by a synthetic run in a temp dir."""
    import tempfile

    from mailroom_sandbox.tui import web as web_mod
    from mailroom_sandbox.tui.demo import DemoRun

    root = Path(tempfile.mkdtemp(prefix="mailroom-watch-demo-"))
    demo = DemoRun(root)
    return web_mod.serve_watch_web(
        resolve=demo.resolve,
        ledger=demo.ledger,
        cap_usd=5.0,
        logs=False,
        interval=getattr(args, "interval", None) or 1.0,
        times_dir=demo.times_dir,
        log_path=None,
        serving_dir=demo.serving_dir,
        host=args.host or web_mod.DEFAULT_HOST,
        port=web_mod.DEFAULT_PORT if args.port is None else args.port,
        open_browser=False if args.no_browser else None,
        tick=demo.step,
    )


def _cmd_dev(args) -> int:
    return _serve_demo(args)


def _cmd_board(args) -> int:
    from mailroom_sandbox.tui import board as board_mod

    root = Path(args.root).expanduser() if args.root else None
    if args.tui:
        return board_mod.run_board_tui(root=root, stale_s=args.stale_s, interval=args.interval, once=args.once)
    return board_mod.serve_board(
        root=root,
        host=args.host or "127.0.0.1",
        port=board_mod.DEFAULT_PORT if args.port is None else args.port,
        open_browser=False if args.no_browser else None,
        stale_s=args.stale_s,
        interval=args.interval,
        demo=args.demo,
    )


def _cmd_beacon_update(args) -> int:
    from mailroom_sandbox.tui.beacon import Beacon

    b = Beacon(args.job, package=args.package, title=args.title, root=args.root, resume=True, pid=None)
    metrics = dict(m.split("=", 1) for m in args.metric if "=" in m)
    fields = {k: getattr(args, k) for k in ("phase", "done", "total", "ok", "errors")}
    if args.log:
        b.log(args.log)
    if args.finish:
        b.finish(args.finish, metrics=metrics or None, **fields)
    else:
        b.update(metrics=metrics or None, **fields)
    return 0


def _cmd_scorecard(args) -> int:
    from mailroom_sandbox import watch as watch_mod
    from mailroom_sandbox.job import spec as spec_mod
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.paths import reports_dir

    store = RunStore(spec_mod.runs_root() / str(args.run_id))
    serving = Path(args.serving_dir) if args.serving_dir else reports_dir() / "serving"
    return watch_mod.print_scorecard(store, serving_dir=serving)


def _cmd_run_suite(args) -> int:
    """Print or execute a two-operator / full specialist suite (DMR-077)."""
    from mailroom_sandbox.job.suite import (
        list_suite_ids,
        load_suite,
        suite_runbook_md,
        suite_shell_loop,
    )

    if getattr(args, "list", False):
        ids = list_suite_ids()
        if getattr(args, "json", False):
            _print({"suites": ids})
        else:
            print("Suites (config/runs/suites/):")
            for sid in ids:
                print(f"  {sid}")
            print(
                "Aliases: track-a|a, track-b|b, full|all "
                "(operator cards: sandbox runbook show l4-qwen3-8b)"
            )
        return 0

    suite_name = (getattr(args, "suite", None) or "").strip()
    if not suite_name:
        print(
            "error: pass --suite track-a|track-b|full (or --list)",
            file=sys.stderr,
        )
        return 1

    try:
        suite = load_suite(suite_name)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if getattr(args, "check", False):
        from mailroom_sandbox.job.benchmark_check import check_suite_benchmark_posture

        require_hermes = not bool(getattr(args, "allow_non_hermes", False))
        # Track B is intentionally non-Hermes — auto-allow when profile ≠ Hermes.
        if suite.track == "b":
            require_hermes = False
        report = check_suite_benchmark_posture(
            suite_name,
            require_hermes=require_hermes,
            require_modernbert=False,
        )
        if getattr(args, "json", False):
            _print(report)
        else:
            print(report.get("markdown", ""))
            for err in report.get("errors") or []:
                print(f"ERROR: {err}", file=sys.stderr)
        return 0 if report.get("ok") else 1

    if getattr(args, "print_loop", False):
        print(suite_shell_loop(suite, job_mode=getattr(args, "mode", None) or "endpoint"))
        return 0

    if getattr(args, "execute", False):
        # Chain each config via the existing start path (no teardown).
        mode = getattr(args, "mode", None) or "endpoint"
        for cfg in suite.configs:
            print(f"=== suite {suite.suite_id}: {cfg} ===", flush=True)
            ns = argparse.Namespace(**vars(args))
            ns.config = str(cfg)
            ns.suite = None
            ns.mode = mode
            ns.watch = True
            ns.live = True if getattr(args, "live", False) else getattr(args, "live", False)
            # Prefer live when execute unless mock/offline explicitly set.
            if not getattr(args, "mock", None) and not getattr(args, "offline", False):
                ns.live = True
            rc = _cmd_run_start(ns)
            if rc != 0:
                print(
                    f"error: suite stopped after {cfg} (rc={rc}); "
                    "app left warm — fix and resume, or teardown manually",
                    file=sys.stderr,
                )
                return rc
        print(
            f"suite {suite.suite_id} complete — teardown with "
            "./deploy/teardown_vllm.sh (do not teardown between configs)"
        )
        return 0

    if getattr(args, "json", False):
        _print(
            {
                "suite_id": suite.suite_id,
                "track": suite.track,
                "title": suite.title,
                "configs": suite.config_paths_rel(),
                "scaledown_seconds": suite.scaledown_seconds,
                "warm_once": suite.warm_once,
                "modal_profile_env": suite.modal_profile_env,
                "modal_profile_default": suite.modal_profile_default,
                "resolved_modal_profile": suite.resolve_modal_profile(),
                "rationale": suite.rationale,
                "shell_loop": suite_shell_loop(suite),
            }
        )
        return 0

    print(suite_runbook_md(suite))
    return 0

def _cmd_modernbert_help(args) -> int:
    print("Use: sandbox modernbert status | eval [--sample N] [--json]")
    return 0


def _cmd_modernbert_status(args) -> int:
    from mailroom_sandbox.modernbert import feeder_status

    status = feeder_status()
    _print(status)
    return 0 if status.get("ok") else 1


def _cmd_modernbert_eval(args) -> int:
    from mailroom_sandbox.modernbert import (
        append_experiment_log_from_eval,
        run_modernbert_eval,
        serving_record_from_eval,
    )

    report = run_modernbert_eval(
        sample=int(args.sample),
        seed=int(args.seed),
        subset=str(args.subset),
        checkpoint=args.checkpoint,
    )
    record = serving_record_from_eval(report)
    log_path = None
    if getattr(args, "append_log", False):
        log_path = append_experiment_log_from_eval(report)
    out = {"report": report, "serving_record": record, "experiment_log": str(log_path) if log_path else None}
    if getattr(args, "json", False):
        _print(out)
    else:
        print(
            f"ModernBERT n={record.get('n')} doc_type_acc="
            f"{(record.get('scores') or {}).get('doc_type_accuracy')} "
            f"e2e_s/doc={record.get('e2e_latency_seconds')} "
            f"$/doc={record.get('cost_per_document')}"
        )
        _print(out)
    return 0


def _cmd_modal_matrix_help(args) -> int:
    print(
        "Use: sandbox modal-matrix list | show <model> | env [<model>] [--gpu GPU]\n"
        "Default catalog row (specialist suite): Qwen/Qwen3-8B @ L4\n"
        'Swap: eval "$(sandbox modal-matrix env Qwen/Qwen3-8B-AWQ)" && '
        "modal deploy deploy/modal_vllm.py --strategy recreate"
    )
    return 0


def _cmd_modal_matrix_list(args) -> int:
    from mailroom_sandbox.modal_matrix import list_modal_models

    rows = list_modal_models()
    if getattr(args, "json", False):
        _print({"models": rows})
        return 0
    print(f"{'default':8} {'gpu':14} {'quant':8} {'ctx':6} {'tp':3} model")
    for row in rows:
        flag = "*" if row.get("default") else " "
        print(
            f"{flag:8} {str(row.get('gpu') or '-'):14} "
            f"{str(row.get('quantization') or '-'):8} "
            f"{str(row.get('max_model_len') or '-'):6} "
            f"{str(row.get('tp_size') or 1):3} {row['model']}"
        )
    print("\n* = default specialist cost-eval posture (sandbox runbook show l4-qwen3-8b)")
    return 0


def _cmd_modal_matrix_show(args) -> int:
    from mailroom_sandbox.modal_matrix import cutover_hints, resolve_modal_row

    resolved = resolve_modal_row(args.model, gpu_override=args.gpu)
    if getattr(args, "json", False):
        _print({**resolved, "hints": cutover_hints(resolved)})
        return 0
    print(f"model:          {resolved['model']}")
    print(f"gpu:            {resolved['gpu']}")
    print(f"quantization:   {resolved['quantization'] or '(none / bf16 or auto-FP8)'}")
    print(f"max_model_len:  {resolved['max_model_len']}")
    print(f"tp_size:        {resolved['tp_size']}")
    print(f"default_posture:{resolved['is_default']}")
    if resolved.get("notes"):
        print(f"notes:          {resolved['notes']}")
    print("env:")
    for k, v in resolved["env"].items():
        print(f"  export {k}={v}")
    print("hints:")
    for h in cutover_hints(resolved):
        print(f"  - {h}")
    return 0


def _cmd_modal_matrix_env(args) -> int:
    from mailroom_sandbox.modal_matrix import env_exports

    sys.stdout.write(env_exports(args.model, gpu_override=args.gpu))
    return 0


def _run_load_spec(args) -> tuple[object, Path]:
    """Load the run spec and return it with a resolved ``--config`` path."""
    config = getattr(args, "config", None)
    if not config:
        raise SystemExit("run commands need --config <run.yaml>")
    from mailroom_sandbox.job.spec import load_run_spec

    return load_run_spec(config), Path(config).resolve()


def _run_id_required(args) -> str:
    """Return ``--run-id`` or the id embedded in ``--config``."""
    run_id = getattr(args, "run_id", None) or ""
    if not run_id and getattr(args, "config", None):
        from mailroom_sandbox.job.spec import load_run_spec

        run_id = load_run_spec(args.config).run_id
    if not run_id:
        raise SystemExit("--run-id <id> is required here (or pass --config <run.yaml>)")
    return run_id


def _cmd_run_preflight(args) -> int:
    """Run job preflight and print the lock report."""
    from mailroom_sandbox.job import preflight

    spec, config_path = _run_load_spec(args)
    report = preflight.preflight(
        spec,
        run_id=getattr(args, "run_id", None) or "",
        config_path=config_path,
        offline=bool(getattr(args, "offline", False)),
        force=bool(getattr(args, "force", False)),
        dry_run=bool(getattr(args, "dry_run", False)),
        live=bool(getattr(args, "live", False)),
    )
    _print(report)
    if report.get("status") == "prepared":
        return 0
    return 3 if report.get("status") == "drift_refused" else 1


def _cmd_run_start(args) -> int:
    """Lock a run via preflight, then start it locally or on Modal."""
    from mailroom_sandbox.job import preflight
    from mailroom_sandbox.job import remote as job_remote
    from mailroom_sandbox.job import runner
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    spec, config_path = _run_load_spec(args)
    # DMR-072: the job path must activate the runtime profile like every other
    # live CLI path. Without it the vendored pipeline loads its own default
    # config (openrouter, no key) and the sorter node falls through to the
    # graph's doc_type="unknown" default — a 50-item "run" then "completes" in
    # seconds with 0.0 scores, ok=True rows, and zero endpoint calls (the
    # silent-fallback trap; now also hard-guarded in runner._predict_row).
    activate(
        spec.profile,
        model=_activation_model(spec, getattr(args, "model", None)),
        agent_models=_agent_models(args),
        agent_knobs=_activation_knobs(spec),
    )
    if getattr(args, "mock", None) is not None or getattr(args, "local", None) is not None:
        spec.job.mock = bool(args.mock)
    report = preflight.preflight(
        spec,
        run_id=getattr(args, "run_id", None) or "",
        config_path=config_path,
        offline=bool(getattr(args, "offline", False)),
        force=bool(getattr(args, "force", False)),
        dry_run=bool(getattr(args, "dry_run", False)),
        live=bool(getattr(args, "live", False)),
    )
    if report.get("status") != "prepared":
        _print(report)
        return 3 if report.get("status") == "drift_refused" else 1
    run_id = report["run_id"]
    if getattr(args, "dry_run", False):
        _print({"run_id": run_id, "state": "dry_run"})
        return 0
    store = RunStore(run_dir(run_id))
    mode = getattr(args, "mode", None) or spec.job.mode
    if mode == "modal":
        # DMR-048: default live probe before firing — a stale VLLM_BASE_URL
        # used to lock 'prepared' and fail at item 0 on the worker. Skipped
        # for mock runs and explicit --offline runs.
        if not spec.job.mock and not getattr(args, "offline", False):
            from mailroom_sandbox.job import preflight as _pf

            probe = _pf.probe_engine(spec)
            if not probe.get("ok"):
                _print(
                    {
                        "run_id": run_id,
                        "state": "engine_unreachable",
                        "reason": probe.get("reason"),
                        "base_url": probe.get("base_url"),
                    }
                )
                return 1
        remote_action = job_remote.ensure_running(store)
        _print(remote_action)
        if not getattr(args, "watch", False):
            return 0
        return _watch_remote(store, args)
    summary = _run_endpoint(store, args)
    _print(summary)
    return 0 if summary.get("state") == "done" else 2 if summary.get("state") == "paused" else 1


def _run_endpoint(store, args) -> dict:
    from mailroom_sandbox.job import otel, runner
    from mailroom_sandbox.tui.session import MailroomConsole, run_event_handler

    watch = bool(getattr(args, "watch", False))
    console = MailroomConsole()
    lock = store.read_lock() or {}
    task = str(lock.get("task") or "")
    console.run_banner(run_id=store.run_id, task=task, subtitle="sandbox run · endpoint")
    console.phase("PREFLIGHT", "lock verified · scoring dataset")
    on_event = run_event_handler(console)

    tracer = _endpoint_tracer(store.run_id, lock)
    try:
        with store.acquire(), otel.job_span(
            tracer,
            "job.run",
            run_id=store.run_id,
            task=task,
            model=str((lock.get("engine") or {}).get("model") or ""),
        ) as run_span:
            summary = runner.run_job(
                store,
                mock=None,
                dry_run=False,
                max_items=getattr(args, "max_items", None),
                tracer=tracer,
                on_event=on_event,
            )
            for key in ("state", "cursor", "total", "ok", "errors"):
                if summary.get(key) is not None:
                    run_span.set_attribute(f"job.{key}", summary[key])
    finally:
        otel.flush_tracer(tracer)
    local_path = getattr(tracer, "sandbox_local_path", None)
    if local_path is not None and Path(local_path).is_file():
        summary.setdefault("trace_local_path", str(local_path))
    state = str(summary.get("state") or "unknown")
    detail = f"{summary.get('cursor', summary.get('ok', ''))}/{summary.get('total', '')} {task}".strip()
    console.complete(state=state, summary=detail)
    return summary


def _endpoint_tracer(run_id: str, lock: dict):
    """Tracer for an endpoint-mode run: the locked sink plus the local span mirror."""
    from mailroom_sandbox.job import otel

    trace_block = lock.get("trace") or {}
    try:
        sink_cfg = otel.resolve_sink(
            sink=trace_block.get("sink", "none"),
            otlp=bool(trace_block.get("otlp", True)),
            endpoint=trace_block.get("endpoint"),
            environment=trace_block.get("environment", "pilot"),
            service_name="sandbox-job",
            run_id=run_id,
            tags=trace_block.get("tags") or ["sandbox", "job"],
        )
    except ValueError as exc:
        print(f"warning: trace sink unusable ({exc}); local span mirror only")
        sink_cfg = otel.resolve_sink(sink="none", run_id=run_id)
    return otel.configure_tracing(sink_cfg, local_path=otel.local_trace_path(run_id))


def _finalize_remote(store) -> bool:
    """Pull a terminal remote run's dir back and append its records locally."""
    from mailroom_sandbox.eval import experiment_log
    from mailroom_sandbox.job import remote as job_remote

    rc, err = job_remote.pull_run_dir(store)
    if rc != 0:
        print(
            f"warning: could not pull remote run dir: {err} — check `modal token new` "
            f"and `modal volume ls {job_remote.VOLUME_NAME}`"
        )
        return False
    record_path = store.dir / "experiment_log.jsonl"
    if record_path.is_file():
        for line in record_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                experiment_log.append(json.loads(line))
    return True


def _watch_remote(store, args) -> int:
    from mailroom_sandbox.job import remote as job_remote
    from mailroom_sandbox.tui.session import MailroomConsole, remote_progress_line

    import time
    from datetime import datetime, timezone

    console = MailroomConsole()
    lock = store.read_lock() or {}
    console.run_banner(
        run_id=store.run_id,
        task=str(lock.get("task") or ""),
        subtitle="sandbox run · modal worker",
        route="INBOX → SPECIALIST → REPORT",
    )
    console.phase("DEPLOY", "remote job · state dict mirror")

    # hub#41: the watch must fail after a stall, never poll forever. A worker
    # that dies before its first state_dict.put leaves the Dict without a
    # terminal state; the heartbeat rides the payload, and the remote call
    # liveness is the second leg of the check.
    WATCH_STALL_SECONDS = 20 * 60
    last_heartbeat = time.monotonic()

    while True:
        progress = job_remote.read_progress(store)
        state = (progress or {}).get("state") or store.state() or "unknown"
        remote_progress_line(console, store.run_id, progress)
        heartbeat_at = (progress or {}).get("heartbeat_at")
        if heartbeat_at:
            try:
                ts = datetime.fromisoformat(str(heartbeat_at).replace("Z", "+00:00"))
                if ts.tzinfo is not None:
                    last_heartbeat = time.monotonic() - (datetime.now(timezone.utc) - ts).total_seconds()
            except ValueError:
                pass
        if state in {"done", "failed"}:
            _finalize_remote(store)
            console.complete(state=state, summary=store.run_id)
            if state == "failed":
                error = (progress or {}).get("error") or (store.read_checkpoint() or {}).get(
                    "last_error"
                )
                trace_tail = (progress or {}).get("traceback_tail")
                print(f"run failed: {error}")
                if trace_tail:
                    print("--- worker traceback tail ---")
                    print(trace_tail)
                    print("-----------------------------")
                print(f"diagnose with: sandbox run status {store.run_id} --watch (or --config ... --force)")
            return 0 if state == "done" else 1
        if (
            time.monotonic() - last_heartbeat > WATCH_STALL_SECONDS
            and not job_remote.is_alive(store)
        ):
            print(
                f"run stalled: no heartbeat for {WATCH_STALL_SECONDS // 60} minutes and the "
                f"remote call is no longer alive (last state: {state!r}) — abandoning watch; "
                f"diagnose with: sandbox run status {store.run_id}"
            )
            return 1
        time.sleep(3.0)


def _cmd_run_status(args) -> int:
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir
    from mailroom_sandbox.job import remote as job_remote

    run_id = _run_id_required(args)
    store = RunStore(run_dir(run_id))
    if not store.read_lock():
        _print({"run_id": run_id, "error": "no locked run found"})
        return 1
    if getattr(args, "watch", False):
        return _watch_remote(store, args)
    remote_progress = job_remote.read_progress(store) if _job_mode(store) == "modal" else None
    if remote_progress and remote_progress.get("state") in {"done", "failed"}:
        # Terminal remote run: sync items/checkpoints/records back locally.
        _finalize_remote(store)
    summary = store.summary()
    payload = summary
    if remote_progress:
        payload["remote"] = remote_progress
    _print(payload)
    return 0


def _cmd_run_resume(args) -> int:
    """Resume a locked run after re-checking preflight when ``--config`` is set."""
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    run_id = _run_id_required(args)
    # DMR-072: same profile-activation contract as `run start` — resuming an
    # endpoint-mode job must not re-enter the unactivated silent-fallback path.
    if getattr(args, "config", None):
        from mailroom_sandbox.job.spec import load_run_spec

        _spec = load_run_spec(args.config)
        activate(
            _spec.profile,
            model=_activation_model(_spec, getattr(args, "model", None)),
            agent_models=_agent_models(args),
            agent_knobs=_activation_knobs(_spec),
        )
    store = RunStore(run_dir(run_id))
    if not store.read_lock():
        _print({"run_id": run_id, "error": "no locked run to resume"})
        return 1
    if getattr(args, "config", None):
        from mailroom_sandbox.job import preflight

        spec, config_path = _run_load_spec(args)
        report = preflight.preflight(
            spec,
            run_id=run_id,
            config_path=config_path,
            offline=False,
            force=bool(getattr(args, "force", False)),
        )
        if report.get("status") != "prepared":
            _print(report)
            return 3 if report.get("status") == "drift_refused" else 1
    if _job_mode(store) == "modal":
        from mailroom_sandbox.job import remote as job_remote

        action = job_remote.ensure_running(store)
        _print({"run_id": run_id, **action})
        if getattr(args, "watch", False):
            return _watch_remote(store, args)
        return 0
    summary = _run_endpoint(store, args)
    _print(summary)
    return 0 if summary.get("state") == "done" else 2 if summary.get("state") == "paused" else 1


def _job_mode(store) -> str:
    lock = store.read_lock() or {}
    job = lock.get("job") or {}
    if isinstance(job, dict):
        return "modal" if job.get("mode") == "modal" else "local"
    return "local"


def _cmd_run_cancel(args) -> int:
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.remote import cancel as remote_cancel
    from mailroom_sandbox.job.spec import run_dir

    run_id = _run_id_required(args)
    store = RunStore(run_dir(run_id))
    cp = store.read_checkpoint() or {}
    if isinstance(cp.get("remote"), dict) and cp["remote"].get("call_id"):
        remote_cancel(store)
        _print({"run_id": run_id, "state": "cancel_requested"})
        return 0
    store.write_checkpoint(
        state="paused", cursor=cp.get("cursor", 0), total=cp.get("total", 0), remote=None
    )
    store.append_event("cancel_requested", "info")
    _print(store.summary())
    return 0


def _cmd_run_list(args) -> int:
    from mailroom_sandbox.job.checkpoint import list_runs
    from mailroom_sandbox.job.spec import runs_root

    _print(list_runs(runs_root()))
    return 0


def _cmd_runbook_help(args) -> int:
    print(
        "Use: sandbox runbook list | show <id> [--shell] | check | write\n"
        "Singular L4:  sandbox runbook show l4-qwen3-8b\n"
        "Improved:     sandbox runbook show improved-awq-c8\n"
        "Edit:         config/runbooks/catalog.yaml  then  sandbox runbook write"
    )
    return 0


def _cmd_runbook_list(args) -> int:
    from mailroom_sandbox.job.runbooks import get_runbook, list_runbook_ids

    ids = list_runbook_ids(family=getattr(args, "family", None))
    rows = []
    for rid in ids:
        row = get_runbook(rid)
        rows.append(
            {
                "id": rid,
                "family": row.get("family"),
                "title": row.get("title"),
                "serving": row.get("serving") or "baseline",
                "blocked": bool(row.get("blocked")),
            }
        )
    if getattr(args, "json", False):
        _print({"runbooks": rows})
        return 0
    print("Runbooks (config/runbooks/catalog.yaml):")
    for row in rows:
        flag = " BLOCKED" if row["blocked"] else ""
        print(f"  {row['id']:36}  [{row['family']}]{flag}  {row['title']}")
    print("Show: sandbox runbook show l4-qwen3-8b")
    return 0


def _cmd_runbook_show(args) -> int:
    from mailroom_sandbox.job.runbooks import (
        env_exports,
        get_runbook,
        render_markdown,
        render_shell,
        resolve_runbook_id,
    )

    try:
        rid = resolve_runbook_id(args.name)
    except (KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json", False):
        row = get_runbook(rid)
        _print(
            {
                "id": rid,
                "runbook": row,
                "env": env_exports(row),
                "shell": render_shell(rid),
            }
        )
        return 0
    if getattr(args, "shell", False):
        print(render_shell(rid), end="")
        return 0
    print(render_markdown(rid), end="")
    return 0


def _cmd_runbook_check(args) -> int:
    from mailroom_sandbox.job.runbooks import docs_are_current, verify_live_pins

    errors = verify_live_pins() + docs_are_current()
    if getattr(args, "json", False):
        _print({"ok": not errors, "errors": errors})
        return 0 if not errors else 1
    if errors:
        print("Runbook catalog check FAILED:")
        for err in errors:
            print(f"  ERROR: {err}", file=sys.stderr)
        return 1
    print("Runbook catalog check OK (pins + generated docs).")
    return 0


def _cmd_runbook_write(args) -> int:
    from mailroom_sandbox.job.runbooks import generated_dir, write_docs

    written = write_docs()
    dest = generated_dir()
    print(f"Wrote {len(written)} runbook files under {dest}")
    for path in written:
        print(f"  {path.name}")
    return 0


def _cmd_prompts_help(args):
    print("Use: sandbox prompts list | sandbox prompts show <agent> [--variant X]")
    return 0


def _cmd_prompts_list(args) -> int:
    from mailroom_sandbox.prompt_registry import agent_prompt_names, local_variants

    _print({"agents": agent_prompt_names(), "local_variants": local_variants()})
    return 0


def _cmd_prompts_show(args) -> int:
    from mailroom_sandbox.job.spec import PromptRef
    from mailroom_sandbox.prompt_registry import FAMILY_B_KEYS, agent_prompt_names, resolve_prompt

    name = args.name
    if name not in agent_prompt_names():
        print(
            f"error: unknown agent {name!r} — have {sorted(agent_prompt_names())} "
            "(DMR-056: show now validates, matching prompt_lock_block's refusal)"
        )
        return 2
    variant = getattr(args, "variant", None)
    if variant:
        ref = PromptRef(source="local", file=variant)
    else:
        ref = PromptRef(source="code-default")
    resolved = resolve_prompt(name, ref, offline=bool(getattr(args, "offline", False)))
    # DMR-056: surface the registry's pinned family-B version key (sorter_v14 /
    # contracts_specialist_v33) — the lock resolves it even though code-default
    # refs carry no version of their own.
    pinned = FAMILY_B_KEYS.get(name) if not variant else None
    if pinned:
        resolved["version_key"] = pinned
    _print(resolved)
    return 0


def _cmd_metrics_help(args):
    print(
        "Use: sandbox metrics compare --runs a,b[,c] | --log | --fixture | "
        "--sorter-vs-modernbert [--runs sorter,modernbert]\n"
        "     sandbox metrics extrapolate --run <id> [--corpus-size N] "
        "[--docs-per-day D]\n"
        "     sandbox metrics serving-record --run <id> [--wall-seconds S]\n"
        "     sandbox metrics estimate-suite [--suite track-a|track-b|full] "
        "[--configs run-30-….yaml,…] [--corpus-size N]"
    )
    return 0


_DEFAULT_SPECIALIST_SUITE = (
    "config/runs/run-30-contracts-specialist.yaml",
    "config/runs/run-30-merger-specialist.yaml",
    "config/runs/run-30-corporate-records-specialist.yaml",
    "config/runs/run-30-correspondence-specialist.yaml",
    "config/runs/run-30-insurance-claims-specialist.yaml",
)


def _cmd_metrics_estimate_suite(args) -> int:
    from pathlib import Path

    from mailroom_sandbox.job import metrics
    from mailroom_sandbox.job.spec import FAMILY_CORPUS_SIZE

    paths: list[str] = []
    suite_name = (getattr(args, "suite", None) or "").strip()
    if suite_name:
        from mailroom_sandbox.job.suite import load_suite

        try:
            suite = load_suite(suite_name)
        except (FileNotFoundError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        paths = [str(p) for p in suite.configs]
        print(
            f"# suite={suite.suite_id} track={suite.track} "
            f"scaledown={suite.scaledown_seconds} configs={len(paths)}",
            file=sys.stderr,
        )
    else:
        raw_configs = (getattr(args, "configs", None) or "").strip()
        if raw_configs:
            paths.extend(p.strip() for p in raw_configs.split(",") if p.strip())
        for p in getattr(args, "config_paths", None) or []:
            if p and str(p).strip():
                paths.append(str(p).strip())
        if not paths:
            paths = list(_DEFAULT_SPECIALIST_SUITE)

    missing = [p for p in paths if not Path(p).is_file()]
    if missing:
        print(
            "error: missing run YAML(s):\n  " + "\n  ".join(missing),
            file=sys.stderr,
        )
        return 1

    corpus = None
    if not getattr(args, "no_corpus", False):
        corpus = (
            int(args.corpus_size)
            if args.corpus_size is not None
            else FAMILY_CORPUS_SIZE
        )

    result = metrics.estimate_suite(
        paths,
        gpu_usd_per_hour_rate=getattr(args, "gpu_usd_per_hour", None),
        sec_per_doc_override=getattr(args, "sec_per_doc", None),
        cold_start_seconds=float(args.cold_start_seconds),
        scaledown_seconds=getattr(args, "scaledown_seconds", None),
        inter_run_gap_seconds=float(args.inter_run_gap_seconds),
        corpus_size=corpus,
        gen_tok_per_s=getattr(args, "gen_tok_per_s", None),
    )
    if suite_name:
        result["suite_ref"] = suite_name
    if getattr(args, "json", False):
        _print(result)
    else:
        print(result.get("markdown", ""))
    return 0


def _cmd_metrics_serving_record(args) -> int:
    from pathlib import Path

    from mailroom_sandbox.job import metrics
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    run_id = str(args.run_id).strip()
    store = RunStore(run_dir(run_id))
    if not store.lock_path.is_file():
        print(
            f"error: run {run_id!r} has no lock at {store.lock_path}",
            file=sys.stderr,
        )
        return 1
    if not store.load_items():
        print(
            f"error: run {run_id!r} has no items.jsonl — nothing to export",
            file=sys.stderr,
        )
        return 1
    out_path = Path(args.out) if getattr(args, "out", "") else None
    try:
        wall = getattr(args, "wall_seconds", None)
        record = metrics.serving_record_from_store(store, wall_seconds=wall)
        written = metrics.write_serving_json(store, out_path, wall_seconds=wall)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json", False):
        _print({"path": str(written), "record": record})
    else:
        print(f"wrote {written}")
    return 0


def _cmd_metrics_extrapolate(args) -> int:
    from mailroom_sandbox.job import metrics
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import FAMILY_CORPUS_SIZE, run_dir

    run_id = str(args.run_id).strip()
    store = RunStore(run_dir(run_id))
    if not store.lock_path.is_file():
        print(
            f"error: run {run_id!r} has no lock at {store.lock_path} — "
            "preflight + start a live run before extrapolating",
            file=sys.stderr,
        )
        return 1
    lock = store.read_lock() or {}
    items = store.load_items()
    if not items:
        print(
            f"error: run {run_id!r} has no items.jsonl — nothing to extrapolate",
            file=sys.stderr,
        )
        return 1
    engine = lock.get("engine") or {}
    modal = (engine.get("modal") or {}) if isinstance(engine, dict) else {}
    gpu = str(modal.get("gpu") or "").split(":")[0] or None
    rec = metrics.record_from_run(
        run_id=run_id,
        spec_hash=store.spec_hash() or "",
        task=lock.get("task", "?"),
        profile=lock.get("profile", "?"),
        model=(engine.get("model") if isinstance(engine, dict) else None) or "?",
        prompt_version=str(
            (lock.get("prompt") or {}).get("default", {}).get("source") or "code-default"
        ),
        dataset_fingerprint=(lock.get("dataset") or {}).get("sha256", "") or "",
        items=items,
        gpu=gpu,
        mock=bool((lock.get("job") or {}).get("mock")),
    )
    if not rec.get("cost_per_document") and not rec.get("gpu_cost_per_document"):
        print(
            "error: run has neither token nor GPU $/doc — refusing silent $0 "
            "extrapolation. Ensure live items record usage tokens and/or set "
            "MODAL_BILLED_GPU_SECONDS.",
            file=sys.stderr,
        )
        return 1
    corpus = int(args.corpus_size) if args.corpus_size is not None else FAMILY_CORPUS_SIZE
    result = metrics.extrapolate_cost(
        rec,
        corpus_size=corpus,
        docs_per_day=args.docs_per_day,
        docs_per_month=args.docs_per_month,
        cold_start_seconds=float(args.cold_start_seconds),
        scaledown_seconds=float(args.scaledown_seconds),
        concurrency=int(args.concurrency),
        gpu=gpu,
    )
    if getattr(args, "json", False):
        _print(result)
    else:
        print(result.get("markdown", ""))
    return 0


def _cmd_metrics_compare(args) -> int:
    from mailroom_sandbox.job import metrics

    if getattr(args, "sorter_vs_modernbert", False):
        return _cmd_metrics_sorter_vs_modernbert(args)

    if getattr(args, "fixture", False):
        from mailroom_sandbox.datasets import load_cost_compare_fixtures
        from mailroom_sandbox.eval.serving_parity import score_cost_compare

        fixtures = load_cost_compare_fixtures()
        if not any(fixtures.get(k) for k in ("local", "modal", "api")):
            print("error: cost-compare fixture missing or empty", file=sys.stderr)
            return 1
        result = score_cost_compare(fixtures)
        if getattr(args, "json", False):
            _print(result)
        else:
            print(result.get("markdown", ""))
        return 0 if result.get("parity_ok") else 2

    records = []
    if getattr(args, "log", False):
        from mailroom_sandbox.eval import experiment_log

        records = list(experiment_log.load())
    else:
        from mailroom_sandbox.job.checkpoint import RunStore
        from mailroom_sandbox.job.spec import run_dir

        run_ids = [x.strip() for x in getattr(args, "runs", "").split(",") if x.strip()]
        if not run_ids:
            raise SystemExit("metrics compare needs --runs a,b,c")
        for run_id in run_ids:
            store = RunStore(run_dir(run_id))
            if not store.lock_path.is_file():
                print(
                    f"error: run {run_id!r} has no lock file at {store.lock_path} — "
                    f"nothing was preflighted for it; refusing to compare a "
                    f"garbage '?' record",
                    file=sys.stderr,
                )
                return 1
            lock = store.read_lock() or {}
            items = store.load_items()
            engine = lock.get("engine") or {}
            modal = (engine.get("modal") or {}) if isinstance(engine, dict) else {}
            gpu = str(modal.get("gpu") or "").split(":")[0] or None
            rec = metrics.record_from_run(
                run_id=run_id,
                spec_hash=store.spec_hash() or "",
                task=lock.get("task", "?"),
                profile=lock.get("profile", "?"),
                model=(lock.get("engine") or {}).get("model") or "?",
                prompt_version=str((lock.get("prompt") or {}).get("default", {}).get("source") or "code-default"),
                dataset_fingerprint=(lock.get("dataset") or {}).get("sha256", "") or "",
                items=items,
                gpu=gpu,
            )
            records.append(rec)
    result = metrics.compare(records)
    if getattr(args, "json", False):
        _print(result)
    else:
        print(result.get("markdown", ""))
    return 0


def _cmd_metrics_sorter_vs_modernbert(args) -> int:
    """Compare LLM sorter vs ModernBERT from fixtures or two run stores."""
    from mailroom_sandbox.datasets import load_sorter_vs_modernbert_fixtures
    from mailroom_sandbox.job import metrics

    def _scores_from_items(items: list) -> dict | None:
        pairs = [
            (str(i.get("expected") or ""), str(i.get("predicted") or ""))
            for i in items
            if i.get("ok", True) is not False and i.get("predicted") not in (None, "")
        ]
        if not pairs:
            return None
        from mailroom_sandbox.eval import scoring as sc

        return sc.score_classification([e for e, _ in pairs], [p for _, p in pairs])

    run_ids = [x.strip() for x in getattr(args, "runs", "").split(",") if x.strip()]
    if len(run_ids) >= 2:
        from mailroom_sandbox.job.checkpoint import RunStore
        from mailroom_sandbox.job.spec import run_dir

        stores = []
        for run_id in run_ids[:2]:
            store = RunStore(run_dir(run_id))
            if not store.lock_path.is_file():
                print(
                    f"error: run {run_id!r} has no lock — refusing sorter vs ModernBERT compare",
                    file=sys.stderr,
                )
                return 1
            lock = store.read_lock() or {}
            engine = lock.get("engine") or {}
            modal = (engine.get("modal") or {}) if isinstance(engine, dict) else {}
            gpu = str(modal.get("gpu") or "").split(":")[0] or None
            items = store.load_items()
            stores.append(
                metrics.record_from_run(
                    run_id=run_id,
                    spec_hash=store.spec_hash() or "",
                    task=lock.get("task", "sorter"),
                    profile=lock.get("profile", "?"),
                    model=(engine.get("model") if isinstance(engine, dict) else None) or "?",
                    prompt_version=str(
                        (lock.get("prompt") or {}).get("default", {}).get("source") or "code-default"
                    ),
                    dataset_fingerprint=(lock.get("dataset") or {}).get("sha256", "") or "",
                    items=items,
                    scores=_scores_from_items(items),
                    gpu=gpu,
                )
            )
        # Heuristic: modernbert-tagged profile/model second, else order as given.
        left, right = stores[0], stores[1]
        right_blob = f"{right.get('profile')}{right.get('model')}{right.get('serving_kind')}".lower()
        if "modernbert" in right_blob or "bert" in right_blob:
            sorter_rec, mb_rec = left, right
        elif "modernbert" in f"{left.get('profile')}{left.get('model')}".lower():
            sorter_rec, mb_rec = right, left
        else:
            sorter_rec, mb_rec = left, right
    else:
        fixtures = load_sorter_vs_modernbert_fixtures()
        sorter_rec = fixtures.get("sorter") or {}
        mb_rec = fixtures.get("modernbert") or {}
        if not sorter_rec or not mb_rec:
            print(
                "error: sorter_vs_modernbert fixtures missing — expected "
                "data/fixtures/serving/sorter_vs_modernbert.json",
                file=sys.stderr,
            )
            return 1

    result = metrics.compare_sorter_vs_modernbert(sorter_rec, mb_rec)
    if getattr(args, "json", False):
        _print(result)
    else:
        print(result.get("markdown", ""))
    return 0
