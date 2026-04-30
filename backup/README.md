# Home server backup pipeline

Scripts that drive the nightly encrypted backup of `old-mbp`. Run as root via `/etc/cron.d/backup`. Uses `restic` for storage (encryption, dedup, retention) on top of a LUKS-encrypted external SSD at `/mnt/backup`.

Architecture and design discussion lives in Doug's Obsidian vault under "Home Server Backups".

## What runs when

| Schedule | Script | Purpose |
|----------|--------|---------|
| 1:15 AM daily | `run-backup.sh` | Full nightly backup |
| 5:00 AM Sunday | `lib/restic-check.sh` | Weekly repo integrity check |
| 8:00 AM daily | `lib/disk-space-check.sh` | Alert if `/mnt/backup` > 80% full |
| 8:05 AM daily | `lib/last-backup-check.sh` | Alert if no backup in 36 hours |

Defined in `etc/cron.d-backup`. Install with:
```bash
sudo install -m 0644 -o root -g root etc/cron.d-backup /etc/cron.d/backup
```

## Files this depends on

| File | Purpose | Mode |
|------|---------|------|
| `/root/.restic-password` | Restic repo passphrase | 0600 root:root |
| `/root/.ntfy-topic` | ntfy.sh topic name (no `ntfy.sh/` prefix) | 0600 root:root |
| `/root/.healthchecks-url` | healthchecks ping URL (nightly check) | 0600 root:root |
| `/root/.healthchecks-url-restic-check` | (Optional) URL for the weekly restic-check | 0600 root:root |
| `/mnt/backup/.mounted` | Sentinel file proving the LUKS drive is mounted | 0444 root:root |

All four secrets also live in 1Password (source of truth).

## Where stuff lives on disk

| Path | What it is |
|------|------------|
| `/mnt/backup/restic-repo/` | The restic repository (encrypted blobs + indexes) |
| `/mnt/backup/osm-bootstrap/` | Filtered PBF for OSM recovery (refresh quarterly) |
| `/mnt/backup/last-backup-timestamp` | Unix epoch seconds of last successful backup |
| `/mnt/backup/RESTORE.md` | Self-contained restore runbook (copied from this repo each run) |
| `/var/lib/backup-staging/` | Ephemeral DB dumps (cleaned at start + end of each run) |
| `/var/log/backup/` | Backup logs, rotated by `/etc/logrotate.d/backup` |

## Manual operations

### Run the backup right now
```bash
sudo /home/dhughes/infrastructure/backup/run-backup.sh
```

### List snapshots
```bash
sudo restic snapshots \
    --repo /mnt/backup/restic-repo \
    --password-file /root/.restic-password
```

### Browse the latest snapshot (FUSE mount)
```bash
sudo mkdir -p /mnt/restore
sudo restic mount /mnt/restore \
    --repo /mnt/backup/restic-repo \
    --password-file /root/.restic-password
# In another terminal:
ls /mnt/restore/snapshots/latest/
# When done:
sudo fusermount -u /mnt/restore
```

### Send a test ntfy push
```bash
sudo /home/dhughes/infrastructure/backup/lib/notify.sh 3 "Test" "Hello from prod"
```

### Force a healthchecks ping
```bash
HC=$(sudo cat /root/.healthchecks-url)
curl -fsS "$HC"
```

## Customization (env vars)

A few scripts respect env vars for local testing or one-off overrides:

| Script | Env var | Default |
|--------|---------|---------|
| `notify.sh` | `NTFY_TOPIC` | contents of `/root/.ntfy-topic` |
| `pg-dump-all.sh` | `BACKUP_SKIP_DBS` | `color-the-map-osm-template` |
| `sqlite-snapshot.sh` | `APPS_ROOT` | `/home/dhughes/apps` |
| `osm-checkpoint.sh` | `OSM_DB` | `color_the_map` |
| `disk-space-check.sh` | `THRESHOLD`, `MOUNT` | `80`, `/mnt/backup` |
| `last-backup-check.sh` | `TS_FILE`, `THRESHOLD_SECONDS` | `/mnt/backup/last-backup-timestamp`, `129600` |

## See also
- Restore procedures: `RESTORE.md` (in this directory)
- Architecture/design docs: Doug's Obsidian vault, "Home Server Backups" folder
- GitHub issues: [#487](https://github.com/dhughes/color-the-map/issues/487) (this work), [#496](https://github.com/dhughes/color-the-map/issues/496) (GPX encryption — depends on this), [#497](https://github.com/dhughes/color-the-map/issues/497) (NVMe LUKS — depends on this)
