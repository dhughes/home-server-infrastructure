# Restore procedures

Self-contained runbook for recovering data from this backup drive. Copied to `/mnt/backup/RESTORE.md` on every successful nightly run, so this file lives next to the data and is accessible even if everything else is gone.

If you're reading this because something is wrong — take a breath, work through the right scenario below, and don't run anything you don't understand.

## What's on this backup drive

```
/mnt/backup/
├── .mounted                            # Sentinel — confirms drive is mounted
├── RESTORE.md                          # This file
├── last-backup-timestamp               # Unix epoch of last successful run
├── restic-repo/                        # Encrypted restic repository (the bulk of backups)
└── osm-bootstrap/                      # Bootstrap PBF for OSM replication recovery
    └── planet-filtered-YYYY-MM-DD.osm.pbf
```

The `restic-repo/` is encrypted. To use it you need:

- The **restic passphrase** — stored in 1Password as "Restic backup repo passphrase (home server)"
- A working `restic` binary (`apt install restic`)
- Optionally: a copy of the password also lives at `/root/.restic-password` on the prod box (mode 0600), which cron uses

## Three scenarios

### Scenario 1: I deleted one file, give it back

For any single file or directory.

```bash
# Mount the latest snapshot as a read-only filesystem
sudo mkdir -p /mnt/restore
sudo restic mount /mnt/restore \
    --repo /mnt/backup/restic-repo \
    --password-file /root/.restic-password &

# Browse and copy what you need
ls /mnt/restore/snapshots/latest/
cp /mnt/restore/snapshots/latest/path/to/file /wherever/it/goes

# Unmount when done
sudo fusermount -u /mnt/restore
```

Tip: `restic snapshots` lists all snapshots if you want a *previous* version, not the latest:

```bash
sudo restic snapshots --repo /mnt/backup/restic-repo --password-file /root/.restic-password
sudo restic mount /mnt/restore --repo /mnt/backup/restic-repo --password-file /root/.restic-password
ls /mnt/restore/snapshots/  # all snapshots are browsable
```

### Scenario 2: I corrupted a database, restore it

For a single Postgres DB. SQLite files are simpler — see "Single SQLite DB" below.

```bash
# Find and mount the snapshot
sudo restic mount /mnt/restore --repo /mnt/backup/restic-repo --password-file /root/.restic-password &

# DB dumps live at /mnt/restore/snapshots/latest/var/lib/backup-staging/postgres/<db>.dump

# Recreate the DB and restore
sudo -u postgres dropdb "<dbname>"  # if necessary
sudo -u postgres createdb "<dbname>" -O <owner>
sudo -u postgres pg_restore --dbname="<dbname>" \
    /mnt/restore/snapshots/latest/var/lib/backup-staging/postgres/<dbname>.dump

# For color-the-map specifically: also restore the osm schema (separate dump)
sudo -u postgres pg_restore --dbname=color-the-map \
    /mnt/restore/snapshots/latest/var/lib/backup-staging/osm/osm-tables.dump

# Unmount
sudo fusermount -u /mnt/restore
```

**Single SQLite DB:** the `.backup` snapshots are usable directly:

```bash
cp /mnt/restore/snapshots/latest/var/lib/backup-staging/sqlite/<app>/<file>.db \
   /home/dhughes/apps/<app>/<file>.db
```

### Scenario 3: The laptop is dead, rebuild from scratch

Estimated time: a long Saturday for the box itself, plus another several hours for OSM replication catchup. Doable.

#### Step 1 — Get a working machine and install Ubuntu

Same hardware ideally; any Ubuntu-capable x86_64 box works. Follow the rebuild guide in the `home-server-infrastructure` repo's `README.md` for OS install, network config, firewall, Cloudflare DNS, ddclient.

Pay attention to the **T2 MacBook Pro quirks** if rebuilding on the same hardware: `pcie_ports=native` GRUB parameter and `sudo systemctl reboot -ff` workaround.

#### Step 2 — Plug in this backup SSD and unlock it

The drive is LUKS-encrypted. Passphrase is in 1Password as "Sandisk Backup SSD LUKS passphrase".

```bash
# If the drive isn't auto-unlocking yet (you haven't set up /etc/crypttab yet):
sudo cryptsetup luksOpen /dev/sda1 backup
sudo mkdir -p /mnt/backup
sudo mount /dev/mapper/backup /mnt/backup
ls /mnt/backup  # confirm RESTORE.md, restic-repo/, osm-bootstrap/ are visible
```

#### Step 3 — Install restic and restore the latest snapshot to staging

