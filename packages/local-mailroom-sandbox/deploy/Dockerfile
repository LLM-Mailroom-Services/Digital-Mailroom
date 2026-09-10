# Offline sandbox + Jupyter Lab image for local-mailroom-sandbox.
# Build from repo root:
#   docker build -f deploy/Dockerfile -t mailroom-sandbox:offline .
# Or via compose:
#   sandbox up --compose-profile jupyter
#
# This image does NOT reimplement the mailroom graph. It installs the sandbox
# harness and notebook extras so you can prepare fixtures and activate profiles
# without a cloud LLM.

FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SANDBOX_ROOT=/workspace \
    MAILROOM_BASE_DIR=/workspace/data \
    JUPYTER_PORT=8888

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install package metadata first for better layer caching, then the tree.
COPY pyproject.toml README.md AGENTS.md ./
COPY src ./src
COPY config ./config
COPY data/fixtures ./data/fixtures
COPY notebooks ./notebooks
COPY deploy/README.md ./deploy/README.md

RUN pip install --no-cache-dir -e ".[dev,notebooks]" \
    && mkdir -p /workspace/data/runtime /workspace/data/cache /workspace/reports \
    && useradd --create-home --uid 1000 --shell /bin/bash sandbox \
    && chown -R sandbox:sandbox /workspace

# Bind mounts carry host ownership; on hosts whose first user is not uid 1000,
# override with --user "$(id -u):$(id -g)" (docker compose: user: "1000:1000").
USER sandbox

EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8888/lab >/dev/null || exit 1

# Tokenless Lab on the compose network; bind only to localhost from the host.
CMD ["jupyter", "lab", \
     "--ip=0.0.0.0", \
     "--port=8888", \
     "--no-browser", \
     "--ServerApp.token=", \
     "--ServerApp.password=", \
     "--ServerApp.root_dir=/workspace", \
     "--allow-root"]

# To run the sandbox CLI instead of Jupyter:
#   docker run --entrypoint sandbox mailroom-sandbox:offline pilot --mock
#   docker run --entrypoint sandbox mailroom-sandbox:offline up --profile ollama
