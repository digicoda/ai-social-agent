# AI Social Agent

Automated technical-content research and social publishing system designed for lightweight shared hosting.

## Phases 1–4

The system researches technical problems from GitHub Issues, Reddit, Stack Overflow, and RSS/Hacker News; normalizes and deduplicates them; scores and analyzes them with Gemini; clusters related problems; generates content drafts; puts drafts through human approval; and publishes explicitly approved drafts through provider adapters.

Phase 4 currently supports LinkedIn text publishing through the LinkedIn Posts API. Credentials remain environment-only and publishing attempts are audited in SQLite.

## Phase 5 — Scheduling, retries and publishing operations

Phase 5 turns approved publishing into a controlled automation workflow without removing human approval.

Only `approved` drafts can be scheduled. Publishing attempts are audited, retries are classified, and successful remote IDs are reused for idempotent retries.

## Phase 6 — LinkedIn media publishing

### Images

LinkedIn image publishing initializes an image upload, uploads the binary to the returned URL, waits for the asset to become `AVAILABLE`, and then creates the post with the image URN. The implementation supports JPEG, PNG, and GIF and bounds readiness polling with `LINKEDIN_MEDIA_POLL_ATTEMPTS` and `LINKEDIN_MEDIA_POLL_SECONDS`.

### Documents

Native PDF, DOC, DOCX, PPT, and PPTX publishing uses the same initialize/upload/readiness lifecycle. Documents are posted with the required media title.

### Video

Native LinkedIn video publishing uses the Videos API multipart lifecycle: initialize the upload, upload the provider-specified byte ranges, collect ETags, finalize the upload, wait for readiness, then create the video post. Captions and thumbnails remain deferred.

### Multi-image

Phase 6F adds native organic MultiImage posts. LinkedIn supports **2–20 images** in one MultiImage post, and every image must be owned by the author or organization. The agent uploads each image through the Images API, waits for each asset to become available, then sends the resulting image URNs in `content.multiImage.images`.

MultiImage is exposed through:

```text
POST /publish/{draft_id}/multi-image
```

Example:

```json
{
  "provider": "linkedin",
  "image_paths": [
    "/path/to/slide-1.jpg",
    "/path/to/slide-2.jpg",
    "/path/to/slide-3.jpg"
  ]
}
```

CLI usage accepts `--media-path` multiple times:

```bash
python -m app.cli publish --draft-id 1 --provider linkedin --media-type multi_image \
  --media-path /path/to/slide-1.jpg \
  --media-path /path/to/slide-2.jpg \
  --media-path /path/to/slide-3.jpg
```

The existing atomic publish claim, approval requirement, audit trail, retry classification, and idempotency behavior are retained.

## Configuration

```text
INTERNAL_API_KEY=
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

Phase 6I adds a production container and a two-service Compose deployment: one API container and one continuous scheduling worker. The worker polls due schedules and shares the same persistent SQLite and media volumes as the API. Compose named volumes are used so database/media data survive container recreation. citeturn0search2

Build and start:

```bash
cp .env.example .env
# Set APP_ENV=production, INTERNAL_API_KEY, GEMINI_API_KEY,
# LINKEDIN_ACCESS_TOKEN and LINKEDIN_AUTHOR_URN in .env.
docker compose build
docker compose up -d
```

Check service state and logs:

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f worker
```

The API container exposes port `8000` and has a Docker healthcheck against `/health`. Docker healthchecks provide an explicit container health state independent of the application process state. citeturn0search3

The worker uses:

```bash
python -m app.cli worker --loop
```

and defaults to polling every 60 seconds through `WORKER_POLL_SECONDS`. It handles SIGTERM/SIGINT for graceful shutdown and keeps polling after an isolated worker-cycle exception.

### Persistent media

Scheduled media paths must be accessible to both API and worker containers. Store shared media under the mounted `/app/media` volume when using the supplied Compose deployment. The API and worker both mount the same named media volume.

### Secrets

The repository does not contain real credentials. The Compose deployment reads runtime configuration from `.env`; Docker documents `env_file` as a supported way to provide environment variables to services. For higher-security production environments, use the platform's secret-management facility rather than committing secrets to source control. citeturn0search1

### Deployment limitation

This release intentionally keeps SQLite and a single worker. Do not horizontally scale the API/worker pair against the same SQLite database. A future PostgreSQL migration can remove this deployment constraint if multi-instance scaling becomes necessary.

## API

```text
GET  /health
GET  /ready
POST /research/run
POST /analysis/run?limit=25
POST /content/generate?limit=10
GET  /approval/queue?status=pending_approval&limit=25
POST /approval/{draft_id}
POST /publish/{draft_id}?provider=linkedin
POST /publish/{draft_id}/image
POST /publish/{draft_id}/multi-image
POST /publish/{draft_id}/document
POST /publish/{draft_id}/video
POST /schedule/{draft_id}
GET  /schedules?status=scheduled&limit=50
DELETE /schedule/{schedule_id}
POST /worker/run?limit=10
GET  /publishing/history?provider=linkedin&limit=50
GET  /publishing/stats
```

## Lightweight API protection

Set `INTERNAL_API_KEY` in production. When configured, mutation and operational endpoints require the value in the `X-API-Key` header. `/health` remains public.

## Architecture

```text
Sources -> Normalize -> Dedup -> SQLite -> Score -> AI Analysis -> Clusters
                                                     |
                                                     v
                                               Content Draft
                                                     |
                                                     v
                                                Approval Queue
                                                     |
                                                     v
                                             Approved Draft
                                                     |
                                          +----------+----------+
                                          |                     |
                                      Immediate             Schedule
                                          |                     |
                                          +----------+----------+
                                                     |
                                                   Worker
                                                     |
                                                 Publisher
                                                     |
                                                  Social API
                                                     |
                                          Attempts / History
```

The system remains SQLite-friendly and avoids heavy infrastructure such as Redis, Elasticsearch, or Temporal.
