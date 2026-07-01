#!/usr/bin/env bash
# Installs the LaunchAgent that watches the Photo Booth library and runs
# import + catalog automatically whenever a new photo is saved.
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
LABEL="com.juddy.disc-pics"

CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
if [[ -z "${CLAUDE_BIN}" ]]; then
  echo "error: cannot find 'claude' on PATH. set CLAUDE_BIN=/path/to/claude and re-run." >&2
  exit 1
fi

echo "==> repo root     : ${REPO_ROOT}"
echo "==> claude binary : ${CLAUDE_BIN}"
echo "==> watching      : ${HOME}/Pictures/Photo Booth Library/Pictures"

mkdir -p "${LAUNCH_AGENTS}"
chmod +x "${SCRIPT_DIR}/import.sh" "${SCRIPT_DIR}/catalog.sh" "${SCRIPT_DIR}/auto-catalog.sh" "${SCRIPT_DIR}/sync.sh"

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
  disc-pics watcher installed.

  every photo saved in Photo Booth now auto-imports and auto-catalogs.

  tail the log:
    tail -f "${HOME}/Library/Logs/juddy/disc-pics.log"

  uninstall:
    launchctl bootout "gui/$(id -u)/${LABEL}"
    rm "${dest}"
==========================================================================
EOF
