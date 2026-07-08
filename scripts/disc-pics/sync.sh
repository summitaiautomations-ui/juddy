#!/usr/bin/env bash
# Commits new disc-pics-data files (staged photos + sidecars) and pushes them.
# The mini only ever ADDS files under incoming/, so a rebase onto the latest
# remote is always clean -- this is what makes pushes conflict-proof.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DATA_DIR="${REPO_ROOT}/disc-pics-data"

if [[ ! -d "${DATA_DIR}" ]]; then
  echo "==> nothing to sync (no ${DATA_DIR})"
  exit 0
fi

cd "${REPO_ROOT}"
branch="$(git rev-parse --abbrev-ref HEAD)"

# Fallback identity only if none is configured on this machine.
GIT_ID=()
if ! git config user.email >/dev/null 2>&1; then
  GIT_ID=(-c user.name="juddy disc-pics" -c user.email="juddy@localhost")
fi

git add disc-pics-data
if ! git diff --cached --quiet; then
  git "${GIT_ID[@]}" commit -m "disc-pics: stage $(ls "${DATA_DIR}/incoming"/*.sidecar 2>/dev/null | wc -l | tr -d ' ') incoming disc(s)"
fi

# Nothing to push?
if [[ "$(git rev-list --count "origin/${branch}..HEAD" 2>/dev/null || echo 0)" == "0" ]]; then
  echo "==> nothing new to sync"
  exit 0
fi

for delay in 0 2 4 8 16; do
  sleep "${delay}"
  # Always rebase onto the latest remote first. Our commits only add files, so
  # this never conflicts; it just avoids "rejected -- fetch first" failures.
  git fetch origin "${branch}" --quiet 2>/dev/null || true
  git "${GIT_ID[@]}" rebase "origin/${branch}" --quiet 2>/dev/null || git rebase --abort 2>/dev/null || true
  if git push origin "${branch}"; then
    echo "==> synced to origin/${branch}"
    exit 0
  fi
  echo "==> push failed, retrying..." >&2
done
echo "error: could not push after retries; will go out with the next sync" >&2
exit 1
