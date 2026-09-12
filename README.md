# AI Social Agent

Automated technical-content research, AI analysis, content generation, approval, scheduling, and social publishing system designed for lightweight deployment.

## Current implementation status

Tasks 1–9 are implemented on `main`. Task 10 (final Windows installer/release work) is intentionally the next stage.

### Task 1 — Multi-source Research

- Web Search is a first-class research source.
- GitHub Issues, Reddit, Stack Overflow, and RSS/News remain supported and query-aware.
- Source selection, category/intent filters, time range, research depth, relevance/opportunity/trend scoring, and cross-source deduplication are supported.
- Structured API errors are normalized for safe dashboard rendering.

### Task 2 — Research → Content

- Research results persist into the problems store used by AI analysis.
- Targeted Create Content can analyze an item when needed and then generate a draft.
- Content generation supports both current `ai_intelligence` and legacy `problem_analyses` data.
- Duplicate non-rejected drafts are avoided.

### Task 3 — Incremental AI Analyzer

- Already analyzed research is skipped on subsequent runs.
- Only new/unanalyzed research is sent to the AI provider.
- Existing intelligence and clusters are retained rather than rebuilt on every run.
- New research receives structured category, intent, sentiment, severity, trend, opportunity, and content-gap analysis.
- Near-duplicate research can reuse an existing analysis without another AI call.

### Task 4 — Multi-profile Architecture

- Profiles are persisted in a master `automation_profiles` store.
- Each profile can use an isolated SQLite database under `data/profiles/`.
- Active profile context overlays profile database and AI provider/model settings.
- The default/shared database remains available when no profile is selected.
- The dashboard includes profile switching and profile management.

### Task 5 — Manual vs Automatic Mode

- Each profile supports Manual or Automatic mode.
- Automatic profiles have a persisted daily run time and timezone-aware `next_run`.
- Manual profiles are not worker-due but can be run explicitly with Run now.
- Automation can be enabled/disabled without losing the saved profile pipeline configuration.
- Profile UI exposes mode, enabled state, approval mode, schedule, timezone, and publishing controls.

### Task 6 — Automatic End-to-End Pipeline

Automatic profile execution follows:

`Research → AI Analysis → Content → Approval → Scheduling → Publishing worker`

- Profile categories, resources, query, time range, and research limit drive the research stage.
- Analysis is scoped to the research cycle.
- Content generation is scoped to current research problems and prioritizes opportunity.
- Human approval leaves drafts pending until an explicit decision.
- Auto approval is applied only when the profile is configured for it.
- Scheduling occurs only for approved drafts and only when auto-publish is enabled.
- Actual publishing remains delegated to the existing worker.
- Pipeline stage/run status is persisted for observability.

### Task 7 — Approval System

- Human approval cannot be bypassed.
- Rejection requires a reason.
- Approval/rejection transitions and audit records are atomic.
- Terminal drafts cannot be approved or rejected again through the decision path.
- Direct publishing requires an approved draft.
- Approval history is persisted in SQLite.

### Task 8 — Scheduling & Publishing

- Only approved drafts can be scheduled.
- Schedule times require a future ISO-8601 timestamp and are normalized to UTC.
- Active duplicate schedules for a draft/provider are blocked.
- Scheduled/retrying jobs can be safely rescheduled while preserving provider/media settings.
- Rescheduling clears stale retry errors.
- Cancellation, retries, idempotency, media-aware scheduling, and the existing publisher worker remain supported.
- LinkedIn text, image, document, video, and MultiImage publishing are supported.

### Task 9 — Full Regression & Cross-Environment Testing

- Python 3.11 and 3.12 regression suites run in CI.
- Source compilation is checked before tests.
- Docker build/smoke validation and Compose configuration validation are retained.
- Windows CI validates Python tests, icon generation, installer build, and installer payload.
- Critical runtime modules and workflow files have regression presence guards.

## Dashboard

The dashboard is a compact desktop-first workspace with:

1. Overview
2. Research
3. Content
4. Content Approval
5. Calendar
6. Analytics
7. Integrations
8. Settings

AI providers and social integrations are separated. Provider configuration dynamically supports Gemini, OpenAI, and Hugging Face model discovery where provider credentials are available. Research state, filters, source coverage, ranking, workflow guidance, profile selection, approval, calendar, analytics, and publishing history are integrated into the dashboard.

## AI providers

