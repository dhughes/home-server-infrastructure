# Infrastructure Documentation

This repository contains the infrastructure for doughughes.net - a self-hosted web server running on an Intel MacBook Pro with Ubuntu 25.10.

## Overview

```
~/infrastructure/          <- this repo (infrastructure config)
  caddy/Caddyfile          <- reverse proxy config
  services/auth/           <- authentication service
  scripts/                 <- utility scripts (ddns, etc.)
  deploy.sh                <- deployment script

~/apps/                    <- separate git repos for each app
  random-word/             <- Python app (port 8001, requires auth)
  lottery-numbers/         <- Go app (port 8002, public)
```

## Architecture

```
Internet → Cloudflare (DNS/SSL) → Router (port forward) → Caddy (reverse proxy) → Apps
```

- **Domain**: doughughes.net (DNS managed by Cloudflare)
- **SSL**: Automatic via Caddy + Let's Encrypt
- **Dynamic DNS**: ddclient updates Cloudflare when IP changes
- **SSH**: ssh.doughughes.net (DNS-only, not proxied through Cloudflare)

## Adding a New App

### 1. Create the app

```bash
mkdir ~/apps/my-new-app
cd ~/apps/my-new-app
git init
# ... create your app, listening on a port (e.g., 8003)
```

### 2. Create a systemd service

Create `~/apps/my-new-app/my-new-app.service`:
```ini
[Unit]
Description=My New App
After=network.target

[Service]
Type=simple
User=dhughes
WorkingDirectory=/home/dhughes/apps/my-new-app
ExecStart=/path/to/executable
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Install and start:
```bash
sudo ln -s /home/dhughes/apps/my-new-app/my-new-app.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable my-new-app
sudo systemctl start my-new-app
```

### 3. Add route to Caddy

Edit `~/infrastructure/caddy/Caddyfile`:

**For a public app:**
```caddy
handle /my-new-app* {
    reverse_proxy localhost:8003
}
```

**For a protected app (requires login):**
```caddy
handle /my-new-app* {
    forward_auth localhost:8000 {
        uri /verify
    }
    reverse_proxy localhost:8003
}
```

### 4. Update the index page

Edit `~/infrastructure/services/auth/app.py` - find the `index_page` method and add your app to the list:

```python
# In the index_page method, add to the HTML:
<li><a href="/my-new-app">My New App</a></li>

# For protected apps, wrap in the `if user:` block
```

### 5. Deploy

```bash
cd ~/infrastructure
sudo ./deploy.sh
```

## Services

### Auth Service (port 8000)

Handles authentication for the entire site.

- **Location**: `~/infrastructure/services/auth/`
- **Default login**: admin / changeme (CHANGE THIS)
- **Data files** (not in git):
  - `users.json` - usernames, hashed passwords, roles
  - `sessions.json` - active sessions

**Endpoints:**
- `/` - Index page (shows apps, different view when logged in)
- `/login` - Login form
- `/logout` - Clear session
- `/verify` - Caddy forward_auth endpoint (returns 200 if logged in, 401 if not)
- `/account` - Change password (requires login)
- `/admin/users` - User management (admin only)

### Caddy (ports 80, 443)

Reverse proxy with automatic HTTPS.

- **Config**: `~/infrastructure/caddy/Caddyfile`
- **Active config**: `/etc/caddy/Caddyfile` (copied by deploy.sh)

### ddclient

Updates Cloudflare DNS when public IP changes.

- **Config**: `/etc/ddclient.conf`
- **Updates**: doughughes.net, ssh.doughughes.net

## Deployment

The `deploy.sh` script handles deployment and can run with passwordless sudo.

```bash
# Deploy everything
sudo ./deploy.sh

# Deploy only Caddy config
sudo ./deploy.sh caddy

# Deploy only auth service
sudo ./deploy.sh auth

# Deploy all services
sudo ./deploy.sh services
```

## Port Assignments

| Port | Service | Public |
|------|---------|--------|
| 22 | SSH | Yes (via ssh.doughughes.net) |
| 80 | Caddy (HTTP → HTTPS redirect) | Yes |
| 443 | Caddy (HTTPS) | Yes |
| 8000 | Auth service | No (internal) |
| 8001 | random-word app | No (internal) |
| 8002 | lottery-numbers app | No (internal) |

When adding new apps, use ports 8003+.

## Firewall (ufw)

```bash
sudo ufw status          # View rules
sudo ufw allow 8003      # Open a port (if needed externally)
sudo ufw delete allow 8003  # Remove a rule
```

Current open ports: 22, 80, 443

## Common Tasks

### Check service status
```bash
systemctl status caddy
systemctl status auth
systemctl status random-word
```

### View logs
```bash
journalctl -u caddy -f
journalctl -u auth -f
```

### Restart a service
```bash
sudo systemctl restart caddy
sudo systemctl restart auth
```

### Check public IP
```bash
curl ifconfig.me
```

### Force DNS update
```bash
sudo ddclient -force
```

## Troubleshooting

### App not accessible
1. Check the service is running: `systemctl status <service>`
2. Check Caddy config has the route
3. Check firewall if accessing directly: `sudo ufw status`

### Auth not working
1. Check auth service: `systemctl status auth`
2. Check Caddy is forwarding to auth: verify `forward_auth` block in Caddyfile
3. Check browser cookies (clear and retry)

### DNS not resolving
1. Check ddclient: `systemctl status ddclient`
2. Force update: `sudo ddclient -force`
3. Check Cloudflare dashboard for correct IP

## Files NOT in Git

These files contain sensitive data and are in `.gitignore`:
- `services/auth/users.json`
- `services/auth/sessions.json`

If setting up on a new machine, the auth service will create a default admin user on first run.
