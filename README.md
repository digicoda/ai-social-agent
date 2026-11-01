# AI Social Agent

**Research → Insight → Content → Approval → Schedule → Publish**

AI Social Agent is an open-source project in active development that aims to turn useful signals from the web into researched, platform-ready social content—with configurable AI providers, human review, automation profiles, and controlled publishing.

The goal is not just another AI caption generator. The long-term direction is a dependable, extensible social-content operations platform: discover relevant topics, understand why they matter, create useful content grounded in research, keep people in control, and publish through a traceable workflow.

> **Project status: Active development / not yet enterprise-ready.** The core workflow and integrations exist, but research relevance/coverage and research-to-content generation still need quality, reliability, and end-to-end validation. Do not treat the current build as a production guarantee.

[Repository](https://github.com/digicoda/ai-social-agent) · [Report a bug](https://github.com/digicoda/ai-social-agent/issues/new?template=bug_report.md) · [Request a feature](https://github.com/digicoda/ai-social-agent/issues/new?template=feature_request.md) · [Contributing](CONTRIBUTING.md) · [Roadmap](ROADMAP.md) · [Licensing](docs/LICENSING.md) · [Community / Enterprise Architecture](docs/COMMUNITY-ENTERPRISE-ARCHITECTURE.md)

---

## Why this project exists

Teams and independent creators need more than high-volume generated posts. They need a repeatable process to:

1. Find relevant conversations, questions, problems, trends, and opportunities.
2. Separate useful signals from noise, duplicates, and low-quality results.
3. Analyze findings and understand the audience/context.
4. Turn selected research into useful drafts for the right platform.
5. Review, edit, approve, reject, and audit content.
6. Schedule and publish approved content.
7. Learn from workflow and publishing history, then improve the process.

That end-to-end workflow remains the project's central idea and product direction.

## Current status

The repository contains working foundations for the following areas. Feature presence in code and automated tests does **not** mean every source, provider, environment, or end-to-end user path has been fully validated.

| Area | Current position |
|---|---|
| Multi-source research | Implemented foundation; relevance, source coverage, ranking, consistency, and result quality need further improvement and validation |
| Research-to-content | Integration exists; reliability, context hand-off, output quality, and failure handling are active improvement priorities |
| AI analysis | Incremental analysis and structured classification are implemented; quality depends on input data and provider responses |
| AI providers | Gemini, OpenAI, and Hugging Face provider support exists in the provider layer; validate each provider/model with real credentials |
| Profiles and automation | Persistent profiles, manual/automatic modes, and pipeline execution are implemented |
| Approval | Human approval, rejection reasons, and approval history are implemented |
| Scheduling and publishing | Worker-based scheduling and LinkedIn publishing paths are implemented; provider/API changes and real-account behavior require validation |
| Deployment | Docker Compose and Windows packaging workflows exist; deployment hardening and operational validation remain part of the roadmap |
| Enterprise readiness | Not yet complete; see [Roadmap](ROADMAP.md) |

### Known improvement priorities

- Improve research relevance, precision, recall, source diversity, deduplication, ranking, and explainability.
- Make search behavior predictable: clear filters, source status, useful empty states, partial-failure reporting, and actionable errors.
- Make research-to-content generation dependable: preserve source context, handle missing/weak analysis, prevent unsupported claims, and explain provider failures.
- Improve generated content quality, platform-specific formatting, repeatability, and user control.
- Expand automated tests from component-level coverage to realistic end-to-end scenarios.
- Strengthen observability, security, deployment, and data-management capabilities before describing the product as enterprise-ready.

See [ROADMAP.md](ROADMAP.md) for the staged plan.

## Core workflow

```text
Profile / User Request
        |
        v
Research Sources
        |
        v
Normalize → Deduplicate → Filter → Rank
        |
        v
Persist Research
        |
        v
AI Analysis / Insights
        |
        v
Generate Platform-aware Drafts
        |
        v
Human Review & Approval
        |
        v
Schedule
        |
        v
Publishing Worker
        |
        v
Publishing History / Audit
```

Human approval is intended to remain a first-class control. Automatic approval is an explicit profile configuration, not an assumption that every generated draft should be published.

## Current capabilities

### Research

The research layer includes integrations for web search, GitHub Issues, Reddit, Stack Overflow, and RSS/news sources. The implementation includes source selection, query-aware collection, filters, normalization, deduplication, scoring, and structured error handling.

**Important:** the existence of these integrations does not mean every query returns comprehensive or high-quality results. Improving research quality and reliability is a current priority.

### AI analysis and content

Research can be persisted and passed into the analysis and content workflows. The application includes incremental analysis behavior and targeted content-generation paths, with compatibility for existing analysis data.

The intended output is useful, evidence-aware content—not generic text detached from the research. Better context handling, generation consistency, quality evaluation, and transparent failure states are active development priorities.

### Profiles and automation

- Multiple persisted automation profiles.
- Profile-specific configuration and data isolation using SQLite databases.
- Manual execution and configured automatic runs.
- Timezone-aware schedules and explicit Run now behavior.
- Pipeline status persistence.

### Review, scheduling, and publishing

- Draft approval and rejection with a reason.
- Approval history and audit records.
- Approved-only scheduling and publishing guards.
- Worker-based execution, retry handling, and idempotency protections.
- LinkedIn publishing paths for text, images, documents, video, and multi-image posts.

Publishing integrations depend on valid provider credentials, API permissions, and current third-party platform requirements. Test with a controlled account before enabling automation.

### Dashboard

The dashboard currently includes:

1. Overview
2. Research
3. Content
4. Content Approval
5. Calendar
6. Analytics
7. Integrations
8. Settings

## Technology and architecture

The current implementation is Python-based and uses a lightweight application architecture with SQLite persistence, an API/dashboard, background worker execution, and Docker deployment support.

The project intentionally avoids requiring a large infrastructure stack for the initial deployment. SQLite is currently intended for a single application/worker deployment; horizontal scaling against the same SQLite database is not supported. A production-grade shared database and related migration work are future architecture priorities.

## AI providers and configuration

The provider layer includes support for Gemini, OpenAI, and Hugging Face. Actual model availability and behavior depend on provider credentials, selected models, API access, and provider-side changes.

Start with the example environment file:

```bash
cp .env.example .env
```

Configure only the credentials required for the providers and integrations you intend to test. Never commit real API keys, access tokens, passwords, session secrets, or production configuration.

Common settings include:

- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `HUGGINGFACE_API_KEY`
- `LINKEDIN_ACCESS_TOKEN`
- `LINKEDIN_AUTHOR_URN`
- `INTERNAL_API_KEY`
- `ADMIN_PASSWORD`
- `SESSION_SECRET`

Refer to [`.env.example`](.env.example) for the current variable list. Keep secrets in environment variables or a deployment secret manager.

## Run locally

The following is the current CLI-oriented development path. Exact setup requirements may evolve as the project is improved.

```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
```

Run the available workflow commands:

```bash
python -m app.cli research
python -m app.cli analyze --limit 25
python -m app.cli generate --limit 10
python -m app.cli queue --limit 25
```

Approval and publishing commands can affect connected social accounts. Review the configuration and draft before running them:

```bash
python -m app.cli approve --draft-id 1
python -m app.cli publish --draft-id 1 --provider linkedin
```

Do not run publishing commands against a real account until credentials, permissions, approval behavior, and the target content have been checked.

## Docker deployment

A Docker Compose configuration is provided for the API and worker:

```bash
cp .env.example .env
# Add deployment credentials to .env or your secret manager.
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f api
docker compose logs -f worker
```

The API uses port `8000` and exposes `/health` and `/ready`. The worker runs separately and shares persistent application data and media storage with the API through the supplied Compose configuration.

Before production use, review authentication, secret management, backups, storage permissions, logging, monitoring, network exposure, and recovery procedures. The current SQLite deployment is for a single application/worker deployment, not horizontal scaling.

## API overview

The current API includes endpoints for:

- Health and readiness
- Research and AI analysis
- Content generation
- Approval queue and approval history
- Publishing and media publishing
- Scheduling, rescheduling, and cancellation
- Publishing history and statistics
- Automation profile management and execution

When `INTERNAL_API_KEY` is configured, protected mutation/operational endpoints require the `X-API-Key` header. Check the current application routes and configuration before integrating against the API; endpoint contracts may evolve during active development.

## Testing

The repository includes automated tests and GitHub Actions workflows for Python validation, Docker/Compose checks, and Windows packaging. Run the test suite locally before submitting changes:

```bash
python -m compileall -q app
python -m pytest -q
```

A passing test suite is necessary but not sufficient for production readiness. Research and generation changes should also be checked against representative real-world queries, provider failures, empty/partial source responses, and complete research-to-draft workflows.

## Contributing

Contributions are welcome, especially around research quality, generation reliability, testing, documentation, and operational hardening.

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. For larger changes, open an issue first so the approach can be discussed before implementation.

## Security

Please do not publish credentials, tokens, private data, or exploitable security details in public issues. See [SECURITY.md](SECURITY.md) for responsible reporting guidance.

## License

The Community Edition is released under the **Apache License 2.0**. See the root [LICENSE](LICENSE) file for the complete terms.

The project is preparing an open-core model: a free Community Edition and a future paid Enterprise Edition built around separately maintained enterprise modules and services. Apache-2.0 does not require downstream users to publish private modifications or contribute them back.

A Contributor License Agreement is still a legal-review draft and is **not active**. Do not treat [the CLA draft](docs/legal/CLA-DRAFT.md) as an agreement to sign. See [Licensing and Community / Enterprise Model](docs/LICENSING.md) for the intended model, limits, and release checklist.

## Project direction

The product vision is unchanged: build a dependable AI-assisted social content workflow that connects research, analysis, content creation, human control, automation, scheduling, and publishing.

The immediate focus is to make research and content generation trustworthy and testable. Enterprise capabilities—such as stronger multi-user access controls, scalable persistence, deeper observability, operational resilience, and broader integration coverage—should be delivered in deliberate stages rather than claimed prematurely.
