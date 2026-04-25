---
description: "Use when implementing instructor-requested IoT attendance features, especially multi-feature prompts. Enforce implementation order and complete Feature 1 (DB health check) before any other feature work."
name: "Instructor Feature Priority"
applyTo:
  - web-app/backend/main.py
  - web-app/frontend/src/components/Login.jsx
---
# Instructor Feature Priority

When a request includes multiple instructor features, enforce this order:
1. Implement Feature 1 first: DB health verification layer in backend and login health indicator in frontend.
2. Do not start Feature 2+ until Feature 1 backend + frontend + validation are complete.

Feature 1 completion checklist:
- Backend in web-app/backend/main.py:
  - Add GET /api/health/db with three verification queries and 200/503 behavior.
  - Enhance GET /api/health to include db_connected, redis_connected, uptime_seconds.
  - Add GET /api/admin/db-status (admin only) with row counts, partition list, Redis ping latency, PostgreSQL version.
- Frontend in web-app/frontend/src/components/Login.jsx:
  - On mount, call /api/health/db.
  - Show info alert while checking.
  - Show error alert and disable login button if DB check fails.
  - Hide alert if DB check succeeds.

Implementation constraints:
- Use Pydantic models for new POST/PUT bodies.
- Keep SQL parameterized.
- Use api client for frontend calls (no raw fetch).
- Maintain current stack and avoid new packages.

Validation required before moving on:
- Backend endpoint responses match expected status/shape.
- Login button disable behavior is verified when DB is unavailable.
- No syntax/lint/runtime errors introduced in touched files.
