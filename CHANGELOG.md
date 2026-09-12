# Changelog

## 1.2.3 - 2026-09-12

### Final Windows release

- Completed Tasks 1–10 release packaging.
- Finalized the Windows desktop installer metadata as v1.2.3.
- Retained the branded AI Social Agent icon for installer, Start Menu, desktop, startup, and uninstall shortcuts.
- Added CI SHA-256 checksum generation alongside the installer artifact.
- Added automated v1.2.3 GitHub release publishing from the v1.2.3 release branch.
- Preserved in-place upgrade behavior and persistent ProgramData application data.

## Unreleased — Tasks 1–9

### Research and AI

- Added Web Search as a first-class research source alongside GitHub Issues, Reddit, Stack Overflow, and RSS/News.
- Made multi-source research query-aware with source coverage, ranking, filters, deterministic IDs, and structured error handling.
- Connected research persistence to AI intelligence and content generation.
- Added targeted research-result content generation with legacy `problem_analyses` compatibility.
- Optimized AI analysis to skip already analyzed research and process only new/unanalyzed items while preserving existing intelligence and clusters.

### Dashboard and configuration

- Added the eight-page compact desktop dashboard: Overview, Research, Content, Content Approval, Calendar, Analytics, Integrations, and Settings.
- Separated AI provider configuration from social integrations.
- Added dynamic provider model discovery for Gemini, OpenAI, and Hugging Face where supported by configured credentials.
- Added persistent profile switching and profile-specific configuration UI.

### Profiles and automation

- Added persistent multi-profile architecture with isolated per-profile SQLite databases.
- Added Manual vs Automatic profile modes with daily time/timezone scheduling.
- Added automation enable/disable controls and explicit Run now support.
- Added the automatic Research → AI Analysis → Content → Approval → Scheduling pipeline with persisted run/stage status.
- Preserved human approval and auto-approval as explicit profile modes.

### Approval, scheduling, and publishing

- Added atomic approval/rejection transitions with audit history and required rejection reasons.
- Enforced approved-only direct publishing and scheduling.
- Added safe rescheduling for scheduled/retrying jobs with future UTC normalization.
- Preserved duplicate-schedule protection, cancellation, retries, idempotency, media-aware scheduling, and worker publishing.
- Retained LinkedIn text, image, document, video, and MultiImage publishing.

### Validation

- Added Task 9 full regression validation across Python 3.11 and 3.12.
- Added source compilation checks, Docker/Compose validation, and Windows installer/icon/payload checks to CI.
- Added regression coverage for Tasks 1–9 and critical runtime/workflow presence.

### Security and operations

- Retained production session/authentication hardening, CSRF/origin protection, security headers, safe source URLs, and runtime-only credentials.
- Retained Docker API + worker deployment with persistent database/media storage and graceful worker shutdown.

## 1.0.0 - 2026-09-10

### Added

- Multi-source technical problem research with deterministic deduplication.
- Gemini-powered analysis, scoring, clustering, and content generation.
- Human approval workflow for generated social drafts.
- LinkedIn text, image, document, video, and MultiImage publishing.
- Persistent publishing attempts, idempotency, retry classification, and concurrent publish protection.
- Scheduled publishing with a continuous worker mode and graceful shutdown.
- Persistent media paths for scheduled publishing.
- Production readiness endpoint at `/ready`.
- Docker image and Docker Compose deployment architecture with persistent database/media volumes.
- CI coverage for Python tests, Compose validation, Docker builds, and container health smoke testing.

### Operational notes

- SQLite is supported for a single application/worker deployment. Use a shared production database before horizontal scaling.
- Scheduled media files must be available at the same path inside both the API and worker containers; the Compose setup provides a shared `/app/media` volume.
- Keep publishing credentials in deployment secrets/environment configuration and never commit `.env`.
