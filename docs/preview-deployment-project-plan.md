# Preview Deployment System - Project Plan

## Epic Overview

Transform home server infrastructure to support parallel development with automatic preview deployments for pull requests.

**Estimated Total Tickets:** 26
**Phases:** 6

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

### New App Creation (Zero Server Setup)
1. Clone app-template to new repo
2. Customize and push to GitHub
3. Add DEPLOY_API_KEY to repo secrets
4. Create first PR → preview deploys automatically
5. Merge PR → production deploys automatically to new subdomain
6. **No server-side configuration required!**

---

## Phase 1: Foundation - User Systemd Migration

**Goal:** Eliminate sudo requirements for app management by migrating to user systemd services.

### TICKET-001: Server Setup for User Systemd
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

### TICKET-002: Create Migration Script for Systemd Services
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

**Dependencies:** TICKET-001

---

### TICKET-003: Migrate doughughes-net to User Service
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

**Dependencies:** TICKET-002

---

### TICKET-004: Migrate All Apps to User Services
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

**Dependencies:** TICKET-003

---

### TICKET-005: Update App Template for User Services
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

**Dependencies:** TICKET-004

---

### TICKET-006: Update Infrastructure Documentation
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

**Dependencies:** TICKET-005

---

## Phase 2: Port Management & Environment Configuration

**Goal:** Enable apps to run on configurable ports for parallel development.

### TICKET-007: Add PORT Environment Variable Support to App Template
**Priority:** P0
**Estimate:** 30 minutes

**Description:**
Update app-template to read port from environment variable. Apps no longer have hardcoded ports - the deploy service assigns them dynamically.

**Tasks:**
- Update `app.py` to read: `PORT = int(os.getenv('PORT', 8000))`
- Update README/CLAUDE.md to explain PORT is set by systemd service
- Note: Port is provided by deploy service, not configured by developer

**Acceptance Criteria:**
- App reads PORT from environment
- Falls back to 8000 if not set (for local dev)
- Documentation explains PORT is deployment-managed

**Dependencies:** TICKET-005

---

### TICKET-008: Add PORT Support to Existing Apps
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

**Dependencies:** TICKET-007

---

### TICKET-009: Initialize Port Allocation Tracking
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

**Dependencies:** TICKET-008

---

## Phase 3: Deploy Service Development

**Goal:** Create API service to handle preview deployments.

### TICKET-010: Create Deploy Service App Structure
**Priority:** P0
**Estimate:** 2 hours

**Description:**
Set up deploy-service app with basic structure.

**Tasks:**
- Create `~/apps/deploy-service/` directory
- Create basic Flask/FastAPI app with endpoints:
  - POST /api/deploy (handles both production and preview)
  - POST /api/cleanup (preview only)
  - GET /api/status
  - GET /health
- Add API key authentication
- Create `deploy-service.service` (user service)
- Create `caddy-subdomain.conf` for deploy.doughughes.net
- Add basic logging
- Note: Deploy service itself gets a port via manual allocation (bootstrap)

**Acceptance Criteria:**
- Service runs on dynamically allocated port
- Endpoints return 200 OK with stub responses
- API key authentication works
- Accessible at deploy.doughughes.net (private)

**Dependencies:** TICKET-009

---

### TICKET-011: Implement Port Allocation Logic
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

**Dependencies:** TICKET-010

---

### TICKET-012: Implement Unified Deploy Endpoint
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
- Check if deployment exists (git pull) or clone fresh
- Get or allocate port for this deployment_id
- Generate systemd service file:
  - Name: `{deployment_id}.service`
  - WorkingDirectory: `~/apps/{deployment_id}`
  - Environment: PORT={allocated_port}
