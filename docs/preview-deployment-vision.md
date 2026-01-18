# Preview Deployment System - Vision & Architecture

## Overview

Create a parallelizable "vibe coding" infrastructure that enables rapid development across multiple feature branches simultaneously, with automatic preview deployments for every pull request.

## Goals

1. **Parallel Development**: Work on multiple features using git worktrees
2. **Automatic Preview Deployments**: Every PR gets its own live preview URL
3. **CI/CD Integration**: GitHub Actions run tests, deploy on pass, cleanup on close
4. **Zero Server Setup**: New apps deploy automatically with no manual configuration
5. **Template-Based**: Easy to add to new apps via app-template
6. **Unified System**: All apps (including homepage and deploy service) use same deployment system
7. **Retrofit-Friendly**: Straightforward to add to existing apps

## Current State

**Infrastructure:**
- Caddy reverse proxy on ports 80/443
- Apps run as systemd services
- Subdomain-based routing (`app-name.doughughes.net`)
- Wildcard DNS (`*.doughughes.net`)
- doughughes-net app provides homepage with app tiles
- Apps carry their own Caddy configs (caddy.conf, caddy-subdomain.conf)
- Centralized authentication via forward_auth

**Deployment:**
- Manual `deploy-to-prod.sh` scripts per app
- SSH-based deployment
- Requires manual Caddy restarts

**Pain Points:**
- Path-based routing causes dev/prod differences
- Can't run multiple branches simultaneously
- No preview environments
- Manual deployment process

## Target Architecture

### Subdomain Naming Convention

**Production:** `{app-name}.doughughes.net`
- Example: `color-the-map.doughughes.net`

**Preview:** `pr-{number}.{app-name}.doughughes.net`
- Example: `pr-123.color-the-map.doughughes.net`
- Uses PR number (stable, short, unambiguous)

### Port Allocation Strategy

**Dynamic Allocation (First Available Port):**
- All deployments (production and preview) use dynamic port allocation
- Deploy service tracks allocations in `~/preview-deployments/ports.json`
- Each deployment gets the next available port starting at 8000
- Ports are stable (same deployment ID always gets same port)
- No manual port configuration or range planning needed
- No distinction between production and preview ports

**Port Tracking:**
```json
{
  "doughughes-net": 8000,
  "random-word": 8001,
  "lottery-numbers": 8002,
  "home-inventory": 8003,
  "cranium-charades": 8004,
  "color-the-map": 8005,
  "color-the-map-pr-123": 8006,
  "new-app": 8007,
  "new-app-pr-1": 8008
}
```

**Key Insight:** Production is just a deployment that never gets cleaned up. The deployment ID for production is just the app name (e.g., `"color-the-map"`), while previews use `"{app}-pr-{number}"` (e.g., `"color-the-map-pr-123"`). Production and preview deployments use identical logic.

### Service Management

**User Systemd (No Sudo Required):**
- All apps run as user services (`systemd --user`)
- Production: `color-the-map.service`
- Previews: `color-the-map-pr-123.service`
- Services in `~/.config/systemd/user/`
- One-time setup: `loginctl enable-linger dhughes`

**Exception:**
- Caddy remains system service (needs privileged ports 80/443)
- Passwordless sudo configured for Caddy restart only

### Deploy Service API

**New service:** `deploy.doughughes.net`
- Private, requires API key authentication
- Handles all deployment lifecycle
- No SSH required from GitHub Actions

