#!/usr/bin/env bash
# Build the OpenAI (ChatGPT / Codex) plugin ZIP for Praxis Agent.
#
# Output: <repo>/dist/praxis-openai-plugin-<version>.zip
# Layout: plugin.json, mcp.json, skills/, assets/ at the archive root.
# Only the files in PACKAGE_FILES go in. REVIEW.md, README.md and the
# scripts stay out: OpenAI rejects reviewer instructions and credentials
# in the package.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
DIST="$REPO/dist"

PACKAGE_FILES=(
  plugin.json
  mcp.json
  assets/logo.png
  skills/public-law-research/SKILL.md
)

VERSION="$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$HERE/plugin.json")"
ZIP="$DIST/praxis-openai-plugin-$VERSION.zip"
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/praxis-openai-stage.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT

for f in "${PACKAGE_FILES[@]}"; do
  mkdir -p "$STAGE/$(dirname "$f")"
  cp "$HERE/$f" "$STAGE/$f"
done

echo "== check staged package"
python3 -I "$HERE/check_package.py" "$STAGE" --review "$HERE/REVIEW.md"

mkdir -p "$DIST"
rm -f "$ZIP"
# -X: no extra file attributes; -D: no directory entries. Fixed mtimes keep
# the ZIP byte-stable across builds.
find "$STAGE" -exec touch -t 202610200000 {} +
(cd "$STAGE" && zip -q -X -D "$ZIP" "${PACKAGE_FILES[@]}")

echo "== check built ZIP"
python3 -I "$HERE/check_package.py" "$ZIP"

echo "== contents"
unzip -l "$ZIP"
echo "Built $ZIP"
