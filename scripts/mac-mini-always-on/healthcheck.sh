#!/usr/bin/env bash
# Periodic healthcheck for the always-on Mac mini.
# Logs uptime, load, disk, and whether the claude-code launchd job is alive.
# Run via launchd every 5 min (see com.juddy.healthcheck.plist.template).

set -uo pipefail

LOG_DIR="${HOME}/Library/Logs/juddy"
mkdir -p "${LOG_DIR}"

ts() { date "+%Y-%m-%d %H:%M:%S"; }

# The always-on launchd jobs we keep an eye on.
JOBS=("com.juddy.claude-code" "com.juddy.jarvis" "com.juddy.jarvis-capture")

# Is a launchd job loaded and running? `launchctl list <label>` prints a dict
# with PID = <n> when running, PID = - when loaded but not running.
job_state() {
  local label="$1" out pid
  if ! out="$(launchctl list "${label}" 2>/dev/null)"; then
    echo "not-loaded"
    return
  fi
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

STATES=""
for job in "${JOBS[@]}"; do
  STATES+="${job#com.juddy.}=$(job_state "${job}") "
done

echo "[$(ts)] uptime=${UPTIME} | disk=${DISK} | mem=${MEM} | ${STATES}"

# Optional: ping a heartbeat URL if HEALTHCHECK_URL is set in the env
if [[ -n "${HEALTHCHECK_URL:-}" ]]; then
  curl -fsS --max-time 10 "${HEALTHCHECK_URL}" >/dev/null \
    && echo "[$(ts)] heartbeat OK" \
    || echo "[$(ts)] heartbeat FAILED"
fi
