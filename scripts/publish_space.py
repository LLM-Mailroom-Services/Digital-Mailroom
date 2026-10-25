#!/usr/bin/env python3
"""Publish the live Observatory to a Hugging Face Docker Space.

Uses the committed root Dockerfile (MAILROOM_EDITION=hosted, port 7860).
Langfuse keys and HF_TOKEN stay in the environment / Space secrets — this
script never writes them into the Space git tree.

  python scripts/publish_space.py --check
  HF_TOKEN=hf_... \\
    LANGFUSE_PUBLIC_KEY=pk-lf-... LANGFUSE_SECRET_KEY=sk-lf-... \\
    LANGFUSE_HOST=https://us.cloud.langfuse.com \\
    MAILROOM_PIPELINE_URL=https://<user>-mailroom-producer.hf.space \\
    MAILROOM_PIPELINE_TOKEN=$MAILROOM_API_TOKEN \\
    MAILROOM_PIPELINE_API_PREFIX=/v1 \\
    python scripts/publish_space.py --repo <user>/mailroom-observatory

``LANGFUSE_BASE_URL`` is accepted as an alias of ``LANGFUSE_HOST``.
Optional producer knobs become Space secrets/variables when set; they are
never written into the Space git tree.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SPACE_README = ROOT / "hosted" / "SPACE_README.md"
DOCKERFILE = ROOT / "Dockerfile"
DOCKERIGNORE = ROOT / ".dockerignore"
PYPROJECT = ROOT / "pyproject.toml"

# Payload the Space image needs (mirrors Dockerfile COPY lines).
COPY_PATHS = (
    "mailroom_ui",
    "server",
    "hosted",
    "web",
    "tui",
    "operator_desk",
)

REQUIRED_FRONTMATTER = (
    "sdk: docker",
    "app_port: 7860",
)

# Hub YAML enum — "rose" is rejected by /api/validate-yaml.
HF_COLORS = frozenset({"red", "yellow", "green", "blue", "indigo", "purple", "pink", "gray"})

DEFAULT_HOST = "https://us.cloud.langfuse.com"
DEFAULT_SPACE_NAME = "mailroom-observatory"

SPACE_SECRETS = (
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_HOST",
)

# Optional — set when a reachable llm-mailroom producer exists.
# 127.0.0.1:8000 is local-only; a Space Observatory needs a public producer URL.
OPTIONAL_PIPELINE_SECRETS = (
    "MAILROOM_PIPELINE_URL",
    "MAILROOM_PIPELINE_TOKEN",
)

SPACE_VARIABLES = (
    "MAILROOM_SOURCE",
    "MAILROOM_EDITION",
)


def _die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def check_payload() -> list[str]:
    """Validate the Space card + Docker payload. Returns human-readable notes."""
    notes: list[str] = []
    if not SPACE_README.is_file():
        _die(f"missing Space card: {SPACE_README}")
    card = SPACE_README.read_text(encoding="utf-8")
    if not card.lstrip().startswith("---"):
        _die("hosted/SPACE_README.md must start with Hugging Face YAML frontmatter")
    for needle in REQUIRED_FRONTMATTER:
        if needle not in card:
            _die(f"hosted/SPACE_README.md missing `{needle}`")
    for field in ("colorFrom:", "colorTo:"):
        for line in card.splitlines():
            if line.startswith(field):
                color = line.split(":", 1)[1].strip()
                if color not in HF_COLORS:
                    _die(f"hosted/SPACE_README.md {field} {color!r} is not a Hub color")
                break
    notes.append("SPACE_README frontmatter: sdk=docker app_port=7860")
    if not DOCKERFILE.is_file():
        _die("missing root Dockerfile")
    docker = DOCKERFILE.read_text(encoding="utf-8")
    if "MAILROOM_EDITION=hosted" not in docker:
        _die("Dockerfile must set MAILROOM_EDITION=hosted")
    if "7860" not in docker:
        _die("Dockerfile must expose/bind 7860 (Spaces convention)")
    if "server.hosted" not in docker:
        _die("Dockerfile CMD must run server.hosted")
    notes.append("Dockerfile: hosted edition on :7860")
    if not PYPROJECT.is_file():
        _die("missing pyproject.toml")
    for rel in COPY_PATHS:
        path = ROOT / rel
        if not path.exists():
            _die(f"missing payload path: {rel}")
        notes.append(f"payload: {rel}/")
    return notes


def _resolved_host() -> str:
    host = (os.environ.get("LANGFUSE_HOST") or "").strip()
    if not host:
        host = (os.environ.get("LANGFUSE_BASE_URL") or "").strip()
    return host or DEFAULT_HOST


def _secret_values() -> dict[str, str]:
    pub = (os.environ.get("LANGFUSE_PUBLIC_KEY") or "").strip()
    sec = (os.environ.get("LANGFUSE_SECRET_KEY") or "").strip()
    if not pub or not sec:
        _die(
            "set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in the environment "
            "(do not pass them as CLI flags)"
        )
    if pub.startswith("sk-") or sec.startswith("pk-"):
        _die("LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY look swapped")
    out = {
        "LANGFUSE_PUBLIC_KEY": pub,
        "LANGFUSE_SECRET_KEY": sec,
        "LANGFUSE_HOST": _resolved_host(),
    }
    url = (
        os.environ.get("MAILROOM_PIPELINE_URL")
        or os.environ.get("MAILROOM_PIPELINE_API")
        or ""
    ).strip().rstrip("/")
    token = (
        os.environ.get("MAILROOM_PIPELINE_TOKEN")
        or os.environ.get("MAILROOM_API_TOKEN")
        or ""
    ).strip()
    if url:
        out["MAILROOM_PIPELINE_URL"] = url
    if token:
        out["MAILROOM_PIPELINE_TOKEN"] = token
    return out


def _variable_values() -> dict[str, str]:
    out = {
        "MAILROOM_SOURCE": os.environ.get("MAILROOM_SOURCE", "langfuse").strip() or "langfuse",
        "MAILROOM_EDITION": os.environ.get("MAILROOM_EDITION", "hosted").strip() or "hosted",
    }
    prefix = os.environ.get("MAILROOM_PIPELINE_API_PREFIX")
    if prefix is not None:
        text = prefix.strip()
        out["MAILROOM_PIPELINE_API_PREFIX"] = text if text else "/"
    elif (
        os.environ.get("MAILROOM_PIPELINE_URL")
        or os.environ.get("MAILROOM_PIPELINE_API")
    ):
        out["MAILROOM_PIPELINE_API_PREFIX"] = "/v1"
    return out


def stage_space_tree(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SPACE_README, dest / "README.md")
    shutil.copy2(DOCKERFILE, dest / "Dockerfile")
    if DOCKERIGNORE.is_file():
        shutil.copy2(DOCKERIGNORE, dest / ".dockerignore")
    shutil.copy2(PYPROJECT, dest / "pyproject.toml")
    for rel in COPY_PATHS:
        src = ROOT / rel
        target = dest / rel
        if src.is_dir():
            shutil.copytree(
                src,
                target,
                ignore=shutil.ignore_patterns(
                    "__pycache__",
                    "*.pyc",
                    ".pytest_cache",
                    "node_modules",
                    "dist",
                ),
            )
        else:
            shutil.copy2(src, target)
    # Safety: never ship a local .env into the Space tree.
    for leaked in dest.rglob(".env"):
        leaked.unlink()
    for leaked in dest.rglob(".env.*"):
        leaked.unlink()


def _api(token: str):
    try:
        from huggingface_hub import HfApi
    except ImportError:
        _die("huggingface_hub is required: pip install huggingface_hub")
    return HfApi(token=token)


def _whoami(api) -> str:
    info = api.whoami()
    name = info.get("name") if isinstance(info, dict) else None
    if not name:
        _die("HF_TOKEN did not resolve to a Hub username")
    return name


def _repo_id(api, explicit: str | None) -> str:
    if explicit:
        return explicit.strip().lstrip("/")
    env_id = (os.environ.get("MAILROOM_HF_SPACE") or "").strip()
    if env_id:
        return env_id
    return f"{_whoami(api)}/{DEFAULT_SPACE_NAME}"


def publish(args: argparse.Namespace) -> int:
    notes = check_payload()
    for line in notes:
        print(f"ok  {line}")
    if args.check:
        return 0

    token = (os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or "").strip()
    if not token:
        _die("set HF_TOKEN to create/update the Space")

    api = _api(token)
    repo_id = _repo_id(api, args.repo)
    print(f"space  {repo_id}")

    from huggingface_hub import create_repo

    create_repo(
        repo_id,
        repo_type="space",
        space_sdk="docker",
        private=bool(args.private),
        exist_ok=True,
        token=token,
    )

    if not args.skip_secrets:
        secrets = _secret_values()
        variables = _variable_values()
        for key, value in secrets.items():
            api.add_space_secret(repo_id, key, value)
            print(f"secret {key}  (set, value hidden)")
        add_var = getattr(api, "add_space_variable", None)
        for key, value in variables.items():
            if add_var is None:
                api.add_space_secret(repo_id, key, value)
                print(f"secret {key}={value}")
            else:
                add_var(repo_id, key, value)
                print(f"var    {key}={value}")

    if args.secrets_only:
        print(f"https://huggingface.co/spaces/{repo_id}")
        return 0

    staging = Path(tempfile.mkdtemp(prefix="mailroom-space-"))
    try:
        stage_space_tree(staging)
        api.upload_folder(
            repo_id=repo_id,
            repo_type="space",
            folder_path=str(staging),
            commit_message=args.message or "Publish Mailroom Observatory Docker Space",
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    url = f"https://huggingface.co/spaces/{repo_id}"
    print(f"published  {url}")
    print("build     Spaces → Logs  (Docker image on :7860)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate payload; no Hub calls")
    parser.add_argument("--repo", help="Space id (default: <whoami>/mailroom-observatory)")
    parser.add_argument("--private", action="store_true", help="create a private Space")
    parser.add_argument("--secrets-only", action="store_true", help="create/update secrets only")
    parser.add_argument("--skip-secrets", action="store_true", help="upload code without touching secrets")
    parser.add_argument("--message", help="Space commit message")
    args = parser.parse_args(argv)
    return publish(args)


if __name__ == "__main__":
    raise SystemExit(main())
