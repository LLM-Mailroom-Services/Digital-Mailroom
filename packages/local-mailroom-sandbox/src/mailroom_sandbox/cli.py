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
from mailroom_sandbox.runtime import activate, resolve_mailroom_src


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 0
    return int(args.handler(args) or 0)


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
    p.add_argument("-d", "--detach", action="store_true", default=True)
    p.set_defaults(handler=_cmd_up)

    p = sub.add_parser("down", help="Stop compose stack", parents=[shared])
    p.add_argument("--compose-profile", action="append", dest="compose_profiles")
    p.set_defaults(handler=_cmd_down)

    p = sub.add_parser("health", help="Probe the active provider + Langfuse", parents=[shared])
    p.set_defaults(handler=_cmd_health)

    p = sub.add_parser("pull-models", help="Pull Ollama (or listed) weights", parents=[shared])
    p.add_argument("models", nargs="*")
    p.set_defaults(handler=_cmd_pull_models)

    p = sub.add_parser("fetch-deps", help="Clone llm-mailroom @ v0.6.0 into vendor/", parents=[shared])
    p.add_argument("--entity", action="store_true", help="Also clone llm-entity-extraction")
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

    pipe = sub.add_parser("pipeline", help="Run mailroom watcher or API", parents=[shared])
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
        help="For local_vs_api: compare experiment_log.jsonl instead of serving fixtures",
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
    pull = ds.add_parser("pull", parents=[shared])
    pull.add_argument("--dataset", default="Lucius-Morningstar/mailroom-corpus")
    pull.add_argument("--max-rows", type=int, default=50)
    pull.set_defaults(handler=_cmd_datasets_pull)
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
    mcomp.add_argument("--json", action="store_true")
    mcomp.set_defaults(handler=_cmd_metrics_compare)
    mp.set_defaults(handler=_cmd_metrics_help)

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
    host = os.environ.get("LANGFUSE_HOST") or "http://localhost:3000"
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
            "health": {"models_url": "http://localhost:6006/healthz"},
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
    vendor_dir().mkdir(parents=True, exist_ok=True)
    rc = _clone(
        "https://github.com/Exios66/llm-mailroom.git",
        vendor_dir() / "llm-mailroom",
        "v0.6.0",
    )
    if args.entity:
        rc = rc or _clone(
            "https://github.com/Exios66/llm-entity-extraction.git",
            vendor_dir() / "llm-entity-extraction",
            "v0.20.0",
        )
    if getattr(args, "visualizer", False):
        dest = vendor_dir() / "The-Mailroom"
        if dest.is_dir() and (dest / ".git").exists():
            subprocess.run(["git", "-C", str(dest), "pull", "--ff-only"], check=False)
        else:
            rc = rc or subprocess.run(
                ["git", "clone", "--depth", "1", "https://github.com/Exios66/The-Mailroom.git", str(dest)]
            ).returncode
    return rc


def _clone(url: str, dest: Path, tag: str) -> int:
    if dest.is_dir() and (dest / ".git").exists():
        subprocess.run(["git", "-C", str(dest), "fetch", "--tags"], check=False)
        return subprocess.run(["git", "-C", str(dest), "checkout", tag], check=False).returncode
    dest.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(["git", "clone", "--branch", tag, "--depth", "1", url, str(dest)]).returncode


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
    src = resolve_mailroom_src()
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
    _print(result)
    return 0


def _cmd_eval(args: argparse.Namespace) -> int:
    from mailroom_sandbox.eval import runners
    from mailroom_sandbox.eval.agents import SPECS

    mock = _mock_for(args, subcommand="eval")
    os.environ["SANDBOX_RUN_MODE"] = "mock" if mock else "local"
    kwargs = {
        "mock": mock,
        "sample": args.sample,
        "dry_run": args.dry_run,
        "experiment_name": args.experiment_name or f"sandbox_{args.task}",
        "profile": args.profile,
        "model": args.model,
        "agent_models": _agent_models(args),
    }
    if args.task in SPECS:
        result = runners.run_isolated_eval(args.task, prompt_version=args.prompt, **kwargs)
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
    else:
        result = runners.run_legalbench_eval(**kwargs)
    _print(result)
    return 0


def _cmd_matrix(args: argparse.Namespace) -> int:
    from mailroom_sandbox.eval.matrix import run_matrix

    mock = _mock_for(args, subcommand="matrix")
    result = run_matrix(
        task=args.task,
        providers=[p.strip() for p in args.providers.split(",") if p.strip()],
        models=[m.strip() for m in args.models.split(",") if m.strip()],
        prompts=[x.strip() for x in args.prompts.split(",") if x.strip()],
        sample=args.sample,
        seed=args.seed,
        mock=mock,
        dry_run=args.dry_run,
    )
    _print(result)
    return 0


def _cmd_datasets_help(args: argparse.Namespace) -> int:
    print("Use: sandbox datasets pull | sandbox datasets prepare")
    return 0


def _cmd_datasets_pull(args: argparse.Namespace) -> int:
    from mailroom_sandbox.datasets import pull_hf_dataset

    path = pull_hf_dataset(args.dataset, max_rows=args.max_rows)
    print(path)
    return 0


