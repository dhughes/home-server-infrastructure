# Preview Deployment System Documentation

This directory contains planning and implementation documentation for the Preview Deployment System.

## Quick Links

### Planning Documents
- **[Vision & Architecture](preview-deployment-vision.md)** - High-level overview of the system, goals, and architecture
- **[Project Plan](preview-deployment-project-plan.md)** - Detailed tickets with estimates and dependencies

## Document Purpose

### preview-deployment-vision.md
**When to read:** Before starting implementation
**Purpose:** Understand the "why" and "what" of the system
**Contains:**
- Problem statement and goals
- High-level architecture
- Subdomain naming conventions
- Port allocation strategy
- Service management approach
- GitHub Actions workflow
- Benefits and trade-offs

## Project Phases

### Phase 1: Foundation - User Systemd Migration
Migrate all services to user systemd (except Caddy) to eliminate sudo requirements.

**Key Outcomes:**
- All apps run as user services
- No sudo needed for app management
- App template uses user services

### Phase 2: Port Management & Environment Configuration
Enable apps to run on configurable ports for parallel development.

**Key Outcomes:**
- Apps read PORT from environment
- Port ranges defined for each app
- Can run multiple instances locally

### Phase 3: Deploy Service Development
Create API service to handle preview deployments and cleanups.

**Key Outcomes:**
- Deploy API running at deploy.doughughes.net
- Port allocation system working
- Deploy and cleanup endpoints functional

### Phase 4: GitHub Actions Integration
Automate preview deployments via GitHub workflows.

**Key Outcomes:**
- Workflows in app-template
- Auto-deploy on PR open
- Auto-cleanup on PR close/merge

### Phase 5: App Migration & Rollout
Roll out preview deployments to all existing apps.

**Key Outcomes:**
- All apps have preview deployments
- Pilot tested and issues resolved
- Full workflow validated

### Phase 6: Documentation & Polish
Complete documentation and optional enhancements.

**Key Outcomes:**
- Updated infrastructure docs
- Optional: monitoring dashboard
- Optional: auto-cleanup of stale previews

Note: User guide is embedded in app-template workflows and README, not a separate document.

## Getting Started

1. **Read the vision document** to understand what we're building
2. **Review the project plan** to see all tickets
3. **Create GitHub Issues** from the project plan tickets
4. **Start with TICKET-001** and work through sequentially
5. **Track progress** using GitHub Issues and Project board

## Success Criteria

✅ All apps migrated to user services
✅ Deploy service running and tested
✅ Preview deployments work end-to-end
✅ GitHub Actions integrated
✅ App template ready for new apps
✅ Documentation complete

## Estimated Timeline

**Total Time:** 44-55 hours (27 tickets)
**Critical Path:** ~35-40 hours
**Optional Features:** ~5 hours

With focused work sessions, this project could be completed in:
- **Aggressive:** 1-2 weeks (full-time focus)
- **Moderate:** 3-4 weeks (part-time)
- **Relaxed:** 4-6 weeks (as time allows)

## Questions?

Refer to the vision document for architecture questions.
Refer to the project plan for implementation details.
Update the ticket tracker as you discover issues or improvements.
