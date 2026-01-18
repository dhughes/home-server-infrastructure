# Preview Deployment System - Project Plan

## Epic Overview

Transform home server infrastructure to support parallel development with automatic preview deployments for pull requests.

**Estimated Total Tickets:** 25-30
**Phases:** 5

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
Update app-template to read port from environment variable.

**Tasks:**
- Update `app.py` to read: `PORT = int(os.getenv('PORT', 7999))`
- Update README/CLAUDE.md with port override instructions
- Document port range allocation strategy

**Acceptance Criteria:**
- App reads PORT from environment
- Falls back to default if not set
- Documentation explains usage

**Dependencies:** TICKET-005

---

### TICKET-008: Add PORT Support to Existing Apps
**Priority:** P0
**Estimate:** 2 hours

**Description:**
Update all existing apps to support PORT environment variable.

**Apps to update:**
- doughughes-net (default 8000)
- color-the-map (default 8005)
- home-inventory (default 8003)
- cranium-charades (default 8004)
- random-word (default 8001)
- lottery-numbers (default 8002)

**Tasks:**
- For each app:
  - Update port reading logic
  - Test with custom PORT
  - Commit and push changes
  - Deploy to production (should use default)

**Acceptance Criteria:**
- All apps respect PORT environment variable
- Production apps still use correct ports (defaults work)
- Can run app on different port locally

**Dependencies:** TICKET-007

---

### TICKET-009: Define Port Allocation Strategy
**Priority:** P0
**Estimate:** 1 hour

**Description:**
Document port ranges for each app's preview deployments.

**Tasks:**
- Create `~/infrastructure/docs/port-allocation.md`
- Define ranges:
  - doughughes-net: 8000 (prod), 10000-10099 (previews)
  - random-word: 8001 (prod), 10100-10199 (previews)
  - lottery-numbers: 8002 (prod), 10200-10299 (previews)
  - home-inventory: 8003 (prod), 10300-10399 (previews)
  - cranium-charades: 8004 (prod), 10400-10499 (previews)
  - color-the-map: 8005 (prod), 10500-10599 (previews)
  - app-template: 7999 (prod), 10600-10699 (previews)
- Document allocation in app-template CLAUDE.md

**Acceptance Criteria:**
- Clear port range for each app
- No overlapping ranges
- Documented and discoverable

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
  - POST /api/preview/deploy
  - POST /api/preview/cleanup
  - GET /api/preview/status
  - GET /health
- Add API key authentication
- Create `deploy-service.service` (user service)
- Create `caddy-subdomain.conf` for deploy.doughughes.net
- Add basic logging

**Acceptance Criteria:**
- Service runs on port 8100
- Endpoints return 200 OK with stub responses
- API key authentication works
- Accessible at deploy.doughughes.net (private)

**Dependencies:** TICKET-009

---

### TICKET-011: Implement Port Allocation Logic
**Priority:** P0
**Estimate:** 2 hours

**Description:**
Implement port tracking and allocation in deploy service.

**Tasks:**
- Create `~/preview-deployments/ports.json` structure
- Implement `allocate_port(app_name)` function
  - Reads app's port range from config
  - Finds next available port
  - Updates ports.json
  - Returns allocated port
- Implement `free_port(app_name, pr_number)` function
- Add locking for concurrent deployments
- Handle port exhaustion gracefully

**Acceptance Criteria:**
- Can allocate ports from ranges
- Ports are tracked correctly
- Concurrent requests don't allocate same port
- Clear error if range exhausted
- Ports freed on cleanup

**Dependencies:** TICKET-010

---

### TICKET-012: Implement Preview Deploy Endpoint
**Priority:** P0
**Estimate:** 4 hours

**Description:**
Implement POST /api/preview/deploy endpoint logic.

**Input:**
```json
{
  "api_key": "secret",
  "app_name": "color-the-map",
  "pr_number": 123,
  "branch": "feature/foo",
  "repo_url": "https://github.com/user/color-the-map"
}
```

**Tasks:**
- Validate inputs
- Clone branch to `~/apps/{app}-pr-{number}`
- Allocate port from range
- Generate systemd service file
  - Name: `{app}-pr-{number}.service`
  - WorkingDirectory: `~/apps/{app}-pr-{number}`
  - Environment: PORT={allocated_port}
- Generate `caddy-subdomain.conf`
  - Subdomain: `pr-{number}.{app}.doughughes.net`
  - Reverse proxy to localhost:{port}
- Install service: `systemctl --user enable {service}`
- Start service: `systemctl --user start {service}`
- Reload Caddy: `sudo caddy reload --config /etc/caddy/Caddyfile`
- Return preview URL

