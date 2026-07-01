#!/usr/bin/env bash
# Pulls new disc photos out of the Photo Booth library into the disc-pics
# inbox. Photo Booth dumps everything into one package folder; this copies
# only files it hasn't seen before, so it is safe to re-run any time.
#
# Usage:
#   ./import.sh            # copy new photos into the inbox
#   FLIP=1 ./import.sh     # also un-mirror them (Photo Booth mirrors by default)
#   ENHANCE=0 ./import.sh  # skip photo cleanup
#
# Photos are auto-enhanced on import: with ImageMagick installed
# (brew install imagemagick) they get auto-levels, a gentle saturation
# boost, and sharpening; otherwise they're just capped at 1600px.

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: this script only runs on macOS" >&2
  exit 1
fi

PHOTO_BOOTH_DIR="${PHOTO_BOOTH_DIR:-${HOME}/Pictures/Photo Booth Library/Pictures}"
DISC_PICS_DIR="${DISC_PICS_DIR:-${HOME}/Pictures/disc-pics}"
INBOX="${DISC_PICS_DIR}/inbox"
SEEN="${DISC_PICS_DIR}/.imported"

if [[ ! -d "${PHOTO_BOOTH_DIR}" ]]; then
  echo "error: Photo Booth library not found at: ${PHOTO_BOOTH_DIR}" >&2
  echo "take at least one photo in Photo Booth first, or set PHOTO_BOOTH_DIR." >&2
  exit 1
fi

mkdir -p "${INBOX}"
touch "${SEEN}"

# Replace the background with clean white using macOS subject isolation.
# Needs (a) a Shortcuts shortcut named "Remove Background" containing the
# Remove Background action, and (b) ImageMagick for the white composite.
# Quietly skips if either is missing. BGCLEAN=0 disables.
BG_SHORTCUT="${BG_SHORTCUT:-Remove Background}"
clean_background() {
  local f="$1" cutout="${1%.*}.cutout.png"
  if [[ "${BGCLEAN:-1}" == "0" ]]; then
    return 0
  fi
  command -v magick >/dev/null 2>&1 || return 0
  shortcuts list 2>/dev/null | grep -Fxq "${BG_SHORTCUT}" || return 0
  if shortcuts run "${BG_SHORTCUT}" -i "${f}" -o "${cutout}" 2>/dev/null && [[ -s "${cutout}" ]]; then
    # Flatten the cutout onto white with a little breathing room.
    magick "${cutout}" -background white -flatten \
      -bordercolor white -border 48 "${f}" \
      && echo "    background cleaned: $(basename "${f}")"
  fi
  rm -f "${cutout}"
}

# Clean up a photo in place: fix exposure/color cast from indoor webcam
# shots, sharpen a touch, and cap the size. Falls back to a resize-only
# pass via sips when ImageMagick isn't installed.
enhance() {
  local f="$1"
  if [[ "${ENHANCE:-1}" == "0" ]]; then
    return 0
  fi
  if command -v magick >/dev/null 2>&1; then
    magick "${f}" -auto-orient -auto-level -auto-gamma \
      -modulate 100,112,100 -unsharp 0x1.2 -resize '1600x1600>' -strip "${f}"
  else
    sips --resampleHeightWidthMax 1600 "${f}" >/dev/null 2>&1 || true
  fi
}

count=0
while IFS= read -r -d '' src; do
  name="$(basename "${src}")"
  if grep -Fxq "${name}" "${SEEN}"; then
    continue
  fi
  cp "${src}" "${INBOX}/${name}"
  if [[ "${FLIP:-0}" == "1" ]]; then
    sips --flip horizontal "${INBOX}/${name}" >/dev/null
  fi
  clean_background "${INBOX}/${name}"
  enhance "${INBOX}/${name}"
  echo "${name}" >> "${SEEN}"
  echo "==> imported: ${name}"
  count=$((count + 1))
done < <(find "${PHOTO_BOOTH_DIR}" -maxdepth 1 -type f \
  \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.heic' \) -print0)

echo
echo "==> ${count} new photo(s) waiting in ${INBOX}"
echo "==> next: run catalog.sh to identify them and build the inventory"
