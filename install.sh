#!/bin/bash
# obsidian-llm-kb installer
# Usage: ./install.sh [vault_path]
# Default vault: ~/obsidian-vault

set -euo pipefail

VAULT="${1:-$HOME/obsidian-vault}"
USER_HOME="$HOME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Obsidian LLM-KB Installer ==="
echo "Vault: $VAULT"
echo "User home: $USER_HOME"
echo ""

# === 0. Sanity checks ===
if [ ! -d "$VAULT" ]; then
    echo "Vault directory $VAULT does not exist. Create it first or pass a different path."
    exit 1
fi

if ! command -v claude >/dev/null 2>&1; then
    echo "WARNING: 'claude' CLI not found in PATH. compile/lint will fail."
    echo "Install: https://docs.claude.com/claude-code"
fi

if ! command -v /opt/homebrew/bin/python3 >/dev/null 2>&1; then
    echo "WARNING: Homebrew python3 not found at /opt/homebrew/bin/python3."
    echo "The youtube watcher launchd will fail (system python3 is sandboxed)."
    echo "Install: brew install python@3.11"
fi

# === 1. Create vault subdirectory structure ===
echo "[1/5] Creating vault subdirectories..."
mkdir -p "$VAULT/.scripts/logs"
mkdir -p "$VAULT/raw"/{web,papers,data,videos,wiki,code,social,conversations}
mkdir -p "$VAULT/wiki/concepts"
mkdir -p "$VAULT/output"
echo "    ✓ raw/{web,papers,data,videos,wiki,code,social,conversations}"
echo "    ✓ wiki/concepts/, output/, .scripts/logs/"

# === 2. Copy scripts ===
echo "[2/5] Installing scripts to $VAULT/.scripts/..."
cp "$SCRIPT_DIR/scripts/"*.sh "$VAULT/.scripts/"
cp "$SCRIPT_DIR/scripts/"*.py "$VAULT/.scripts/"
chmod +x "$VAULT/.scripts/"*.sh "$VAULT/.scripts/"*.py
echo "    ✓ compile.sh, lint.sh, youtube_transcript.py"

# === 3. Copy SCHEMA.md template if not present ===
echo "[3/5] Installing wiki/SCHEMA.md..."
if [ ! -f "$VAULT/wiki/SCHEMA.md" ]; then
    cp "$SCRIPT_DIR/docs/SCHEMA.md.example" "$VAULT/wiki/SCHEMA.md"
    echo "    ✓ wiki/SCHEMA.md (you can customize 'Priority topics' section)"
else
    echo "    - wiki/SCHEMA.md already exists, kept as-is"
fi

# === 4. Generate launchd plists with real paths, then load ===
echo "[4/5] Installing launchd jobs..."
LA_DIR="$USER_HOME/Library/LaunchAgents"
mkdir -p "$LA_DIR"
for src in "$SCRIPT_DIR/launchd/"*.plist.template; do
    dst="$LA_DIR/$(basename "$src" .template)"
    sed -e "s|__USER_HOME__|$USER_HOME|g" \
        -e "s|__VAULT__|$VAULT|g" \
        "$src" > "$dst"

    label=$(basename "$dst" .plist)
    # Reload (bootout might fail if not loaded yet, that's OK)
    launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$dst"
    echo "    ✓ $label loaded"
done

# === 5. Show next manual steps ===
echo ""
echo "[5/5] Manual steps remaining:"
echo ""
echo "  a. Install Obsidian Web Clipper browser extension:"
echo "     https://obsidian.md/clipper"
echo ""
echo "  b. In Web Clipper General settings, add vault: '$(basename "$VAULT")'"
echo ""
echo "  c. Import 7 templates from $SCRIPT_DIR/templates/ :"
ls "$SCRIPT_DIR/templates/" | sed 's/^/       - /'
echo "     (Settings → Templates → Import → select each JSON)"
echo ""
echo "  d. (Optional) Install yt-dlp for YouTube transcript:"
echo "       brew install yt-dlp"
echo ""
echo "=== Install complete ==="
echo ""
echo "Next compile run: Sunday 09:00 (auto)"
echo "Manual test: bash $VAULT/.scripts/compile.sh"
echo "Logs: $VAULT/.scripts/logs/"