**Acceptance Criteria:**
- Endpoint successfully deploys preview
- Service is running
- Subdomain is accessible
- Returns correct preview URL
- Handles errors gracefully (cleanup on failure)

**Dependencies:** TICKET-011

---

### TICKET-013: Implement Preview Cleanup Endpoint
**Priority:** P0
**Estimate:** 2 hours

**Description:**
Implement POST /api/preview/cleanup endpoint logic.

**Input:**
```json
{
  "api_key": "secret",
  "app_name": "color-the-map",
  "pr_number": 123
}
```

**Tasks:**
- Stop service: `systemctl --user stop {app}-pr-{number}`
- Disable service: `systemctl --user disable {app}-pr-{number}`
- Remove service file from `~/.config/systemd/user/`
- Remove app directory: `~/apps/{app}-pr-{number}`
- Free port in ports.json
- Reload Caddy (config auto-updates via import)
- Return success response

**Acceptance Criteria:**
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
Implement GET /api/preview/status endpoint.

**Output:**
```json
{
  "active_previews": [
    {
      "app": "color-the-map",
      "pr": 123,
      "url": "https://pr-123.color-the-map.doughughes.net",
      "port": 10500,
      "status": "running"
    }
  ],
  "port_usage": {
    "color-the-map": "1/100"
  }
}
```

**Tasks:**
- List all `*-pr-*` services
- Parse service files for metadata
- Check service status
- Read ports.json for port info
- Return formatted response

**Acceptance Criteria:**
- Shows all active previews
- Accurate service status
- Port usage info
- Useful for debugging

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
    - POST to deploy.doughughes.net/api/preview/deploy
    - Comment on PR with preview URL
```

**Tasks:**
- Create workflow file
- Add API key as GitHub secret
- Implement PR comment with preview URL
- Add status badges
- Test with dummy PR

**Acceptance Criteria:**
- Workflow triggers on PR events
- Tests run before deployment
- Only deploys if tests pass
- Posts preview URL to PR
- API key secure in secrets

**Dependencies:** TICKET-015

---

### TICKET-017: Create Production Deploy Workflow Template
**Priority:** P0
**Estimate:** 1 hour

**Description:**
Create workflow for production deployment on merge.

**Location:** `app-template/.github/workflows/deploy-production.yml`

**Workflow:**
```yaml
on:
  push:
    branches: [main]

jobs:
  deploy:
    - SSH to server (or call deploy API)
    - Deploy to production subdomain
    - Cleanup preview if exists (merged PR)
```

**Tasks:**
- Create workflow file
- Add SSH key or API call
- Clean up preview deployment
- Test deployment

**Acceptance Criteria:**
- Triggers on merge to main
- Production deployment succeeds
- Preview cleaned up if exists
- Production subdomain updated

**Dependencies:** TICKET-016

---

### TICKET-018: Create Cleanup Workflow Template
**Priority:** P0
**Estimate:** 1 hour

**Description:**
Create workflow to cleanup preview on PR close.

**Location:** `app-template/.github/workflows/cleanup-preview.yml`

**Workflow:**
```yaml
on:
  pull_request:
    types: [closed]

jobs:
  cleanup:
    - POST to deploy.doughughes.net/api/preview/cleanup
```

**Tasks:**
- Create workflow file
- Call cleanup endpoint
- Handle both merged and closed PRs
- Test with closed PR

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

### TICKET-024: Create Preview Deployment Guide
**Priority:** P1
**Estimate:** 2 hours

**Description:**
Comprehensive guide for using preview deployments.

**Location:** `~/infrastructure/docs/preview-deployment-guide.md`

**Contents:**
- How preview deployments work
- Developer workflow
- Testing previews
- Troubleshooting
- Best practices
- Examples

**Acceptance Criteria:**
- Clear, comprehensive guide
- Covers common scenarios
- Troubleshooting section
- Examples for reference

**Dependencies:** TICKET-023

---

### TICKET-025: Update Main Infrastructure Docs
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

**Dependencies:** TICKET-024

---

### TICKET-026: Add Deploy Service Monitoring (Optional)
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

**Dependencies:** TICKET-024

---

### TICKET-027: Add Auto-Cleanup for Stale Previews (Optional)
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

**Dependencies:** TICKET-024

---

## Summary

**Total Estimated Time:** 45-55 hours

**Phase Breakdown:**
- Phase 1 (Foundation): ~8 hours
- Phase 2 (Port Management): ~3.5 hours
- Phase 3 (Deploy Service): ~14 hours
- Phase 4 (GitHub Actions): ~7 hours
- Phase 5 (Migration): ~8-12 hours
- Phase 6 (Docs & Polish): ~5-8 hours (optional items add more)

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
- ✅ GitHub Actions integrated
- ✅ App template ready for new apps
- ✅ Documentation complete
