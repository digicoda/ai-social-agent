# AI Social Agent

Automated technical-content research and social publishing system designed for lightweight shared hosting.

## Phase 1 — Research Engine

The first implementation collects real technical problems from:

- GitHub Issues
- Reddit
- RSS feeds (default: Hacker News RSS)
- Stack Overflow

Each source is normalized into the same `Problem` model, stored in SQLite, and deduplicated by both source/external ID and normalized title fingerprint.

### Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.cli research
```

### API

```bash
uvicorn app.main:app --reload
```

- `GET /health`
- `POST /research/run`

### Quality pipeline

Research results are intentionally separated from publishing. The current scoring layer provides a deterministic technical-relevance score; AI analysis and platform-specific generation will be added in the next phases.

## Architecture

```text
Sources -> Normalized Problems -> SQLite -> Scoring -> AI Analysis -> Content -> Approval -> Publishing
```

The system avoids local LLMs, Redis, Elasticsearch, Temporal, and other heavy infrastructure so it can remain suitable for shared hosting.
