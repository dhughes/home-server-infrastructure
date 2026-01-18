# Preview Deployment System - Project Plan

## Epic Overview

Transform home server infrastructure to support parallel development with automatic preview deployments for pull requests.

## Key Architectural Decisions

### Unified Deployment Logic
- Production and preview deployments use the **same** /api/deploy endpoint
- Production: `pr_number=null`, deploys to `{app}.doughughes.net`
- Preview: `pr_number=123`, deploys to `pr-123.{app}.doughughes.net`
- No distinction in deployment logic - production is just a deployment that never gets cleaned up

### Dynamic Port Allocation
- No manual port configuration or per-app ranges
- All deployments get next available port starting at 8000
- Existing deployments reuse their port
- Tracked in simple `ports.json` file

### Generated Configuration
- Deploy service generates all Caddy configs and systemd services
- Apps contain only code, app.json, and GitHub workflows
- No Caddy or systemd files in app repos

### No Centralized Authentication
- Removed forward_auth and central login system
- Each app handles its own authentication (or is public)
- doughughes-net homepage shows tiles based on `showOnDoughHughesNet` field in app.json

### New App Creation (Zero Server Setup)
1. Clone app-template to new repo
2. Customize and push to GitHub
3. Add DEPLOY_API_KEY to repo secrets
4. Create first PR → preview deploys automatically
5. Merge PR → production deploys automatically to new subdomain
6. **No server-side configuration required!**

---

# Epic 1: Foundation - User Systemd Migration

**Goal:** Eliminate sudo requirements for app management by migrating to user systemd services.

**Estimated Time:** ~8 hours

---

## Server Setup for User Systemd
**Priority:** P0 (Blocker)
**Estimate:** 30 minutes

**Description:**
One-time server configuration to enable user systemd services.

**Tasks:**
- SSH to server
- Run: `loginctl enable-linger dhughes`
- Create: `mkdir -p ~/.config/systemd/user`
- Verify Caddy sudo config exists: `/etc/sudoers.d/infrastructure`
- Test: `systemctl --user status` works

**Acceptance Criteria:**
- User services persist after logout
- `~/.config/systemd/user/` directory exists
- No errors when running systemctl --user commands

**Dependencies:** None

---

## Create Migration Script for Systemd Services
**Priority:** P0
**Estimate:** 2 hours

**Description:**
Create script to migrate existing system services to user services.

**Tasks:**
- Create `~/infrastructure/scripts/migrate-to-user-services.sh`
- Script should:
  - Stop system service
  - Copy service file to `~/.config/systemd/user/`
  - Remove `User=dhughes` line
  - Change `After=network.target` to `After=default.target`
  - Change `WantedBy=multi-user.target` to `WantedBy=default.target`
  - Enable and start user service
  - Verify service is running
- Add dry-run mode for testing

**Acceptance Criteria:**
- Script successfully migrates a test service
- Original system service is stopped
- User service runs without errors
- Script can be run multiple times safely (idempotent)

**Dependencies:** Server Setup for User Systemd

---

## Migrate doughughes-net to User Service
**Priority:** P0
**Estimate:** 1 hour

**Description:**
Migrate doughughes-net app to user systemd service.

**Tasks:**
- Run migration script for doughughes-net
- Update `~/apps/doughughes-net/deploy.sh` to use `systemctl --user`
- Update `~/infrastructure/deploy.sh` deploy_auth() function
- Test deployment workflow end-to-end
- Verify service survives reboot

**Acceptance Criteria:**
- doughughes-net runs as user service
- No sudo required for restart
- Deploy scripts work
- www.doughughes.net still accessible
- Service auto-starts on boot

**Dependencies:** Create Migration Script for Systemd Services

---

## Migrate All Apps to User Services
**Priority:** P0
**Estimate:** 2 hours

**Description:**
Migrate remaining apps to user systemd services.

**Apps to migrate:**
- color-the-map (port 8005)
- home-inventory (port 8003)
- cranium-charades (port 8004)
- random-word (port 8001)
- lottery-numbers (port 8002)

