#!/usr/bin/env bash
# Periodic healthcheck for the always-on Mac mini.
# Logs uptime, load, disk, and whether the claude-code launchd job is alive.
# Run via launchd every 5 min (see com.juddy.healthcheck.plist.template).

set -uo pipefail

LOG_DIR="${HOME}/Library/Logs/juddy"
mkdir -p "${LOG_DIR}"

ts() { date "+%Y-%m-%d %H:%M:%S"; }

JOB_LABEL="com.juddy.claude-code"

# Is the launchd job loaded and running? `launchctl list <label>` prints a dict
# with PID = <n> when running, PID = - when loaded but not running.
job_state() {
  local out
  if ! out="$(launchctl list "${JOB_LABEL}" 2>/dev/null)"; then
    echo "not-loaded"
    return
  fi
  local pid
  pid="$(echo "${out}" | awk -F'=' '/"PID"/ {gsub(/[ ;"]/,"",$2); print $2}')"
  if [[ -z "${pid}" || "${pid}" == "-" ]]; then
    echo "loaded-not-running"
  else
    echo "running:${pid}"
  fi
}

UPTIME="$(uptime | sed 's/^[[:space:]]*//')"
DISK="$(df -h / | awk 'NR==2 {print $4" free of "$2" ("$5" used)"}')"
MEM="$(vm_stat | awk '/Pages free/ {f=$3} /Pages active/ {a=$3} END {printf "%d MB free", f*4096/1024/1024}')"
STATE="$(job_state)"

echo "[$(ts)] uptime=${UPTIME} | disk=${DISK} | mem=${MEM} | claude-code=${STATE}"

# External Toshiba drive + Time Machine status (best-effort; only reports if set up
# via external-drive-setup.sh). Override the volume name with JUDDY_DATA_VOL.
DATA_VOL="${JUDDY_DATA_VOL:-Juddy Data}"
if [[ -d "/Volumes/${DATA_VOL}" ]]; then
  EXT="$(df -h "/Volumes/${DATA_VOL}" | awk 'NR==2 {print $4" free of "$2}')"
else
  EXT="not-mounted"
fi
LAST_BACKUP="$(tmutil latestbackup 2>/dev/null)"
[[ -z "${LAST_BACKUP}" ]] && LAST_BACKUP="none"
echo "[$(ts)] ext-drive=${EXT} | last-backup=${LAST_BACKUP}"

# Optional: ping a heartbeat URL if HEALTHCHECK_URL is set in the env
if [[ -n "${HEALTHCHECK_URL:-}" ]]; then
  curl -fsS --max-time 10 "${HEALTHCHECK_URL}" >/dev/null \
    && echo "[$(ts)] heartbeat OK" \
    || echo "[$(ts)] heartbeat FAILED"
fi
