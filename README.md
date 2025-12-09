# Server Rebuild Guide

This document describes how to rebuild the doughughes.net server from scratch if the hardware dies or needs to be replaced.

## Overview

This is a self-hosted web server running on commodity hardware (originally an Intel MacBook Pro). It serves personal web apps behind a reverse proxy with authentication.

**Key decisions made:**
- Ubuntu LTS as the OS
- Cloudflare for DNS (free tier) - handles SSL termination option and provides DDNS API
- Caddy as reverse proxy - automatic HTTPS, simple config, Caddyfile auto-generated from app configs
- Custom auth service - session-based login, user management, dynamic app index
- Systemd for service management
- UFW for firewall
- App configuration via `app.json` files - apps self-describe their routes, ports, and visibility

## Hardware Requirements

- Any x86_64 machine with 4GB+ RAM
- Wired or WiFi network connection
- Ability to run with lid closed (if laptop)

## Step 1: Install Ubuntu

1. Download Ubuntu Server or Desktop LTS
2. Install with default options
3. Create user `dhughes` (or your preferred username - update paths in this guide accordingly)
4. Enable SSH during install, or install after: `sudo apt install openssh-server`

## Step 2: Basic System Configuration

### SSH Key Authentication

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
# Add your public key to ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Lid Close Behavior (laptops only)

Edit `/etc/systemd/logind.conf`:
```
HandleLidSwitch=ignore
```

Then: `sudo systemctl restart systemd-logind`

### Keyboard (Mac keyboards only)

If using Mac hardware with keyd for Cmd/Ctrl swap:
```bash
sudo apt install keyd
```

Create `/etc/keyd/default.conf`:
```ini
[ids]
*

[main]
leftmeta = leftcontrol
leftcontrol = leftmeta
rightmeta = rightcontrol
rightcontrol = rightmeta
```

Then: `sudo systemctl enable keyd && sudo systemctl start keyd`

## Step 3: Network and DNS

### Static IP (Router)

Assign a static IP to this machine in your router's DHCP settings using the MAC address.

### Port Forwarding (Router)

Forward these ports from your router to the server:
- 22 (SSH)
- 80 (HTTP)
- 443 (HTTPS)

If behind double NAT, use IP passthrough/DMZ on the outer router.

### Cloudflare DNS

1. Create free Cloudflare account
2. Add your domain
3. Update nameservers at your registrar to Cloudflare's
4. Create A records:
   - `@` (root) → your public IP (proxied - orange cloud)
   - `www` → your public IP (proxied - orange cloud)
   - `ssh` → your public IP (DNS only - grey cloud)

### Dynamic DNS (ddclient)

```bash
sudo apt install ddclient
```

During install, select "other" for provider and enter placeholder values.

Edit `/etc/ddclient.conf`:
```
daemon=600
syslog=yes
pid=/var/run/ddclient/ddclient.pid
ssl=yes

use=web, web=ifconfig.me

protocol=cloudflare
zone=doughughes.net
login=token
password='YOUR_CLOUDFLARE_API_TOKEN'
doughughes.net,ssh.doughughes.net
```

Get API token from Cloudflare: Profile → API Tokens → Create Token → "Edit zone DNS" template

```bash
sudo systemctl enable ddclient
sudo systemctl start ddclient
```

## Step 4: Firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

## Step 5: Clone Infrastructure Repo

```bash
cd ~
git clone <your-infrastructure-repo-url> infrastructure
```

## Step 6: Install Caddy

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

## Step 7: Install Auth Service

```bash
sudo ln -s ~/infrastructure/services/auth/auth.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable auth
sudo systemctl start auth
```

Default login: `admin` / `changeme` (change immediately after first login!)

## Step 8: Configure Passwordless Sudo

### Infrastructure Deploy Script

```bash
echo 'dhughes ALL=(ALL) NOPASSWD: /home/dhughes/infrastructure/deploy.sh' | sudo tee /etc/sudoers.d/infrastructure
sudo chmod 0440 /etc/sudoers.d/infrastructure
```

### App Service Restarts

Allow passwordless restart/status for app services (needed for app deploy scripts):

```bash
echo "dhughes ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart home-inventory, /usr/bin/systemctl restart random-word, /usr/bin/systemctl restart lottery-numbers, /usr/bin/systemctl status home-inventory, /usr/bin/systemctl status random-word, /usr/bin/systemctl status lottery-numbers" | sudo tee /etc/sudoers.d/app-services
sudo chmod 0440 /etc/sudoers.d/app-services
```

**Note:** Sudoers doesn't support wildcards in command arguments, so each service must be listed explicitly. When adding a new app, update this file with the new service name.

## Step 9: Clone and Install Apps

For each app:

```bash
mkdir -p ~/apps
cd ~/apps
git clone <app-repo-url> <app-name>
cd <app-name>

# Build if needed (Go apps)
go build -o <app-name> .

# Install service
sudo ln -s ~/apps/<app-name>/<app-name>.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable <app-name>
sudo systemctl start <app-name>
```

Each app should have:
- **app.json** - Configuration file describing the app (see App Configuration below)
- **<app-name>.service** - Systemd service file
- App code and any images referenced in app.json

## Step 10: Deploy Everything

```bash
cd ~/infrastructure
sudo ./deploy.sh
```

