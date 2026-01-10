# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Deploy everything (caddy config + all services)
sudo ./deploy.sh

# Deploy specific components
sudo ./deploy.sh caddy     # Deploy Caddy config only
sudo ./deploy.sh auth      # Restart doughughes-net service only
sudo ./deploy.sh services  # Restart all services (not Caddy)

# Service management
systemctl status caddy|doughughes-net|random-word  # Check status
journalctl -u <service> -f                          # View logs
sudo systemctl restart <service>                    # Restart a single service
```

## When to Deploy

| What Changed | What to Run |
|--------------|-------------|
| Added/removed an app | `sudo ./deploy.sh` (restarts Caddy + services) |
| Changed an app's `caddy.conf` or `caddy-subdomain.conf` | `sudo ./deploy.sh caddy` |
| Changed app.json (display only) | `sudo ./deploy.sh auth` (restarts doughughes-net) |
| Changed doughughes-net code | `sudo ./deploy.sh auth` (restarts doughughes-net) |
| Changed an app's code | `sudo systemctl restart <app-name>` |

## Architecture

```
Internet → Cloudflare (DNS/SSL) → Router → Caddy (reverse proxy) → Apps
                                              ↓
                                    doughughes-net app (homepage + forward_auth)
```

**This repo (`~/infrastructure/`):**
- `caddy/Caddyfile` - Reverse proxy config with import directives
- `deploy.sh` - Deployment script (runs with passwordless sudo)

**Apps (`~/apps/`)** - Separate git repos, each with:
- `caddy-subdomain.conf` - Subdomain routing (e.g., `app-name.doughughes.net`)
- `caddy.conf` - Path-based routing (legacy, optional, e.g., `/app-name`)
- `app.json` - Display metadata (name, icon, image, description)
- `<app-name>.service` - Systemd service file

**Special app - doughughes-net:**
- Homepage served at root domains (`doughughes.net`, `www.doughughes.net`)
- Provides authentication via forward_auth for private apps
- Runs on port 8000

**Port assignments:** 8000=doughughes-net, 8001+=apps (check existing caddy-subdomain.conf files for used ports)

## Adding a New App

**Use the app template at `/Users/doughughes/Projects/Personal/app-template`.**

See that project's `CLAUDE.md` for detailed instructions on creating a new app.

**Quick summary:**
1. The template copies a complete app skeleton with all required files
2. Claude will ask you for: name, slug, description, icon, port, public/private
3. All files get automatically updated with your values
4. Result is a ready-to-deploy app in `~/apps/<slug>/`

**After creating the app:**
```bash
cd ~/infrastructure
sudo ./deploy.sh
```

This will:
1. Import your app's `caddy-subdomain.conf` and/or `caddy.conf` into the main Caddyfile
2. Restart Caddy with the new routing
3. Restart the doughughes-net service to show your app on the index page

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

### doughughes-net Homepage/Auth App (port 8000)

Serves the homepage and handles authentication for private apps.

- **Location**: `~/apps/doughughes-net/` (standalone app, separate git repo)
- **Served at**: `doughughes.net` and `www.doughughes.net`
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
- Shows app cards with links (prefers subdomain URLs when available)
- Logged out: Shows only public apps
- Logged in: Shows all apps (public + private with lock icons)

### Caddy (ports 80, 443)

Reverse proxy with automatic HTTPS.

- **Config source**: `~/infrastructure/caddy/Caddyfile`
- **Active config**: `/etc/caddy/Caddyfile` (copied by deploy.sh)

**How it works:**
- Imports all `~/apps/*/caddy-subdomain.conf` for subdomain routing (at top level)
- Imports all `~/apps/*/caddy.conf` for path-based routing (within main site block)
- The doughughes-net app provides the catch-all handler for root domains

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
| 8000 | doughughes-net | No (internal) |
| 8001+ | Apps | No (internal) |

Check existing `~/apps/*/caddy-subdomain.conf` files for used ports before assigning a new one.

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
systemctl status doughughes-net
systemctl status <app-name>
```

### View logs
```bash
journalctl -u caddy -f
journalctl -u doughughes-net -f
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
2. Restart doughughes-net: `sudo ./deploy.sh auth`
3. Check doughughes-net logs: `journalctl -u doughughes-net -f`

### App not accessible via URL
1. Check the app service is running: `systemctl status <app-name>`
2. Check app has `caddy-subdomain.conf` (for subdomain) or `caddy.conf` (for path)
3. Redeploy Caddy config: `sudo ./deploy.sh caddy`
4. Check Caddy logs: `journalctl -u caddy -f`

### Private app accessible without login
1. Verify `forward_auth` block exists in app's `caddy-subdomain.conf` or `caddy.conf`
2. Redeploy: `sudo ./deploy.sh`

### Authentication not working
1. Check doughughes-net service: `systemctl status doughughes-net`
2. Check browser cookies (clear and retry)
3. Check doughughes-net logs: `journalctl -u doughughes-net -f`

## Files NOT in Git

The doughughes-net app contains sensitive data files (in its own `.gitignore`):
- `~/apps/doughughes-net/users.json` - User credentials
- `~/apps/doughughes-net/sessions.json` - Active sessions

If setting up on a new machine, the doughughes-net app will create a default admin user on first run (admin/changeme).