**Tasks:**
- For each app:
  - Run migration script
  - Update app's `deploy.sh` to use `systemctl --user`
  - Test deployment
  - Verify app is accessible via subdomain

**Acceptance Criteria:**
- All apps run as user services
- All apps accessible via subdomains
- No sudo required for app restarts
- All services auto-start on boot

**Dependencies:** Migrate doughughes-net to User Service

---

## Update App Template for User Services
**Priority:** P1
**Estimate:** 1 hour

**Description:**
Update app-template to use user systemd services.

**Tasks:**
- Update `app-template.service` file:
  - Remove `User=dhughes`
  - Use `After=default.target`
  - Use `WantedBy=default.target`
- Update `deploy.sh` to use `systemctl --user`
- Update CLAUDE.md with user service instructions
- Test creating a new app from template

**Acceptance Criteria:**
- New apps created from template use user services
- No manual service migration needed for new apps
- Documentation is accurate

**Dependencies:** Migrate All Apps to User Services

---

## Update Infrastructure Documentation for User Services
**Priority:** P1
**Estimate:** 1 hour

**Description:**
Update all infrastructure docs to reflect user systemd usage.

**Files to update:**
- `~/infrastructure/CLAUDE.md`
- `~/infrastructure/README.md`
- Add migration notes for reference

**Tasks:**
- Replace all `sudo systemctl` with `systemctl --user` (except Caddy)
- Update service installation instructions
- Document `loginctl enable-linger` requirement
- Add troubleshooting section for user services

**Acceptance Criteria:**
- All docs accurately reflect user services
- Setup instructions are clear
- No references to sudo for app services (except Caddy)

**Dependencies:** Update App Template for User Services

---

# Epic 2: Simplification - Remove Auth & Centralize Config

**Goal:** Remove centralized authentication and prepare apps for deploy-service-managed configuration.

**Estimated Time:** ~3.5 hours

---

## Remove Authentication from doughughes-net
**Priority:** P0
**Estimate:** 2 hours

**Description:**
Remove all authentication features from doughughes-net app. It becomes a simple homepage displaying app tiles.

**Tasks:**
- Remove login/logout endpoints and UI
- Remove /verify endpoint (forward_auth)
- Remove user management (/account, /admin/users)
- Remove session management code
- Remove users.json and sessions.json
- Simplify to just: index page, app discovery, tile display
- Update app.json scanning to check `showOnDoughHughesNet` field
- Remove lock icons and logged-in/logged-out logic
- Remove cookie domain logic (no longer needed)
- Test locally

**Acceptance Criteria:**
- No authentication code remains
- Homepage shows tiles for apps with showOnDoughHughesNet: true
- No login/logout functionality
- Simplified codebase
- Still displays app tiles correctly

**Dependencies:** Update Infrastructure Documentation for User Services

---

## Add showOnDoughHughesNet to App JSONs
**Priority:** P0
**Estimate:** 30 minutes

**Description:**
Add `showOnDoughHughesNet` field to all existing app.json files.

