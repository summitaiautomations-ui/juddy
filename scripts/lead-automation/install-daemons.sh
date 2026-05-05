#!/usr/bin/env bash
# Installs the lead-automation LaunchAgents:
#   com.juddy.lead-monitor       (continuous, polls Gmail)
#   com.juddy.nurture-engine     (continuous, processes nurture steps)
#   com.juddy.dashboard          (continuous, serves dashboard on $DASHBOARD_PORT)
#   com.juddy.birthday-campaign  (daily at 9:00 AM local)
#
# Re-runnable. Run from anywhere -- it resolves its own path.

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: this installer only runs on macOS" >&2
  exit 1
fi
if [[ $EUID -eq 0 ]]; then
  echo "error: do not run this as root. LaunchAgents must be per-user." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LAUNCH_AGENTS="${HOME}/Library/LaunchAgents"
LOG_DIR="${HOME}/Library/Logs/juddy"

ENV_FILE="${REPO_ROOT}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "error: ${ENV_FILE} not found." >&2
  echo "       create it from ${REPO_ROOT}/.env.example before installing." >&2
  exit 1
fi

echo "==> repo root      : ${REPO_ROOT}"
echo "==> launch agents  : ${LAUNCH_AGENTS}"
echo "==> log directory  : ${LOG_DIR}"
echo

mkdir -p "${LAUNCH_AGENTS}" "${LOG_DIR}"

# Verify Python deps so the daemons don't crash-loop on launch.
echo "==> verifying Python dependencies"
if ! /usr/bin/python3 -c "import requests, dotenv" >/dev/null 2>&1; then
  echo "   installing requests + python-dotenv to user site-packages..."
  /usr/bin/python3 -m pip install --user --quiet requests python-dotenv
fi
echo "   ok"
echo

render_plist() {
  local template="$1" dest="$2"
  sed \
    -e "s|__REPO__|${REPO_ROOT}|g" \
    -e "s|__HOME__|${HOME}|g" \
    "${template}" > "${dest}"
}

install_agent() {
  local label="$1" template="$2"
  local dest="${LAUNCH_AGENTS}/${label}.plist"
  echo "==> installing ${label}"
  launchctl bootout "gui/$(id -u)/${label}" 2>/dev/null || true
  render_plist "${template}" "${dest}"
  launchctl bootstrap "gui/$(id -u)" "${dest}"
  launchctl enable "gui/$(id -u)/${label}"
  launchctl kickstart -k "gui/$(id -u)/${label}" || true
}

install_agent "com.juddy.lead-monitor"      "${SCRIPT_DIR}/com.juddy.lead-monitor.plist.template"
install_agent "com.juddy.nurture-engine"    "${SCRIPT_DIR}/com.juddy.nurture-engine.plist.template"
install_agent "com.juddy.dashboard"         "${SCRIPT_DIR}/com.juddy.dashboard.plist.template"
install_agent "com.juddy.birthday-campaign" "${SCRIPT_DIR}/com.juddy.birthday-campaign.plist.template"

cat <<EOF

==========================================================================
  install complete.

  inspect the agents:
    launchctl print gui/$(id -u)/com.juddy.lead-monitor
    launchctl print gui/$(id -u)/com.juddy.nurture-engine
    launchctl print gui/$(id -u)/com.juddy.dashboard
    launchctl print gui/$(id -u)/com.juddy.birthday-campaign

  tail the logs (in another terminal):
    tail -f "${LOG_DIR}"/lead-monitor.{out,err}.log
    tail -f "${LOG_DIR}"/nurture-engine.{out,err}.log
    tail -f "${LOG_DIR}"/dashboard.{out,err}.log

  dashboard:
    http://localhost:${DASHBOARD_PORT:-18790}/
==========================================================================
EOF
