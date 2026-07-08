#!/usr/bin/env bash
# Add cropped text-screenshot images to the storefront's testimonials section.
#
#   1) AirDrop your screenshots from your phone to the Mac mini
#   2) put them in a folder named  disc-testimonials  on your Desktop
#      (this script creates it for you the first time)
#   3) run:  bash ~/juddy/scripts/disc-pics/add-testimonials.sh
#
# It copies them in, converts iPhone HEIC to web-friendly jpg, rebuilds the
# list, and pushes. Re-runnable and safe.
set -euo pipefail
SRC="${1:-$HOME/Desktop/disc-testimonials}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEST="${ROOT}/docs/testimonials"
mkdir -p "${SRC}" "${DEST}"

shopt -s nullglob nocaseglob
n=0
for f in "${SRC}"/*.jpg "${SRC}"/*.jpeg "${SRC}"/*.png "${SRC}"/*.webp; do
  cp "${f}" "${DEST}/"; n=$((n+1))
done
for f in "${SRC}"/*.heic; do
  base="$(basename "${f%.*}")"
  sips -s format jpeg "${f}" --out "${DEST}/${base}.jpg" >/dev/null 2>&1 && n=$((n+1))
done
echo "==> added ${n} screenshot(s) from ${SRC}"
[[ ${n} -eq 0 ]] && { echo "    (nothing found -- drop images in ${SRC} first)"; exit 0; }

python3 "${ROOT}/scripts/disc-pics/gen-testimonials.py"

cd "${ROOT}"; branch="$(git rev-parse --abbrev-ref HEAD)"
git add docs/testimonials
git diff --cached --quiet || git commit -q -m "testimonials: add ${n} screenshot(s)"
for delay in 0 2 4 8; do sleep "${delay}"
  git fetch origin "${branch}" -q 2>/dev/null || true
  git rebase "origin/${branch}" -q 2>/dev/null || git rebase --abort 2>/dev/null || true
  git push origin "${branch}" && { echo "==> pushed. live on discdiver.com shortly."; exit 0; }
done
echo "error: push failed; try again in a minute" >&2; exit 1
