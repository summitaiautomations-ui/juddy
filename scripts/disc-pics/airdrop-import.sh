#!/usr/bin/env bash
# Sweep new image files that AirDrop dropped into ~/Downloads into the
# disc-pics inbox -- cleaned up and ready for catalog.sh. Only touches image
# files (jpg/jpeg/png/heic); everything else in Downloads is left alone.
# HEIC (iPhone photos) is converted to JPG. Safe to re-run.
#
#   ./airdrop-import.sh
#
# Knobs:
#   AIRDROP_DIR    folder to sweep    (default: ~/Downloads -- where AirDrop lands)
#   DISC_PICS_DIR  pipeline storage   (default: ~/Pictures/disc-pics)
#   ENHANCE=0      skip photo cleanup
#   BGCLEAN=0      skip background removal
#   BG_SHORTCUT    name of the Shortcuts shortcut to use for background removal

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: this script only runs on macOS" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AIRDROP_DIR="${AIRDROP_DIR:-${HOME}/Downloads}"
DISC_PICS_DIR="${DISC_PICS_DIR:-${HOME}/Pictures/disc-pics}"
INBOX="${DISC_PICS_DIR}/inbox"
mkdir -p "${INBOX}"

[[ -d "${AIRDROP_DIR}" ]] || { echo "error: drop folder not found: ${AIRDROP_DIR}" >&2; exit 1; }

# --- photo cleanup (same treatment import.sh gives Photo Booth shots) --------
# Replace the background with clean white using macOS subject isolation. Needs
# a Shortcuts shortcut named "Remove Background" plus ImageMagick. Skips quietly
# if either is missing. BGCLEAN=0 disables.
bg_shortcut() {
  local candidate
  for candidate in "${BG_SHORTCUT:-}" "Remove Background" "Remove Image Background"; do
    [[ -n "${candidate}" ]] || continue
    if shortcuts list 2>/dev/null | grep -Fxq "${candidate}"; then
      echo "${candidate}"; return 0
    fi
  done
  return 1
}
clean_background() {
  local f="$1" cutout="${1%.*}.cutout.png" shortcut
  [[ "${BGCLEAN:-1}" == "0" ]] && return 0
  command -v magick >/dev/null 2>&1 || return 0
  shortcut="$(bg_shortcut)" || return 0
  if shortcuts run "${shortcut}" -i "${f}" -o "${cutout}" 2>/dev/null && [[ -s "${cutout}" ]]; then
    magick "${cutout}" -background white -flatten \
      -bordercolor white -border 48 "${f}" \
      && echo "    background cleaned: $(basename "${f}")"
  fi
  rm -f "${cutout}"
}
enhance() {
  local f="$1"
  [[ "${ENHANCE:-1}" == "0" ]] && return 0
  if command -v magick >/dev/null 2>&1; then
    magick "${f}" -auto-orient -auto-level -auto-gamma \
      -modulate 100,112,100 -unsharp 0x1.2 -resize '1600x1600>' -strip "${f}"
  else
    sips --resampleHeightWidthMax 1600 "${f}" >/dev/null 2>&1 || true
  fi
}

# Auto-crop to a tight, centered square (matches the storefront's 900x900 look).
# Needs python3 + pillow/numpy/scipy; skips quietly otherwise. DISC_CROP=0 disables.
crop_disc() {
  [[ "${DISC_CROP:-1}" == "0" ]] && return 0
  command -v python3 >/dev/null 2>&1 || return 0
  python3 "${SCRIPT_DIR}/crop-disc.py" "$1" 2>/dev/null || true
}

# unique destination path in the inbox so two "IMG_1234" never clobber
dest_for() {
  local base="$1" ext="$2" n=0 cand="${INBOX}/${1}.${2}"
  while [[ -e "${cand}" ]]; do n=$((n+1)); cand="${INBOX}/${base}-${n}.${ext}"; done
  echo "${cand}"
}

now="$(date +%s)"
count=0
while IFS= read -r -d '' src; do
  # Skip files still landing -- let AirDrop finish writing before we grab them.
  mtime="$(stat -f %m "${src}" 2>/dev/null || echo 0)"
  if [[ $(( now - mtime )) -lt 3 ]]; then
    echo "    still arriving, will catch next run: $(basename "${src}")"; continue
  fi
  [[ -s "${src}" ]] || continue

  name="$(basename "${src}")"; stem="${name%.*}"; ext="${name##*.}"
  lc_ext="$(printf '%s' "${ext}" | tr '[:upper:]' '[:lower:]')"

  if [[ "${lc_ext}" == "heic" ]]; then
    dst="$(dest_for "${stem}" jpg)"
    if sips -s format jpeg "${src}" --out "${dst}" >/dev/null 2>&1; then
      rm -f "${src}"
    else
      echo "    HEIC convert failed, moving as-is: ${name}"
      dst="$(dest_for "${stem}" heic)"; mv "${src}" "${dst}"
    fi
  else
    dst="$(dest_for "${stem}" "${lc_ext}")"
    mv "${src}" "${dst}"
  fi

  clean_background "${dst}"
  enhance "${dst}"
  crop_disc "${dst}"
  echo "==> imported from AirDrop: $(basename "${dst}")"
  count=$((count + 1))
done < <(find "${AIRDROP_DIR}" -maxdepth 1 -type f \
  \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.heic' \) -print0)

echo
echo "==> ${count} new AirDropped photo(s) moved into ${INBOX}"
echo "==> next: catalog.sh identifies them and builds the inventory"
