# Mac mini always-on bundle

Scripts to run Claude Code 24/7 on a dedicated Mac mini, plus external-drive setup.

## Always-on service

| Script | What it does |
| --- | --- |
| `install.sh` | Applies power settings and installs the LaunchAgents (auto-start `claude`, run `healthcheck.sh` every 5 min). Re-runnable. |
| `power-settings.sh` | `pmset` tuning: never sleep, nightly 04:00 restart, wake-on-LAN, auto-restart after power loss. |
| `healthcheck.sh` | Logs uptime/load/disk/memory, whether the `claude-code` job is alive, and external-drive + Time Machine status. |
| `uninstall.sh` | Removes the LaunchAgents and resets power settings to defaults. |

```sh
bash scripts/mac-mini-always-on/install.sh
```

## External Toshiba drive

`external-drive-setup.sh` prepares a new external USB drive for the always-on mini.
It **erases** the drive and creates one APFS container with two space-sharing volumes:

- **Juddy Data** — `repos/`, `claude-data/`, `logs/`, `storage/`
- **Time Machine** — a dedicated, enabled Time Machine backup destination

Because both volumes share the APFS container's free space, you never pre-carve
sizes; whichever volume needs room takes it from the shared pool. The data volume
is excluded from Time Machine so backups don't loop onto the same physical disk.

```sh
# 1. find the drive (look for a Media Name containing TOSHIBA)
bash scripts/mac-mini-always-on/external-drive-setup.sh --list

# 2. set it up (asks you to type ERASE to confirm)
bash scripts/mac-mini-always-on/external-drive-setup.sh /dev/diskN
```

Safety: the script refuses to touch internal, boot, or virtual disks — it only
operates on an external *whole* physical disk, and only after you type `ERASE`.

Override volume names with `DATA_VOL=... TM_VOL=...`; skip the prompt with
`ASSUME_YES=1` (for automation only).

To remove the Time Machine configuration and unmount the volumes **without**
erasing your files:

```sh
bash scripts/mac-mini-always-on/external-drive-teardown.sh
```
