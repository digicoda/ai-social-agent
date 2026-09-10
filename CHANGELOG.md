# Changelog

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