```bash
sudo apt update && sudo apt install -y restic

# Get the restic passphrase from 1Password into /root/.restic-password (mode 0600)
sudo install -m 0600 -o root -g root /dev/null /root/.restic-password
sudo nano /root/.restic-password  # paste passphrase, save

# Restore everything to a staging directory
sudo mkdir -p /tmp/restore
sudo restic restore latest \
    --target /tmp/restore \
    --repo /mnt/backup/restic-repo \
    --password-file /root/.restic-password
```

This produces `/tmp/restore/...` mirroring the original filesystem layout (with `home/dhughes/`, `etc/`, `var/lib/backup-staging/`, etc.).

#### Step 4 — Reinstall the packages we had

```bash
sudo apt install -y $(cat /tmp/restore/var/lib/backup-staging/metadata/installed-packages.txt | tr '\n' ' ')
```

This will pull PostgreSQL 18, PostGIS, Caddy, osm2pgsql, ddclient, restic itself, and everything else you had configured.

#### Step 5 — Restore home and config files

```bash
# Home directories
sudo rsync -aHAX /tmp/restore/home/dhughes/apps/ /home/dhughes/apps/
sudo rsync -aHAX /tmp/restore/home/dhughes/infrastructure/ /home/dhughes/infrastructure/
sudo rsync -aHAX /tmp/restore/home/dhughes/.ssh/ /home/dhughes/.ssh/

# /etc files
sudo cp /tmp/restore/etc/ddclient.conf /etc/
sudo cp -r /tmp/restore/etc/ssh/ssh_host_* /etc/ssh/
sudo cp /tmp/restore/etc/crypttab /etc/
sudo cp /tmp/restore/etc/fstab /etc/
sudo cp /tmp/restore/etc/cron.d/* /etc/cron.d/
sudo cp /tmp/restore/etc/logrotate.d/* /etc/logrotate.d/

# LUKS keyfile (so /mnt/backup auto-unlocks at boot)
sudo cp /tmp/restore/root/backup-disk.key /root/
sudo chmod 0400 /root/backup-disk.key

# Reload SSH so host keys take effect
sudo systemctl restart ssh
```

#### Step 6 — Restore Postgres data

For each database dump in `/tmp/restore/var/lib/backup-staging/postgres/`:

```bash
# Inspect what's there
ls /tmp/restore/var/lib/backup-staging/postgres/

# For each <db>.dump:
sudo -u postgres createdb "<db>"
sudo -u postgres pg_restore --dbname="<db>" \
    /tmp/restore/var/lib/backup-staging/postgres/<db>.dump

# Re-create extensions if pg_restore didn't pick them up:
cat /tmp/restore/var/lib/backup-staging/postgres/<db>.extensions.txt
# Run any CREATE EXTENSION commands that show as needed
```

For **color-the-map specifically**, you have a choice for OSM data — see the OSM section below.

#### Step 7 — Restore SQLite DBs

```bash
# Each app's snapshot lives at the same relative path under apps/
# e.g. home-inventory/inventory.db -> /home/dhughes/apps/home-inventory/inventory.db
ls /tmp/restore/var/lib/backup-staging/sqlite/
sudo cp /tmp/restore/var/lib/backup-staging/sqlite/home-inventory/inventory.db \
        /home/dhughes/apps/home-inventory/inventory.db
sudo chown dhughes:dhughes /home/dhughes/apps/home-inventory/inventory.db
```

#### Step 8 — Reinstall systemd unit files

Every app's `.service` file is in its own repo. The deploy procedure is:

```bash
# For each app under ~/apps:
for APP in $(ls /home/dhughes/apps/); do
    SERVICE_FILE="/home/dhughes/apps/$APP/$APP.service"
    if [ -f "$SERVICE_FILE" ]; then
        sudo ln -sf "$SERVICE_FILE" /etc/systemd/system/
    fi
done

sudo systemctl daemon-reload

# Enable and start each app
for APP in $(ls /home/dhughes/apps/); do
    if [ -f "/etc/systemd/system/$APP.service" ]; then
        sudo systemctl enable "$APP"
        sudo systemctl start "$APP"
    fi
done
```

#### Step 9 — Deploy Caddy + auth

```bash
cd /home/dhughes/infrastructure
sudo ./deploy.sh
```

This regenerates `/etc/caddy/Caddyfile` from the per-app `caddy-subdomain.conf` files, restarts Caddy, and restarts doughughes-net.

#### Step 10 — Restore root crontab + cron jobs

Cron jobs in `/etc/cron.d/` were already restored in Step 5. For root's user crontab (if any):

```bash
sudo crontab /tmp/restore/var/lib/backup-staging/metadata/crontab-root.txt
crontab /tmp/restore/var/lib/backup-staging/metadata/crontab-dhughes.txt  # as dhughes
```

