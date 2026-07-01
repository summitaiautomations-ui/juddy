#!/usr/bin/env bash
# Commits and pushes disc-pics-data/ (photos + inventory + sheet.csv) so the
# shared Google Sheet -- which reads sheet.csv and the photos over raw
# GitHub URLs -- picks up new discs automatically.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DATA_DIR="${REPO_ROOT}/disc-pics-data"

if [[ ! -d "${DATA_DIR}" ]]; then
  echo "==> nothing to sync (no ${DATA_DIR})"
  exit 0
fi

cd "${REPO_ROOT}"
git add disc-pics-data

if git diff --cached --quiet; then
  echo "==> nothing new to sync"
  exit 0
fi

# Use a fallback identity only if none is configured on this machine.
GIT_ID=()
if ! git config user.email >/dev/null 2>&1; then
  GIT_ID=(-c user.name="juddy disc-pics" -c user.email="juddy@localhost")
fi

discs=$(( $(wc -l < "${DATA_DIR}/inventory.csv") - 1 ))
git "${GIT_ID[@]}" commit -m "disc-pics: sync inventory (${discs} discs)"

branch="$(git rev-parse --abbrev-ref HEAD)"
for delay in 0 2 4 8 16; do
  sleep "${delay}"
  if git push -u origin "${branch}"; then
    echo "==> synced ${discs} disc(s) to origin/${branch}"
    exit 0
  fi
  echo "==> push failed, retrying..." >&2
done
echo "error: could not push after retries; will go out with the next sync" >&2
exit 1
