#!/usr/bin/env bash
# Undo the *configuration* done by external-drive-setup.sh:
#   - remove the Time Machine destination and disable automatic backups
#   - drop the data-volume Time Machine exclusion
#   - unmount the two volumes
#
# It does NOT erase the drive or delete your files -- the data volume and its
# contents are left intact. To fully wipe the drive, re-run external-drive-setup.sh
# (or use Disk Utility).
#
# Usage:
#   ./external-drive-teardown.sh
#   DATA_VOL="Juddy Data" TM_VOL="Time Machine" ./external-drive-teardown.sh

set -uo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: macOS only" >&2
  exit 1
fi

DATA_VOL="${DATA_VOL:-Juddy Data}"
TM_VOL="${TM_VOL:-Time Machine}"
DATA_MNT="/Volumes/${DATA_VOL}"
TM_MNT="/Volumes/${TM_VOL}"

echo "==> disabling automatic Time Machine backups"
sudo tmutil disable || true

echo "==> removing Time Machine destination '${TM_MNT}'"
sudo tmutil removedestination "${TM_MNT}" 2>/dev/null || \
  echo "   note: '${TM_MNT}' was not a registered destination (skipping)."

echo "==> removing data-volume Time Machine exclusion"
sudo tmutil removeexclusion "${DATA_MNT}" 2>/dev/null || true

for mnt in "${TM_MNT}" "${DATA_MNT}"; do
  if [[ -d "${mnt}" ]]; then
    echo "==> unmounting '${mnt}'"
    diskutil unmount "${mnt}" || echo "   note: could not unmount '${mnt}' (in use?)."
  fi
done

echo "done. the drive's files are untouched; only Time Machine config was removed."
