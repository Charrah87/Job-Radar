#!/bin/bash
# ── Job Radar — One-time Setup ────────────────────────────────────────────────
# Run this once after cloning to:
#   1. Create a Python virtual environment
#   2. Install all dependencies
#   3. Make launch.command executable
#   4. (macOS) Build a clickable .app launcher on your Desktop
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

PYTHON=$(command -v python3)
if [ -z "$PYTHON" ]; then
    echo ""
    echo "ERROR: Python 3 not found."
    echo "Install Python 3.10+ from https://www.python.org/downloads/ and re-run this script."
    echo ""
    exit 1
fi

echo ""
echo "─────────────────────────────────────────────"
echo "  Job Radar — Setup"
echo "─────────────────────────────────────────────"
echo ""

# ── Step 1: Virtual environment ──────────────────────────────────────────────
if [ -d "$DIR/venv" ]; then
    echo "✓ Virtual environment already exists — skipping creation."
else
    echo "Creating virtual environment..."
    "$PYTHON" -m venv "$DIR/venv"
    echo "✓ Virtual environment created."
fi

VENV_PYTHON="$DIR/venv/bin/python"
VENV_PIP="$DIR/venv/bin/pip"

# ── Step 2: Install dependencies ─────────────────────────────────────────────
echo "Installing dependencies..."
"$VENV_PIP" install --upgrade pip --quiet
"$VENV_PIP" install -r "$DIR/requirements.txt" --quiet
echo "✓ Dependencies installed."

# ── Step 3: Make launch.command executable ───────────────────────────────────
chmod +x "$DIR/launch.command"
echo "✓ launch.command is executable."

# ── Step 4: macOS .app launcher (optional) ───────────────────────────────────
if [[ "$OSTYPE" == "darwin"* ]]; then
    APP_NAME="Job Radar"
    DESKTOP="$HOME/Desktop"
    APP_PATH="$DESKTOP/${APP_NAME}.app"

    echo "Building macOS launcher app..."

    # AppleScript that opens Terminal and runs launch.command
    APPLESCRIPT=$(cat <<ASEOF
tell application "Terminal"
    activate
    do script "exec '$DIR/launch.command'"
end tell
ASEOF
)

    osacompile -e "$APPLESCRIPT" -o "$APP_PATH" 2>/dev/null

    # Apply custom icon if icon.png exists
    ICON_SRC="$DIR/icon.png"
    if [ -f "$ICON_SRC" ]; then
        # Convert PNG to ICNS using sips + iconutil
        ICONSET_DIR="$DIR/.iconset_tmp.iconset"
        ICNS_PATH="$DIR/icon.icns"
        mkdir -p "$ICONSET_DIR"

        for SIZE in 16 32 64 128 256 512; do
            sips -z "$SIZE" "$SIZE" "$ICON_SRC" \
                --out "$ICONSET_DIR/icon_${SIZE}x${SIZE}.png" > /dev/null 2>&1
            DOUBLE=$((SIZE * 2))
            sips -z "$DOUBLE" "$DOUBLE" "$ICON_SRC" \
                --out "$ICONSET_DIR/icon_${SIZE}x${SIZE}@2x.png" > /dev/null 2>&1
        done

        iconutil -c icns "$ICONSET_DIR" -o "$ICNS_PATH" 2>/dev/null
        rm -rf "$ICONSET_DIR"

        if [ -f "$ICNS_PATH" ]; then
            # Replace the default applet icon inside the .app bundle
            ICON_DEST="$APP_PATH/Contents/Resources/applet.icns"
            cp "$ICNS_PATH" "$ICON_DEST"
            rm "$ICNS_PATH"
            # Touch the .app to refresh Finder's icon cache
            touch "$APP_PATH"
            echo "✓ Custom icon applied."
        fi
    fi

    if [ -d "$APP_PATH" ]; then
        echo "✓ Launcher created: $APP_PATH"
        echo "  Double-click it from your Desktop to start Job Radar."
    else
        echo "  (Could not build .app — you can still use launch.command directly.)"
    fi
fi

echo ""
echo "─────────────────────────────────────────────"
echo "  Setup complete!"
echo ""
echo "  Next steps:"
echo "  1. Edit config.json — add your Google Alert RSS URLs and resume path."
echo "  2. Double-click 'Job Radar.app' on your Desktop (macOS)"
echo "     or run:  ./launch.command"
echo "─────────────────────────────────────────────"
echo ""
