# Preview Deployment System - Vision & Architecture

## Overview

Create a parallelizable "vibe coding" infrastructure that enables rapid development across multiple feature branches simultaneously, with automatic preview deployments for every pull request.

## Goals

1. **Parallel Development**: Work on multiple features using git worktrees
2. **Automatic Preview Deployments**: Every PR gets its own live preview URL
3. **CI/CD Integration**: GitHub Actions run tests, deploy on pass, cleanup on close
4. **Template-Based**: Easy to add to new apps via app-template
5. **Retrofit-Friendly**: Straightforward to add to existing apps

## Current State

**Infrastructure:**
- Caddy reverse proxy on ports 80/443
- Apps run as systemd services
- Subdomain-based routing (`app-name.doughughes.net`)
- Wildcard DNS (`*.doughughes.net`)
- doughughes-net app provides homepage and authentication

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

**Port Ranges Per App:**
```
color-the-map:
  Production: 8005
  Previews: 9000-9099 (100 concurrent PRs max)

home-inventory:
  Production: 8003
  Previews: 9100-9199

cranium-charades:
  Production: 8004
  Previews: 9200-9299
```

**Port Tracking:**
- JSON file on server: `~/preview-deployments/ports.json`
- Deploy service allocates next available port from range
- Cleanup frees ports back to pool

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
POST /api/preview/deploy
  - Clone branch to ~/apps/{app}-pr-{number}
  - Allocate port from range
  - Generate user systemd service
  - Generate caddy-subdomain.conf
  - Start service
  - Reload Caddy (graceful)
  - Return preview URL

POST /api/preview/cleanup
  - Stop user service
  - Remove app directory
  - Free port
  - Remove Caddy config
  - Reload Caddy

GET /api/preview/status
  - List all active previews
  - Show port allocations
  - Service health status
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
2. If pass: POST to deploy.doughughes.net/api/preview/deploy
3. Comment on PR with preview URL
```

**On PR Merge to Main:**
```
1. Deploy to production subdomain
2. POST to deploy.doughughes.net/api/preview/cleanup (delete preview)
```

**On PR Close (without merge):**
```
1. POST to deploy.doughughes.net/api/preview/cleanup
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
PORT = int(os.getenv('PORT', 8005))  # Default to production port
```

### Directory Structure (Server)

```
~/apps/
├── color-the-map/              # Production (main branch)
│   ├── app.py
│   ├── caddy-subdomain.conf    # color-the-map.doughughes.net
│   └── color-the-map.service
├── color-the-map-pr-123/       # Preview deployment
│   ├── app.py
│   ├── caddy-subdomain.conf    # pr-123.color-the-map.doughughes.net
│   └── color-the-map-pr-123.service
├── color-the-map-pr-124/       # Another preview
├── deploy-service/             # Deploy API
└── doughughes-net/             # Homepage/auth

~/.config/systemd/user/
├── color-the-map.service       # Production
├── color-the-map-pr-123.service
├── color-the-map-pr-124.service
├── deploy-service.service
└── doughughes-net.service

~/preview-deployments/
└── ports.json                  # Port allocation tracking
```

## Benefits

1. **Rapid Iteration**: Work on multiple features simultaneously
2. **Safe Testing**: Preview environments isolated from production
3. **Collaboration**: Share preview URLs with stakeholders
4. **Automated**: No manual deployment steps
5. **Resource Efficient**: Previews cleaned up automatically
6. **Scalable**: Template makes it easy to add to new apps

## Authentication Considerations

**Initial approach: Public previews**
- Simplest for testing and sharing
- No auth complexity

**Future options:**
- Basic auth per preview
- GitHub OAuth (only PR participants)
- Shared doughughes-net auth (if needed)

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
