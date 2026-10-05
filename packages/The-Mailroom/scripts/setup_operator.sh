#!/bin/bash
# Prepare the operator desk (auth / archive / bin observer).
# Does not clone llm-mailroom, does not install npm, does not build a React UI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== The-Mailroom operator desk setup ==="

mkdir -p "${MAILROOM_BASE_DIR:-data}/pipeline/"{inbox,processing,classified,review,failed}
mkdir -p "${MAILROOM_BASE_DIR:-data}/archive"

python -m operator_desk

echo "=== Setup complete. ==="
echo "  mailroom-web            # visualizer + /v1/auth /v1/archive /v1/ops /ws/pipeline"
echo "  mailroom-observer       # optional standalone bin watcher (or MAILROOM_OBSERVER=1)"
echo "  docker compose -f operator_desk/docker-compose.yml up --build"
