# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Deploy everything (generates Caddyfile from app configs + restarts all services)
sudo ./deploy.sh

# Deploy specific components
sudo ./deploy.sh caddy     # Regenerate Caddyfile and restart Caddy
sudo ./deploy.sh auth      # Restart auth service only
sudo ./deploy.sh services  # Restart all services (not Caddy)

# Service management
systemctl status caddy|auth|random-word  # Check status
journalctl -u <service> -f               # View logs
sudo systemctl restart <service>         # Restart a single service
```

## When to Deploy

| What Changed | What to Run |
|--------------|-------------|
| Added/removed an app | `sudo ./deploy.sh` (regenerates Caddyfile + restarts services) |
| Changed an app's `app.json` (port, path, public/private) | `sudo ./deploy.sh caddy` |
| Changed auth service code | `sudo ./deploy.sh auth` |
| Changed an app's code | `sudo systemctl restart <app-name>` |

## Architecture

```
Internet → Cloudflare (DNS/SSL) → Router → Caddy (reverse proxy) → Apps
                                              ↓
                                         Auth service (forward_auth)
```

**This repo (`~/infrastructure/`):**
- `caddy/Caddyfile` - Auto-generated from app.json files (don't edit manually)
- `generate-caddyfile.py` - Reads ~/apps/*/app.json and generates Caddyfile
- `services/auth/app.py` - Python auth service (port 8000), serves index page
- `deploy.sh` - Deployment script (runs with passwordless sudo)

**Apps (`~/apps/`)** - Separate git repos, each with its own systemd service and app.json config

**Port assignments:** 8000=auth, 8001+=apps (check existing app.json files for used ports)

## Adding a New App

### 1. Create the app directory and code

```bash
mkdir ~/apps/my-new-app
cd ~/apps/my-new-app
git init
# ... create your app, listening on a port (e.g., 8003)
```

### 2. Create app.json

Create `~/apps/my-new-app/app.json`:
```json
{
  "name": "My New App",
  "path": "/my-new-app",
  "port": 8003,
  "public": false,
  "icon": "🚀",
  "image": null,
  "description": "Short description of the app"
}
```

**Fields:**
- `name` - Display name on index page
- `path` - URL path (e.g., `/my-new-app` → `https://doughughes.net/my-new-app`)
- `port` - Local port the app listens on
- `public` - `true` = visible to everyone, `false` = requires login
- `icon` - Emoji fallback if no image
- `image` - Filename of image in app directory (e.g., `"logo.png"`), or `null`
- `description` - Short description shown on card

### 3. Create a systemd service

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

### 4. Deploy infrastructure

```bash
cd ~/infrastructure
sudo ./deploy.sh
```

This will:
1. Read all `~/apps/*/app.json` files
2. Generate a new Caddyfile with routes for all apps
3. Restart Caddy with the new config
4. Restart the auth service (which also reads app.json for the index page)

## Modifying an Existing App

### Changed the app's code
```bash
sudo systemctl restart <app-name>
```

### Changed app.json (port, path, public/private, name, description, image)
```bash
cd ~/infrastructure
sudo ./deploy.sh
```

### Changed app's image file only
No deploy needed - images are served directly from the app directory.

## Services

### Auth Service (port 8000)

Handles authentication and serves the index page with app cards.

- **Location**: `~/infrastructure/services/auth/`
- **Default login**: admin / changeme (CHANGE THIS)
- **Data files** (not in git):
  - `users.json` - usernames, hashed passwords, roles
  - `sessions.json` - active sessions

**Endpoints:**
- `/` - Index page (dynamically loads apps from ~/apps/*/app.json)
- `/login` - Login form
- `/logout` - Clear session
- `/verify` - Caddy forward_auth endpoint (returns 200 if logged in, 401 if not)
- `/account` - Change password (requires login)
- `/admin/users` - User management (admin only)
- `/app-image/<app-dir>` - Serves app images from app directories

**Index page behavior:**
- Logged out: Shows only public apps
- Logged in: Shows all apps (public + private)

### Caddy (ports 80, 443)

Reverse proxy with automatic HTTPS.

- **Config source**: `~/infrastructure/caddy/Caddyfile` (auto-generated)
- **Active config**: `/etc/caddy/Caddyfile` (copied by deploy.sh)
- **Generator**: `~/infrastructure/generate-caddyfile.py`

**Don't edit Caddyfile manually** - it gets overwritten on deploy. To change routes, modify the app's `app.json` and redeploy.

### ddclient

Updates Cloudflare DNS when public IP changes.

- **Config**: `/etc/ddclient.conf`
- **Updates**: doughughes.net, ssh.doughughes.net

## Port Assignments

| Port | Service | Public |
|------|---------|--------|
| 22 | SSH | Yes (via ssh.doughughes.net) |
| 80 | Caddy (HTTP → HTTPS redirect) | Yes |
| 443 | Caddy (HTTPS) | Yes |
| 8000 | Auth service | No (internal) |
| 8001+ | Apps | No (internal) |

Check existing `~/apps/*/app.json` files for used ports before assigning a new one.

## Firewall (ufw)

```bash
sudo ufw status          # View rules
```

Current open ports: 22, 80, 443

Apps don't need firewall rules - they're only accessible through Caddy.

## Common Tasks

### Check service status
```bash
systemctl status caddy
systemctl status auth
systemctl status <app-name>
```

### View logs
```bash
journalctl -u caddy -f
journalctl -u auth -f
journalctl -u <app-name> -f
```

### Force DNS update
```bash
sudo ddclient -force
```

### Check public IP
```bash
curl ifconfig.me
```

## Troubleshooting

### App not showing on index page
1. Check `~/apps/<app>/app.json` exists and is valid JSON
2. Restart auth: `sudo ./deploy.sh auth`
3. Check auth logs: `journalctl -u auth -f`

### App not accessible via URL
1. Check the app service is running: `systemctl status <app-name>`
2. Redeploy to regenerate Caddyfile: `sudo ./deploy.sh caddy`
3. Check Caddy logs: `journalctl -u caddy -f`

### Private app accessible without login
1. Verify `"public": false` in app.json
2. Redeploy: `sudo ./deploy.sh`

### Auth not working
1. Check auth service: `systemctl status auth`
2. Check browser cookies (clear and retry)
3. Check auth logs: `journalctl -u auth -f`

## Files NOT in Git

These files contain sensitive data and are in `.gitignore`:
- `services/auth/users.json`
- `services/auth/sessions.json`

If setting up on a new machine, the auth service will create a default admin user on first run.
