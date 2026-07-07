#!/usr/bin/env bash
# One-shot rescue for when the mini cataloged photos but its push is blocked
# by CSV conflicts with newer rows edited elsewhere. The mini's PHOTO FILES
# are the only irreplaceable thing; the authoritative inventory lives on the
# remote. This merges, keeps the mini's new photos, takes the remote's CSVs,
# and pushes. Non-destructive: no reset --hard, no stash drop.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"
BRANCH="claude/photobooth-disc-pics-vueawx"

GIT_ID=(-c user.name="juddy disc-pics" -c user.email="juddy@localhost")

echo "==> committing any uncommitted mini work first"
git add disc-pics-data
git "${GIT_ID[@]}" commit -m "disc-pics: mini catalog (pre-rescue)" 2>/dev/null || true

echo "==> fetching remote"
git fetch origin "${BRANCH}"

echo "==> merging remote (CSV conflicts expected, resolved automatically)"
git "${GIT_ID[@]}" merge --no-edit "origin/${BRANCH}" || true

# Whatever happened to the CSVs, the remote's copies are authoritative.
git checkout "origin/${BRANCH}" -- disc-pics-data/inventory.csv disc-pics-data/sheet.csv
git add disc-pics-data

# If the merge left us mid-conflict, completing the add + commit finishes it.
if ! git "${GIT_ID[@]}" commit --no-edit -m "disc-pics: merge mini photos, keep remote inventory" 2>/dev/null; then
  echo "==> (nothing extra to commit, merge already clean)"
fi

echo "==> pushing"
git push origin "${BRANCH}"

echo "==> done. photos now in the repo:"
git ls-tree -r --name-only HEAD -- disc-pics-data/photos/ | grep -v gitkeep
