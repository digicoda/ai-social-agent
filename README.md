# AI Social Agent

Automated technical-content research and social publishing system designed for lightweight shared hosting.

## Phases 1–4

The system researches technical problems from GitHub Issues, Reddit, Stack Overflow, and RSS/Hacker News; normalizes and deduplicates them; scores and analyzes them with Gemini; clusters related problems; generates content drafts; puts drafts through human approval; and publishes explicitly approved drafts through provider adapters.

Phase 4 currently supports LinkedIn text publishing through the LinkedIn Posts API. Credentials remain environment-only and publishing attempts are audited in SQLite.

## Phase 5 — Scheduling, retries and publishing operations

Phase 5 turns approved publishing into a controlled automation workflow without removing human approval.

```text
Research -> Analyze -> Generate -> Human Approval
                                      |
                                   Approved
                                      |
                              Schedule / Publish
                                      |
                              Worker -> Publisher
                                      |
                       +--------------+--------------+
                       |                             |
                    Success                       Failure
                       |                             |
                  Published                  Exponential Retry
                       |                             |
                       +-------- History / Stats ---+
```

### Scheduling

Only `approved` drafts can be scheduled. Each schedule stores the provider, UTC execution time, attempt limit, current state, and last error.

Supported schedule states:

- `scheduled`
- `running`
- `retrying`
- `published`
- `failed`
- `cancelled`

The worker is intentionally cron-friendly. A shared-hosting cron job can call `python -m app.cli worker` every minute, or an external scheduler can call `POST /worker/run`.

### Retry handling

Failed publishing attempts are retried with exponential backoff. Defaults are 60 seconds, then 120, 240, and so on, capped at 1 hour. Each schedule has a maximum attempt count, defaulting to 3.

### Idempotency

If a provider already has a successful publishing attempt for the same draft, a later publish or worker retry returns the stored remote ID instead of creating another post. This protects against the common case where the remote API succeeds but the local status update is interrupted.

### Publishing history and stats

Phase 5 exposes publishing attempts and aggregate operational statistics through both the API and CLI.

### Lightweight API protection

Set `INTERNAL_API_KEY` in production. When configured, all mutation and operational endpoints require the same value in the `X-API-Key` header. `/health` remains public. Development keeps the key optional for local use.

## Configuration

```text
INTERNAL_API_KEY=
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_AUTHOR_URN=urn:li:person:<id>
LINKEDIN_API_VERSION=202608
PUBLISHING_TIMEOUT_SECONDS=20
RETRY_BASE_SECONDS=60
RETRY_MAX_SECONDS=3600
WORKER_BATCH_SIZE=10
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

Schedule an approved draft:

```bash
python -m app.cli schedule --draft-id 1 --provider linkedin --scheduled-for 2026-09-11T10:00:00+00:00 --max-attempts 3
python -m app.cli worker --limit 10
python -m app.cli history --provider linkedin
python -m app.cli stats
```

## API

```text
GET  /health
POST /research/run
POST /analysis/run?limit=25
POST /content/generate?limit=10
GET  /approval/queue?status=pending_approval&limit=25
POST /approval/{draft_id}
POST /publish/{draft_id}?provider=linkedin
POST /schedule/{draft_id}
GET  /schedules?status=scheduled&limit=50
DELETE /schedule/{schedule_id}
POST /worker/run?limit=10
GET  /publishing/history?provider=linkedin&limit=50
GET  /publishing/stats
```

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
