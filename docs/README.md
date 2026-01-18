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

## Epics (Implementation Order)

### Epic 1: Foundation - User Systemd Migration (~8h)
Migrate all services to user systemd (except Caddy) to eliminate sudo requirements. Keep existing deploy scripts working.

**Key Outcomes:**
- All apps run as user services
- No sudo needed for app management
- Existing deploy scripts still work (need them for bootstrap)

### Epic 2: Simplification (~3.5h)
Remove centralized auth, add showOnDoughHughesNet field, remove Caddy configs from repos.

**Key Outcomes:**
- No central authentication (apps handle their own)
- doughughes-net shows tiles based on showOnDoughHughesNet
- App repos contain only code + app.json (no Caddy configs)

### Epic 3: Port Management (~3h)
Enable apps to run on configurable ports via environment variables.

**Key Outcomes:**
- Apps read PORT from environment
- Dynamic port allocation (no ranges needed)
- Can run multiple instances locally

### Epic 4: Deploy Service Development (~13.5h)
Build the deploy API using old deployment methods.

**Key Outcomes:**
- Deploy service built and tested
- Handles production and preview deployments
- Port allocation working
- Ready to be bootstrapped

### Epic 5: Bootstrap Deploy Service (~2h)
Manually deploy deploy-service using old deploy.sh method (can't deploy itself yet).

**Key Outcome:**
- Deploy service running at deploy.doughughes.net

### Epic 6: Make Deploy Service Self-Deploying (~4.5h) ⭐ **Critical Milestone**
Add GitHub Actions to deploy-service and validate it can deploy itself.

**Key Outcomes:**
- Deploy service has GitHub workflows
- Deploy service can update itself via GitHub Actions
- **System proven to work before broader rollout**

### Epic 7: GitHub Actions Templates (~3.5h)
Create generic workflow templates for app-template (now that deploy service is proven).

**Key Outcomes:**
- Workflows in app-template
- Auto-deploy on PR/push
- Auto-cleanup on PR close

### Epic 8: App Migration & Rollout (~9-13h)
Roll out GitHub Actions to all apps, remove legacy deploy scripts.

**Key Outcomes:**
- All apps have GitHub workflows
- Legacy deploy scripts removed
- All apps deploy via GitHub Actions

### Epic 9: Documentation & Polish (~3-6h)
Update infrastructure docs, optional enhancements.

**Key Outcomes:**
- Updated infrastructure docs
- Optional: monitoring dashboard
- Optional: auto-cleanup of stale previews

## Getting Started

1. **Read the vision document** to understand what we're building
2. **Review the project plan** to see all epics and tickets
3. **Create GitHub Issues** from the project plan tickets
4. **Follow epic order** - critical to do Epic 6 before Epic 7/8
5. **Track progress** using GitHub Issues and Project board

## Critical Milestone

**Epic 6: Make Deploy Service Self-Deploying** is the key validation point. Once the deploy service can successfully update itself via GitHub Actions, we know the system works and it's safe to migrate other apps.

## Success Criteria

✅ All apps migrated to user services
✅ No centralized authentication (apps handle their own)
✅ Deploy service running and self-deploying
✅ All Caddy/systemd configs generated dynamically
✅ Preview deployments work end-to-end
✅ Production deployments work via same endpoint
✅ GitHub Actions integrated for all apps
✅ App template ready for new apps
✅ New apps deploy with zero server setup
✅ Infrastructure repo is minimal (just Caddy glue + docs)
✅ Legacy deploy scripts removed

## Estimated Timeline

**Total Time:** 46-59 hours (30 tickets across 9 epics)
**Critical Path:** ~38-45 hours (through Epic 8)
**Optional Features:** ~5 hours (Epic 9 optional tickets)

**Epic Breakdown:**
- Epic 1 (User Systemd): ~8h
- Epic 2 (Simplification): ~3.5h
- Epic 3 (Port Management): ~3h
- Epic 4 (Deploy Service Dev): ~13.5h
- Epic 5 (Bootstrap): ~2h
- Epic 6 (Self-Deploying): ~4.5h ⭐ **Key Milestone**
- Epic 7 (GitHub Actions Templates): ~3.5h
- Epic 8 (App Rollout): ~9-13h
- Epic 9 (Documentation): ~3-6h

With focused work sessions, this project could be completed in:
- **Aggressive:** 1-2 weeks (full-time focus)
- **Moderate:** 3-4 weeks (part-time)
- **Relaxed:** 4-6 weeks (as time allows)

## Questions?

Refer to the vision document for architecture questions.
Refer to the project plan for implementation details.
Update the ticket tracker as you discover issues or improvements.
