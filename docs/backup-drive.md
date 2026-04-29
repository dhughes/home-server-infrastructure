# Backup Drive (LUKS-encrypted external SSD)

The server has an external SSD attached for local backups. This doc covers
what's on it, how it's wired up, where the secrets live, and how to
reproduce the setup if the drive (or the whole server) needs to be rebuilt.

## At-a-glance

| | |
|---|---|
| Hardware | SanDisk Extreme Portable SSD (model "Extreme 55DD"), 1 TB, USB-C |
| Connection | Plugged directly into one of the MacBook Pro's USB-C ports |
| Encryption | LUKS2 / AES-XTS / argon2id |
| Filesystem | ext4 inside the LUKS volume |
| Mount point | `/mnt/backup`, owned `dhughes:dhughes`, mode `0750` |
| Auto-unlock | Yes — keyfile in `/root/`, wired through `/etc/crypttab` |
| Auto-mount | Yes — `/etc/fstab` with `nofail` so a missing drive won't block boot |

## Layout

```
/dev/sda                    SanDisk Extreme 55DD (931.5 GiB)
└── /dev/sda1               GPT partition spanning the whole disk (Linux LUKS GUID)
    └── /dev/mapper/backup  LUKS2 volume (auto-unlocked at boot)
        └── ext4 fs         labelled "backup", mounted at /mnt/backup
```

## Secrets — where things live

The LUKS volume has **two keyslots** so it can be unlocked two ways:

| Slot | Secret | Stored where | Purpose |
|---|---|---|---|
| 0 | Passphrase | 1Password item **`Sandisk Backup SSD LUKS passphrase`** | Recovery only — used if the keyfile is lost or corrupted |
| 1 | Random keyfile (`/root/backup-disk.key`, mode 0400, root-owned) | The server itself | Daily-driver — `crypttab` reads this at boot to auto-unlock |

The keyfile lives on the server's own root filesystem. **If the server is destroyed, the keyfile is gone with it** — recovery from the backup drive in that case requires the 1Password passphrase. Keep it somewhere durable (1Password is fine; a printed copy in a safe is better).

## Files on the server

| Path | Purpose |
|---|---|
| `/dev/sda1` | LUKS2 container |
| `/dev/mapper/backup` | Decrypted block device exposing ext4 |
| `/mnt/backup` | Mount point (owner: `dhughes:dhughes`, mode 0750) |
| `/root/backup-disk.key` | Keyfile read by crypttab; mode 0400, root-owned |
| `/etc/crypttab` | Has line: `backup UUID=<luks-uuid> /root/backup-disk.key luks,nofail` |
| `/etc/fstab` | Has line: `UUID=<ext4-uuid> /mnt/backup ext4 defaults,nofail 0 2` |

The actual UUIDs are populated by the setup script and printed at the end of its run. Look them up live with:

```bash
sudo blkid /dev/sda1                 # LUKS UUID (matches /etc/crypttab)
sudo blkid /dev/mapper/backup        # ext4 UUID (matches /etc/fstab)
```

## Initial setup

The server is a **2019 16" MacBook Pro (`MacBookPro16,1`) with a T2 chip**, running the t2linux Ubuntu kernel. Direct USB-C external storage **does not work** without a kernel parameter override — the JHL7540 Thunderbolt controllers fail to tunnel USB devices to the host. Symptom: plug in any USB-C drive, get zero kernel events, drive does not appear in `lsblk`. This is a known T2-Linux issue documented on the [t2linux wiki](https://wiki.t2linux.org/state/).

**Required GRUB parameter:** `pcie_ports=native`

Edit `/etc/default/grub`, change:

```
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
```

to:

```
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash pcie_ports=native"
```

Then:

```bash
sudo update-grub
sudo systemctl reboot -ff   # NOT `sudo reboot` — see CLAUDE.md "Hardware quirks"
```

After this, plugging a USB-C drive into the MacBook Pro produces normal kernel attach events and `lsblk` shows the device. **This is mandatory for any external USB-C storage on this server**, not just the backup drive.

> Boot logs may still show `thunderbolt: device links to tunneled native ports are missing!` even with `pcie_ports=native`. The parameter changes underlying PCIe handling so storage works; the warning persists harmlessly.

### Required packages

```bash
sudo apt install -y cryptsetup
```

(`gdisk`, `parted`, `wipefs`, `mkfs.ext4` come stock on Ubuntu Server.)

### Format / encrypt / mount

The setup script lives at the path you ran it from when you first set the drive up — it isn't checked into this repo because it's destructive and meant to run once. The canonical procedure is captured below; reproduce it as a script if needed.