**Endpoints:**
```
POST /api/deploy
  Input: {
    "api_key": "secret",
    "app_name": "color-the-map",
    "branch": "main" or "feature/foo",
    "pr_number": null (for production) or 123 (for preview),
    "repo_url": "https://github.com/user/color-the-map"
  }

  Actions:
  - Calculate deployment_id: "{app}" or "{app}-pr-{number}"
  - Calculate subdomain: "{app}.doughughes.net" or "pr-{number}.{app}.doughughes.net"
  - Check if deployment exists (git pull, reuse port) or clone fresh
  - Get or allocate port for this deployment_id
  - Generate user systemd service with PORT environment variable
  - Generate caddy-subdomain.conf dynamically:
      - Subdomain mapping
      - Reverse proxy to localhost:{port}
      - No authentication (apps handle their own)
  - Install/update service: systemctl --user enable/restart
  - Reload Caddy (graceful)
  - Return deployment URL

  Production: pr_number=null, subdomain={app}.doughughes.net
  Preview: pr_number=123, subdomain=pr-123.{app}.doughughes.net

  Special case - doughughes-net app:
  - When deployed to production, also generates catch-all caddy.conf
  - Catch-all routes doughughes.net/www.doughughes.net to the app
  - App displays tiles based on app.json files with showOnDoughHughesNet=true

POST /api/cleanup
  Input: {
    "api_key": "secret",
    "app_name": "color-the-map",
    "pr_number": 123
  }

  Actions:
  - Validate pr_number is provided (cannot cleanup production)
  - Stop user service
  - Remove app directory
  - Free port from allocations
  - Reload Caddy (config auto-updates via import)

GET /api/status
  Output: {
    "deployments": [
      {
        "id": "color-the-map",
        "type": "production",
        "url": "https://color-the-map.doughughes.net",
        "port": 8005,
        "status": "running"
      },
      {
        "id": "color-the-map-pr-123",
        "type": "preview",
        "pr": 123,
        "url": "https://pr-123.color-the-map.doughughes.net",
        "port": 8006,
        "status": "running"
      }
    ],
    "next_available_port": 8007
  }
```

### Caddy Dynamic Configuration

**Strategy: Graceful Reload**
- Deploy service generates `~/apps/{app}-pr-{number}/caddy-subdomain.conf`
- Main Caddyfile imports: `import /home/dhughes/apps/*/caddy-subdomain.conf`
- After config change: `sudo caddy reload --config /etc/caddy/Caddyfile`
- Zero connection drops (graceful reload)

**Alternative (Future):**
- Upgrade to Caddy JSON API for zero-touch updates
- Only if graceful reload becomes bottleneck

### GitHub Actions Workflow

**On PR Open/Update:**
```
1. Run tests, linters, type checks
2. If pass: POST to deploy.doughughes.net/api/deploy
   - app_name: from repo
   - branch: PR branch
   - pr_number: PR number
3. Comment on PR with preview URL: pr-{number}.{app}.doughughes.net
```

**On Push to Main (merge or direct push):**
```
1. Run tests, linters, type checks
2. If pass: POST to deploy.doughughes.net/api/deploy
   - app_name: from repo
   - branch: "main"
   - pr_number: null
3. This creates/updates production deployment at {app}.doughughes.net
```

**On PR Merge to Main:**
```
1. Deploy production (see above)
2. POST to deploy.doughughes.net/api/cleanup
   - app_name: from repo
   - pr_number: PR number
3. This removes the preview deployment
```

**On PR Close (without merge):**
```
1. POST to deploy.doughughes.net/api/cleanup
   - app_name: from repo
   - pr_number: PR number
```

**New App Creation:**
```
1. Clone app-template to new repo
2. Customize app.json and code
3. Add DEPLOY_API_KEY to GitHub secrets
4. Create first PR
5. Preview deploys automatically to pr-1.{app}.doughughes.net
6. Merge PR
7. Production deploys automatically to {app}.doughughes.net
8. Zero server-side setup required!
```

### Local Development with Worktrees

**Port Override via Environment Variable:**
```bash
# Main branch (worktree 1)
PORT=8005 python app.py

# Feature branch (worktree 2)
PORT=8006 python app.py

# Another feature (worktree 3)
PORT=8007 python app.py
```

**App Code:**
```python
PORT = int(os.getenv('PORT', 8000))  # Default for local dev
```

### Directory Structure (Server)

```
~/apps/
├── color-the-map/              # Production (main branch)
│   ├── app.py
│   ├── app.json                # Includes showOnDoughHughesNet field
│   ├── .github/
│   │   └── workflows/          # CI/CD workflows
│   └── ... (app code only - no Caddy/systemd configs)
├── color-the-map-pr-123/       # Preview deployment
│   ├── app.py
│   ├── app.json
│   └── ... (app code)
├── deploy-service/             # Deploy API (manages all deployments)
│   ├── app.py
│   ├── app.json
│   └── .github/workflows/
└── doughughes-net/             # Homepage (regular app, not special)
    ├── app.py
    ├── app.json                # showOnDoughHughesNet: false (doesn't show itself)
    └── .github/workflows/

~/infrastructure/               # Minimal glue layer
├── caddy/
│   └── Caddyfile              # Just import statements
├── deploy.sh                  # Caddy config deployment only
└── docs/                      # Architecture documentation

~/.config/systemd/user/         # Generated by deploy service
├── color-the-map.service
├── color-the-map-pr-123.service
├── deploy-service.service
└── doughughes-net.service

~/.config/caddy/                # Generated by deploy service
├── color-the-map.caddy-subdomain.conf
├── color-the-map-pr-123.caddy-subdomain.conf
├── deploy-service.caddy-subdomain.conf
├── doughughes-net.caddy-subdomain.conf
└── doughughes-net.caddy.conf  # Special: catch-all for root domains

~/preview-deployments/
└── ports.json                  # Port allocation tracking
```

