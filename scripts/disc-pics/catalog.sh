#!/usr/bin/env bash
# Runs Claude over every photo waiting in the inbox and stages each disc into
# disc-pics-data/incoming/ as a photo plus a one-line sidecar of the AI's
# identification. It does NOT touch inventory.csv or sheet.csv -- that keeps
# the mini's git pushes purely additive, so they can never conflict with disc
# rows edited elsewhere. Run merge-incoming.py to fold incoming discs into the
# spreadsheet (assigning ids, cleaning photos) from a single place.
#
# Usage:
#   ./catalog.sh
#
# Requires the `claude` CLI. Override with CLAUDE_BIN=/path/to/claude.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

DISC_PICS_DIR="${DISC_PICS_DIR:-${HOME}/Pictures/disc-pics}"
INBOX="${DISC_PICS_DIR}/inbox"
DATA_DIR="${REPO_ROOT}/disc-pics-data"
INCOMING="${DATA_DIR}/incoming"

CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
if [[ -z "${CLAUDE_BIN}" ]]; then
  echo "error: cannot find 'claude' on PATH. set CLAUDE_BIN=/path/to/claude and re-run." >&2
  exit 1
fi

if [[ ! -d "${INBOX}" ]]; then
  echo "error: no inbox at ${INBOX} -- run import.sh first" >&2
  exit 1
fi

mkdir -p "${INCOMING}"

slugify() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -e 's/[^a-z0-9]\{1,\}/-/g' -e 's/^-//' -e 's/-$//'
}

identify_prompt() {
  local photo="$1"
  cat <<EOF
Read the image file at ${photo}. It is a photo of a single disc golf disc.
Identify it as best you can from the stamp, shape, and color.
Reply with exactly one line and nothing else: eight fields separated by
the | character, in this order:
mold|brand|plastic|color|stamped_weight|condition|price|notes
- condition is the Sleepy Scale, 1-10
- stamped_weight is the weight in grams printed/stamped on the disc if
  visible in the photo, otherwise unknown (the owner weighs discs on a
  scale separately -- do not guess)
- price is a suggested asking price in whole US dollars, number only.
  Anchor: an average used disc in decent shape is 9. Beat-in base plastic
  is 5-7, near-new premium plastic is 10-14, hot molds or limited/tour
  stamps can be 15 or more. Anything condition 5 or below caps at 6.
  Never go below 4 -- the local shop pays 3 with zero effort.
- notes: stamp, run, dyes, ink, wear -- anything a buyer or trader would want
- use the word unknown for any field you cannot determine
- do not use commas, quotes, or | inside a field
EOF
}

shopt -s nullglob
photos=("${INBOX}"/*)
if [[ ${#photos[@]} -eq 0 ]]; then
  echo "==> inbox is empty -- nothing to catalog. run import.sh first."
  exit 0
fi

ERR_LOG="${HOME}/Library/Logs/juddy/claude-catalog.err.log"
mkdir -p "$(dirname "${ERR_LOG}")"

cataloged=0
skipped=0
for photo in "${photos[@]}"; do
  name="$(basename "${photo}")"
  echo "==> identifying: ${name}"

  # Unique, collision-proof stem: high-res timestamp + a slug we fill in after
  # identification. Two runs (or two discs in one run) never share a stem.
  stamp="$(date +%s%N)"
  ext="${name##*.}"

  # Stage the photo inside the repo first: claude's sandbox can only read files
  # under its working directory, and the inbox in ~/Pictures is not.
  staged="${INCOMING}/${stamp}.${ext}"
  mv "${photo}" "${staged}"

  # A claude failure must not kill the whole run (set -e); errors go to the
  # error log so they can actually be diagnosed.
  line="$(cd "${REPO_ROOT}" && "${CLAUDE_BIN}" -p "$(identify_prompt "${staged}")" 2>>"${ERR_LOG}" | awk 'NF {last=$0} END {print last}')" || {
    echo "    claude failed for ${name} (see ${ERR_LOG}), returning to inbox" >&2
    mv "${staged}" "${photo}"
    skipped=$((skipped + 1))
    continue
  }

  pipes="${line//[^|]/}"
  if [[ ${#pipes} -ne 7 ]]; then
    echo "    could not parse response, returning to inbox: ${line:-<empty>}" >&2
    mv "${staged}" "${photo}"
    skipped=$((skipped + 1))
    continue
  fi

  IFS='|' read -r mold _rest <<< "${line}"
  slug="$(slugify "${mold}")"

  # Rename the photo to include the mold slug, and drop a sidecar next to it.
  final_photo="${INCOMING}/${stamp}-${slug:-disc}.${ext}"
  mv "${staged}" "${final_photo}"
  printf 'photo=%s\ndate=%s\nidentify=%s\n' \
    "$(basename "${final_photo}")" "$(date +%Y-%m-%d)" "${line}" \
    > "${INCOMING}/${stamp}-${slug:-disc}.sidecar"

  echo "    staged: ${line%%|*} -> incoming/$(basename "${final_photo}")"
  cataloged=$((cataloged + 1))
done

echo
echo "==> staged ${cataloged} disc(s) to incoming/, ${skipped} left in inbox"
echo "==> run merge-incoming.py to fold them into the spreadsheet"
