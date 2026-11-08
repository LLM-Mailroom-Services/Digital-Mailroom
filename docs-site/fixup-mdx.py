"""Fix MDX-invalid HTML left by the GitBook migration (run 2).

- Self-close void tags (<img>, <source>, <br>, <hr>) in .mdx files.
- Escape bare '<' that cannot start a JSX tag ('< ' / '<=' / '<digit' / '`<').
Only touches prose outside fenced code blocks and outside inline code spans.
Idempotent. Run from ~/workspace/digital-mailroom-docs.
"""
import re
from pathlib import Path

ROOT = Path("pages")
VOID_RE = re.compile(r"<(img|source|br|hr)(\s[^>]*?)(/?)>")
BARE_LT_RE = re.compile(r"<(?=[\s=`0-9])")

# Split a line into (is_code, text) segments on backtick runs.
CODE_RE = re.compile(r"(`+[^`]*`+)")


def fix_plain(seg: str) -> str:
    def close_void(m):
        tag, attrs, slash = m.group(1), m.group(2), m.group(3)
        if slash:
            return m.group(0)
        return f"<{tag}{attrs} />"

    seg = VOID_RE.sub(close_void, seg)
    seg = BARE_LT_RE.sub(r"\\<", seg)
    return seg


def fix_line(line: str) -> str:
    parts = CODE_RE.split(line)
    out = []
    for i, part in enumerate(parts):
        # Odd-index parts are backtick code spans (CODE_RE has a group).
        out.append(part if i % 2 == 1 else fix_plain(part))
    return "".join(out)


total = {"files": 0, "lines": 0}
for f in sorted(ROOT.rglob("*.mdx")):
    lines = f.read_text().splitlines(keepends=True)
    in_fence = False
    changed = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            new_lines.append(line)
            continue
        if in_fence:
            new_lines.append(line)
            continue
        fixed = fix_line(line.rstrip("\n"))
        if fixed != line.rstrip("\n"):
            changed = True
            total["lines"] += 1
            new_lines.append(fixed + "\n" if line.endswith("\n") else fixed)
        else:
            new_lines.append(line)
    if changed:
        f.write_text("".join(new_lines))
        total["files"] += 1
        print(f"  fixed {f.relative_to(ROOT)}")
print("files changed:", total["files"], "lines changed:", total["lines"])