- Generate `caddy-subdomain.conf`:
  - Subdomain: calculated above
  - Reverse proxy to localhost:{port}
  - Include forward_auth if app is private (parse from repo's config)
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

**Dependencies:** TICKET-011

---

### TICKET-013: Implement Cleanup Endpoint
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
- Free port in ports.json
- Reload Caddy: `sudo caddy reload --config /etc/caddy/Caddyfile`
- Return success response

**Acceptance Criteria:**
- Rejects cleanup requests without pr_number (production protection)
- Service is stopped and removed
- Directory is deleted
- Port is freed
- Subdomain no longer accessible (404)
- Idempotent (can call multiple times safely)

**Dependencies:** TICKET-012

---

### TICKET-014: Implement Status Endpoint
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

**Dependencies:** TICKET-013

---

### TICKET-015: Deploy Service Testing & Hardening
**Priority:** P0
**Estimate:** 3 hours

**Description:**
Comprehensive testing and error handling for deploy service.

**Test scenarios:**
- Deploy to non-existent repo
- Deploy with invalid branch
- Deploy when port range exhausted
- Cleanup non-existent preview
- Concurrent deploys to same app
- Concurrent deploys to different apps
- Invalid API key
- Malformed requests

**Tasks:**
- Add comprehensive error handling
- Add request validation
- Add detailed logging
- Test all failure scenarios
- Document API in README

**Acceptance Criteria:**
- All error scenarios handled gracefully
- Clear error messages returned
- No partial deployments on failure
- API documentation complete

**Dependencies:** TICKET-014

---

## Phase 4: GitHub Actions Integration

**Goal:** Automate preview deployments via GitHub workflows.

### TICKET-016: Create Preview Deploy Workflow Template
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

**Dependencies:** TICKET-015

---

### TICKET-017: Create Production Deploy Workflow Template
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

**Dependencies:** TICKET-016

---

### TICKET-018: Create Cleanup Workflow Template
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

Note: If PR was merged, production already deployed via TICKET-017 workflow.
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
- Calls cleanup endpoint
- Preview is torn down
- Works for merged and abandoned PRs

**Dependencies:** TICKET-017

---

### TICKET-019: Add GitHub Workflows to App Template
**Priority:** P0
**Estimate:** 1 hour

**Description:**
Integrate all workflows into app-template with documentation.

**Tasks:**
- Add all three workflow files
- Update app-template CLAUDE.md with:
  - GitHub secrets setup instructions
  - Workflow explanations
  - How to customize for specific apps
- Create example .env.example for required secrets
- Test creating new app from template

**Acceptance Criteria:**
- Template includes all workflows
- Documentation is clear
- New apps have working CI/CD out of box
- Secrets documented

**Dependencies:** TICKET-018

---

## Phase 5: App Migration & Rollout

**Goal:** Roll out preview deployments to existing apps.

### TICKET-020: Add GitHub Workflows to color-the-map (Pilot)
**Priority:** P0
**Estimate:** 2 hours

**Description:**
Add preview deployment workflows to color-the-map as pilot project.

**Tasks:**
- Copy workflows from app-template
- Customize for color-the-map specifics
- Add GitHub secrets (API key, SSH key if needed)
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

**Dependencies:** TICKET-019

---

### TICKET-021: Fix Issues from Pilot (if any)
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

**Dependencies:** TICKET-020

---

### TICKET-022: Add Workflows to home-inventory
**Priority:** P1
**Estimate:** 1 hour

**Description:**
Roll out preview deployments to home-inventory.

**Tasks:**
- Copy workflows
- Add secrets
- Test preview deployment
- Document any app-specific customizations

**Acceptance Criteria:**
- Full preview deployment cycle works
- No issues during testing

**Dependencies:** TICKET-021

---

### TICKET-023: Add Workflows to Remaining Apps
**Priority:** P1
**Estimate:** 3 hours

**Description:**
Roll out to remaining apps:
- cranium-charades
- random-word
- lottery-numbers

**Tasks:**
- For each app:
  - Copy workflows
  - Add secrets
  - Test cycle
  - Document customizations

**Acceptance Criteria:**
- All apps have preview deployments
- All tested successfully

**Dependencies:** TICKET-022

---

## Phase 6: Documentation & Polish

**Goal:** Complete documentation and add nice-to-have features.

### TICKET-024: Update Main Infrastructure Docs
**Priority:** P1
**Estimate:** 1 hour

**Description:**
Update all infrastructure documentation with preview deployment info.

**Files to update:**
- README.md
- CLAUDE.md
- Add links to preview deployment docs

**Tasks:**
- Add preview deployment section
- Update architecture diagrams
- Link to detailed docs
- Update port allocation info

**Acceptance Criteria:**
- Docs reflect new capabilities
- Easy to discover preview deployment info
- Architecture clear

**Dependencies:** TICKET-023

---

### TICKET-025: Add Deploy Service Monitoring (Optional)
**Priority:** P2
**Estimate:** 3 hours

**Description:**
Basic monitoring and dashboard for deploy service.

**Features:**
- Simple web dashboard showing active previews
- Service health status
- Port utilization
- Recent deployment activity

**Tasks:**
- Add web UI to deploy service
- Show active previews table
- Display port usage charts
- Add activity log

**Acceptance Criteria:**
- Dashboard accessible at deploy.doughughes.net
- Shows useful info
- Helps with debugging

**Dependencies:** TICKET-023

---

### TICKET-026: Add Auto-Cleanup for Stale Previews (Optional)
**Priority:** P3
**Estimate:** 2 hours

**Description:**
Automatically cleanup preview deployments older than 30 days.

**Tasks:**
- Add created_at timestamp to preview tracking
- Create cleanup cron job
- Identify previews >30 days old
- Call cleanup endpoint for each
- Log cleanup actions

**Acceptance Criteria:**
- Stale previews auto-cleaned
- Configurable age threshold
- Runs daily via cron

**Dependencies:** TICKET-023

---

## Summary

**Total Estimated Time:** 43-54 hours (26 tickets)

**Phase Breakdown:**
- Phase 1 (Foundation): ~8 hours
- Phase 2 (Port Management): ~3 hours (simplified - dynamic allocation)
- Phase 3 (Deploy Service): ~13.5 hours (unified deploy endpoint)
- Phase 4 (GitHub Actions): ~7.5 hours (unified workflows)
- Phase 5 (Migration): ~8-12 hours
- Phase 6 (Docs & Polish): ~3-6 hours (2 optional tickets)

**Key Simplifications from Original Plan:**
- No per-app port ranges (dynamic allocation only)
- Unified deploy endpoint (production and preview use same logic)
- Zero server setup for new apps (automatic allocation)

**Critical Path:**
TICKET-001 → 002 → 003 → 004 → 007 → 008 → 009 → 010 → 011 → 012 → 013 → 015 → 016 → 017 → 018 → 019 → 020 → 021 → 024

**Parallelization Opportunities:**
- TICKET-005 and 006 can happen during/after TICKET-004
- TICKET-022 and 023 can happen in parallel
- Phase 6 tickets can happen in any order

**Risk Areas:**
- TICKET-015: Deploy service testing critical
- TICKET-020: Pilot may reveal unforeseen issues
- TICKET-021: Contingency for pilot issues

**Success Criteria:**
- ✅ All apps migrated to user services
- ✅ Deploy service running and tested
- ✅ Preview deployments work end-to-end
- ✅ Production deployments work via same endpoint
- ✅ GitHub Actions integrated
- ✅ App template ready for new apps
- ✅ New apps can be created and deployed with zero server setup
- ✅ Documentation complete
