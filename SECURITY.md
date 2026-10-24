# Security policy

## Reporting a vulnerability

**Do not open a public issue or PR with exploit details.** GitHub's private
vulnerability reporting is not enabled on this repository yet, so contact a
maintainer directly through their GitHub profile ([Exios66](https://github.com/Exios66),
[grantmooslin](https://github.com/grantmooslin)). If you cannot reach anyone, open an issue that
says only "security contact request", with no technical details, and a
maintainer will reach out. Include what you found, the affected path or
package, and steps to reproduce once you have a private channel.

If the issue lives in a package's own code (`llm-mailroom`, `llm-dojo-scoring`,
`The-Mailroom`, `local-mailroom-sandbox`, `mailroom-corpus-eda`), report it on
that standalone `Exios66/*` repo as well, because the standalone repos own
that code and hub copies are imported from them.

## What is in scope here

- Hub tooling: `scripts/`, `board-site/` (including its `/api/` proxy),
  `.github/` workflows
- Secrets handling: tokens committed, logged or exposed through the served board
- Anything that lets a contributor bypass the board or release governance

## Secrets: the rules

- Never commit credentials. `.env` and `*.env.local` are gitignored, and the
  repo's real tokens live in Vercel and GitHub secrets.
- The served board's proxy uses a `GITHUB_TOKEN` (or `MAILROOM_GH_TOKEN`) with
  Issues read/write on this repo only. It never sets GitHub assignees, and the
  token is never shipped to the browser.
- Sandbox and pipeline provider keys (HF, OpenRouter, Langfuse, Modal) belong
  in your local `.env` or a `modal.Secret`, never in code, tests or fixtures.
- If you committed a secret by accident, **rotate it first**, then ask a
  maintainer about history cleanup. Rewriting pushed history is reserved for
  human-directed corrections.

## Data handling

The corpora are legal-style documents. Treat anything outside the public
`mailroom-dataset` as sensitive. Do not paste real client documents into
issues, cards, commit messages or LLM prompts on third-party providers.
