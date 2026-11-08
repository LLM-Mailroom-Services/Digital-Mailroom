"""Fix-up pass for the GitBook -> Tome migration of Digital-Mailroom docs.

Run once from ~/workspace/digital-mailroom-docs. Deterministic, idempotent.
Does NOT touch the source repos (mailroom-documentation-intake,
digital-mailroom-intake) — only the Tome site in CWD.
"""
import re
import shutil
from pathlib import Path

ROOT = Path.cwd()
PAGES = ROOT / "pages"
SRC_DOCS = Path.home() / "workspace/mailroom-documentation-intake/docs"

OPENAPI_RE = re.compile(
    r'\{%\s*openapi\s+src="[^"]*"\s+path="([^"]+)"\s+method="(\w+)"\s*%\}.*?\{%\s*endopenapi\s*%\}',
    re.IGNORECASE | re.DOTALL,
)
UPDATES_RE = re.compile(r"^\{%\s*updates?[^%]*%\}\s*$", re.MULTILINE)
ENDUPDATE_RE = re.compile(r"^\{%\s*endupdates?\s*%\}\s*$", re.MULTILINE)
ENDEMBED_RE = re.compile(r"^\{%\s*endembed\s*%\}\s*$", re.MULTILINE)
# Asset paths inside img src / source srcset / markdown image targets only.
ASSET_RE = re.compile(r'((?:src|srcset)=")(?:\.\./)*\.gitbook/assets/')
ASSET_RE2 = re.compile(r"(\]\()(?:\.\./)*\.gitbook/assets/")

counts = {}


def count(key, n=1):
    counts[key] = counts.get(key, 0) + n


# 1. Copy the OpenAPI spec to the site root (Tome api.spec points here).
spec_src = SRC_DOCS / "api-reference/mailroom-openapi.yaml"
shutil.copyfile(spec_src, ROOT / "openapi.yaml")
print("copied openapi.yaml")

# 2. Replace {% openapi %} blocks in api-reference pages with a pointer
#    to Tome's generated /api reference.
for f in sorted((PAGES / "api-reference").glob("*.md")):
    text = f.read_text()

    def repl(m):
        path, method = m.group(1), m.group(2).upper()
        return f"See the interactive reference for `{method} {path}` on the [API page](/api)."

    new, n = OPENAPI_RE.subn(repl, text)
    if n:
        f.write_text(new)
        count("openapi-blocks", n)
        print(f"  {f.name}: replaced {n} openapi blocks")

# 3. Strip {% updates %}/{% update %}/{% endupdate %} wrappers in changelog README.
f = PAGES / "changelog/README.mdx"
text = f.read_text()
new = UPDATES_RE.sub("", text)
new = ENDUPDATE_RE.sub("", new)
if new != text:
    f.write_text(new)
    count("changelog-update-wrappers", 1)
    print("  changelog/README.mdx: stripped updates/update wrappers")

# 4. Remove stray {% endembed %} lines left by the migrator.
for f in PAGES.rglob("*.md*"):
    text = f.read_text()
    new, n = ENDEMBED_RE.subn("", text)
    if n:
        f.write_text(new)
        count("endembed-lines", n)
        print(f"  {f.relative_to(PAGES)}: removed {n} stray endembed lines")

# 5. Rewrite GitBook asset paths to Tome public paths (img/srcset/md-image only).
for f in PAGES.rglob("*.md*"):
    text = f.read_text()
    new = ASSET_RE.sub(r"\1/assets/", text)
    new = ASSET_RE2.sub(r"\1/assets/", new)
    if new != text:
        f.write_text(new)
        count("asset-path-rewrites", 1)
        print(f"  {f.relative_to(PAGES)}: rewrote asset paths")

# 6. Move the asset-inventory READMEs out of pages/ (they are not site pages).
notes = ROOT / "notes"
notes.mkdir(exist_ok=True)
for src in [PAGES / "assets/README.md", PAGES / "assets/mascot/README.md"]:
    if src.exists():
        dest = notes / ("assets-inventory.md" if src.parent.name == "assets" else "mascot-inventory.md")
        shutil.move(str(src), str(dest))
        count("moved-inventory-readmes", 1)
        print(f"  moved {src.relative_to(PAGES)} -> notes/{dest.name}")
# Remove now-empty assets dirs under pages/
for d in [PAGES / "assets/mascot", PAGES / "assets"]:
    if d.exists() and not any(d.iterdir()):
        d.rmdir()

print("counts:", counts)
