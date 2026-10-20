#!/usr/bin/env python3
"""Check the Praxis Agent OpenAI plugin package against OpenAI's published rules.

OpenAI publishes no offline validator for plugin ZIPs (checked 2026-10-20), so
this script enforces the limits written in:

  https://developers.openai.com/apps-sdk/deploy/submission
  https://developers.openai.com/plugins/build/plugins
  https://developers.openai.com/plugins/deploy/submission-errors
  https://developers.openai.com/plugins/plugin-guidelines

Usage:
  python3 check_package.py DIR          # check a staged package folder (build-zip.sh stages one)
  python3 check_package.py FILE.zip     # check a built ZIP
  python3 check_package.py DIR --review REVIEW.md   # also compare test cases

Standard library only. Exit code 0 = no errors, 1 = errors.
"""

from __future__ import annotations

import json
import re
import struct
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"

CATEGORIES = {
    "Productivity", "Creativity", "Developer Tools", "Business & Operations",
    "Data & Analytics", "Communication", "Education & Research", "Security",
    "Finance", "Healthcare", "Travel", "Entertainment", "Other",
}
ROOT_KEYS = {"$schema", "name", "version", "description", "author", "homepage",
             "repository", "license", "keywords", "extensions"}
FORBIDDEN_KEYS = {"clientSecret", "client_secret", "test_credentials",
                  "reviewer_instructions", "apps", "hooks"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
# Schema pattern AND the portal's final-submission rule.
NAME_SCHEMA = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
NAME_PORTAL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
COUNTRY = re.compile(r"^[A-Z]{2}$")
SECRET_PATTERNS = [
    re.compile(r"pa_cred_[A-Za-z0-9]"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{16,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}"),
    re.compile(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
FORBIDDEN_FILES = {"REVIEW.md", "test_credentials", "reviewer_instructions",
                   ".env", ".app.json"}

errors: list[str] = []
notes: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def supported_text(value: str, multiline: bool) -> bool:
    for ch in value:
        if ch == "\n" and multiline:
            continue
        cat = unicodedata.category(ch)
        if cat in ("Cc", "Zl", "Zp") or (cat == "Cf" and ch not in "‍"):
            return False
    return True


def check_text(label: str, value, maximum: int, multiline: bool = False,
               required: bool = True) -> None:
    if value is None:
        if required:
            err(f"{label}: required")
        return
    if not isinstance(value, str):
        err(f"{label}: must be a string")
        return
    if not value.strip():
        err(f"{label}: must not be empty or whitespace")
    if len(value) > maximum:
        err(f"{label}: {len(value)} characters, limit {maximum}")
    if not supported_text(value, multiline):
        err(f"{label}: contains unsupported characters"
            + ("" if multiline else " or a line break"))


def check_https(label: str, value, maximum: int, required: bool = True) -> None:
    check_text(label, value, maximum, required=required)
    if not isinstance(value, str):
        return
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        err(f"{label}: must be an HTTPS URL with a host")
    if parsed.username or parsed.password:
        err(f"{label}: must not embed credentials")


def luminance(hex_color: str) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def png_size(data: bytes):
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def check_image(root: Path, label: str, rel) -> None:
    if not isinstance(rel, str) or not rel.startswith("./"):
        err(f"{label}: path must start with ./ (got {rel!r})")
        return
    p = PurePosixPath(rel[2:])
    if p.is_absolute() or ".." in p.parts:
        err(f"{label}: path must stay inside the plugin")
        return
    f = root / p
    if not f.is_file():
        err(f"{label}: file {rel} is missing")
        return
    if f.suffix.lower() not in IMAGE_EXT:
        err(f"{label}: unsupported image type {f.suffix}")
        return
    data = f.read_bytes()
    if len(data) > MAX_IMAGE_BYTES:
        err(f"{label}: {len(data)} bytes, limit 5 MiB")
    if f.suffix.lower() == ".png":
        size = png_size(data)
        if size is None:
            err(f"{label}: not a valid PNG")
            return
        w, h = size
        if w != h:
            err(f"{label}: {w}x{h} is not square")
        if w < 48:
            err(f"{label}: {w}x{h} is smaller than 48x48")
        if w > 4096:
            err(f"{label}: {w}x{h} is larger than 4096x4096")
        notes.append(f"{label}: {rel} PNG {w}x{h}, {len(data)} bytes")
    else:
        notes.append(f"{label}: {rel} (format not measured by this checker)")


def walk_keys(obj, path: str = ""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield f"{path}.{k}" if path else k, k
            yield from walk_keys(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_keys(v, f"{path}[{i}]")


def check_plugin(root: Path) -> dict:
    f = root / "plugin.json"
    if not f.is_file():
        err("plugin.json missing at the plugin root")
        return {}
    try:
        m = json.loads(f.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        err(f"plugin.json: {e}")
        return {}

    if m.get("$schema") != PLUGIN_SCHEMA:
        err(f"plugin.json $schema must be {PLUGIN_SCHEMA}")
    for k in m:
        if k not in ROOT_KEYS:
            err(f"plugin.json: unknown root key {k!r} (schema has additionalProperties false)")
    name = m.get("name")
    check_text("name", name, 64)
    if isinstance(name, str) and not (NAME_SCHEMA.match(name) and NAME_PORTAL.match(name)):
        err("name: use lowercase letters, digits and single hyphens")
    check_text("version", m.get("version"), 64)
    if isinstance(m.get("version"), str) and not SEMVER.match(m["version"]):
        err("version: must be semantic versioning")
    check_text("description", m.get("description"), 1024, multiline=True)
    author = m.get("author") or {}
    check_text("author.name", author.get("name"), 120)
    check_text("author.email", author.get("email"), 320, required=False)
    if "url" in author:
        check_https("author.url", author["url"], 2048)
    if "homepage" in m:
        check_https("homepage", m["homepage"], 2048)

    for path, key in walk_keys(m):
        if key in FORBIDDEN_KEYS:
            err(f"plugin.json: forbidden key {path}")

    oa = (m.get("extensions") or {}).get("com.openai")
    if not isinstance(oa, dict):
        err("extensions.com.openai: missing")
        return m
    ui = oa.get("interface") or {}
    check_text("interface.displayName", ui.get("displayName"), 30)
    check_text("interface.shortDescription", ui.get("shortDescription"), 30)
    check_text("interface.longDescription", ui.get("longDescription"), 4000, multiline=True)
    check_text("interface.developerName", ui.get("developerName"), 80)
    if ui.get("category") not in CATEGORIES:
        err(f"interface.category: {ui.get('category')!r} is not a supported category")
    caps = ui.get("capabilities", [])
    if not isinstance(caps, list) or len(caps) > 20:
        err("interface.capabilities: list of at most 20")
    else:
        for i, c in enumerate(caps):
            check_text(f"interface.capabilities[{i}]", c, 120)
    for key in ("websiteURL", "supportURL", "privacyPolicyURL", "termsOfServiceURL"):
        check_https(f"interface.{key}", ui.get(key), 1024)
    prompts = ui.get("defaultPrompt", [])
    prompts = [prompts] if isinstance(prompts, str) else prompts
    if len(prompts) > 3:
        err("interface.defaultPrompt: at most 3")
    seen = set()
    for i, p in enumerate(prompts):
        check_text(f"interface.defaultPrompt[{i}]", p, 128)
        if isinstance(p, str):
            if "@" in p:
                err(f"interface.defaultPrompt[{i}]: no @mentions")
            norm = " ".join(unicodedata.normalize("NFKC", p).split()).casefold()
            if norm in seen:
                err(f"interface.defaultPrompt[{i}]: duplicate")
            seen.add(norm)
    for key, against in (("brandColor", "#FFFFFF"), ("brandColorDark", "#212121")):
        if key in ui:
            v = ui[key]
            if not isinstance(v, str) or not HEX.match(v):
                err(f"interface.{key}: must be #RRGGBB")
            else:
                ratio = contrast(v, against)
                notes.append(f"interface.{key} {v}: contrast {ratio:.2f}:1 against {against}")
                if ratio < 2:
                    err(f"interface.{key}: contrast {ratio:.2f}:1 against {against}, need 2:1")
    if "logo" not in ui:
        err("interface.logo: required for submission")
    for key in ("logo", "logoDark", "composerIcon", "composerIconDark"):
        if key in ui:
            check_image(root, f"interface.{key}", ui[key])
    if ui.get("screenshots"):
        err("interface.screenshots: allowed only for an MCP server with custom UI; Praxis has none")

    if "onboardingSkill" in oa:
        rel = oa["onboardingSkill"]
        if not (isinstance(rel, str) and rel.startswith("./") and (root / rel[2:]).is_file()):
            err("onboardingSkill: must be a ./ path to an included SKILL.md")

    review = oa.get("review") or {}
    cases = review.get("test_cases") or {}
    pos, neg = cases.get("positive", []), cases.get("negative", [])
    if len(pos) != 5:
        err(f"review.test_cases.positive: {len(pos)} cases, need exactly 5")
    if len(neg) != 3:
        err(f"review.test_cases.negative: {len(neg)} cases, need exactly 3")
    for i, c in enumerate(pos):
        check_text(f"positive[{i}].description", c.get("description"), 4000, multiline=True)
        check_text(f"positive[{i}].prompt", c.get("prompt"), 4000, multiline=True)
        check_text(f"positive[{i}].tools_triggered", c.get("tools_triggered"), 4000)
        check_text(f"positive[{i}].expected_behavior", c.get("expected_behavior"), 4000,
                   multiline=True)
    for i, c in enumerate(neg):
        check_text(f"negative[{i}].description", c.get("description"), 4000, multiline=True)
        check_text(f"negative[{i}].prompt", c.get("prompt"), 4000, multiline=True)
    if not review.get("demo_recording_url"):
        notes.append("WARNING review.demo_recording_url: not set. Required before "
                     "submission; add it to plugin.json or in the portal.")
    else:
        check_https("review.demo_recording_url", review["demo_recording_url"], 2048)

    pub = oa.get("publication") or {}
    countries = pub.get("countries")
    if countries is not None:
        if not isinstance(countries, list) or not all(
                isinstance(c, str) and COUNTRY.match(c) for c in countries):
            err("publication.countries: list of uppercase two-letter codes")
    if not pub.get("release_notes"):
        notes.append("WARNING publication.release_notes: not set (required at submission)")
    return m


def check_mcp(root: Path) -> None:
    f = root / "mcp.json"
    if not f.is_file():
        err("mcp.json missing at the plugin root")
        return
    try:
        m = json.loads(f.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        err(f"mcp.json: {e}")
        return
    if m.get("$schema") != MCP_SCHEMA:
        err(f"mcp.json $schema must be {MCP_SCHEMA}")
    servers = m.get("mcpServers")
    if not isinstance(servers, dict) or len(servers) != 1:
        err("mcp.json: exactly one MCP server (plugin-level test cases need one server)")
        return
    for path, key in walk_keys(m):
        if key in {"clientSecret", "client_secret", "clientId"}:
            err(f"mcp.json: {path} must not be in a DCR package")
    for name, s in servers.items():
        if not name.strip():
            err("mcp.json: empty server name")
        if s.get("type") != "streamable-http":
            err(f"mcp.json {name}: type must be streamable-http")
        check_https(f"mcp.json {name}.url", s.get("url"), 2048)
        if s.get("headers"):
            err(f"mcp.json {name}: public submission rejects non-empty headers")
        auth = ((s.get("extensions") or {}).get("com.openai") or {}).get("auth") or {}
        if auth.get("type") != "oauth":
            err(f"mcp.json {name}: auth.type must be oauth (the server answers 401 without a token)")
        if (auth.get("client") or {}).get("mode") != "dcr":
            err(f"mcp.json {name}: auth.client.mode must be dcr")


def frontmatter(text: str):
    if not text.startswith("---\n"):
        return None, ""
    end = text.find("\n---", 4)
    if end < 0:
        return None, ""
    fields = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip().strip('"').strip("'")
    return fields, text[end + 4:].lstrip("-\n")


def check_skills(root: Path, plugin_name: str) -> None:
    sdir = root / "skills"
    skills = [d for d in sdir.iterdir() if d.is_dir()] if sdir.is_dir() else []
    if not skills:
        err("skills/: a public submission ZIP needs at least one valid skill "
            "(plugin_runtime_surface_missing)")
    names = set()
    for d in skills:
        if d.name.startswith("."):
            err(f"skills/{d.name}: hidden skill directory")
        sk = d / "SKILL.md"
        if not sk.is_file():
            err(f"skills/{d.name}: SKILL.md missing")
            continue
        fm, body = frontmatter(sk.read_text(encoding="utf-8"))
        if fm is None:
            err(f"skills/{d.name}/SKILL.md: YAML front matter missing or unclosed")
            continue
        check_text(f"skills/{d.name} name", fm.get("name"), 64)
        check_text(f"skills/{d.name} description", fm.get("description"), 1024)
        if not body.strip():
            err(f"skills/{d.name}: instructions are empty")
        ident = f"{plugin_name}:{fm.get('name', '')}"
        if len(ident) > 64:
            err(f"skills/{d.name}: identity {ident!r} is over 64 characters")
        if fm.get("name") in names:
            err(f"skills/{d.name}: duplicate skill name")
        names.add(fm.get("name"))


def check_files(root: Path, manifest: dict) -> None:
    for f in root.rglob("*"):
        rel = f.relative_to(root).as_posix()
        if f.name in FORBIDDEN_FILES:
            err(f"{rel}: must not be in the package")
        if f.is_symlink():
            err(f"{rel}: symbolic links are not allowed")
        if f.is_file() and f.suffix.lower() in {".json", ".md", ".txt", ".yaml", ".yml"}:
            text = f.read_text(encoding="utf-8", errors="replace")
            for pat in SECRET_PATTERNS:
                if pat.search(text):
                    err(f"{rel}: looks like it contains a secret ({pat.pattern})")


def check_zip(path: Path) -> Path:
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if not names:
            err("ZIP is empty")
        if len(names) > 5000:
            err("ZIP has more than 5000 entries")
        seen = set()
        for n in names:
            if "\\" in n or n.startswith("/") or n != n.strip():
                err(f"ZIP entry {n!r}: bad path")
            parts = [p for p in n.rstrip("/").split("/")]
            if any(p in ("", "..") for p in parts):
                err(f"ZIP entry {n!r}: empty or .. segment")
            if len(parts) > 20:
                err(f"ZIP entry {n!r}: deeper than 20 segments")
            key = unicodedata.normalize("NFC", n).casefold()
            if key in seen:
                err(f"ZIP entry {n!r}: duplicate after normalization")
            seen.add(key)
        if "plugin.json" not in names:
            err("ZIP: plugin.json must be at the archive root")
        bad = z.testzip()
        if bad:
            err(f"ZIP entry {bad!r}: unreadable")
        tmp = Path(tempfile.mkdtemp(prefix="praxis-oa-check-"))
        z.extractall(tmp)
        notes.append(f"ZIP entries: {', '.join(n for n in names if not n.endswith('/'))}")
        return tmp


def check_review(review_md: Path, manifest: dict) -> None:
    text = review_md.read_text(encoding="utf-8")
    cases = manifest["extensions"]["com.openai"]["review"]["test_cases"]
    for kind in ("positive", "negative"):
        for i, c in enumerate(cases[kind]):
            if c["prompt"] not in text:
                err(f"REVIEW.md: {kind}[{i}] prompt differs from plugin.json")
    for pat in SECRET_PATTERNS:
        if pat.search(text):
            err(f"REVIEW.md: looks like it contains a secret ({pat.pattern})")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    target = Path(argv[0])
    review = Path(argv[argv.index("--review") + 1]) if "--review" in argv else None
    root = check_zip(target) if target.suffix == ".zip" else target
    manifest = check_plugin(root)
    check_mcp(root)
    check_skills(root, manifest.get("name", ""))
    check_files(root, manifest)
    if review and manifest:
        check_review(review, manifest)
    for n in notes:
        print(f"  note: {n}")
    for e in errors:
        print(f"ERROR: {e}")
    print(f"{target}: {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
