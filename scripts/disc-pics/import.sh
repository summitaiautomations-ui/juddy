#!/usr/bin/env bash
# Pulls new disc photos out of the Photo Booth library into the disc-pics
# inbox. Photo Booth dumps everything into one package folder; this copies
# only files it hasn't seen before, so it is safe to re-run any time.
#
# Usage:
#   ./import.sh            # copy new photos into the inbox
#   FLIP=1 ./import.sh     # also un-mirror them (Photo Booth mirrors by default)

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
  echo "${name}" >> "${SEEN}"
  echo "==> imported: ${name}"
  count=$((count + 1))
done < <(find "${PHOTO_BOOTH_DIR}" -maxdepth 1 -type f \
  \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.heic' \) -print0)

echo
echo "==> ${count} new photo(s) waiting in ${INBOX}"
echo "==> next: run catalog.sh to identify them and build the inventory"
