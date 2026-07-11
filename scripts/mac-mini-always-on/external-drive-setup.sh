#!/usr/bin/env bash
# Set up a Toshiba (or any) external USB drive on the always-on Mac mini.
#
# What it does:
#   1. Helps you identify the external drive:  ./external-drive-setup.sh --list
#   2. ERASES the drive and formats it APFS, creating ONE container with TWO
#      space-sharing volumes:
#        - "Juddy Data"   -> repos, Claude Code data, logs, bulk storage
#        - "Time Machine" -> dedicated Time Machine backup destination
#      APFS volumes share the container's free space, so you never pre-carve sizes:
#      whichever volume needs room takes it from the shared pool.
#   3. Registers the Time Machine volume as a backup destination and enables backups
#      (excluding the data volume so backups don't loop onto the same physical disk).
#   4. Creates a tidy directory layout on the data volume.
#
# Safety: refuses to touch internal/boot/virtual disks, only operates on an external
# *whole* physical disk, and makes you type ERASE to confirm. Nothing is wiped
# without that confirmation.
#
# Usage:
#   ./external-drive-setup.sh --list             # show candidate external disks
#   ./external-drive-setup.sh /dev/diskN         # set up that disk
#   DISK=/dev/diskN ./external-drive-setup.sh    # same, via env var
#
# Overrides (env vars):
#   DATA_VOL="Juddy Data"   TM_VOL="Time Machine"   # volume names
#   ASSUME_YES=1                                    # skip the interactive prompt
#
# This is intentionally NOT wired into install.sh: it is a destructive, one-time
# step, whereas install.sh is meant to be safely re-runnable.

set -euo pipefail

usage() {
  sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
}

case "${1:-}" in -h|--help) usage; exit 0 ;; esac

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: this script only runs on macOS" >&2
  exit 1
fi
if [[ $EUID -eq 0 ]]; then
  echo "error: do not run this as root. it will sudo where needed." >&2
  exit 1
fi

DATA_VOL="${DATA_VOL:-Juddy Data}"
TM_VOL="${TM_VOL:-Time Machine}"
DISK="${DISK:-}"
LIST=0

for arg in "$@"; do
  case "${arg}" in
    --list|-l)          LIST=1 ;;
    -h|--help)          usage; exit 0 ;;
    /dev/disk*|disk[0-9]*) DISK="${arg}" ;;
    *) echo "error: unrecognised argument '${arg}'" >&2; echo; usage; exit 1 ;;
  esac
done

if [[ ${LIST} -eq 1 ]]; then
  echo "==> external physical disks:"
  echo
  diskutil list external physical
  echo
  echo "Find your Toshiba above (its Media Name usually contains 'TOSHIBA'),"
  echo "note its identifier (e.g. disk4), then run:"
  echo "    $0 /dev/diskN"
  exit 0
fi

if [[ -z "${DISK}" ]]; then
  echo "error: no disk specified." >&2
  echo "run '$0 --list' to find your Toshiba drive, then pass it in." >&2
  exit 1
fi

# Normalise: accept 'disk4', '/dev/disk4', 'disk4s1' -> '/dev/disk4'
DISK="${DISK#/dev/}"
DISK="${DISK%%s[0-9]*}"   # strip any partition/volume suffix -> whole disk
DISK="/dev/${DISK}"

INFO="$(diskutil info "${DISK}" 2>/dev/null)" || {
  echo "error: ${DISK} is not a disk diskutil recognises." >&2
  echo "run '$0 --list' to see valid identifiers." >&2
  exit 1
}

# Pull a field out of `diskutil info` text: field "Whole" -> "Yes"
field() { printf '%s\n' "${INFO}" | sed -n "s/^ *$1: *//p" | head -1; }

DEV_ID="$(field 'Device Identifier')"
WHOLE="$(field 'Whole')"
VIRTUAL="$(field 'Virtual')"
LOCATION="$(field 'Device Location')"
INTERNAL="$(field 'Internal')"
MEDIA="$(field 'Device / Media Name')"; [[ -z "${MEDIA}" ]] && MEDIA="$(field 'Media Name')"
SIZE="$(field 'Disk Size')"

# The whole disk backing "/", so we can be certain we never touch the boot drive.
BOOT_WHOLE="$(diskutil info / 2>/dev/null | sed -n 's/^ *Part of Whole: *//p' | head -1)"

fail() { echo "error: $*" >&2; exit 1; }

