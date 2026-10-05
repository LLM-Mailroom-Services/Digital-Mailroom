# Mailroom Observatory — public hosted edition.
# Works on Hugging Face Spaces (Docker SDK, port 7860), Railway, Fly, Render,
# or any host that runs a container and injects Langfuse secrets. This is NOT
# the GitHub Pages snapshot and NOT the local pixel-art console.
#
# Prefer platform PORT (Railway/Fly/Render) over the Spaces image default.
# Health: GET /health and GET /api/health.

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

RUN pip install --no-cache-dir --prefix=/install .


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
