#!/usr/bin/env bash
# Runs Claude over every photo waiting in the inbox, appends one row per disc
# to inventory.csv, and files the photo into library/ renamed after the disc.
# Photos Claude can't parse are left in the inbox so nothing is lost.
#
# Usage:
#   ./catalog.sh
#
# Requires the `claude` CLI. Override with CLAUDE_BIN=/path/to/claude.

set -euo pipefail

DISC_PICS_DIR="${DISC_PICS_DIR:-${HOME}/Pictures/disc-pics}"
INBOX="${DISC_PICS_DIR}/inbox"
LIBRARY="${DISC_PICS_DIR}/library"
INVENTORY="${DISC_PICS_DIR}/inventory.csv"

CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
if [[ -z "${CLAUDE_BIN}" ]]; then
  echo "error: cannot find 'claude' on PATH. set CLAUDE_BIN=/path/to/claude and re-run." >&2
  exit 1
fi

if [[ ! -d "${INBOX}" ]]; then
  echo "error: no inbox at ${INBOX} -- run import.sh first" >&2
  exit 1
fi

mkdir -p "${LIBRARY}"
if [[ ! -f "${INVENTORY}" ]]; then
  echo 'id,date,photo,mold,brand,plastic,color,weight,condition,notes' > "${INVENTORY}"
fi

# CSV-quote a single field: wrap in quotes, double any embedded quotes.
csv_field() {
  local f="${1//\"/\"\"}"
  printf '"%s"' "${f}"
}

# Turn a mold name into a filename-safe slug ("Champion Destroyer" -> champion-destroyer).
slugify() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -e 's/[^a-z0-9]\{1,\}/-/g' -e 's/^-//' -e 's/-$//'
}

identify_prompt() {
  local photo="$1"
  cat <<EOF
Read the image file at ${photo}. It is a photo of a single disc golf disc.
Identify it as best you can from the stamp, shape, and color.
Reply with exactly one line and nothing else: seven fields separated by
the | character, in this order:
mold|brand|plastic|color|weight|condition|notes
- condition is the Sleepy Scale, 1-10
- weight is in grams if visible on the disc, otherwise unknown
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

cataloged=0
skipped=0
for photo in "${photos[@]}"; do
  name="$(basename "${photo}")"
  echo "==> identifying: ${name}"

  # Take the last non-empty line in case the model adds any preamble.
  line="$("${CLAUDE_BIN}" -p "$(identify_prompt "${photo}")" 2>/dev/null | awk 'NF {last=$0} END {print last}')"

  pipes="${line//[^|]/}"
  if [[ ${#pipes} -ne 6 ]]; then
    echo "    could not parse response, leaving in inbox: ${line:-<empty>}" >&2
    skipped=$((skipped + 1))
    continue
  fi

  IFS='|' read -r mold brand plastic color weight condition notes <<< "${line}"

  rows=$(( $(wc -l < "${INVENTORY}") - 1 ))
  id="$(printf '%03d' $((rows + 1)))"
  ext="${name##*.}"
  slug="$(slugify "${mold}")"
  new_name="${id}-${slug:-disc}.${ext}"

  mv "${photo}" "${LIBRARY}/${new_name}"
  {
    printf '%s,%s,%s' "${id}" "$(date +%Y-%m-%d)" "$(csv_field "${new_name}")"
    for f in "${mold}" "${brand}" "${plastic}" "${color}" "${weight}" "${condition}" "${notes}"; do
      printf ',%s' "$(csv_field "${f}")"
    done
    printf '\n'
  } >> "${INVENTORY}"

  echo "    ${id}: ${brand} ${mold} (${plastic}, ${color}) -> library/${new_name}"
  cataloged=$((cataloged + 1))
done

echo
echo "==> cataloged ${cataloged} disc(s), ${skipped} left in inbox"
echo "==> inventory: ${INVENTORY}"
