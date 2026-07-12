#!/usr/bin/env bash
# Installs the LaunchAgent that watches ~/Downloads and runs the disc pipeline
# automatically every time you AirDrop photos to the Mac mini.
# Re-runnable. Run from anywhere -- it resolves its own path.

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
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
USER_NAME="$(id -un)"
LAUNCH_AGENTS="${HOME}/Library/LaunchAgents"
LABEL="com.juddy.disc-airdrop"

CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
if [[ -z "${CLAUDE_BIN}" ]]; then
  echo "error: cannot find 'claude' on PATH. set CLAUDE_BIN=/path/to/claude and re-run." >&2
  exit 1
fi

echo "==> repo root     : ${REPO_ROOT}"
echo "==> claude binary : ${CLAUDE_BIN}"
echo "==> watching      : ${HOME}/Downloads  (AirDrop's save folder)"

mkdir -p "${LAUNCH_AGENTS}"
chmod +x "${SCRIPT_DIR}/airdrop-import.sh" "${SCRIPT_DIR}/airdrop-catalog.sh" \
         "${SCRIPT_DIR}/catalog.sh" "${SCRIPT_DIR}/sync.sh" "${SCRIPT_DIR}/import.sh" 2>/dev/null || true

dest="${LAUNCH_AGENTS}/${LABEL}.plist"
launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
sed \
  -e "s|__USER__|${USER_NAME}|g" \
  -e "s|__REPO__|${REPO_ROOT}|g" \
  -e "s|__CLAUDE_BIN__|${CLAUDE_BIN}|g" \
  "${SCRIPT_DIR}/${LABEL}.plist.template" > "${dest}"
launchctl bootstrap "gui/$(id -u)" "${dest}"
launchctl enable "gui/$(id -u)/${LABEL}"

cat <<EOF

==========================================================================
  AirDrop watcher installed.

  Now just AirDrop disc photos to this Mac mini. ~30s later they're
  cleaned up, identified, filed, and pushed live to discdiver.com.

  Heads up: it sweeps NEW IMAGE files out of ~/Downloads (jpg/png/heic)
  into the disc pipeline. If you also save non-disc images to Downloads,
  point it at a dedicated folder instead:
    AIRDROP_DIR="\${HOME}/DiscDrop"  (set in the plist EnvironmentVariables)

  tail the log:
    tail -f "${HOME}/Library/Logs/juddy/disc-pics.log"

  uninstall:
    launchctl bootout "gui/$(id -u)/${LABEL}"
    rm "${dest}"
==========================================================================
EOF
