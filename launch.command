#!/bin/bash
# ── Job Radar Launcher ────────────────────────────────────────────────────
# Double-click this file to start Job Radar and open it in your browser.
# Close this terminal window (or press Ctrl+C) to stop the server.
# ─────────────────────────────────────────────────────────────────────────

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# ── Python resolution ─────────────────────────────────────────────────────
# Use venv if install.sh has already set one up; otherwise fall back to
# the system Python 3. The venv is created by install.sh.
if [ -f "$DIR/venv/bin/python" ]; then
    PYTHON="$DIR/venv/bin/python"
    PIP="$DIR/venv/bin/pip"
    echo "Using virtual environment at $DIR/venv"
else
    PYTHON=$(command -v python3)
    PIP=$(command -v pip3)
    if [ -z "$PYTHON" ]; then
        echo ""
        echo "ERROR: Python 3 not found."
        echo "Install Python 3.10+ from https://www.python.org/downloads/"
        echo "or run install.sh to set up a virtual environment."
        echo ""
        read -p "Press Enter to close..."
        exit 1
    fi
    echo "No venv found — using system Python ($PYTHON)"
    echo "Run install.sh once for a cleaner setup."
fi

# ── Dependency check ──────────────────────────────────────────────────────
echo "Checking dependencies..."
MISSING=0
for pkg in flask feedparser requests bs4 lxml docx; do
    if ! "$PYTHON" -c "import $pkg" 2>/dev/null; then
        MISSING=1
        break
    fi
done

if [ "$MISSING" -eq 1 ]; then
    echo "Installing dependencies..."
    "$PIP" install -r requirements.txt --quiet
    if [ $? -ne 0 ]; then
        echo ""
        echo "ERROR: Dependency install failed."
        echo "Try running install.sh or manually:"
        echo "  pip3 install flask feedparser requests beautifulsoup4 lxml python-docx"
        echo ""
        read -p "Press Enter to close..."
        exit 1
    fi
fi

# ── Read port from config ─────────────────────────────────────────────────
PORT=$("$PYTHON" -c "
import json, sys
try:
    cfg = json.load(open('config.json'))
    print(cfg.get('app', {}).get('port', 5000))
except Exception:
    print(5000)
")

# ── Start server ──────────────────────────────────────────────────────────
echo "Starting Job Radar on port $PORT..."
"$PYTHON" app.py &
SERVER_PID=$!

# ── Wait until server is ready (up to 15 seconds) ────────────────────────
MAX_WAIT=15
COUNT=0
until curl -s "http://127.0.0.1:$PORT" > /dev/null 2>&1; do
    sleep 0.5
    COUNT=$((COUNT + 1))
    if [ "$COUNT" -ge $((MAX_WAIT * 2)) ]; then
        echo ""
        echo "ERROR: Server did not start within ${MAX_WAIT}s."
        echo "Check for errors above and make sure port $PORT is not in use."
        kill "$SERVER_PID" 2>/dev/null
        read -p "Press Enter to close..."
        exit 1
    fi
done

# ── Open in browser ───────────────────────────────────────────────────────
open "http://127.0.0.1:$PORT"
echo ""
echo "✓ Job Radar running at http://127.0.0.1:$PORT"
echo "  Close this window or press Ctrl+C to stop."
echo ""

# ── Keep running until user closes window ────────────────────────────────
trap "echo ''; echo 'Stopping Job Radar...'; kill $SERVER_PID 2>/dev/null; exit 0" INT TERM

wait $SERVER_PID