#### Step 11 — Bring back OSM data (color-the-map)

This is the slow part. Two paths — pick one based on urgency.

**Quick path: app serves traffic immediately, replication broken until full path runs.** ~1-3 hours.

```bash
sudo -u postgres pg_restore --dbname=color-the-map \
    /tmp/restore/var/lib/backup-staging/osm/osm-tables.dump
```

That's it. CTM is now serving traffic with OSM data current as of the last backup. The `osm` schema is populated but `osm2pgsql-replication` won't work because the middle tables and `flat-nodes.bin` don't exist yet. **OSM data will go stale until you run the full path.**

**Full path: replication working again.** ~6-10 hours.

If the quick path was already run, drop the partially-populated osm schema first:

```bash
sudo -u postgres psql -d color-the-map -c "DROP SCHEMA osm CASCADE"
```

Then run osm2pgsql against the bootstrap PBF:

```bash
PBF=$(ls -t /mnt/backup/osm-bootstrap/planet-filtered-*.osm.pbf | head -1)

OSM_SCHEMA=osm osm2pgsql \
    --slim --flat-nodes=/home/dhughes/flat-nodes.bin \
    --middle-schema=osm \
    -d color-the-map \
    -O flex \
    -S /home/dhughes/apps/color-the-map/scripts/osm/osm2pgsql-flex.lua \
    "$PBF"
```

After import: set the replication sequence to the saved value so we resume from the backup point (rather than the PBF's age):

```bash
# Inspect the saved properties
cat /tmp/restore/var/lib/backup-staging/osm/osm2pgsql_properties.csv

# Apply the relevant property values to the freshly-imported osm schema
# (column names may vary — see the CSV header)
```

Then run incremental replication to catch up to upstream OSM:

```bash
/home/dhughes/apps/color-the-map/scripts/osm/osm-update.sh
```

Could take minutes (recent PBF) to hours (very stale PBF).

Detailed OSM restore procedure with exact commands and edge cases lives in `color-the-map/docs/backup-and-restore.md`.

#### Step 12 — Verify everything

```bash
# Services
systemctl status caddy
systemctl status doughughes-net
systemctl status color-the-map
systemctl status home-inventory  # etc., one per app

# DNS / external
curl ifconfig.me
dig doughughes.net
ssh dhughes@ssh.doughughes.net  # from another machine

# Per-app smoke tests
curl -k https://doughughes.net  # should serve homepage
# ... log in to color-the-map, confirm tracks render
```

## OSM-specific notes

OSM gets two artifacts in the backup:

1. **`osm-tables.dump`** in restic — the app-facing tables (highways, admin_boundaries, exclusion_areas) excluding osm2pgsql middle tables. ~50 GB compressed. Used by the **quick** restore path.
2. **`/mnt/backup/osm-bootstrap/planet-filtered-*.osm.pbf`** — outside the restic repo, manually refreshed quarterly. ~25 GB. Used by the **full** restore path to regenerate everything (middle tables, `flat-nodes.bin`).

If the bootstrap PBF is missing or very stale, you'll need to regenerate it from upstream OpenStreetMap. Procedure:

```bash
cd /tmp
wget -O planet-latest.osm.pbf https://planet.openstreetmap.org/pbf/planet-latest.osm.pbf
# ~91 GB; ~12+ hours over a home connection

osmium tags-filter planet-latest.osm.pbf \
    w/highway r/boundary=administrative \
    a/leisure=golf_course a/leisure=stadium a/leisure=water_park \
    a/landuse=military a/landuse=quarry a/landuse=landfill a/landuse=railway \
    a/military a/amenity=prison a/aeroway=aerodrome a/power=plant \
    a/tourism=theme_park a/tourism=zoo \
    -o /mnt/backup/osm-bootstrap/planet-filtered-$(date +%F).osm.pbf

rm planet-latest.osm.pbf
```

The filter must match `color-the-map/CLAUDE.md` "OSM Data" section.

## Where to find more detail

If you have working internet but the box is rebuilt:

- **CTM-specific OSM details** — `color-the-map/docs/backup-and-restore.md`
- **Operational reference for the backup pipeline** — `home-server-infrastructure/backup/README.md`
- **Server rebuild guide (the deeper one)** — `home-server-infrastructure/README.md`

If you're stuck and remembering this from cold storage:

- The restic repo at `/mnt/backup/restic-repo/` is the source of truth for everything we backed up.
- `restic mount` lets you browse any snapshot as a regular filesystem.
- `cat /mnt/backup/last-backup-timestamp` tells you when the most recent successful backup was.
- The credential to unlock everything is in 1Password.
