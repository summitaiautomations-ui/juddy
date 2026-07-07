#!/usr/bin/env bash
# Runs Claude over every photo waiting in the inbox, appends one row per disc
# to the repo inventory, and files the photo into disc-pics-data/photos/.
# Photos Claude can't parse are left in the inbox so nothing is lost.
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
PHOTOS="${DATA_DIR}/photos"
INVENTORY="${DATA_DIR}/inventory.csv"
SHEET="${DATA_DIR}/sheet.csv"

CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
if [[ -z "${CLAUDE_BIN}" ]]; then
  echo "error: cannot find 'claude' on PATH. set CLAUDE_BIN=/path/to/claude and re-run." >&2
  exit 1
fi

if [[ ! -d "${INBOX}" ]]; then
  echo "error: no inbox at ${INBOX} -- run import.sh first" >&2
  exit 1
fi

mkdir -p "${PHOTOS}"
if [[ ! -f "${INVENTORY}" ]]; then
  echo 'id,date,photo,mold,brand,plastic,color,stamped_weight,scale_weight,condition,price,status,notes' > "${INVENTORY}"
fi
if [[ ! -f "${SHEET}" ]]; then
  echo 'photo_url,id,mold,brand,plastic,color,stamped_weight_g,scale_weight_g,condition,price_usd,status,notes' > "${SHEET}"
fi

# Public raw-file URL prefix for photos, derived from the git remote and the
# currently checked-out branch. Used by the shared Google Sheet's IMAGE column.
raw_base() {
  local remote owner_repo branch
  remote="$(git -C "${REPO_ROOT}" remote get-url origin)"
  # owner/repo = last two path segments; works for https, ssh, and proxy URLs.
  owner_repo="$(echo "${remote%.git}" | tr ':' '/' | awk -F/ '{print $(NF-1)"/"$NF}')"
  branch="$(git -C "${REPO_ROOT}" rev-parse --abbrev-ref HEAD)"
  echo "https://raw.githubusercontent.com/${owner_repo}/${branch}/disc-pics-data/photos"
}
RAW_BASE="$(raw_base)"

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

  # Stage the photo inside the repo first: claude's sandbox can only read
  # files under its working directory, and the inbox in ~/Pictures is not.
  staged="${PHOTOS}/staging-${name}"
  mv "${photo}" "${staged}"

  # Take the last non-empty line in case the model adds any preamble.
  # A claude failure must not kill the whole run (set -e); errors go to
  # the error log so they can actually be diagnosed.
  line="$(cd "${REPO_ROOT}" && "${CLAUDE_BIN}" -p "$(identify_prompt "${staged}")" 2>>"${ERR_LOG}" | awk 'NF {last=$0} END {print last}')" || {
    echo "    claude failed for ${name} (see ${ERR_LOG}), leaving in inbox" >&2
    mv "${staged}" "${photo}"
    skipped=$((skipped + 1))
    continue
  }

  pipes="${line//[^|]/}"
  if [[ ${#pipes} -ne 7 ]]; then
    echo "    could not parse response, leaving in inbox: ${line:-<empty>}" >&2
    mv "${staged}" "${photo}"
    skipped=$((skipped + 1))
    continue
  fi

  IFS='|' read -r mold brand plastic color stamped_weight condition price notes <<< "${line}"
  scale_weight="unknown"  # filled in by hand when the owner weighs the disc

  rows=$(( $(wc -l < "${INVENTORY}") - 1 ))
  id="$(printf '%03d' $((rows + 1)))"
  ext="${name##*.}"
  slug="$(slugify "${mold}")"
  new_name="${id}-${slug:-disc}.${ext}"
  today="$(date +%Y-%m-%d)"

  mv "${staged}" "${PHOTOS}/${new_name}"

  {
    printf '%s,%s,%s' "${id}" "${today}" "$(csv_field "${new_name}")"
    for f in "${mold}" "${brand}" "${plastic}" "${color}" "${stamped_weight}" "${scale_weight}" "${condition}" "${price}" "available" "${notes}"; do
      printf ',%s' "$(csv_field "${f}")"
    done
    printf '\n'
  } >> "${INVENTORY}"

  {
    printf '%s,%s' "$(csv_field "${RAW_BASE}/${new_name}")" "${id}"
    for f in "${mold}" "${brand}" "${plastic}" "${color}" "${stamped_weight}" "${scale_weight}" "${condition}" "${price}" "available" "${notes}"; do
      printf ',%s' "$(csv_field "${f}")"
    done
    printf '\n'
  } >> "${SHEET}"

  echo "    ${id}: ${brand} ${mold} (${plastic}, ${color}) ~\$${price} -> photos/${new_name}"
  cataloged=$((cataloged + 1))
done

echo
echo "==> cataloged ${cataloged} disc(s), ${skipped} left in inbox"
echo "==> inventory: ${INVENTORY}"
