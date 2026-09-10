# AI Social Agent

Automated technical-content research and social publishing system designed for lightweight shared hosting.

## Phases 1–3

The project researches technical problems, deduplicates and scores them, analyzes eligible problems with Gemini, clusters related issues, generates educational content, and stores drafts in a human approval queue.

## Phase 4 — Social Publishing

Phase 4 adds a provider-based publishing layer. The first production provider is LinkedIn text-post publishing through the current LinkedIn Posts API. LinkedIn's current API uses the `/rest/posts` endpoint, Bearer authorization, `Linkedin-Version`, and `X-Restli-Protocol-Version: 2.0.0`; successful creation returns the post identifier in `x-restli-id`. citeturn0search0turn0search8

The safety flow is intentionally strict:

```text
pending_approval -> approved -> publish -> published
                         \
                          -> publishing_attempts (success/failure audit)
```

A draft that is not explicitly `approved` cannot be published. Successful and failed attempts are recorded in SQLite, including the provider and remote post ID when available. Publishing credentials are read only from environment variables and are never stored in SQLite.

### LinkedIn configuration

```text
LINKEDIN_ACCESS_TOKEN=
LINKEDIN_AUTHOR_URN=urn:li:person:<id>
# or urn:li:organization:<id>
LINKEDIN_API_VERSION=202603
PUBLISHING_TIMEOUT_SECONDS=20
```

The LinkedIn Posts API supports text-only organic posts for both members and organizations, subject to the permissions of the authenticated account. citeturn0search0

### Run locally

```bash
python -m app.cli research
python -m app.cli analyze --limit 25
python -m app.cli generate --limit 10
python -m app.cli queue --limit 25
python -m app.cli approve --draft-id 1
python -m app.cli publish --draft-id 1 --provider linkedin
```

### API

```text
POST /research/run
POST /analysis/run?limit=25
POST /content/generate?limit=10
GET  /approval/queue?status=pending_approval&limit=25
POST /approval/{draft_id}
POST /publish/{draft_id}?provider=linkedin
```

Publishing is deliberately provider-based so additional networks can be added without changing the research, analysis, content, or approval layers.

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
                                                  Publisher
                                                     |
                                                     v
                                                 Social API
```

The system remains lightweight and SQLite-friendly for shared hosting.
