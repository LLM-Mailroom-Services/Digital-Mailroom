"""Railway Infrastructure as Code — the LLM-Mailroom project.

Railway retired Config as Code (railway.json / railway.toml): existing files
kept working only until 2026-12-01, and new projects stopped reading them on
2026-08-28. This file is the replacement — one project definition evaluated by
the Railway CLI (`railway config plan` / `railway config apply`).

IaC is project-wide (omit a service = delete it), so BOTH services of the
LLM-Mailroom project are declared here:

- `llm-mailroom` — the producer. Its config lives in the llm-mailroom repo;
  this file only pins its current shape (`preserve()` everywhere) so the
  visualizer's IaC never touches it.
- `The-Mailroom` — this visualizer. Owned here: Dockerfile source (Railway
  builds the repo's root Dockerfile when it finds one), start command,
  `/health` liveness probe, and the non-secret variables. Secrets stay as
  `preserve()` on the service.

Authoring is the beta Python mirror of the TypeScript DSL (`railway_sdk`);
install it on the authoring machine only (never at runtime):
    pip install railway-sdk

Deploy code with `railway up` or the GitHub integration.
"""

from railway_sdk import define_railway, github, preserve, project, service


@define_railway
def main(ctx=None):
    # Producer — managed by the llm-mailroom repo. Placeholder only.
    llmMailroom = service(
        "llm-mailroom",
        replicas={"sfo": 1},
        env={
            "HF_HOME": preserve(),
            "HF_HUB_CACHE": preserve(),
            "HF_TOKEN": preserve(),
            "HUGGING_FACE_HUB_TOKEN": preserve(),
            "LANGFUSE_BASE_URL": preserve(),
            "LANGFUSE_HOST": preserve(),
            "LANGFUSE_PUBLIC_KEY": preserve(),
            "LANGFUSE_SECRET_KEY": preserve(),
            "LOG_FORMAT": preserve(),
            "MAILROOM_API_HOST": preserve(),
            "MAILROOM_API_TOKEN": preserve(),
            "MAILROOM_BASE_DIR": preserve(),
            "MAILROOM_EMBED_WATCHER": preserve(),
            "MAILROOM_HF_CORPUS": preserve(),
            "MAILROOM_HF_DATASET": preserve(),
            "MAILROOM_HF_REVISION": preserve(),
            "OBSERVABILITY_PROVIDER": preserve(),
            "OPENROUTER_API_KEY": preserve(),
        },
    )

    # Visualizer — this repo owns it. Secrets preserve()d; non-secret
    # variables declared here so a fresh checkout reproduces the service.
    TheMailroom = service(
        "The-Mailroom",
        source=github("Exios66/The-Mailroom"),
        start="python -m server.hosted",
        healthcheck="/health",
        healthcheckTimeout=300,
        replicas={"us-east4-eqdc4a": 1},
        networking={"privateNetworkEndpoint": "the-mailroom"},
        env={
            "MAILROOM_EDITION": "hosted",
            "MAILROOM_HOST": "0.0.0.0",
            "MAILROOM_POLL_ENRICH": "inflight",
            "MAILROOM_TRACE_CACHE_DIR": "/tmp/mailroom-trace-cache",
            "HF_TOKEN": preserve(),
            "HUGGING_FACE_HUB_TOKEN": preserve(),
            "LANGFUSE_BASE_URL": preserve(),
            "LANGFUSE_HOST": preserve(),
            "LANGFUSE_PUBLIC_KEY": preserve(),
            "LANGFUSE_SECRET_KEY": preserve(),
            "MAILROOM_HF_CONFIG": preserve(),
            "MAILROOM_HF_DATASET": preserve(),
            "MAILROOM_HF_REVISION": preserve(),
            "MAILROOM_PIPELINE_API_PREFIX": preserve(),
            "MAILROOM_PIPELINE_TOKEN": preserve(),
            "MAILROOM_PIPELINE_URL": preserve(),
            "MAILROOM_TRACE_ENVIRONMENTS": preserve(),
            "MAILROOM_TRACE_LIMIT": preserve(),
            "MAILROOM_TRACE_NAMES": preserve(),
            "MAILROOM_TRACE_TAGS": preserve(),
            "OPENROUTER_API_KEY": preserve(),
        },
    )

    return project("LLM-Mailroom", resources=[llmMailroom, TheMailroom])