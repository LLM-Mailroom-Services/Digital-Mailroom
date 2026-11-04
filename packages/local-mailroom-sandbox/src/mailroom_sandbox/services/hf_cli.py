"""``sandbox hf …``: guarded passthrough to the installed ``hf`` CLI.

Wraps the maintained ``hf`` binary (never the deprecated ``huggingface-cli``). The sandbox
adds only the missing-binary guard, the pinned ``FAMILY_HF_REVISION`` as the default for the
sandbox corpus, and an *explicit* cache: the operator's own ``HF_HOME`` by default, or
``data/cache/hf`` (what ``sandbox datasets pull`` reads) with ``--sandbox-cache``.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from mailroom_sandbox.paths import repo_root
from mailroom_sandbox.services.beacon import service_job
from mailroom_sandbox.services._cli import format_command, nonblank_path, nonempty, print_plan, strip_separator
from mailroom_sandbox.services._exec import (
    ServiceError,
    ToolFailed,
    passthrough_tool,
    run_tool,
    stream_tool,
    strip_ansi,
)

INSTALL_HINT = "pip install -U huggingface_hub (it provides the `hf` command)"
LOGIN_HINT = "run `hf auth login` or export HF_TOKEN (gated and private repos need a token)"
_AUTH_FAILURE = re.compile(r"\b40[13]\b|unauthori[sz]ed|gated|forbidden|not logged in|invalid token", re.IGNORECASE)


def sandbox_cache() -> Path:
    """The repo-local cache ``sandbox datasets pull`` reads (``corpus._ensure_hf_home``)."""
    return repo_root() / "data" / "cache" / "hf"


def _env_overrides(args: argparse.Namespace) -> dict[str, str]:
    _prepare()
    return {"HF_HOME": str(sandbox_cache())} if getattr(args, "sandbox_cache", False) else {}


def _prepare() -> None:
    from mailroom_sandbox.runtime import load_env_file

    load_env_file()


def _cache_in_use(overrides: dict[str, str]) -> str:
    return overrides.get("HF_HOME") or os.environ.get("HF_HOME") or "~/.cache/huggingface (hf default)"


def _child_env(overrides: dict[str, str]) -> dict[str, str]:
    if overrides:
        sandbox_cache().mkdir(parents=True, exist_ok=True)
    return {**os.environ, **overrides}


def _cmd_whoami(args: argparse.Namespace) -> int:
    _prepare()
    argv = ["hf", "auth", "whoami"]
    result = run_tool(argv, timeout=60.0, check=False, hint=INSTALL_HINT)
    if result.returncode != 0:
        detail = " ".join(strip_ansi(result.stderr or result.stdout or "").split())[:200]
        raise ServiceError(f"not authenticated with Hugging Face ({detail or 'no detail'}) — {LOGIN_HINT}")
    print((result.stdout or "").rstrip())
    return 0


def _download_argv(args: argparse.Namespace) -> list[str]:
    from mailroom_sandbox.datasets import HF_DATASET
    from mailroom_sandbox.job.spec import FAMILY_HF_REVISION

    sandbox_corpus = args.repo is None or args.repo == HF_DATASET
    repo = args.repo or HF_DATASET
    repo_type = args.repo_type or ("dataset" if sandbox_corpus else None)
    revision = args.revision or (FAMILY_HF_REVISION if sandbox_corpus else None)
    argv = ["hf", "download", repo]
    if repo_type:
        argv += ["--repo-type", repo_type]
    if revision:
        argv += ["--revision", revision]
    for pattern in args.include:
        argv += ["--include", pattern]
    for pattern in args.exclude:
        argv += ["--exclude", pattern]
    if args.local_dir:
        argv += ["--local-dir", args.local_dir]
    return argv


def _cmd_download(args: argparse.Namespace) -> int:
    argv = _download_argv(args)
    overrides = _env_overrides(args)
    if args.dry_run:
        print_plan(argv, overrides)
        print(f"dry-run: cache would be {_cache_in_use(overrides)}; nothing downloaded.")
        return 0
    print(f"cache: {_cache_in_use(overrides)}")
    print(f"-> {format_command(argv, overrides)}")
    tail: list[str] = []
    with service_job("hf-download", title=f"hf download · {argv[2]}") as job:
        job.update(phase="DOWNLOADING")

        def _line(line: str) -> None:
            tail.append(line)
            job.log(line)

        rc = stream_tool(argv, env=_child_env(overrides), hint=INSTALL_HINT, on_line=_line)
        if rc != 0:  # raised inside the job so the board shows it failed, not done
            recent = "\n".join(tail[-5:])
            message = str(ToolFailed(argv, rc, recent))
            if _AUTH_FAILURE.search(recent):
                message += f" — {LOGIN_HINT}"
            raise ServiceError(message)
    print("next: `sandbox datasets sample --per-class 40` / `sandbox datasets prepare` "
          "(use --sandbox-cache so the files land where `sandbox datasets pull` reads them)")
    return 0


def _cmd_cache(args: argparse.Namespace) -> int:
    argv = ["hf", "cache", "ls", *(["--revisions"] if args.revisions else [])]
    overrides = _env_overrides(args)
    rc = stream_tool(argv, env=_child_env(overrides), hint=INSTALL_HINT)
    if rc != 0:
        raise ToolFailed(argv, rc)
    return 0


def _cmd_raw(args: argparse.Namespace) -> int:
    rest = strip_separator(args.rest)
    if not rest:
        print("error: usage: sandbox hf raw -- <hf arguments>", file=sys.stderr)
        return 2
    _prepare()
    return passthrough_tool(["hf", *rest], hint=INSTALL_HINT)


def _cmd_help(args: argparse.Namespace) -> int:
    print(
        "Use: sandbox hf whoami|download|cache|raw\n"
        "  whoami                                   hf auth whoami (is a token available?)\n"
        "  download [REPO] [--revision R] [--include P]… [--sandbox-cache] [--dry-run]\n"
        "                                           default REPO: the sandbox dataset at the pinned FAMILY_HF_REVISION\n"
        "  cache [--revisions] [--sandbox-cache]    hf cache ls\n"
        "  raw -- <args>                            any other hf command, unchanged\n"
        "Cache: your own HF_HOME unless --sandbox-cache (data/cache/hf, where `sandbox datasets pull` reads)."
    )
    return 0


def register(sub: argparse._SubParsersAction, leaf: argparse.ArgumentParser) -> None:
    """Add the ``hf`` group to the root parser."""
    group = sub.add_parser("hf", parents=[leaf], help="guarded passthrough to the hf CLI (whoami/download/cache/raw)")
    cmds = group.add_subparsers(dest="hf_cmd")

    whoami = cmds.add_parser("whoami", parents=[leaf], help="hf auth whoami")
    whoami.set_defaults(handler=_cmd_whoami)

    download = cmds.add_parser("download", parents=[leaf], help="hf download (default: the pinned sandbox dataset)")
    download.add_argument("repo", nargs="?", type=nonempty, default=None, help="repo id (default: the sandbox dataset)")
    download.add_argument("--repo-type", choices=["model", "dataset", "space"], default=None)
    download.add_argument("--revision", type=nonempty, default=None, help="default: FAMILY_HF_REVISION for the sandbox dataset only")
    download.add_argument("--include", action="append", default=[], metavar="GLOB")
    download.add_argument("--exclude", action="append", default=[], metavar="GLOB")
    download.add_argument("--local-dir", type=nonblank_path, default=None)
    download.add_argument("--sandbox-cache", action="store_true", help="use data/cache/hf as HF_HOME")
    download.add_argument("--dry-run", action="store_true")
    download.set_defaults(handler=_cmd_download)

    cache = cmds.add_parser("cache", parents=[leaf], help="hf cache ls")
    cache.add_argument("--revisions", action="store_true")
    cache.add_argument("--sandbox-cache", action="store_true")
    cache.set_defaults(handler=_cmd_cache)

    raw = cmds.add_parser("raw", parents=[leaf], help="run any hf command: sandbox hf raw -- <args>")
    raw.add_argument("rest", nargs=argparse.REMAINDER)
    raw.set_defaults(handler=_cmd_raw)

    group.set_defaults(handler=_cmd_help)