The provider layer supports Gemini, OpenAI, and Hugging Face through lightweight HTTP REST clients. Provider/model configuration is stored through the system settings and profile configuration layers; credentials remain runtime configuration and are not committed to the repository.

## LinkedIn publishing

The publishing layer supports:

- Text posts
- Single-image posts
- Documents: PDF, DOC, DOCX, PPT, PPTX
- Native video upload lifecycle
- Native MultiImage posts with 2–20 images

Publishing retains approved-only guards, atomic publish claims, audit records, retry classification, and idempotency protection.

## Configuration

Typical runtime settings include:

```text
APP_ENV=development
DATABASE_URL=sqlite:///./data/agent.db
INTERNAL_API_KEY=
GEMINI_API_KEY=
OPENAI_API_KEY=
HUGGINGFACE_API_KEY=
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_AUTHOR_URN=urn:li:person:<id>
LINKEDIN_API_VERSION=202608
PUBLISHING_TIMEOUT_SECONDS=20
LINKEDIN_MEDIA_POLL_ATTEMPTS=10
LINKEDIN_MEDIA_POLL_SECONDS=1
RETRY_BASE_SECONDS=60
RETRY_MAX_SECONDS=3600
WORKER_BATCH_SIZE=10
WORKER_POLL_SECONDS=60
```

Never commit real credentials.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python -m app.cli research
python -m app.cli analyze --limit 25
python -m app.cli generate --limit 10
python -m app.cli queue --limit 25
python -m app.cli approve --draft-id 1
python -m app.cli publish --draft-id 1 --provider linkedin
```

## Production deployment

The supplied Docker Compose deployment runs an API service and a continuous worker service using persistent SQLite and media volumes.

```bash
cp .env.example .env
# Configure production credentials/secrets in .env or your deployment secret store.
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f api
docker compose logs -f worker
```

The API exposes port `8000` and provides `/health` and `/ready`. The worker uses `python -m app.cli worker --loop`, polls according to `WORKER_POLL_SECONDS`, and handles graceful SIGTERM/SIGINT shutdown.

Scheduled media must be accessible to both API and worker containers. The supplied Compose configuration shares `/app/media` between them.

SQLite is intentionally kept for a single application/worker deployment. Horizontal scaling against the same SQLite database is not supported; a future PostgreSQL migration can remove that limitation.

## API surface

```text
GET  /health
GET  /ready
POST /research/run
POST /analysis/run?limit=25
POST /content/generate?limit=10
GET  /approval/queue?status=pending_approval&limit=25
POST /approval/{draft_id}
GET  /approval/{draft_id}/history
POST /publish/{draft_id}?provider=linkedin
POST /publish/{draft_id}/image
POST /publish/{draft_id}/multi-image
POST /publish/{draft_id}/document
POST /publish/{draft_id}/video
POST /schedule/{draft_id}
POST /schedule/{schedule_id}/reschedule
GET  /schedules?status=scheduled&limit=50
DELETE /schedule/{schedule_id}
POST /worker/run?limit=10
GET  /publishing/history?provider=linkedin&limit=50
GET  /publishing/stats
GET  /profiles
POST /profiles
PUT  /profiles/{profile_id}
DELETE /profiles/{profile_id}
POST /profiles/{profile_id}/run
POST /profiles/{profile_id}/enable
POST /profiles/{profile_id}/disable
```

When `INTERNAL_API_KEY` is configured, protected mutation/operational endpoints require the `X-API-Key` header. `/health` remains public.

## Architecture

```text
Configured Profile
       |
       v
Research Sources -> Normalize -> Dedup -> SQLite -> Score
                                               |
                                               v
                                         Incremental AI Analysis
                                               |
                                               v
                                         Content Drafts
                                               |
                                               v
                                         Approval Queue
                                               |
                                  +------------+------------+
                                  |                         |
                             Human Approval           Auto Approval
                                  |                         |
                                  +------------+------------+
                                               |
                                      Approved Draft
                                               |
                                      +--------+--------+
                                      |                 |
                                  Immediate          Schedule
                                      |                 |
                                      +--------+--------+
                                               |
                                            Worker
                                               |
                                          Publisher
                                               |
                                         Social API
                                               |
                                      Attempts / History
```

The project intentionally uses lightweight dependencies and avoids Redis, Elasticsearch, Temporal, and other heavy infrastructure.