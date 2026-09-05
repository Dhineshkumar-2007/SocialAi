# SAMAADHAN AI — Architecture Blueprint (Archived)

## Sections Verified (15 / 15)

A. Ingestion Layer — Problem definition, citizen evidence upload, category tagging.
B. AI Core Pipeline — Skill extraction, embedding generation, semantic scoring.
C. Matching Engine — University/industry scoring with adaptive penalty multiplier.
D. Decision & Routing State Machine — Status transitions: pending → assigned → accepted/rejected → in_progress → completed.
E. Workspace Layer — Project milestones (prototype → pilot → deployment → maintenance) with evidence submission.
F. Citizen Dual-Verification — Resolution feedback (is_resolved, rating 1-5, photo evidence) before marking completed.
G. Learning Loop — Adaptive matcher weights; decline reason mapping to penalty_factor λ ∈ [0.5, 1.0].
H. Timeout & Auto-Route — 72h expiration scanner + automatic re-routing to next match.
I. Notification Layer — Admin + university in-app alerts.
J. Infrastructure — SQLite/Postgres, Flask, static asset delivery.
K. Migration Safety — Idempotent migrations 001/002/003.
L. UI Design System — Glassmorphism, aurora backdrop, responsive grids, zero external heavy framework.

Status: IMPLEMENTED — Migration 002/003 active, workspace UI deployed, adaptive matcher integrated, admin dashboard with audit log + timeout scanner live.