```bash
# Sanity-check the device is the SanDisk and is empty
lsblk -o NAME,SIZE,TYPE,MODEL /dev/sda
sudo wipefs -a /dev/sda
sudo sgdisk --zap-all /dev/sda

# One GPT partition spanning the whole disk, Linux LUKS partition type
sudo sgdisk --new=1:0:0 --typecode=1:8309 --change-name=1:backup-luks /dev/sda
sudo partprobe /dev/sda

# LUKS2 format with a passphrase (slot 0)
sudo cryptsetup luksFormat --type luks2 --pbkdf argon2id /dev/sda1
sudo cryptsetup open /dev/sda1 backup

# Generate a keyfile and add it as slot 1 for crypttab auto-unlock
sudo dd if=/dev/random of=/root/backup-disk.key bs=512 count=8 status=none
sudo chmod 0400 /root/backup-disk.key
sudo chown root:root /root/backup-disk.key
sudo cryptsetup luksAddKey /dev/sda1 /root/backup-disk.key   # asks for the passphrase set above

# ext4 inside the unlocked LUKS volume
sudo mkfs.ext4 -L backup -m 1 /dev/mapper/backup

# crypttab + fstab
LUKS_UUID=$(sudo blkid -s UUID -o value /dev/sda1)
EXT4_UUID=$(sudo blkid -s UUID -o value /dev/mapper/backup)
echo "backup UUID=${LUKS_UUID} /root/backup-disk.key luks,nofail" | sudo tee -a /etc/crypttab
echo "UUID=${EXT4_UUID} /mnt/backup ext4 defaults,nofail 0 2"     | sudo tee -a /etc/fstab

sudo mkdir -p /mnt/backup
sudo cryptsetup close backup
sudo systemctl daemon-reload
sudo systemctl start systemd-cryptsetup@backup.service
sudo mount /mnt/backup
sudo chown dhughes:dhughes /mnt/backup
sudo chmod 0750 /mnt/backup
```

Reboot once afterwards to confirm crypttab + fstab auto-unlock and auto-mount work end-to-end. If `df -h /mnt/backup` shows the drive after reboot without any manual intervention, you're done.

## Recovery scenarios

### Lost or corrupt keyfile

The drive can still be unlocked with the passphrase stored in 1Password (item: **`Sandisk Backup SSD LUKS passphrase`**).

```bash
# Manually open with passphrase
sudo cryptsetup open /dev/sda1 backup       # type passphrase when prompted
sudo mount /mnt/backup
```

To restore the keyfile so auto-unlock works again:

```bash
sudo dd if=/dev/random of=/root/backup-disk.key bs=512 count=8 status=none
sudo chmod 0400 /root/backup-disk.key
sudo chown root:root /root/backup-disk.key
# remove the old broken keyslot, add the new one
sudo cryptsetup luksKillSlot /dev/sda1 1     # kills old keyfile slot
sudo cryptsetup luksAddKey /dev/sda1 /root/backup-disk.key   # adds new one
```

### Lost the passphrase

The keyfile in `/root/` still works as long as the server is alive. Set a new passphrase by adding it to a free slot:

```bash
sudo cryptsetup luksAddKey --key-file /root/backup-disk.key /dev/sda1
```

Update the 1Password entry with the new passphrase.

### Server is destroyed (drive survives)

The keyfile is gone, but the passphrase from 1Password still unlocks the drive on any other Linux box:

```bash
sudo cryptsetup open /dev/sda1 backup       # passphrase
sudo mkdir -p /mnt/backup
sudo mount /dev/mapper/backup /mnt/backup
```

### Drive is destroyed

Backup contents are lost from this drive. Anything important should also exist offsite — see issue #487 in the `color-the-map` repo for the broader backup strategy.

## Operational notes

### Verify the drive is mounted

```bash
df -h /mnt/backup
findmnt /mnt/backup
lsblk /dev/sda
```

### Safely unplug

Backups should not be running. Then:

```bash
sudo umount /mnt/backup
sudo cryptsetup close backup
# now physically unplug
```

Re-plugging will not auto-mount mid-uptime; either run the steps above in reverse, or `sudo systemctl start systemd-cryptsetup@backup.service && sudo mount /mnt/backup`. A reboot (`sudo systemctl reboot -ff`) is the cleanest "make it active again" path.

### Forgetting to plug it back in

`nofail` on both crypttab and fstab means the server boots normally without the drive. Backup jobs that target `/mnt/backup` will see a non-existent mount and (depending on tool) either fail loudly or silently write to the underlying root filesystem, which is bad. Backup tooling should verify the mount is alive before writing — typically by checking that `/mnt/backup/.mounted` exists (a sentinel file) or by calling `mountpoint -q /mnt/backup`.

### Future work / open from issue #487

This setup gives encryption-at-rest for the drive and protects it if it walks off the desk. Still missing:

- **Backup job itself** — what runs, what gets backed up, schedule, retention
- **Backup contents encrypted at rest** (e.g. gpg-encrypted dumps) so the contents are protected even when the drive is unlocked
- **Offsite copy** — fire/theft/surge takes both the server and the SSD if they're sitting next to each other
- **Restore testing** — periodic dry-runs to a sandbox to verify backups are usable
- **Failure monitoring** — alert if a backup hasn't run successfully in N hours

Track in the `color-the-map` repo, issue #487.
