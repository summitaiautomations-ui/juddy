#!/usr/bin/env bash
# Install the recruiting LaunchAgents:
#   - com.juddy.recruiting-digest : daily digest, every morning
#   - com.juddy.recruiting-weekly : weekly funnel review, Monday morning
#
#   bash recruiting/install-schedule.sh
#   DIGEST_HOUR=6 DIGEST_MINUTE=30 bash recruiting/install-schedule.sh
#   WEEKLY_WEEKDAY=1 WEEKLY_HOUR=8 bash recruiting/install-schedule.sh
#
# Re-runnable. Run from anywhere -- it resolves its own path. Uninstall:
#   launchctl bootout "gui/$(id -u)/com.juddy.recruiting-digest"
#   launchctl bootout "gui/$(id -u)/com.juddy.recruiting-weekly"
#   rm ~/Library/LaunchAgents/com.juddy.recruiting-{digest,weekly}.plist

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: this installer only runs on macOS" >&2
  exit 1
fi
if [[ $EUID -eq 0 ]]; then
  echo "error: do not run this as root." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
USER_NAME="$(id -un)"
LAUNCH_AGENTS="${HOME}/Library/LaunchAgents"
LOG_DIR="${HOME}/Library/Logs/juddy"

# Daily schedule
HOUR="${DIGEST_HOUR:-7}"
MINUTE="${DIGEST_MINUTE:-0}"
# Weekly schedule (Weekday: 0/7=Sun, 1=Mon)
WEEKDAY="${WEEKLY_WEEKDAY:-1}"
WHOUR="${WEEKLY_HOUR:-7}"
WMINUTE="${WEEKLY_MINUTE:-30}"

VENV_PY="${REPO_ROOT}/recruiting/.venv/bin/python"
if [[ ! -x "${VENV_PY}" ]]; then
  echo "error: ${VENV_PY} not found." >&2
  echo "       create it first:" >&2
  echo "         python3 -m venv recruiting/.venv" >&2
  echo "         recruiting/.venv/bin/pip install -r recruiting/requirements.txt" >&2
  exit 1
fi

echo "==> repo root   : ${REPO_ROOT}"
echo "==> daily       : ${HOUR}:$(printf '%02d' "${MINUTE}") every day"
echo "==> weekly      : weekday ${WEEKDAY} at ${WHOUR}:$(printf '%02d' "${WMINUTE}")"
echo "==> python      : ${VENV_PY}"
echo "==> logs        : ${LOG_DIR}/recruiting-{digest,weekly}.log"
echo

mkdir -p "${LAUNCH_AGENTS}" "${LOG_DIR}"

install_agent() {
  local label="$1"; shift
  local dest="${LAUNCH_AGENTS}/${label}.plist"
  sed "$@" "${SCRIPT_DIR}/${label}.plist.template" > "${dest}"
  # Bootout first so edits to the plist always take effect.
  launchctl bootout "gui/$(id -u)/${label}" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "${dest}"
  launchctl enable "gui/$(id -u)/${label}"
  echo "==> installed ${label}"
}

install_agent "com.juddy.recruiting-digest" \
  -e "s|__USER__|${USER_NAME}|g" \
  -e "s|__REPO__|${REPO_ROOT}|g" \
  -e "s|__HOUR__|${HOUR}|g" \
  -e "s|__MINUTE__|${MINUTE}|g"

install_agent "com.juddy.recruiting-weekly" \
  -e "s|__USER__|${USER_NAME}|g" \
  -e "s|__REPO__|${REPO_ROOT}|g" \
  -e "s|__WEEKDAY__|${WEEKDAY}|g" \
  -e "s|__HOUR__|${WHOUR}|g" \
  -e "s|__MINUTE__|${WMINUTE}|g"

echo
echo "send each one right now to test:"
echo "    launchctl kickstart -k \"gui/$(id -u)/com.juddy.recruiting-digest\""
echo "    launchctl kickstart -k \"gui/$(id -u)/com.juddy.recruiting-weekly\""
echo "tail logs:"
echo "    tail -f \"${LOG_DIR}\"/recruiting-{digest,weekly}.log"
