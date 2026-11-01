# Contributing

Thank you for considering a contribution to AI Social Agent.

The project is building a dependable workflow for research, AI analysis, content generation, human approval, scheduling, and social publishing. Contributions should strengthen that direction rather than turn the project into a collection of unrelated automation features.

## Before you start

1. Read the [README](README.md) and [Roadmap](ROADMAP.md).
2. Search existing issues and pull requests to avoid duplicate work.
3. For substantial changes, open an issue first and describe the problem and proposed approach.
4. Do not submit credentials, access tokens, personal data, generated database files, or private account information.

## Good first contribution areas

- Research source reliability, relevance, ranking, and deduplication.
- Search filters, source status, partial failures, and empty-state behavior.
- Research-to-analysis and research-to-content integration.
- AI provider error handling, timeouts, and response validation.
- Content quality evaluation and platform-specific formatting.
- Automated tests, documentation, accessibility, and deployment hardening.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Add only the provider credentials needed for the feature you are testing. Never commit your local `.env` file or real credentials.

## Before submitting

Run the relevant checks:

```bash
python -m compileall -q app
python -m pytest -q
```

For Docker, deployment, or workflow changes, also validate the relevant Compose configuration and CI workflow.

For research or generation changes, include tests for realistic success and failure cases where possible. Consider empty results, duplicate results, malformed provider responses, rate limits, timeouts, missing credentials, and partial source failures.

## Pull request guidelines

- Use a focused branch and keep the change as small as practical.
- Explain the problem, root cause, and solution.
- Link the related issue.
- Include tests and update documentation when behavior changes.
- Include screenshots for meaningful dashboard/UI changes.
- Call out migrations, configuration changes, API contract changes, and operational risks.
- Do not claim a feature is production-ready solely because unit tests pass.

A maintainer may request changes, additional tests, or a narrower scope before merging.

## Commit and code style

Follow the conventions already used in the affected part of the codebase. Prefer readable, typed, testable code and explicit error handling. Avoid adding heavy dependencies without explaining why they are necessary.

## Scope and product direction

The long-term direction remains an end-to-end AI social content operations workflow:

`Research → Analysis → Content → Human Approval → Scheduling → Publishing → History`

New features should support this workflow, improve its quality/reliability, or provide a clear foundation for future scale and enterprise readiness.
