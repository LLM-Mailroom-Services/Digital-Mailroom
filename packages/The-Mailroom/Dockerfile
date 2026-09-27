# Mailroom Observatory — public hosted edition.
# Works on Hugging Face Spaces (Docker SDK, port 7860), Railway, Fly, Render,
# or any host that runs a container and injects Langfuse secrets. This is NOT
# the GitHub Pages snapshot and NOT the local pixel-art console.
#
# Prefer platform PORT (Railway/Fly/Render) over the Spaces image default.
# Health: GET /health and GET /api/health.
#
# Build targets:
#   (default)   hosted Observatory — `pip install .`, port 7860,
#               `python -m server.hosted`. HF Spaces / Railway / Fly.
#   operator    operator desk — `pip install .[operator]`, prebuilt React
#               /desk baked in, port 8001, `python -m server.main`.
#               Built by operator_desk/docker-compose.yml; see its README.
#
# The default build is the hosted edition unchanged: the operator extras are
# opt-in via --build-arg MAILROOM_EXTRAS and the final stage below stays the
# hosted image (Docker builds the LAST stage when no --target is given).

FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# Hosted default installs no extras. The operator compose passes
# MAILROOM_EXTRAS=operator so this same builder stage also produces the
# operator image — the hosted path never sees the flag.
ARG MAILROOM_EXTRAS=""

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY mailroom_ui ./mailroom_ui
COPY server ./server
COPY hosted ./hosted
COPY web ./web
COPY tui ./tui
COPY operator_desk ./operator_desk

RUN if [ -n "$MAILROOM_EXTRAS" ]; then \
        pip install --no-cache-dir --prefix=/install ".[${MAILROOM_EXTRAS}]"; \
    else \
        pip install --no-cache-dir --prefix=/install .; \
    fi


# --- optional React operator desk ------------------------------------------
# Built only for the `operator` target (this stage is not an ancestor of the
# default hosted image, so a bare `docker build .` skips it — no Node in the
# hosted path). Vite's production base is /desk/, matching operator_desk/mount.
FROM node:22-alpine AS ui-builder

ENV NODE_ENV=production
WORKDIR /ui

COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build


# ---- Optional React operator desk (ui/) — build stage only, never a runtime
# dependency. The production compose (`operator_desk/docker-compose.yml`) uses
# the `operator` target below, which bakes ui/dist into the image; this stage
# is not part of the default (hosted) build.
FROM node:22-alpine AS ui-builder

WORKDIR /ui

COPY ui/package.json ui/package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund

COPY ui/ ./
# Production default base is /desk/ (vite.config.ts); the standalone ui image
# overrides it with VITE_BASE=/. The baked operator desk keeps /desk/.
RUN npm run build


FROM python:3.11-slim-bookworm AS runtime

WORKDIR /app

# Bake the deployed commit so /health and /api/meta can verify the live build.
# Railway injects RAILWAY_GIT_COMMIT_SHA for GitHub-sourced deploys; the
# default keeps HF Spaces / Fly / Render builds working unchanged.
ARG RAILWAY_GIT_COMMIT_SHA=unknown
ENV MAILROOM_BUILD_SHA=$RAILWAY_GIT_COMMIT_SHA

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 mailroom \
    && useradd --system --uid 10001 --gid mailroom --home-dir /app --shell /usr/sbin/nologin mailroom \
    && mkdir -p /tmp/mailroom-trace-cache \
    && chown -R mailroom:mailroom /app /tmp/mailroom-trace-cache

COPY --from=builder /install /usr/local
COPY --chown=mailroom:mailroom pyproject.toml README.md ./
COPY --chown=mailroom:mailroom mailroom_ui ./mailroom_ui
COPY --chown=mailroom:mailroom server ./server
COPY --chown=mailroom:mailroom hosted ./hosted
COPY --chown=mailroom:mailroom web ./web
COPY --chown=mailroom:mailroom tui ./tui
COPY --chown=mailroom:mailroom operator_desk ./operator_desk

ENV MAILROOM_EDITION=hosted
ENV MAILROOM_HOST=0.0.0.0
ENV MAILROOM_PORT=7860
ENV MAILROOM_POLL_ENRICH=inflight
ENV MAILROOM_TRACE_CACHE_DIR=/tmp/mailroom-trace-cache
ENV PYTHONUNBUFFERED=1

USER mailroom

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import os,urllib.request; p=os.environ.get('PORT') or os.environ.get('MAILROOM_PORT','7860'); urllib.request.urlopen(f'http://127.0.0.1:{p}/health', timeout=3)"

CMD ["python", "-m", "server.hosted"]


# ---- Operator edition: the hosted runtime + operator extras. Built
# explicitly with `docker build --target operator-core` for an optional
# standalone `mailroom-observer` CLI image — no Node stage, no ui/dist.
# Default compose does NOT run this as a sidecar (issue #78: one watcher).
FROM runtime AS operator-core

USER root

# MAILROOM_EXTRAS is a build ARG (compose passes `args: MAILROOM_EXTRAS:
# operator`); the explicit fallback pins the same four deps as the
# `[operator]` extra in case the workspace copy is not installable as-is.
ARG MAILROOM_EXTRAS=operator
RUN pip install --no-cache-dir ".[${MAILROOM_EXTRAS}]" || \
    pip install --no-cache-dir bcrypt PyJWT watchdog pymupdf

# /data (bins + operator SQLite) must be writable by the app user. A fresh
# named volume is populated from this directory on first mount, so the
# ownership carries over — without this, `mailroom` (uid 10001) cannot
# create /data/operator.db or the pipeline bins in a root-owned volume.
RUN mkdir -p /data && chown -R mailroom:mailroom /data

USER mailroom

# /app/ui/dist → operator_desk.mount.react_ui_dist() default, so /desk mounts.
# ---- Operator edition + the baked React operator desk: extends
# operator-core with the ui-builder output → /app/ui/dist →
# operator_desk/mount.py `react_ui_dist()` → GET /desk when index.html
# exists. Built with `docker build --target operator` or by the operator-
# desk compose for the visualizer service.
FROM operator-core AS operator

ENV MAILROOM_EDITION=console
ENV MAILROOM_PORT=8001

COPY --from=ui-builder --chown=mailroom:mailroom /ui/dist ./ui/dist

EXPOSE 8001

CMD ["python", "-m", "server.main"]

# --- default build target: hosted Observatory (MUST stay last) --------------
# A bare `docker build .` (HF Spaces / Railway / Fly) targets the last stage,
# so this alias keeps the hosted edition byte-for-byte unchanged. Do not move
# a stage below it.
FROM runtime AS observatory
