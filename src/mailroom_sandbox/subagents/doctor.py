"""Harness health checks for OpenCode, Cursor, and family roster sync."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from mailroom_sandbox.paths import repo_root
from mailroom_sandbox.subagents.parse_opencode import parse_opencode_markdown
from mailroom_sandbox.subagents.roster import SubagentEntry, harness_config, load_roster

Severity = Literal["ok", "warn", "fail", "info"]

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FRAMEWORK_MARKER = "## Agent framework (v2)"


@dataclass
class Finding:
    code: str
    severity: Severity
    message: str
    path: str | None = None
    hint: str | None = None


@dataclass
class DoctorReport:
    findings: list[Finding] = field(default_factory=list)
    harness: str = "multi"

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)


def _package_for_checkout(base: Path) -> str | None:
    pointer = base / "config" / "subagents" / "roster.yaml"
    if not pointer.is_file():
        return None
    doc = yaml.safe_load(pointer.read_text(encoding="utf-8")) or {}
    pkg = doc.get("package")
    return str(pkg) if pkg else None


def expand_agents_dir(agents_dir: str) -> Path:
    p = Path(agents_dir)
    if agents_dir.startswith("~/"):
        return Path.home() / agents_dir[2:]
    return p.expanduser().resolve()


def _read_jsonc(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    # Strip // and /* */ comments for a coarse parse
    stripped = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Do not strip `//` inside URLs (https://); only line comments after whitespace
    stripped = re.sub(r"(^|\s)//[^\n]*", r"\1", stripped, flags=re.MULTILINE)
    # OpenCode env placeholders like {env:VAR} are not JSON — treat as strings
    stripped = re.sub(r"\{env:[^}]+\}", "ENV_PLACEHOLDER", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def _framework_excerpt(root: Path) -> str:
    path = root / "config" / "subagents" / "AGENT_FRAMEWORK.md"
    if not path.is_file():
        return ""
    raw = path.read_text(encoding="utf-8")
    # Body only (skip title line)
    lines = raw.splitlines()
    if lines and lines[0].startswith("#"):
        lines = lines[1:]
    return _FRAMEWORK_MARKER + "\n\n" + "\n".join(lines).strip() + "\n"


def _agent_has_framework(body: str) -> bool:
    return _FRAMEWORK_MARKER in body


def audit_agent_file(path: Path, *, expect_roster_id: str | None = None) -> list[Finding]:
    out: list[Finding] = []
    if not path.is_file():
        out.append(
            Finding(
                code="agent.missing",
                severity="fail",
                message=f"Agent file missing: {path}",
            )
        )
        return out
    text = path.read_text(encoding="utf-8")
    doc = parse_opencode_markdown(text)
    if not doc.description and not doc.frontmatter.get("description"):
        out.append(
            Finding(
                code="agent.no_description",
                severity="warn",
                message="Frontmatter missing description (OpenCode routing quality degrades)",
                path=str(path),
            )
        )
    roster_id = doc.frontmatter.get("roster_id")
    if expect_roster_id and roster_id != expect_roster_id:
        out.append(
            Finding(
                code="agent.roster_id_mismatch",
                severity="fail",
                message=f"roster_id {roster_id!r} != expected {expect_roster_id!r}",
                path=str(path),
                hint="Run sandbox subagents sync --harness opencode-global",
            )
        )
    if not _agent_has_framework(doc.body):
        out.append(
            Finding(
                code="agent.framework_v2_missing",
                severity="warn",
                message="Agent body missing Agent framework (v2) block",
                path=str(path),
                hint="sandbox subagents doctor --apply-framework",
            )
        )
    return out


def _compare_canonical(entry: SubagentEntry, deployed: Path, canonical: Path) -> Finding | None:
    if not deployed.is_file() or not canonical.is_file():
        return None
    dep = parse_opencode_markdown(deployed.read_text(encoding="utf-8"))
    can = parse_opencode_markdown(canonical.read_text(encoding="utf-8"))
    if dep.body.strip() != can.body.strip():
        return Finding(
            code="agent.body_drift",
            severity="warn",
            message=f"Global/project copy drift from canonical for {entry.id}",
            path=str(deployed),
            hint=f"sync from {canonical}",
        )
    return None


def run_doctor(
    *,
    root: Path | None = None,
    package: str | None = None,
    include_global: bool = True,
    include_cursor: bool = True,
    extra_roots: tuple[Path, ...] = (),
) -> DoctorReport:
    bases: list[tuple[Path, str | None]] = [(root or repo_root(), package)]
    for extra in extra_roots:
        bases.append((extra, package or _package_for_checkout(extra)))

    report = DoctorReport()
    for base, pkg in bases:
        report.findings.extend(
            _run_doctor_one(
                base,
                package=pkg,
                include_global=include_global and base == (root or repo_root()),
                include_cursor=include_cursor,
            )
        )
    return report


def opencode_db_report() -> list[Finding]:
    """Read-only size / sidecar stats for ~/.local/share/opencode/opencode.db."""
    out: list[Finding] = []
    share = Path.home() / ".local" / "share" / "opencode"
    db = share / "opencode.db"
    if not db.is_file():
        return out
    gb = db.stat().st_size / (1024**3)
    wal = share / "opencode.db-wal"
    shm = share / "opencode.db-shm"
    out.append(
        Finding(
            code="opencode.db_size",
            severity="warn" if gb > 2 else "info",
            message=f"opencode.db is {gb:.2f} GiB",
            path=str(db),
            hint=(
                "Quit OpenCode, backup the db, then: sqlite3 opencode.db 'VACUUM;'"
                if gb > 2
                else None
            ),
        )
    )
    if wal.is_file():
        wal_mb = wal.stat().st_size / (1024**2)
        if wal_mb > 500:
            out.append(
                Finding(
                    code="opencode.wal_large",
                    severity="warn",
                    message=f"opencode.db-wal is {wal_mb:.0f} MiB — checkpoint may be delayed",
                    path=str(wal),
                )
            )
    if shm.is_file():
        out.append(
            Finding(
                code="opencode.db_sidecars",
                severity="info",
                message="WAL mode sidecars present (normal while OpenCode is running)",
                path=str(shm),
            )
        )
    return out


def _run_doctor_one(
    base: Path,
    *,
    package: str | None,
    include_global: bool,
    include_cursor: bool,
) -> list[Finding]:
    findings: list[Finding] = []

    if include_global:
        opencode_cfg = Path.home() / ".config" / "opencode" / "opencode.jsonc"
        cfg = _read_jsonc(opencode_cfg)
        if cfg is None:
            findings.append(
                Finding(
                    code="opencode.config_missing",
                    severity="fail",
                    message=f"Cannot read OpenCode config at {opencode_cfg}",
                )
            )
        else:
            mcp = cfg.get("mcp") or {}
            enabled = [k for k, v in mcp.items() if isinstance(v, dict) and v.get("enabled")]
            findings.append(
                Finding(
                    code="opencode.mcp_enabled",
                    severity="info",
                    message=f"OpenCode MCP servers enabled: {', '.join(enabled) or '(none)'}",
                    path=str(opencode_cfg),
                )
            )

        mcp_auth = Path.home() / ".local" / "share" / "opencode" / "mcp-auth.json"
        if not mcp_auth.is_file():
            findings.append(
                Finding(
                    code="opencode.mcp_auth_missing",
                    severity="warn",
                    message="mcp-auth.json missing — remote MCP OAuth may fail until you sign in",
                    path=str(mcp_auth.parent),
                )
            )

        findings.extend(opencode_db_report())

    node = shutil.which("node")
    if node:
        try:
            ver = subprocess.check_output([node, "--version"], text=True).strip()
            major = int(ver.lstrip("v").split(".")[0])
            if major < 24:
                findings.append(
                    Finding(
                        code="node.below_eve",
                        severity="warn",
                        message=f"{ver} installed — eve agents need Node >= 24 for `npx eve`",
                        hint="brew install node@24 && export PATH=/opt/homebrew/opt/node@24/bin:$PATH",
                    )
                )
        except (subprocess.CalledProcessError, ValueError):
            pass

    if not (base / "config" / "subagents" / "family-roster.yaml").is_file() and not (
        base / "governance" / "subagents" / "family-roster.yaml"
    ).is_file():
        findings.append(
            Finding(
                code="family.roster_missing",
                severity="fail",
                message=f"No family roster under {base}",
                hint="sandbox subagents materialize --package <id> --root <path>",
            )
        )
        return findings

    roster = load_roster(base, package)
    for entry in roster:
        canonical = entry.opencode_path(base)
        findings.extend(audit_agent_file(canonical, expect_roster_id=entry.id))

        project_copy = base / ".opencode" / "agents" / f"{entry.id}.md"
        drift = _compare_canonical(entry, project_copy, canonical)
        if drift:
            findings.append(drift)

        if include_global and "opencode-global" in entry.harnesses:
            try:
                gcfg = harness_config("opencode-global", base)
                global_dir = expand_agents_dir(gcfg["agents_dir"])
                global_path = global_dir / f"{entry.id}.md"
                findings.extend(audit_agent_file(global_path, expect_roster_id=entry.id))
                drift_g = _compare_canonical(entry, global_path, canonical)
                if drift_g:
                    findings.append(drift_g)
            except KeyError:
                findings.append(
                    Finding(
                        code="roster.no_opencode_global",
                        severity="warn",
                        message="family-roster missing opencode-global harness definition",
                    )
                )

        if include_cursor:
            cursor_path = entry.cursor_path(base)
            if cursor_path.is_file():
                text = cursor_path.read_text(encoding="utf-8")
                if "Harness note:" not in text:
                    findings.append(
                        Finding(
                            code="cursor.stub_stale",
                            severity="warn",
                            message=f"Cursor stub for {entry.id} missing harness note",
                            path=str(cursor_path),
                            hint="sandbox subagents sync --harness cursor",
                        )
                    )
            else:
                findings.append(
                    Finding(
                        code="cursor.stub_missing",
                        severity="warn",
                        message=f"Missing Cursor stub for roster agent {entry.id}",
                        path=str(cursor_path),
                    )
                )

    return findings


def apply_framework_to_agents(
    *,
    root: Path | None = None,
    package: str | None = None,
    targets: tuple[str, ...] = ("opencode", "opencode-global"),
    dry_run: bool = False,
) -> list[Path]:
    base = root or repo_root()
    pkg = package or _package_for_checkout(base)
    excerpt = _framework_excerpt(base if (base / "config" / "subagents" / "AGENT_FRAMEWORK.md").is_file() else repo_root())
    if not excerpt.strip():
        raise FileNotFoundError(base / "config" / "subagents" / "AGENT_FRAMEWORK.md")

    written: list[Path] = []
    for entry in load_roster(base, pkg):
        paths: list[Path] = []
        if "opencode" in targets:
            paths.append(entry.opencode_path(base))
        if "opencode-global" in targets and "opencode-global" in entry.harnesses:
            gcfg = harness_config("opencode-global", base)
            paths.append(expand_agents_dir(gcfg["agents_dir"]) / f"{entry.id}.md")

        for path in paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            doc = parse_opencode_markdown(text)
            if _agent_has_framework(doc.body):
                continue
            new_body = doc.body.rstrip() + "\n\n" + excerpt
            front = doc.frontmatter
            yaml_block = yaml.safe_dump(front, sort_keys=False, allow_unicode=True, width=1000).strip()
            new_text = f"---\n{yaml_block}\n---\n\n{new_body}"
            if not dry_run:
                path.write_text(new_text, encoding="utf-8")
            written.append(path)
    return written


def apply_framework_to_global_profiles(*, dry_run: bool = False) -> list[Path]:
    """Append framework v2 to global OpenCode agents not on the family roster."""
    global_dir = Path.home() / ".config" / "opencode" / "agents"
    base = repo_root()
    excerpt = _framework_excerpt(base)
    if not excerpt.strip():
        raise FileNotFoundError(base / "config" / "subagents" / "AGENT_FRAMEWORK.md")
    roster_ids = {e.id for e in load_roster(base)}
    written: list[Path] = []
    if not global_dir.is_dir():
        return written
    for path in sorted(global_dir.glob("*.md")):
        if path.name.startswith("PROVENANCE") or path.name.startswith("PROMPT_"):
            continue
        agent_id = path.stem
        if agent_id in roster_ids:
            continue
        text = path.read_text(encoding="utf-8")
        doc = parse_opencode_markdown(text)
        if _agent_has_framework(doc.body):
            continue
        new_body = doc.body.rstrip() + "\n\n" + excerpt
        front = doc.frontmatter
        yaml_block = yaml.safe_dump(front, sort_keys=False, allow_unicode=True, width=1000).strip()
        new_text = f"---\n{yaml_block}\n---\n\n{new_body}"
        if not dry_run:
            path.write_text(new_text, encoding="utf-8")
        written.append(path)
    return written


def findings_to_dict(report: DoctorReport) -> dict[str, Any]:
    return {
        "harness": report.harness,
        "findings": [
            {
                "code": f.code,
                "severity": f.severity,
                "message": f.message,
                "path": f.path,
                "hint": f.hint,
            }
            for f in report.findings
        ],
        "summary": {
            "fail": sum(1 for f in report.findings if f.severity == "fail"),
            "warn": sum(1 for f in report.findings if f.severity == "warn"),
            "ok": sum(1 for f in report.findings if f.severity == "ok"),
        },
    }