[[ "${WHOLE}" == "Yes" ]]                              || fail "${DISK} is not a whole disk. Pass the whole disk (e.g. /dev/disk4), not a partition."
[[ "${VIRTUAL}" != "Yes" ]]                            || fail "${DISK} is a virtual/synthesised disk, not your physical drive."
[[ "${LOCATION}" == "External" || "${INTERNAL}" == "No" ]] || fail "${DISK} does not look external. Refusing to erase it."
[[ -n "${DEV_ID}" && "${DEV_ID}" != "${BOOT_WHOLE}" ]] || fail "${DISK} is your boot disk (${BOOT_WHOLE}). Refusing."

cat <<EOF

==========================================================================
  ABOUT TO ERASE AND REFORMAT:

    Disk        : ${DISK}  (${DEV_ID})
    Media       : ${MEDIA:-unknown}
    Size        : ${SIZE:-unknown}
    External    : ${LOCATION:-$( [[ "${INTERNAL}" == "No" ]] && echo External || echo unknown )}

  This will PERMANENTLY ERASE everything on the disk and create:

    APFS container on ${DEV_ID}
      |- volume "${DATA_VOL}"    (repos / Claude data / logs / storage)
      '- volume "${TM_VOL}"      (Time Machine backups)

  The two volumes share the drive's free space dynamically.
==========================================================================

EOF

if [[ "${ASSUME_YES:-}" != "1" ]]; then
  read -r -p "Type ERASE (all caps) to proceed, anything else to abort: " CONFIRM
  [[ "${CONFIRM}" == "ERASE" ]] || { echo "aborted. nothing was changed."; exit 1; }
fi

echo
echo "==> erasing ${DISK} and creating APFS volume '${DATA_VOL}'"
diskutil eraseDisk APFS "${DATA_VOL}" GPT "${DISK}"

DATA_MNT="/Volumes/${DATA_VOL}"
[[ -d "${DATA_MNT}" ]] || fail "expected '${DATA_MNT}' to be mounted after erase, but it is not."

# Resolve the APFS container so we can add the second volume to the SAME pool.
CONTAINER="$(diskutil info "${DATA_MNT}" | sed -n 's/^ *APFS Container Reference: *//p' | head -1)"
[[ -n "${CONTAINER}" ]] || fail "could not determine the APFS container reference for '${DATA_MNT}'."

echo
echo "==> adding volume '${TM_VOL}' to container ${CONTAINER} (shares free space)"
diskutil apfs addVolume "${CONTAINER}" APFS "${TM_VOL}"

TM_MNT="/Volumes/${TM_VOL}"
[[ -d "${TM_MNT}" ]] || fail "expected '${TM_MNT}' to be mounted after addVolume, but it is not."

echo
echo "==> creating directory layout on '${DATA_MNT}'"
mkdir -p \
  "${DATA_MNT}/repos" \
  "${DATA_MNT}/claude-data" \
  "${DATA_MNT}/logs" \
  "${DATA_MNT}/storage"

echo
echo "==> configuring Time Machine (will prompt for sudo)"
sudo tmutil setdestination -a "${TM_MNT}"
sudo tmutil enable
# Don't back the external data volume up onto the same physical drive.
sudo tmutil addexclusion "${DATA_MNT}" 2>/dev/null || \
  echo "   note: could not add '${DATA_MNT}' as a Time Machine exclusion (non-fatal)."

echo
echo "==> Time Machine destination(s):"
tmutil destinationinfo || true

cat <<EOF

==========================================================================
  done. your Toshiba drive is set up:

    ${DATA_MNT}
      repos/         put working clones here
      claude-data/   Claude Code state/logs if you relocate ~/.claude
      logs/          general logs
      storage/       bulk storage

    ${TM_MNT}
      Time Machine backup destination (backups are now enabled)

  verify:
    diskutil apfs list
    tmutil destinationinfo
    tmutil startbackup --block      # kick off the first backup now (optional)

  OPTIONAL next steps (not done automatically -- they touch the live setup):

  * Move this repo onto the drive and re-point the launch agent:
      cp -R "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)" "${DATA_MNT}/repos/"
      cd "${DATA_MNT}/repos/$(basename "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)")"
      bash scripts/mac-mini-always-on/install.sh   # re-render the LaunchAgent path

  * Keep Claude Code data on the drive (survives internal-disk resets):
      mv ~/.claude "${DATA_MNT}/claude-data/dot-claude"
      ln -s "${DATA_MNT}/claude-data/dot-claude" ~/.claude
    (or set CLAUDE_CONFIG_DIR="${DATA_MNT}/claude-data/dot-claude" in the
     LaunchAgent's EnvironmentVariables)
==========================================================================
EOF
