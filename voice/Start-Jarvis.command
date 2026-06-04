#!/usr/bin/env bash
# Double-click to start Jarvis in this Terminal window.
# Keep the window open while you want Jarvis listening. Ctrl+C to stop.

set -uo pipefail

cd "$(dirname "$0")" || exit 1

# Make sure common Python install locations are on PATH.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Load env from .env if present (PICOVOICE_ACCESS_KEY, ANTHROPIC_API_KEY, NOTION_TOKEN)
if [ -f .env ]; then
  set -a; . ./.env; set +a
fi

if ! command -v python3 >/dev/null; then
  echo "Python 3 is not installed. Install from https://www.python.org/downloads/"
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

# Create venv once.
if [ ! -d .venv ]; then
  echo "Creating Python virtual environment (one-time, ~30s)..."
  python3 -m venv .venv
fi

# Activate + install/refresh deps.
source .venv/bin/activate
echo "Installing/updating dependencies (one-time, takes a few minutes)..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo
echo "============================================================"
echo "  Jarvis is starting. Say \"Jarvis\" to wake him."
echo "  Ctrl+C to stop. Close this window when you are done."
echo "============================================================"
echo

exec python juddy.py
