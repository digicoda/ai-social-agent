# AI Social Agent

Automated technical-content research and social publishing system designed for lightweight shared hosting.

## Phase 1 — Research Engine

The first implementation collects real technical problems from:

- GitHub Issues
- Reddit
- RSS feeds (default: Hacker News RSS)
- Stack Overflow

Each source is normalized into the same `Problem` model, stored in SQLite, and deduplicated by both source/external ID and normalized title fingerprint.

## Phase 2 — AI Analysis

Phase 2 adds a Gemini-backed analysis layer after research and scoring.

The pipeline is:

```text
Sources -> Normalized Problems -> SQLite -> Deterministic Score -> Gemini Analysis -> Decision
```

Decision thresholds:

- `85–100`: auto-publish candidate
- `70–84`: approval queue
- `<70`: discard

Gemini returns structured analysis containing the pain point, audience, root cause, solution angle, three hooks, risks, and confidence. The API key is loaded from `GEMINI_API_KEY` and sent to Gemini using the `x-goog-api-key` request header; it is never stored in SQLite.

### Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.cli research
python -m app.cli analyze --limit 25
```

### API

```bash
uvicorn app.main:app --reload
```

- `GET /health`
- `POST /research/run`
- `POST /analysis/run?limit=25`

Publishing is intentionally not included in Phase 2 yet. Analysis produces candidates and approval decisions for the publishing phase.

## Architecture

```text
Sources -> Normalized Problems -> SQLite -> Scoring -> AI Analysis -> Content -> Approval -> Publishing
```

The system avoids local LLMs, Redis, Elasticsearch, Temporal, and other heavy infrastructure so it can remain suitable for shared hosting.
