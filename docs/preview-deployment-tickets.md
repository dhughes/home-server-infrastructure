# Preview Deployment System - Ticket Tracker

## Status Legend
- 🔴 Not Started
- 🟡 In Progress
- 🟢 Complete
- ⏸️ Blocked

---

## Phase 1: Foundation - User Systemd Migration (8 hours)

| Ticket | Status | Title | Est. | Assignee | Notes |
|--------|--------|-------|------|----------|-------|
| TICKET-001 | 🔴 | Server Setup for User Systemd | 0.5h | | |
| TICKET-002 | 🔴 | Create Migration Script for Systemd Services | 2h | | Depends on TICKET-001 |
| TICKET-003 | 🔴 | Migrate doughughes-net to User Service | 1h | | Depends on TICKET-002 |
| TICKET-004 | 🔴 | Migrate All Apps to User Services | 2h | | Depends on TICKET-003 |
| TICKET-005 | 🔴 | Update App Template for User Services | 1h | | Depends on TICKET-004 |
| TICKET-006 | 🔴 | Update Infrastructure Documentation | 1h | | Depends on TICKET-005 |

---

## Phase 2: Port Management & Environment Configuration (3.5 hours)

| Ticket | Status | Title | Est. | Assignee | Notes |
|--------|--------|-------|------|----------|-------|
| TICKET-007 | 🔴 | Add PORT Environment Variable Support to App Template | 0.5h | | Depends on TICKET-005 |
| TICKET-008 | 🔴 | Add PORT Support to Existing Apps | 2h | | Depends on TICKET-007 |
| TICKET-009 | 🔴 | Define Port Allocation Strategy | 1h | | Depends on TICKET-008 |

---

## Phase 3: Deploy Service Development (14 hours)

| Ticket | Status | Title | Est. | Assignee | Notes |
|--------|--------|-------|------|----------|-------|
| TICKET-010 | 🔴 | Create Deploy Service App Structure | 2h | | Depends on TICKET-009 |
| TICKET-011 | 🔴 | Implement Port Allocation Logic | 2h | | Depends on TICKET-010 |
| TICKET-012 | 🔴 | Implement Preview Deploy Endpoint | 4h | | Depends on TICKET-011 |
| TICKET-013 | 🔴 | Implement Preview Cleanup Endpoint | 2h | | Depends on TICKET-012 |
| TICKET-014 | 🔴 | Implement Status Endpoint | 1h | | Depends on TICKET-013 |
| TICKET-015 | 🔴 | Deploy Service Testing & Hardening | 3h | | Depends on TICKET-014 |

---

## Phase 4: GitHub Actions Integration (7 hours)

| Ticket | Status | Title | Est. | Assignee | Notes |
|--------|--------|-------|------|----------|-------|
| TICKET-016 | 🔴 | Create Preview Deploy Workflow Template | 2h | | Depends on TICKET-015 |
| TICKET-017 | 🔴 | Create Production Deploy Workflow Template | 1h | | Depends on TICKET-016 |
| TICKET-018 | 🔴 | Create Cleanup Workflow Template | 1h | | Depends on TICKET-017 |
| TICKET-019 | 🔴 | Add GitHub Workflows to App Template | 1h | | Depends on TICKET-018 |

---

## Phase 5: App Migration & Rollout (8-12 hours)

| Ticket | Status | Title | Est. | Assignee | Notes |
|--------|--------|-------|------|----------|-------|
| TICKET-020 | 🔴 | Add GitHub Workflows to color-the-map (Pilot) | 2h | | Depends on TICKET-019 |
| TICKET-021 | 🔴 | Fix Issues from Pilot (if any) | 2-4h | | Depends on TICKET-020 |
| TICKET-022 | 🔴 | Add Workflows to home-inventory | 1h | | Depends on TICKET-021 |
| TICKET-023 | 🔴 | Add Workflows to Remaining Apps | 3h | | Depends on TICKET-022 |

---

## Phase 6: Documentation & Polish (5-8 hours)

| Ticket | Status | Title | Est. | Assignee | Notes |
|--------|--------|-------|------|----------|-------|
| TICKET-024 | 🔴 | Create Preview Deployment Guide | 2h | | Depends on TICKET-023 |
| TICKET-025 | 🔴 | Update Main Infrastructure Docs | 1h | | Depends on TICKET-024 |
| TICKET-026 | 🔴 | Add Deploy Service Monitoring (Optional) | 3h | | Depends on TICKET-024 |
| TICKET-027 | 🔴 | Add Auto-Cleanup for Stale Previews (Optional) | 2h | | Depends on TICKET-024 |

---

## Progress Summary

**Total Tickets:** 27
**Completed:** 0
**In Progress:** 0
**Not Started:** 27

**Phases:**
- Phase 1: 0/6 complete
- Phase 2: 0/3 complete
- Phase 3: 0/6 complete
- Phase 4: 0/4 complete
- Phase 5: 0/4 complete
- Phase 6: 0/4 complete

**Estimated Completion:** 45-55 hours

---

## Critical Path

```
TICKET-001 (Server Setup)
    ↓
TICKET-002 (Migration Script)
    ↓
TICKET-003 (Migrate doughughes-net)
    ↓
TICKET-004 (Migrate All Apps)
    ↓
TICKET-005 (Update App Template)
    ↓
TICKET-007 (PORT Support in Template)
    ↓
TICKET-008 (PORT Support in Apps)
    ↓
TICKET-009 (Port Allocation Strategy)
    ↓
TICKET-010 (Deploy Service Structure)
    ↓
TICKET-011 (Port Allocation Logic)
    ↓
TICKET-012 (Deploy Endpoint)
    ↓
TICKET-013 (Cleanup Endpoint)
    ↓
TICKET-014 (Status Endpoint)
    ↓
TICKET-015 (Testing & Hardening)
    ↓
TICKET-016 (Preview Workflow)
    ↓
TICKET-017 (Production Workflow)
    ↓
TICKET-018 (Cleanup Workflow)
    ↓
TICKET-019 (Workflows in Template)
    ↓
TICKET-020 (Pilot: color-the-map)
    ↓
TICKET-021 (Fix Pilot Issues)
    ↓
TICKET-022 (home-inventory)
    ↓
TICKET-023 (Remaining Apps)
    ↓
TICKET-024 (Documentation)
```

---

## Parallelization Opportunities

**Can be done in parallel:**
- TICKET-005 and TICKET-006 (after TICKET-004)
- TICKET-022 and TICKET-023 (different apps)
- TICKET-026 and TICKET-027 (optional features)

---

## Notes

- Update this file as tickets are completed
- Mark blockers if dependencies aren't met
- Add implementation notes as we go
- Capture lessons learned for future reference
