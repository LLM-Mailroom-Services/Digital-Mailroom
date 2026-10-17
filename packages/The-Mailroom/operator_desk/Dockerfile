# Operator-desk image — the visualizer plus the `[operator]` extra
# (watchdog / bcrypt / PyJWT / PyMuPDF) and the prebuilt React /desk.
#
# Built by operator_desk/docker-compose.yml with the repo root as context:
#   docker build -f operator_desk/Dockerfile .
#
# The hosted Observatory image (root Dockerfile: HF Spaces / Railway / Fly)
# is deliberately separate and unchanged — it never needs Node or ui/, and
# the Space payload (scripts/publish_space.py) does not ship ui/ at all.
# Keep the Python base image in step with the root Dockerfile.

FROM node:22-alpine AS ui-builder

WORKDIR /ui

# devDependencies (vite, typescript) are build tools: install them, and only
# set NODE_ENV=production for the build itself, which selects the /desk/ base
# (ui/vite.config.ts).
COPY ui/package.json ui/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY ui/ ./
RUN NODE_ENV=production npm run build


FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

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

RUN pip install --no-cache-dir --prefix=/install ".[operator]"


FROM python:3.11-slim-bookworm AS operator

WORKDIR /app

ARG MAILROOM_BUILD_SHA=unknown
ENV MAILROOM_BUILD_SHA=$MAILROOM_BUILD_SHA

# /data holds the bins + operator SQLite. A fresh named volume is seeded from
# this directory on first mount, so the app user owns it from the start.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 mailroom \
    && useradd --system --uid 10001 --gid mailroom --home-dir /app --shell /usr/sbin/nologin mailroom \
    && mkdir -p /data /tmp/mailroom-trace-cache \
    && chown -R mailroom:mailroom /app /data /tmp/mailroom-trace-cache

COPY --from=builder /install /usr/local
COPY --chown=mailroom:mailroom pyproject.toml README.md ./
COPY --chown=mailroom:mailroom mailroom_ui ./mailroom_ui
COPY --chown=mailroom:mailroom server ./server
COPY --chown=mailroom:mailroom hosted ./hosted
COPY --chown=mailroom:mailroom web ./web
COPY --chown=mailroom:mailroom tui ./tui
COPY --chown=mailroom:mailroom operator_desk ./operator_desk
# operator_desk.mount.react_ui_dist() defaults to <repo>/ui/dist → GET /desk.
COPY --from=ui-builder --chown=mailroom:mailroom /ui/dist ./ui/dist

ENV MAILROOM_EDITION=console
ENV MAILROOM_HOST=0.0.0.0
ENV MAILROOM_PORT=8001
ENV MAILROOM_BASE_DIR=/data
ENV MAILROOM_OPERATOR_DB=/data/operator.db
ENV MAILROOM_TRACE_CACHE_DIR=/tmp/mailroom-trace-cache
ENV PYTHONUNBUFFERED=1

USER mailroom

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import os,urllib.request; p=os.environ.get('PORT') or os.environ.get('MAILROOM_PORT','8001'); urllib.request.urlopen(f'http://127.0.0.1:{p}/health', timeout=3)"

CMD ["python", "-m", "server.main"]
