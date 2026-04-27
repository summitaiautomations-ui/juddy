#!/usr/bin/env bash
# Configure a Mac mini to stay awake and run 24/7.
# Idempotent: safe to re-run.

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: this script only runs on macOS" >&2
  exit 1
fi

if [[ $EUID -ne 0 ]]; then
  echo "re-running with sudo (pmset needs root)..."
  exec sudo --preserve-env=HOME,USER "$0" "$@"
fi

echo "==> applying pmset power settings"
# sleep 0          : never sleep the system
# disksleep 0      : never spin down disks
# displaysleep 10  : turn display off after 10 min (system stays awake)
# womp 1           : wake on network access (Wake-on-LAN)
# autorestart 1    : restart automatically after a power failure
# powernap 1       : allow background tasks during display sleep
# standby 0        : disable deep-sleep "standby" mode
# hibernatemode 0  : RAM-only sleep (no disk image), faster wake
pmset -a \
  sleep 0 \
  disksleep 0 \
  displaysleep 10 \
  womp 1 \
  autorestart 1 \
  powernap 1 \
  standby 0 \
  hibernatemode 0

echo "==> scheduling nightly restart at 04:00 to clear leaks"
pmset repeat restart MTWRFSU 04:00

echo "==> current power settings:"
pmset -g custom

echo
echo "==> scheduled power events:"
pmset -g sched

cat <<'EOF'

done. additional manual steps (System Settings UI):
  1. Lock Screen  -> "Require password after sleep" -> set to a long delay or Never
  2. Users & Groups -> enable Automatic Login (so unattended reboots return to desktop)
  3. Displays -> Advanced -> "Prevent automatic sleeping on power adapter when display is off" = ON
  4. plug into a UPS so brief outages don't reboot the box
EOF
