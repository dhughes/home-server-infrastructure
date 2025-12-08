# Server Rebuild Guide

This document describes how to rebuild the doughughes.net server from scratch if the hardware dies or needs to be replaced.

## Overview

This is a self-hosted web server running on commodity hardware (originally an Intel MacBook Pro). It serves personal web apps behind a reverse proxy with authentication.

**Key decisions made:**
- Ubuntu LTS as the OS
- Cloudflare for DNS (free tier) - handles SSL termination option and provides DDNS API
- Caddy as reverse proxy - automatic HTTPS, simple config
- Custom auth service - session-based login, user management
- Systemd for service management
- UFW for firewall

## Hardware Requirements

- Any x86_64 machine with 4GB+ RAM
- Wired or WiFi network connection
- Ability to run with lid closed (if laptop)

## Step 1: Install Ubuntu

1. Download Ubuntu Server or Desktop LTS
2. Install with default options
3. Create user `dhughes` (or your preferred username)
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

Copy config:
```bash
sudo cp ~/infrastructure/caddy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl restart caddy
```

## Step 7: Install Auth Service

```bash
sudo ln -s ~/infrastructure/services/auth/auth.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable auth
sudo systemctl start auth
```

Default login: `admin` / `changeme` (change immediately!)

## Step 8: Configure Passwordless Deploy

```bash
echo 'dhughes ALL=(ALL) NOPASSWD: /home/dhughes/infrastructure/deploy.sh' | sudo tee /etc/sudoers.d/infrastructure
sudo chmod 440 /etc/sudoers.d/infrastructure
```

Test: `sudo ~/infrastructure/deploy.sh`

## Step 9: Clone and Install Apps

For each app in `~/apps/`:

```bash
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

## Step 10: Verify Everything

```bash
# Check services
systemctl status caddy
systemctl status auth
systemctl status ddclient

# Check firewall
sudo ufw status

# Check DNS
dig doughughes.net
dig ssh.doughughes.net

# Test external access
curl https://doughughes.net
ssh dhughes@ssh.doughughes.net
```

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

### Why custom auth instead of Authelia?
- Simpler for single-user/small setup
- Full control over behavior
- No Docker dependency
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

## Backup Considerations

**What to back up:**
- `~/infrastructure/` (git repo)
- `~/apps/*/` (git repos)
- `~/infrastructure/services/auth/users.json` (user credentials - NOT in git)
- `/etc/ddclient.conf` (contains API token)

**What doesn't need backup:**
- Session files (users just re-login)
- SSL certificates (Caddy regenerates them)
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
3. Verify Caddy config has `forward_auth` blocks