def _cmd_datasets_prepare(args: argparse.Namespace) -> int:
    from mailroom_sandbox.prep import prepare_offline_datasets

    activate(args.profile, model=args.model, prompt_variant=args.prompt, agent_models=_agent_models(args))
    summary = prepare_offline_datasets()
    _print(summary)
    return 0 if summary.get("counts", {}).get("fixtures", 0) else 1


def _cmd_traces_help(args: argparse.Namespace) -> int:
    print("Use: sandbox traces export")
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
    print("Use: sandbox run preflight | start | status | resume | cancel | list  --config <run.yaml>")
    return 0


def _run_load_spec(args) -> tuple[object, Path]:
    config = getattr(args, "config", None)
    if not config:
        raise SystemExit("run commands need --config <run.yaml>")
    from mailroom_sandbox.job.spec import load_run_spec

    return load_run_spec(config), Path(config)


def _run_id_required(args) -> str:
    run_id = getattr(args, "run_id", None) or ""
    if not run_id:
        raise SystemExit("--run-id <id> is required here")
    return run_id


def _cmd_run_preflight(args) -> int:
    from mailroom_sandbox.job import preflight

    spec, _ = _run_load_spec(args)
    report = preflight.preflight(
        spec,
        run_id=getattr(args, "run_id", None) or "",
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
    from mailroom_sandbox.job import preflight
    from mailroom_sandbox.job import remote as job_remote
    from mailroom_sandbox.job import runner
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    spec, _ = _run_load_spec(args)
    if getattr(args, "mock", None) is not None or getattr(args, "local", None) is not None:
        spec.job.mock = bool(args.mock)
    report = preflight.preflight(
        spec,
        run_id=getattr(args, "run_id", None) or "",
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
    from mailroom_sandbox.job import runner

    with store.acquire():
        return runner.run_job(
            store,
            mock=None,
            dry_run=False,
            max_items=getattr(args, "max_items", None),
            tracer=None,
        )


def _finalize_remote(store) -> bool:
    """Pull a terminal remote run's dir back and append its records locally."""
    from mailroom_sandbox.eval import experiment_log
    from mailroom_sandbox.job import remote as job_remote

    rc, err = job_remote.pull_run_dir(store)
    if rc != 0:
        print(f"warning: could not pull remote run dir: {err}")
        return False
    record_path = store.dir / "experiment_log.jsonl"
    if record_path.is_file():
        for line in record_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                experiment_log.append(json.loads(line))
    return True


def _watch_remote(store, args) -> int:
    from mailroom_sandbox.job import remote as job_remote

    import time

    while True:
        progress = job_remote.read_progress(store)
        state = (progress or {}).get("state") or store.state() or "unknown"
        print(f"{store.run_id} {state} {progress or {}}")
        if state in {"done", "failed"}:
            _finalize_remote(store)
            return 0 if state == "done" else 1
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
    from mailroom_sandbox.job.checkpoint import RunStore
    from mailroom_sandbox.job.spec import run_dir

    run_id = _run_id_required(args)
    store = RunStore(run_dir(run_id))
    if not store.read_lock():
        _print({"run_id": run_id, "error": "no locked run to resume"})
        return 1
    if getattr(args, "config", None):
        from mailroom_sandbox.job import preflight

        spec, _ = _run_load_spec(args)
        report = preflight.preflight(spec, run_id=run_id, offline=False, force=bool(getattr(args, "force", False)))
        if report.get("status") == "drift_refused":
            _print(report)
            return 3
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


def _cmd_prompts_help(args):
    print("Use: sandbox prompts list | sandbox prompts show <agent> [--variant X]")
    return 0


def _cmd_prompts_list(args) -> int:
    from mailroom_sandbox.prompt_registry import agent_prompt_names, local_variants

    _print({"agents": agent_prompt_names(), "local_variants": local_variants()})
    return 0


def _cmd_prompts_show(args) -> int:
    from mailroom_sandbox.job.spec import PromptRef
    from mailroom_sandbox.prompt_registry import agent_prompt_names, resolve_prompt

    name = args.name
    variant = getattr(args, "variant", None)
    if variant:
        ref = PromptRef(source="local", file=variant)
    elif name == "mailroom-default":
        ref = PromptRef(source="code-default")
    else:
        ref = PromptRef(source="code-default")
    resolved = resolve_prompt(name, ref, offline=bool(getattr(args, "offline", False)))
    _print(resolved)
    return 0


def _cmd_metrics_help(args):
    print("Use: sandbox metrics compare --runs a,b[,c] | --log")
    return 0


def _cmd_metrics_compare(args) -> int:
    from mailroom_sandbox.job import metrics

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
            lock = store.read_lock() or {}
            items = store.load_items()
            rec = metrics.record_from_run(
                run_id=run_id,
                spec_hash=store.spec_hash() or "",
                task=lock.get("task", "?"),
                profile=lock.get("profile", "?"),
                model=(lock.get("engine") or {}).get("model") or "?",
                prompt_version=str((lock.get("prompt") or {}).get("default", {}).get("source") or "code-default"),
                dataset_fingerprint=(lock.get("dataset") or {}).get("sha256", "") or "",
                items=items,
            )
            records.append(rec)
    result = metrics.compare(records)
    if getattr(args, "json", False):
        _print(result)
    else:
        print(result.get("markdown", ""))
    return 0
