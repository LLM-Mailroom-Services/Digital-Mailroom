#!/usr/bin/env bash
# scripts/setup_t3.sh — guided local setup for a sandbox checkout (t3-code worktrees included).
#
# Usage: bash scripts/setup_t3.sh [--dry-run] [--worktree NAME] [--refresh-vendor]
#
#   --dry-run         change nothing: print the plan and record every step as "planned"
#   --worktree NAME   also create a git worktree ../<repo>-NAME on a new branch NAME
#   --refresh-vendor  run `sandbox fetch-deps` (network) instead of only verifying vendor/
#
# Every step records its real outcome (ok / failed / skipped / planned) as one JSON line in
# data/runtime/setup/evidence.jsonl, and the run's summary card goes to
# data/runtime/setup/card.json. Both are machine-local and gitignored (data/runtime/).
# Exported environment variables win over values in .env.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DRY_RUN=0
WORKTREE_NAME=""
REFRESH_VENDOR=0
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run) DRY_RUN=1 ;;
    --refresh-vendor) REFRESH_VENDOR=1 ;;
    --worktree)
      [[ $# -ge 2 && -n "$2" && "$2" != --* ]] || { echo "--worktree needs a NAME" >&2; exit 2; }
      WORKTREE_NAME="$2"; shift ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

# Load .env without overriding variables already exported in this shell.
if [[ -f .env ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*(export[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]] || continue
    key="${BASH_REMATCH[2]}"; val="${BASH_REMATCH[3]}"
    val="${val%$'\r'}"
    if [[ "$val" =~ ^\"(.*)\"$ || "$val" =~ ^\'(.*)\'$ ]]; then val="${BASH_REMATCH[1]}"; fi
    [[ -n "${!key+x}" ]] || export "$key=$val"
  done < .env
fi

PROFILE="${SANDBOX_PROFILE:-modal-vllm}"
OUT_DIR="data/runtime/setup"
EVIDENCE_LOG="$OUT_DIR/evidence.jsonl"
CARD_FILE="$OUT_DIR/card.json"
RUN_ID="setup-t3-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT_DIR"   # the run's own evidence directory (gitignored), written even in a dry run

# Step outcomes, in order, for the card: "name=status" entries.
STEPS=()

# record STEP STATUS DETAIL — append one JSON evidence line (values serialized by Python).
record() {
  STEPS+=("$1=$2")
  python3 - "$EVIDENCE_LOG" "$RUN_ID" "$1" "$2" "$3" "$PROFILE" "${WORKTREE_NAME:-}" "$DRY_RUN" <<'PY'
import json, sys
from datetime import datetime, timezone
path, run_id, step, status, detail, profile, worktree, dry = sys.argv[1:9]
rec = {"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "run_id": run_id, "step": step,
       "status": status, "detail": detail, "profile": profile, "worktree": worktree or None,
       "dry_run": dry == "1"}
with open(path, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
PY
}

# step NAME DETAIL CMD... — run CMD (or plan it in a dry run) and record the outcome.
step() {
  local name="$1" detail="$2"; shift 2
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "  [dry-run] would run: $*"
    record "$name" planned "$detail"
    return 0
  fi
  if "$@"; then
    record "$name" ok "$detail"
  else
    record "$name" failed "$detail (exit $?)"
    return 1
  fi
}

echo "=== Required environment (configure in .env before live runs) ==="
cat <<'CREDS'
  OPENROUTER_API_KEY    — token-billed Decisions / sorter_reviewer routes
  MODAL_TOKEN_ID + MODAL_TOKEN_SECRET (or a `modal` profile; MODAL_PROFILE selects it)
  SANDBOX_PROFILE       — default serving profile (default: modal-vllm)
  LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY — tracing (default sink)
  HF_TOKEN              — Hugging Face Hub pulls
  MAILROOM_CHECKPOINTER — human-review checkpointer (sqlite default)
  SANDBOX_DEBUG=1       — optional: set -x + results/run.log diagnostics
CREDS

if [[ $DRY_RUN -eq 1 ]]; then
  record credential_prompt skipped "dry run"
elif [[ -t 0 ]]; then
  echo "Press ENTER after confirming your .env has the keys above (or Ctrl+C to abort)."
  read -r
  record credential_prompt ok "confirmed interactively"
else
  record credential_prompt skipped "no terminal on stdin"
fi

echo "=== Setup: virtual environment ==="
if [[ -x .venv/bin/python ]]; then
  record venv ok ".venv already present"
elif ! step venv "python3 -m venv .venv" python3 -m venv .venv; then
  echo "error: could not create .venv; stopping before any install." >&2
  exit 1
fi
VENV_PY="$REPO_ROOT/.venv/bin/python"
# Install only through the venv's own interpreter, never into whatever pip is on PATH.
# The editable install provides the package and the `sandbox` entry point; requirements/dev.txt
# mirrors only the dependencies.
step install "pip install -e .[dev]" "$VENV_PY" -m pip install -q -e ".[dev]" || true

echo "=== Setup: .env ==="
if [[ -f .env ]]; then
  record env ok ".env already present"
else
  step env "copied config/.env.example to .env" cp config/.env.example .env || true
fi

echo "=== Setup: vendor snapshots ==="
if [[ $REFRESH_VENDOR -eq 1 ]]; then
  step vendor "sandbox fetch-deps (network refresh)" "$VENV_PY" -m mailroom_sandbox.cli fetch-deps || true
else
  # The tracked snapshots are self-contained; only verify that both import.
  step vendor "vendored llm-mailroom and llm-dojo-scoring import" \
    "$VENV_PY" -c "import mailroom_sandbox, pipeline.config, llm_dojo_scoring" || true
fi

echo "=== Setup: Modal CLI ==="
if [[ -n "${MODAL_PROFILE:-}" ]]; then
  step modal "modal profile activate $MODAL_PROFILE" "$REPO_ROOT/.venv/bin/modal" profile activate "$MODAL_PROFILE" || true
elif [[ -n "${MODAL_TOKEN_ID:-}" && -n "${MODAL_TOKEN_SECRET:-}" ]]; then
  record modal ok "MODAL_TOKEN_ID/MODAL_TOKEN_SECRET set (the SDK reads them; no profile change)"
else
  echo "warning: no Modal credentials — deploy / vLLM serve will fail."
  record modal skipped "no MODAL_PROFILE or MODAL_TOKEN_ID/MODAL_TOKEN_SECRET"
fi

echo "=== Setup: Hugging Face ==="
# huggingface_hub reads HF_TOKEN from the environment; no login (and no token on disk) is needed.
if [[ -n "${HF_TOKEN:-}" ]]; then
  record hf ok "HF_TOKEN set"
else
  record hf skipped "HF_TOKEN not set"
fi

echo "=== Setup: model overlay ==="
step overlay "config/models.yaml overlay loads" \
  "$VENV_PY" -c "from mailroom_sandbox.overlay import load_model_map; assert load_model_map(), 'empty model map'" || true

echo "=== Setup: worktree ==="
if [[ -n "$WORKTREE_NAME" ]]; then
  WT_PATH="$(dirname "$REPO_ROOT")/$(basename "$REPO_ROOT")-$WORKTREE_NAME"
  step worktree "git worktree add $WT_PATH -b $WORKTREE_NAME" git worktree add "$WT_PATH" -b "$WORKTREE_NAME" || true
else
  record worktree skipped "no --worktree"
fi

echo "=== Setup: subagent harness stubs ==="
# In a dry run the CLI itself plans the writes (`--dry-run`) instead of being skipped.
if [[ $DRY_RUN -eq 1 && -x .venv/bin/sandbox ]]; then
  if .venv/bin/sandbox subagents sync --harness all --dry-run; then
    record subagents planned "sandbox subagents sync --harness all --dry-run"
  else
    record subagents failed "sandbox subagents sync --harness all --dry-run"
  fi
else
  step subagents "sandbox subagents sync --harness all" "$REPO_ROOT/.venv/bin/sandbox" subagents sync --harness all || true
fi

echo "=== Setup: card ==="
python3 - "$CARD_FILE" "$RUN_ID" "$PROFILE" "${WORKTREE_NAME:-}" "$DRY_RUN" "$EVIDENCE_LOG" "${STEPS[@]}" <<'PY'
import json, subprocess, sys
from datetime import datetime, timezone
card_path, run_id, profile, worktree, dry, evidence, *steps = sys.argv[1:]
def git(*args):
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
checks = dict(s.split("=", 1) for s in steps)
card = {
    "card_id": "SETUP-T3",
    "run_id": run_id,
    "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "repo": "Exios66/local-mailroom-sandbox",
    "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
    "commit": git("rev-parse", "HEAD"),
    "profile": profile,
    "worktree": worktree or None,
    "dry_run": dry == "1",
    "credentials_required": ["OPENROUTER_API_KEY", "MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET", "SANDBOX_PROFILE",
                             "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "HF_TOKEN"],
    "checks": checks,
    "ready": dry != "1" and not any(v == "failed" for v in checks.values()),
    "evidence_file": evidence,
}
with open(card_path, "w", encoding="utf-8") as fh:
    json.dump(card, fh, indent=2)
    fh.write("\n")
failed = sorted(k for k, v in checks.items() if v == "failed")
print(f"card: {card_path} (ready={card['ready']})" + (f"; failed: {', '.join(failed)}" if failed else ""))
PY

echo "=== Setup finished (profile=$PROFILE, dry_run=$DRY_RUN) ==="
echo "Next: fill .env keys (see above), then: sandbox run preflight --config config/runs/<name>.yaml"
echo "Evidence: $EVIDENCE_LOG  Card: $CARD_FILE"
for s in "${STEPS[@]}"; do [[ "${s#*=}" == failed ]] && exit 1; done
exit 0
