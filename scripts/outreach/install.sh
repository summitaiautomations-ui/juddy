#!/usr/bin/env bash
# Install (or re-install) the four outreach launchd jobs on the Mac mini.
# Safe to re-run any time — unloads existing jobs first, then re-renders
# the plists from the templates with absolute paths.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/Library/Logs/juddy"

mkdir -p "$LAUNCH_AGENTS" "$LOG_DIR"

JOBS=(
  outreach-birthday
  outreach-scan
  outreach-day1-info
  outreach-digest
)

for job in "${JOBS[@]}"; do
  src="$REPO_ROOT/scripts/outreach/com.juddy.${job}.plist.template"
  dst="$LAUNCH_AGENTS/com.juddy.${job}.plist"

  if [[ ! -f "$src" ]]; then
    echo "✗ missing template: $src" >&2
    exit 1
  fi

  launchctl unload "$dst" 2>/dev/null || true
  sed "s|__REPO__|$REPO_ROOT|g; s|__USER__|$USER|g" "$src" > "$dst"
  launchctl load "$dst"
  echo "✓ installed com.juddy.${job}"
done

echo ""
echo "Current juddy launchd jobs:"
launchctl list | grep com.juddy || echo "(none — something went wrong)"