**Key changes from current state:**
- ✅ No Caddy configs in app repos (deploy service generates them)
- ✅ No systemd service files in app repos (deploy service generates them)
- ✅ App repos contain only app code, app.json, and workflows
- ✅ All configuration generated dynamically based on deployment context
- ✅ doughughes-net is a regular app (uses deploy service like everything else)

## Benefits

1. **Rapid Iteration**: Work on multiple features simultaneously
2. **Safe Testing**: Preview environments isolated from production
3. **Collaboration**: Share preview URLs with stakeholders
4. **Automated**: No manual deployment steps
5. **Resource Efficient**: Previews cleaned up automatically
6. **Scalable**: Template makes it easy to add to new apps

## App Configuration (app.json)

**All apps include app.json** with metadata for the homepage:

```json
{
  "name": "Color The Map",
  "icon": "🗺️",
  "image": "logo.png",
  "description": "Interactive US election mapping tool",
  "showOnDoughHughesNet": true
}
```

**Fields:**
- `name`: Display name on homepage
- `icon`: Emoji icon (fallback if no image)
- `image`: Optional image file (relative to app directory)
- `description`: Short description for app card
- `showOnDoughHughesNet`: Boolean - show this app on the homepage (default: false)

**Homepage Behavior:**
- doughughes-net app scans `~/apps/*/app.json`
- Displays tiles for apps where `showOnDoughHughesNet: true`
- Preview deployments don't have app.json or have showOnDoughHughesNet: false
- No authentication - just a directory of public apps

**Per-App Authentication:**
- Each app handles its own authentication if needed
- No centralized auth system
- Apps can be completely public, have their own login, use OAuth, etc.

## Infrastructure Repo Final State

After migration, the infrastructure repo becomes minimal:

```
~/infrastructure/
├── caddy/
│   └── Caddyfile              # Just import statements, no app-specific config
├── docs/                      # Planning and architecture documentation
├── deploy.sh                  # Deploys Caddy config only (sudo caddy reload)
├── deploy-to-prod.sh          # Remote Caddy deploy trigger
├── CLAUDE.md                  # Infrastructure context
└── README.md                  # Setup guide
```

**What it does:**
- Provides base Caddy configuration that imports all app configs
- Documents the architecture and deployment system
- That's it!

**What it doesn't do:**
- ❌ No app code or services
- ❌ No app deployment logic (moved to deploy-service)
- ❌ No authentication (removed)
- ❌ No app-specific configuration

**The Caddyfile:**
```
# Import all app subdomain configs (generated by deploy-service)
import /home/dhughes/.config/caddy/*.caddy-subdomain.conf

# Root domain (doughughes-net provides catch-all handler)
doughughes.net, www.doughughes.net {
    import /home/dhughes/.config/caddy/*.caddy.conf
}
```

## doughughes-net Special Bootstrap

While doughughes-net uses the deploy system like any other app, it has one special requirement: it needs to handle the root domain catch-all.

**Deploy service special handling:**
When deploying doughughes-net production (pr_number=null):
1. Generate standard `doughughes-net.caddy-subdomain.conf` (like any app)
2. **Also** generate `doughughes-net.caddy.conf`:
   ```
   handle {
       reverse_proxy localhost:{port}
   }
   ```
3. This catch-all routes doughughes.net/www.doughughes.net root to the homepage

This is the **only** special case. All other apps are completely uniform.

## Database Considerations

**Per-App Strategy:**
- Apps with SQLite: Each preview gets own DB file
- Apps with Postgres/MySQL: Shared DB with table prefixing or separate preview DBs
- Define in app-template, apps choose their approach

## Resource Management

**Cleanup Policies:**
- PRs deleted: Immediate cleanup
- Stale previews (>30 days): Auto-cleanup (future enhancement)
- Port limits: 100 previews per app max

**Monitoring (Future):**
- Dashboard showing active previews
- Resource usage per preview
- Alert on port exhaustion