This will:
1. Read all `~/apps/*/app.json` files
2. Generate Caddyfile with routes for all apps
3. Copy Caddyfile to `/etc/caddy/` and restart Caddy
4. Restart the auth service

## Step 11: Verify Everything

```bash
# Check services
systemctl status caddy
systemctl status auth
systemctl status ddclient
systemctl status <app-name>

# Check firewall
sudo ufw status

# Check DNS
dig doughughes.net
dig ssh.doughughes.net

# Test external access
curl https://doughughes.net
ssh dhughes@ssh.doughughes.net
```

## App Configuration

Each app in `~/apps/<app-name>/` needs an `app.json` file:

```json
{
  "name": "My App",
  "path": "/my-app",
  "port": 8003,
  "public": false,
  "icon": "🚀",
  "image": "logo.png",
  "description": "Short description of the app"
}
```

**Fields:**
- `name` - Display name on the index page
- `path` - URL path (e.g., `/my-app` → `https://doughughes.net/my-app`)
- `port` - Local port the app listens on (use 8001+ to avoid conflicts)
- `public` - `true` = visible to everyone, `false` = requires login
- `icon` - Emoji fallback if no image is provided
- `image` - Filename of image in app directory (e.g., `"logo.png"`), or `null` for icon-only
- `description` - Short description shown on the app card

**How it works:**
- `generate-caddyfile.py` reads all app.json files and creates Caddy routes
- The auth service reads app.json files to build the index page with app cards
- Private apps (`"public": false`) require login to access and only appear on the index when logged in

## Architecture Decisions

### Why Cloudflare?
- Free tier is sufficient
- Handles SSL between user and Cloudflare
- Provides API for dynamic DNS updates
- Protects real IP (proxied records)
- Alternative considered: Let's Encrypt directly (more config)

### Why Caddy?
- Automatic HTTPS with Let's Encrypt
- Simple configuration syntax
- Built-in reverse proxy
- `forward_auth` for authentication
- Alternative considered: Nginx (more complex config)

### Why auto-generated Caddyfile?
- Apps are self-describing via app.json
- No need to manually edit Caddy config when adding apps
- Single source of truth for app configuration
- Deploy script regenerates Caddyfile from app.json files

### Why custom auth instead of Authelia?
- Simpler for single-user/small setup
- Full control over behavior
- No Docker dependency
- Serves the dynamic index page with app cards
- Authelia is better for multi-app SSO at scale

### Why systemd services?
- Built into Ubuntu
- Automatic restart on failure
- Starts on boot
- Easy logging via journalctl
- Alternative considered: Docker (more overhead for simple apps)

### Why UFW?
- Simple frontend to iptables
- Default deny is secure
- Easy to add/remove rules
- Built into Ubuntu

## Directory Structure

```
~/infrastructure/           # This repo
├── CLAUDE.md              # Documentation for Claude Code
├── README.md              # This file (rebuild guide)
├── deploy.sh              # Deployment script (passwordless sudo)
├── generate-caddyfile.py  # Generates Caddyfile from app.json files
├── caddy/
│   └── Caddyfile          # Auto-generated, don't edit manually
└── services/
    └── auth/
        ├── app.py         # Auth service + index page
        ├── auth.service   # Systemd service file
        ├── users.json     # User credentials (not in git)
        └── sessions.json  # Active sessions (not in git)

~/apps/                    # Separate git repo per app
├── <app-name>/
│   ├── app.json           # App configuration
│   ├── <app-name>.service # Systemd service file
│   ├── logo.png           # Optional app image
│   └── ... (app code)
```

## Backup Considerations

**What to back up:**
- `~/infrastructure/` (git repo, push to remote)
- `~/apps/*/` (git repos, push to remotes)
- `~/infrastructure/services/auth/users.json` (user credentials - NOT in git)
- `/etc/ddclient.conf` (contains API token)

**What doesn't need backup:**
- Session files (users just re-login)
- SSL certificates (Caddy regenerates them)
- Generated Caddyfile (regenerated from app.json on deploy)
- System packages (reinstall from apt)

## Troubleshooting

### Can't access site externally
1. Check public IP: `curl ifconfig.me`
2. Check Cloudflare DNS points to that IP
3. Check port forwarding on router
4. Check firewall: `sudo ufw status`
5. Check Caddy: `systemctl status caddy`

### SSL certificate errors
1. Caddy handles this automatically
2. Check Caddy logs: `journalctl -u caddy -f`
3. Ensure ports 80 and 443 are open and forwarded

### Dynamic DNS not updating
1. Check ddclient: `systemctl status ddclient`
2. Force update: `sudo ddclient -force -verbose`
3. Verify API token is valid in Cloudflare

### Auth not working
1. Check service: `systemctl status auth`
2. Check logs: `journalctl -u auth -f`
3. Clear browser cookies and retry

### App not showing on index page
1. Verify `~/apps/<app>/app.json` exists and is valid JSON
2. Redeploy: `sudo ~/infrastructure/deploy.sh`
3. Check auth logs: `journalctl -u auth -f`

### App not accessible via URL
1. Check app service is running: `systemctl status <app-name>`
2. Redeploy to regenerate Caddyfile: `sudo ~/infrastructure/deploy.sh`
3. Check Caddy logs: `journalctl -u caddy -f`
