#!/usr/bin/env bash
# Removes the always-on dashboard service.

set -uo pipefail

LABEL="com.juddy.dashboard-serve"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$PLIST"

echo
echo "============================================================"
echo "  Always-on dashboard removed."
echo "  (Files in this folder were not touched.)"
echo "============================================================"
echo
read -n 1 -s -r -p "Press any key to close..."
echo
