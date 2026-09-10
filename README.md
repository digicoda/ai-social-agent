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
Sources -> Normalize -> Cross-source dedup -> SQLite -> Deterministic score -> Gemini analysis -> Decision -> Clusters
```

Decision thresholds:

- `85–100`: auto-publish candidate
- `70–84`: approval queue
- `<70`: discard

Gemini returns structured analysis containing the pain point, audience, root cause, solution angle, three hooks, risks, and confidence. The API key is loaded from `GEMINI_API_KEY` and sent to Gemini using the `x-goog-api-key` request header; it is never stored in SQLite.

### Cross-source deduplication

Phase 1's exact fingerprint remains the database safety net. Phase 2 adds deterministic fuzzy matching across different sources using normalized technical tokens and title/body Jaccard similarity. This catches the same underlying issue when GitHub, Reddit, Stack Overflow, or RSS describe it with slightly different wording.

### Problem clustering

Phase 2 also groups related problems into SQLite-backed clusters. Clustering is deterministic and local, so it does not require embeddings or an additional AI request. The highest-scoring problem becomes the cluster representative, and related problems are assigned to it using a similarity threshold.

## Phase 3 — Content Generation & Approval

Phase 3 turns eligible analyzed problems into reviewable content drafts. Gemini generates a platform-neutral educational draft with a title, body, hashtags, call-to-action, and generation confidence. Discarded problems are never generated, and existing non-rejected drafts are not duplicated on repeat runs.

Drafts are stored in SQLite with an explicit lifecycle:

```text
pending_approval -> approved
                  -> rejected
```

Rejections require a reason so a future regeneration/editing workflow can use that feedback. Publishing is still intentionally disabled in Phase 3: an approved draft is only an approved artifact and is not sent to any social network.

### Run locally

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
python -m app.cli reject --draft-id 2 --reason "Needs a clearer example"
```

### API

```bash
uvicorn app.main:app --reload
```

- `GET /health`
- `POST /research/run`
- `POST /analysis/run?limit=25`
- `POST /content/generate?limit=10`
- `GET /approval/queue?status=pending_approval&limit=25`
- `POST /approval/{draft_id}` with `{"action":"approved"}` or `{"action":"rejected","reason":"..."}`

## Architecture

```text
Sources -> Normalized Problems -> Deduplication -> SQLite -> Scoring -> AI Analysis -> Clustering -> Content -> Approval -> Publishing
```

The system avoids local LLMs, Redis, Elasticsearch, Temporal, and other heavy infrastructure so it can remain suitable for shared hosting.