**Apps to update:**
- color-the-map: true
- home-inventory: true
- cranium-charades: true
- random-word: true
- lottery-numbers: true
- doughughes-net: false (doesn't show itself)
- app-template: false (template shouldn't show)

**Tasks:**
- Update each app's app.json
- Commit changes to each repo
- Test that doughughes-net homepage shows correct apps

**Acceptance Criteria:**
- All apps have showOnDoughHughesNet field
- doughughes-net displays correct apps
- Template has field set to false

**Dependencies:** Remove Authentication from doughughes-net

---

## Remove Caddy Configs from App Repos
**Priority:** P0
**Estimate:** 1 hour

**Description:**
Remove caddy.conf and caddy-subdomain.conf from all app repos since deploy service will generate them dynamically.

**Apps to update:**
- color-the-map
- home-inventory
- cranium-charades
- random-word
- lottery-numbers
- doughughes-net
- app-template

**Tasks:**
- Delete caddy.conf from each repo (if exists)
- Delete caddy-subdomain.conf from each repo (if exists)
- Update app-template to not include Caddy configs
- Update app-template CLAUDE.md to remove Caddy references
- Commit changes
- Note: Apps will temporarily break until deploy service is ready

**Acceptance Criteria:**
- No Caddy config files in app repos
- App-template doesn't include Caddy configs
- Ready for deploy-service-generated configs

**Dependencies:** Add showOnDoughHughesNet to App JSONs

---

# Epic 3: Port Management & Environment Configuration

**Goal:** Enable apps to run on configurable ports for parallel development.

**Estimated Time:** ~3 hours

---

## Add PORT Environment Variable Support to App Template
**Priority:** P0
**Estimate:** 30 minutes

**Description:**
Update app-template to read port from environment variable. Apps no longer have hardcoded ports - the deploy service assigns them dynamically.

**Tasks:**
- Update `app.py` to read: `PORT = int(os.getenv('PORT', 8000))`
- Update README/CLAUDE.md to explain PORT is set by systemd service
- Note: Port is provided by deploy service, not configured by developer
- Remove any hardcoded port references

**Acceptance Criteria:**
- App reads PORT from environment
- Falls back to 8000 if not set (for local dev)
- Documentation explains PORT is deployment-managed

**Dependencies:** Remove Caddy Configs from App Repos

---

## Add PORT Support to Existing Apps
**Priority:** P0
**Estimate:** 2 hours

**Description:**
Update all existing apps to support PORT environment variable. After migration, existing production deployments will keep their current ports (tracked in ports.json).

**Apps to update:**
- doughughes-net (currently 8000)
- color-the-map (currently 8005)
- home-inventory (currently 8003)
- cranium-charades (currently 8004)
- random-word (currently 8001)
- lottery-numbers (currently 8002)

**Tasks:**
- For each app:
  - Update port reading logic: `PORT = int(os.getenv('PORT', 8000))`
  - Test with custom PORT locally
  - Commit and push changes
  - Note: Production deployment will continue using current port (no change)

**Acceptance Criteria:**
- All apps respect PORT environment variable
- Can run app on different port locally for worktree development
- Production apps continue working on existing ports

**Dependencies:** Add PORT Environment Variable Support to App Template

---

## Initialize Port Allocation Tracking
**Priority:** P0
**Estimate:** 30 minutes

**Description:**
Create initial port allocation file with existing production deployments. All future deployments (production and preview) will use dynamic allocation starting at next available port.

**Tasks:**
- Create `~/preview-deployments/ports.json` structure
- Document current production allocations:
  ```json
  {
    "doughughes-net": 8000,
    "random-word": 8001,
    "lottery-numbers": 8002,
    "home-inventory": 8003,
    "cranium-charades": 8004,
    "color-the-map": 8005
  }
  ```
- Create `~/infrastructure/docs/port-allocation.md` documenting:
  - Dynamic allocation strategy (find first available port)
  - No per-app ranges needed
  - Production and preview use same allocation logic
  - Existing production apps keep their current ports

**Acceptance Criteria:**
- Port allocation file exists with current production ports
- Documentation explains dynamic allocation
- No manual port assignment needed for new deployments

**Dependencies:** Add PORT Support to Existing Apps

---

# Epic 4: Deploy Service Development

**Goal:** Create API service to handle all deployments (production and preview).

**Estimated Time:** ~13.5 hours

---

## Create Deploy Service App Structure
**Priority:** P0
**Estimate:** 2 hours

**Description:**
Set up deploy-service app with basic structure.

**Tasks:**
- Create app from app-template (new repo)
- Rename to deploy-service
- Create basic Flask/FastAPI app with endpoints:
  - POST /api/deploy (handles both production and preview)
  - POST /api/cleanup (preview only)
  - GET /api/status
  - GET /health
- Add API key authentication (Bearer token)
- Update app.json: name="Deploy Service", showOnDoughHughesNet=false
- Add basic logging
- Set up to run on PORT from environment
- Create GitHub workflows for CI/CD
- Test locally

**Acceptance Criteria:**
- Service runs on PORT from environment
- Endpoints return 200 OK with stub responses
- API key authentication works
- Ready to be deployed via its own workflows

**Dependencies:** Initialize Port Allocation Tracking

---

## Implement Port Allocation Logic
**Priority:** P0
**Estimate:** 1.5 hours

**Description:**
Implement simple dynamic port allocation in deploy service. No ranges needed - just find the next available port starting at 8000.

**Tasks:**
- Load/save `~/preview-deployments/ports.json`
- Implement `get_or_allocate_port(deployment_id)` function:
  - Check if deployment_id already has a port (reuse it)
  - If not, find first unused port starting at 8000
  - Update ports.json
  - Return allocated port
- Implement `free_port(deployment_id)` function:
  - Remove from ports.json
  - Return freed port
- Add file locking for concurrent deployments (fcntl)
- No port exhaustion possible (unlimited ports above 8000)

**Acceptance Criteria:**
- Same deployment always gets same port
- New deployments get next available port
- Concurrent requests don't allocate same port (file locking)
- Ports freed on cleanup
- Works for both production and preview deployments

**Dependencies:** Create Deploy Service App Structure

---

## Implement Unified Deploy Endpoint
**Priority:** P0
**Estimate:** 5 hours

**Description:**
Implement POST /api/deploy endpoint that handles both production and preview deployments using identical logic.

**Input:**
```json
{
  "api_key": "secret",
  "app_name": "color-the-map",
  "branch": "main" or "feature/foo",
  "pr_number": null (for production) or 123 (for preview),
  "repo_url": "https://github.com/user/color-the-map"
}
```

**Tasks:**
- Validate inputs and authenticate API key
- Calculate deployment_id: `{app}` (prod) or `{app}-pr-{number}` (preview)
- Calculate subdomain: `{app}.doughughes.net` (prod) or `pr-{number}.{app}.doughughes.net` (preview)
- Check if deployment exists (git pull) or clone fresh to `~/apps/{deployment_id}`
- Get or allocate port for this deployment_id
- Generate systemd service file in `~/.config/systemd/user/`:
  - Name: `{deployment_id}.service`
  - WorkingDirectory: `~/apps/{deployment_id}`
  - Environment: PORT={allocated_port}
- Generate `~/.config/caddy/{deployment_id}.caddy-subdomain.conf`:
  - Subdomain: calculated above
  - Reverse proxy to localhost:{port}
- Special case for doughughes-net production: also generate catch-all `caddy.conf`
- Install/update service: `systemctl --user enable {service}`
- Restart service: `systemctl --user restart {service}`
- Reload Caddy: `sudo caddy reload --config /etc/caddy/Caddyfile`
- Return deployment URL

**Acceptance Criteria:**
- Production deployments work (pr_number=null)
- Preview deployments work (pr_number provided)
- Redeploying existing deployment reuses same port
- New deployments get next available port
- Service is running and accessible
- Returns correct URL
- Handles errors gracefully (cleanup on failure)
- Works for brand new apps (zero manual setup)
- doughughes-net gets catch-all config when deployed to production

**Dependencies:** Implement Port Allocation Logic

---

## Implement Cleanup Endpoint
**Priority:** P0
**Estimate:** 2 hours

**Description:**
Implement POST /api/cleanup endpoint for tearing down preview deployments. Production deployments cannot be cleaned up via this endpoint.

**Input:**
```json
{
  "api_key": "secret",
  "app_name": "color-the-map",
  "pr_number": 123
}
```

**Tasks:**
- Validate pr_number is provided (cannot cleanup production deployments)
- Calculate deployment_id: `{app}-pr-{number}`
- Stop service: `systemctl --user stop {deployment_id}`
- Disable service: `systemctl --user disable {deployment_id}`
- Remove service file from `~/.config/systemd/user/`
- Remove app directory: `~/apps/{deployment_id}`
- Remove Caddy config: `~/.config/caddy/{deployment_id}.caddy-subdomain.conf`
- Free port in ports.json
- Reload Caddy: `sudo caddy reload --config /etc/caddy/Caddyfile`
- Return success response

**Acceptance Criteria:**
- Rejects cleanup requests without pr_number (production protection)
- Service is stopped and removed
- Directory is deleted
- Caddy config removed
- Port is freed
- Subdomain no longer accessible (404)
- Idempotent (can call multiple times safely)

**Dependencies:** Implement Unified Deploy Endpoint

---

## Implement Status Endpoint
**Priority:** P1
**Estimate:** 1 hour

**Description:**
Implement GET /api/status endpoint showing all deployments (production and preview).

**Output:**
```json
{
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
      "app": "color-the-map",
      "pr": 123,
      "url": "https://pr-123.color-the-map.doughughes.net",
      "port": 8006,
      "status": "running"
    }
  ],
  "next_available_port": 8007,
  "total_deployments": 2,
  "production_count": 1,
  "preview_count": 1
}
```

**Tasks:**
- List all user services
- Distinguish production (no pr in name) from preview (has -pr- in name)
- Parse service files for metadata if needed
- Check service status via systemctl
- Read ports.json for port info
- Return formatted response

**Acceptance Criteria:**
- Shows all deployments (production and preview)
- Accurate service status
- Next available port shown
- Useful for debugging and monitoring

**Dependencies:** Implement Cleanup Endpoint

---

## Deploy Service Testing & Hardening
**Priority:** P0
**Estimate:** 3 hours

**Description:**
Comprehensive testing and error handling for deploy service.

**Test scenarios:**
- Deploy to non-existent repo
- Deploy with invalid branch
- Deploy when all ports below 10000 are taken
- Cleanup non-existent preview
- Concurrent deploys to same app
- Concurrent deploys to different apps
- Invalid API key
- Malformed requests
- Deploy doughughes-net (verify catch-all config generated)
- Deploy new app that doesn't exist yet

**Tasks:**
- Add comprehensive error handling
- Add request validation
- Add detailed logging
- Test all failure scenarios
- Test doughughes-net special case
- Test brand new app deployment
- Document API in deploy-service README

**Acceptance Criteria:**
- All error scenarios handled gracefully
- Clear error messages returned
- No partial deployments on failure
- doughughes-net special handling works
- New apps deploy successfully
- API documentation complete

**Dependencies:** Implement Status Endpoint

---

# Epic 5: GitHub Actions Integration

**Goal:** Automate deployments via GitHub workflows.

**Estimated Time:** ~7.5 hours

---

## Create Preview Deploy Workflow Template
**Priority:** P0
**Estimate:** 2 hours

**Description:**
Create reusable GitHub Actions workflow for preview deployment.

**Location:** `app-template/.github/workflows/preview-deploy.yml`

**Workflow:**
```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  test:
    - Run tests
    - Run linters
    - Type checking

  deploy-preview:
    needs: test
    if: success()
    - Extract app name from repo
    - POST to deploy.doughughes.net/api/deploy
      - app_name: extracted
      - branch: ${{ github.head_ref }}
      - pr_number: ${{ github.event.pull_request.number }}
      - repo_url: ${{ github.repository }}
    - Comment on PR with preview URL: pr-{number}.{app}.doughughes.net
```

**Tasks:**
- Create workflow file
- Add DEPLOY_API_KEY as GitHub secret (repo or org level)
- Extract app name from repo name or config
- Implement PR comment with preview URL
- Add status badges (optional)
- Test with dummy PR

**Acceptance Criteria:**
- Workflow triggers on PR events
- Tests run before deployment
- Only deploys if tests pass
- Posts preview URL to PR
- API key secure in secrets
- Works for any app without customization

**Dependencies:** Deploy Service Testing & Hardening

---

## Create Production Deploy Workflow Template
**Priority:** P0
**Estimate:** 1.5 hours

**Description:**
Create workflow for production deployment on push to main. Uses the same /api/deploy endpoint as previews, but with pr_number=null.

**Location:** `app-template/.github/workflows/deploy-production.yml`

**Workflow:**
```yaml
on:
  push:
    branches: [main]

jobs:
  test:
    - Run tests
    - Run linters
    - Type checking

  deploy-production:
    needs: test
    if: success()
    - Extract app name from repo
    - POST to deploy.doughughes.net/api/deploy
      - app_name: extracted
      - branch: "main"
      - pr_number: null
      - repo_url: ${{ github.repository }}
    - Creates/updates {app}.doughughes.net
```

**Tasks:**
- Create workflow file
- Use same DEPLOY_API_KEY secret as preview workflow
- Extract app name from repo name or config
- Call unified deploy endpoint with pr_number=null
- Test with push to main

**Acceptance Criteria:**
- Triggers on push to main
- Tests run before deployment
- Calls deploy endpoint correctly (pr_number=null)
- Production deployment succeeds
- Works for brand new apps (first merge creates production)
- Uses same API endpoint as preview (unified logic)

**Dependencies:** Create Preview Deploy Workflow Template

---

## Create Cleanup Workflow Template
**Priority:** P0
**Estimate:** 1 hour

**Description:**
Create workflow to cleanup preview deployments on PR close (whether merged or abandoned).

**Location:** `app-template/.github/workflows/cleanup-preview.yml`

**Workflow:**
```yaml
on:
  pull_request:
    types: [closed]

jobs:
  cleanup:
    - Extract app name from repo
    - POST to deploy.doughughes.net/api/cleanup
      - app_name: extracted
      - pr_number: ${{ github.event.pull_request.number }}
    - Removes preview deployment (pr-{number}.{app}.doughughes.net)

Note: If PR was merged, production already deployed via production workflow.
This just cleans up the preview instance.
```

**Tasks:**
- Create workflow file
- Use same DEPLOY_API_KEY secret
- Extract app name
- Call cleanup endpoint
- Test with closed PR (both merged and abandoned)
- Verify it's safe to call even if preview doesn't exist (idempotent)

**Acceptance Criteria:**
- Triggers when PR closed (merged or not)
- Calls cleanup endpoint correctly
- Works for merged and abandoned PRs
- Idempotent (safe to call multiple times)

**Dependencies:** Create Production Deploy Workflow Template

---

## Add GitHub Workflows to App Template
**Priority:** P0
**Estimate:** 1 hour

**Description:**
Integrate all workflows into app-template with documentation.

**Tasks:**
- Add all three workflow files to app-template
- Update app-template README.md with:
  - How preview deployments work
  - GitHub secrets setup instructions (DEPLOY_API_KEY)
  - Workflow explanations
  - How to customize for specific test frameworks
- Update app-template CLAUDE.md:
  - Explain automated deployment
  - Document workflow structure
  - Note that no manual deployment is needed
- Create example test files if not already present
- Test creating new app from template

**Acceptance Criteria:**
- Template includes all three workflows
- Documentation is clear and comprehensive
- New apps have working CI/CD out of box
- Secrets documented
- Ready for actual use

**Dependencies:** Create Cleanup Workflow Template

---

# Epic 6: Bootstrap Deploy Service

**Goal:** Deploy the deploy-service itself (chicken-and-egg problem).

**Estimated Time:** ~2 hours

---

## Bootstrap Deploy Service to Production
**Priority:** P0
**Estimate:** 2 hours

**Description:**
Manually deploy the deploy-service app to the server since it can't deploy itself initially.

**Tasks:**
- Clone deploy-service repo to `~/apps/deploy-service` on server
- Manually allocate port (next available, likely 8006)
- Add to ports.json: `"deploy-service": 8006`
- Create systemd service manually in `~/.config/systemd/user/`
- Create Caddy config manually in `~/.config/caddy/deploy-service.caddy-subdomain.conf`
- Enable and start service: `systemctl --user enable deploy-service && systemctl --user start deploy-service`
- Reload Caddy
- Verify accessible at deploy.doughughes.net
- Test API endpoints work
- Generate and save DEPLOY_API_KEY
- Add DEPLOY_API_KEY to deploy-service repo secrets in GitHub

**Acceptance Criteria:**
- Deploy service running and accessible at deploy.doughughes.net
- API endpoints respond correctly
- API key authentication works
- Can make test deployment
- Deploy service itself has GitHub workflows
- Future updates to deploy-service deploy via GitHub Actions

**Dependencies:** Add GitHub Workflows to App Template

---

# Epic 7: App Migration & Rollout

**Goal:** Roll out preview deployments to all existing apps.

**Estimated Time:** ~9-13 hours

---

## Add GitHub Workflows to color-the-map (Pilot)
**Priority:** P0
**Estimate:** 2 hours

**Description:**
Add preview deployment workflows to color-the-map as pilot project.

**Tasks:**
- Copy workflows from app-template
- Customize for color-the-map specifics (test commands, etc.)
- Add DEPLOY_API_KEY to GitHub repo secrets
- Create test PR to trigger preview deploy
- Verify preview URL works
- Test merge (production deploy)
- Test close (cleanup)
- Document any issues

**Acceptance Criteria:**
- Preview deploys on PR open
- Preview URL accessible
- Production deploys on merge
- Preview cleaned up on close/merge
- Full cycle tested end-to-end

**Dependencies:** Bootstrap Deploy Service to Production

---

## Fix Issues from Pilot
**Priority:** P0
**Estimate:** 2-4 hours (contingency)

**Description:**
Address any issues discovered during color-the-map pilot.

**Tasks:**
- Fix deploy service bugs
- Update workflows if needed
- Improve error handling
- Update documentation
- Re-test color-the-map

**Acceptance Criteria:**
- All issues from pilot resolved
- Workflows robust and reliable
- Ready for broader rollout

**Dependencies:** Add GitHub Workflows to color-the-map (Pilot)

---

## Add Workflows to home-inventory
**Priority:** P1
**Estimate:** 1 hour

**Description:**
Roll out preview deployments to home-inventory.

**Tasks:**
- Copy workflows from app-template
- Customize test commands if needed
- Add DEPLOY_API_KEY to repo secrets
- Test preview deployment
- Document any app-specific customizations

**Acceptance Criteria:**
- Full preview deployment cycle works
- No issues during testing

**Dependencies:** Fix Issues from Pilot

---

## Add Workflows to Remaining Apps
**Priority:** P1
**Estimate:** 3 hours

**Description:**
Roll out to remaining apps:
- cranium-charades
- random-word
- lottery-numbers
- doughughes-net (yes, even the homepage uses the system!)

**Tasks:**
- For each app:
  - Copy workflows from app-template
  - Add DEPLOY_API_KEY to repo secrets
  - Test deployment cycle
  - Verify doughughes-net gets catch-all config when deployed
  - Document customizations

**Acceptance Criteria:**
- All apps have preview deployments
- All tested successfully
- doughughes-net deploys correctly with catch-all handler

**Dependencies:** Add Workflows to home-inventory

---

## Remove Legacy Deploy Scripts from Apps
**Priority:** P1
**Estimate:** 1 hour

**Description:**
Remove deploy.sh and deploy-to-prod.sh scripts from all apps now that GitHub Actions handles deployment.

**Apps to update:**
- color-the-map
- home-inventory
- cranium-charades
- random-word
- lottery-numbers
- doughughes-net

**Tasks:**
- For each app:
  - Delete `deploy.sh`
  - Delete `deploy-to-prod.sh`
  - Commit changes with message explaining GitHub Actions replacement
- Update app-template to not include deploy scripts
- Update app-template CLAUDE.md to remove deploy script references
- Document GitHub Actions as the only deployment method

**Acceptance Criteria:**
- All legacy deploy scripts removed from app repos
- App-template doesn't include deploy scripts
- Documentation updated
- Deployment only happens via GitHub Actions

**Dependencies:** Add Workflows to Remaining Apps

---

# Epic 8: Documentation & Polish

**Goal:** Complete documentation and add nice-to-have features.

**Estimated Time:** ~3-6 hours

---

## Update Main Infrastructure Docs
**Priority:** P1
**Estimate:** 1.5 hours

**Description:**
Update all infrastructure documentation to reflect the final minimal state of the infrastructure repo and document the preview deployment system.

**Files to update:**
- ~/infrastructure/README.md
- ~/infrastructure/CLAUDE.md
- ~/infrastructure/docs/README.md

**Tasks:**
- Document what remains in infrastructure repo (just Caddy glue and docs)
- Update Caddyfile to import from ~/.config/caddy/ instead of ~/apps/
- Add preview deployment system overview
- Update architecture diagrams (deploy service, GitHub Actions, no auth)
- Explain that apps are now deployed via GitHub Actions only
- Document doughughes-net's special role (catch-all handler)
- Update deployment commands (only Caddy deploy remains in infrastructure)
- Link to preview deployment vision docs
- Document showOnDoughHughesNet field in app.json

**Acceptance Criteria:**
- Clear what infrastructure repo contains (minimal)
- Docs reflect GitHub Actions as only deployment method
- Easy to discover preview deployment info
- Architecture diagrams updated
- No references to per-app deploy scripts
- showOnDoughHughesNet field documented

**Dependencies:** Remove Legacy Deploy Scripts from Apps

---

## Add Deploy Service Monitoring (Optional)
**Priority:** P2
**Estimate:** 3 hours

**Description:**
Basic monitoring and dashboard for deploy service.

**Features:**
- Simple web dashboard showing active deployments
- Service health status
- Port utilization
- Recent deployment activity
- Distinguish production vs preview

**Tasks:**
- Add web UI to deploy service (simple HTML page)
- Show active deployments table (production and preview)
- Display port usage
- Add activity log
- Link from doughughes-net homepage (admin/debug link)

**Acceptance Criteria:**
- Dashboard accessible at deploy.doughughes.net
- Shows useful info
- Helps with debugging

**Dependencies:** Update Main Infrastructure Docs

---

## Add Auto-Cleanup for Stale Previews (Optional)
**Priority:** P3
**Estimate:** 2 hours

**Description:**
Automatically cleanup preview deployments older than 30 days.

**Tasks:**
- Add created_at timestamp to deployment tracking
- Create cleanup cron job or scheduled task in deploy service
- Identify previews >30 days old
- Call cleanup endpoint for each
- Log cleanup actions
- Make threshold configurable

**Acceptance Criteria:**
- Stale previews auto-cleaned
- Configurable age threshold
- Runs daily
- Logs actions taken

**Dependencies:** Update Main Infrastructure Docs

---

## Summary

**Total Tickets:** 30
**Total Estimated Time:** 46-59 hours

**Phase Breakdown:**
- Epic 1 (User Systemd): ~8 hours (6 tickets)
- Epic 2 (Simplification): ~3.5 hours (3 tickets)
- Epic 3 (Port Management): ~3 hours (3 tickets)
- Epic 4 (Deploy Service): ~13.5 hours (5 tickets)
- Epic 5 (GitHub Actions): ~7.5 hours (4 tickets)
- Epic 6 (Bootstrap): ~2 hours (1 ticket)
- Epic 7 (Migration): ~9-13 hours (5 tickets)
- Epic 8 (Documentation): ~3-6 hours (3 tickets, 2 optional)

**Critical Path:**
Server Setup → Migration Script → Migrate doughughes-net → Migrate All Apps → Update Template → Remove Auth → Add showOnDoughHughesNet → Remove Caddy Configs → Add PORT to Template → Add PORT to Apps → Initialize Ports → Create Deploy Service → Port Allocation → Deploy Endpoint → Cleanup Endpoint → Testing → Preview Workflow → Production Workflow → Cleanup Workflow → Add to Template → Bootstrap Deploy Service → Pilot → Fix Issues → Rollout Apps → Remove Scripts → Update Docs

**Parallelization Opportunities:**
- Update App Template and Update Infrastructure Docs can happen after Migrate All Apps
- Add Workflows to different apps can happen in parallel (home-inventory and remaining apps)
- Documentation tickets can happen in any order

**Risk Areas:**
- Deploy Service Testing critical (TICKET-015 equivalent)
- Pilot may reveal unforeseen issues (color-the-map)
- Bootstrap deploy-service is chicken-and-egg (manual first deploy)
- doughughes-net special case for catch-all routing

**Success Criteria:**
- ✅ All apps migrated to user services
- ✅ No centralized authentication (apps handle their own)
- ✅ Deploy service running and tested
- ✅ All Caddy/systemd configs generated dynamically
- ✅ Preview deployments work end-to-end
- ✅ Production deployments work via same endpoint
- ✅ GitHub Actions integrated
- ✅ App template ready for new apps
- ✅ New apps can be created and deployed with zero server setup
- ✅ Documentation complete
- ✅ Infrastructure repo is minimal (just Caddy glue + docs)
