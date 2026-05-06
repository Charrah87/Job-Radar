#!/bin/bash
# ── Job Radar — Updater (macOS / Linux) ──────────────────────────────────────
# Pulls the latest code while preserving your personal data files.
#
# Safe to run at any time. Your config.json and jobs.json are never overwritten.
#
# Usage:
#   chmod +x update.sh
#   ./update.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo ""
echo "─────────────────────────────────────────────"
echo "  Job Radar — Update"
echo "─────────────────────────────────────────────"
echo ""

CURRENT_VERSION="unknown"
[ -f "$DIR/VERSION" ] && CURRENT_VERSION=$(cat "$DIR/VERSION" | tr -d '[:space:]')
echo "Current version: $CURRENT_VERSION"

# ── Detect install method ─────────────────────────────────────────────────────
if ! git -C "$DIR" rev-parse --git-dir > /dev/null 2>&1; then
    echo ""
    echo "This installation was not set up with Git (you downloaded a ZIP)."
    echo ""
    echo "To update:"
    echo "  1. Download the latest ZIP from GitHub."
    echo "  2. Extract it to a new folder."
    echo "  3. Copy your personal files into the new folder:"
    echo "       config.json   ← your Google Alert URLs, resume path, and settings"
    echo "       jobs.json     ← your saved jobs and notes (if it exists)"
    echo "  4. Run install.sh in the new folder."
    echo ""
    echo "Your data files will not be affected."
    echo ""
    exit 0
fi

# ── Back up personal data files ───────────────────────────────────────────────
echo "Backing up your personal data files..."
BACKUP_DIR="$DIR/.update_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

cp "$DIR/config.json" "$BACKUP_DIR/config.json" 2>/dev/null && echo "  ✓ config.json backed up"
[ -f "$DIR/jobs.json" ] && cp "$DIR/jobs.json" "$BACKUP_DIR/jobs.json" && echo "  ✓ jobs.json backed up"

# ── Pull latest code ──────────────────────────────────────────────────────────
echo ""
echo "Pulling latest changes..."

# Stash any local changes (including config.json) so pull doesn't conflict
git stash --quiet 2>/dev/null || true

git pull --ff-only origin main 2>&1 || {
    echo ""
    echo "ERROR: Could not pull updates. Check your internet connection"
    echo "or visit the GitHub page to download the latest release manually."
    # Restore stash so nothing is lost
    git stash pop --quiet 2>/dev/null || true
    exit 1
}

# ── Restore personal data files ───────────────────────────────────────────────
# Always restore user's config and jobs — never let a pull overwrite them.
cp "$BACKUP_DIR/config.json" "$DIR/config.json"
[ -f "$BACKUP_DIR/jobs.json" ] && cp "$BACKUP_DIR/jobs.json" "$DIR/jobs.json"
echo "✓ Your personal data files restored."

# Clean up backup
rm -rf "$BACKUP_DIR"

# ── Update dependencies ───────────────────────────────────────────────────────
echo ""
echo "Updating dependencies..."
if [ -f "$DIR/venv/bin/pip" ]; then
    "$DIR/venv/bin/pip" install -r "$DIR/requirements.txt" --quiet
    echo "✓ Dependencies updated."
else
    echo "  (No venv found — run install.sh if you see import errors.)"
fi

# ── Rebuild macOS .app if on macOS ───────────────────────────────────────────
if [[ "$OSTYPE" == "darwin"* ]]; then
    APP_PATH="$HOME/Desktop/Job Radar.app"
    if [ -d "$APP_PATH" ]; then
        echo ""
        echo "Rebuilding macOS launcher..."
        APPLESCRIPT="tell application \"Terminal\"
    activate
    do script \"exec '$DIR/launch.command'\"
end tell"
        osacompile -e "$APPLESCRIPT" -o "$APP_PATH" 2>/dev/null
        echo "✓ Launcher updated."
    fi
fi

NEW_VERSION="unknown"
[ -f "$DIR/VERSION" ] && NEW_VERSION=$(cat "$DIR/VERSION" | tr -d '[:space:]')

echo ""
echo "─────────────────────────────────────────────"
if [ "$CURRENT_VERSION" != "$NEW_VERSION" ]; then
    echo "  Updated: $CURRENT_VERSION → $NEW_VERSION"
else
    echo "  Already up to date ($CURRENT_VERSION)."
fi
echo ""
echo "  Launch Job Radar as normal — no re-install needed."
echo "─────────────────────────────────────────────"
echo ""
