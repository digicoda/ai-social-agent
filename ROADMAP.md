# Product Roadmap

This roadmap records the intended direction of AI Social Agent. It is a planning document, not a promise that every item is scheduled or already implemented.

## Product vision — unchanged

Build a dependable AI-assisted social content operations platform that connects:

`Research → Insight → Content → Human Review → Scheduling → Publishing → Learning`

The objective is to help creators and teams discover meaningful topics, understand them, create useful platform-aware content, retain control over publishing, and improve through traceable workflows.

The project is not intended to become only a generic chatbot, caption generator, or disconnected collection of social-media scripts.

## Current foundation

The repository already contains implementation for multi-source research, AI analysis, content generation paths, profiles, manual/automatic automation, approval, scheduling, LinkedIn publishing, dashboard pages, Docker deployment, and Windows packaging.

These foundations are not equivalent to enterprise readiness. The owner has identified research result quality and the research-to-content generation experience as areas that still need improvement. The roadmap prioritizes validating and strengthening these core user journeys before expanding the product surface.

## Stage 1 — Research quality and reliability

**Priority: Immediate**

- Establish representative research-query test cases and expected relevance criteria.
- Improve source coverage, query interpretation, and source-specific collection behavior.
- Improve relevance ranking, deduplication, freshness, and result diversity.
- Make filters and ranking behavior consistent and understandable.
- Show source-level success, empty results, partial failures, and actionable errors.
- Preserve useful provenance: source, URL, timestamp, and supporting context.
- Add regression tests for real-world query patterns and source/provider failures.

**Exit criteria:** repeatable evaluation demonstrates that representative queries return relevant, traceable, non-duplicated results and that partial failures are visible rather than silently hidden.

## Stage 2 — Research-to-content quality

**Priority: Immediate**

- Make selected research reliably available to analysis and generation.
- Preserve source context and provenance throughout the workflow.
- Handle missing, stale, weak, or conflicting analysis explicitly.
- Improve prompts and output structure for platform-specific content.
- Validate provider responses and handle rate limits, timeouts, malformed output, and missing credentials.
- Prevent unsupported factual claims and make source grounding reviewable.
- Improve draft regeneration, editing, and failure recovery.
- Add end-to-end tests from a selected research result to a saved draft.

**Exit criteria:** a user can select a research item, understand the context used, generate a useful draft, recover from common failures, and review the resulting content before approval.

## Stage 3 — Product usability and workflow consistency

- Improve onboarding and first-run configuration.
- Make dashboard states, loading, errors, empty results, and progress clear.
- Improve research-to-content navigation and reduce unnecessary steps.
- Strengthen profile configuration and explain automation behavior.
- Improve content editing, approval queue, calendar, and publishing history.
- Add user-facing diagnostics without exposing secrets.

**Exit criteria:** a new user can configure a provider, run research, generate and review content, and understand each workflow stage without relying on developer intervention.

## Stage 4 — Enterprise foundations

These capabilities should be designed and validated before the project is marketed as enterprise-ready.

- Multi-user identity, roles, permissions, and workspace boundaries.
- Strong tenant/profile isolation and secure secret handling.
- PostgreSQL or another production-grade shared persistence option and migration strategy.
- Background job reliability, concurrency controls, and scalable worker architecture.
- Auditability across configuration, research, content decisions, and publishing.
- Structured logs, metrics, tracing, health checks, and operational alerts.
- Backup, restore, retention, and disaster-recovery procedures.
- Rate limiting, abuse protection, secure defaults, and dependency/security scanning.
- Documented deployment, upgrade, rollback, and incident procedures.

**Exit criteria:** architecture, security review, operational runbooks, and load/recovery tests support the intended deployment scale. No enterprise claim should be made before evidence exists.

## Stage 5 — Integration and intelligence expansion

- Improve and expand social platform integrations behind stable provider interfaces.
- Add platform-specific content constraints and validation.
- Improve analytics and feedback loops to inform future research and content.
- Add configurable workflows while retaining clear approval and publishing safeguards.
- Evaluate additional research sources based on user value, reliability, and maintenance cost.

## Stage 6 — Distribution and release maturity

- Publish the Community Edition under Apache License 2.0 after code and dependency provenance review.
- Finalize a transparent CLA and verification workflow before relying on commercial relicensing of external contributions.
- Keep Community Core public and build a future paid Enterprise Edition through separately maintained modules and services.
- Version public extension contracts and publish Community / Enterprise compatibility information.
- Improve installation, upgrades, and configuration validation.
- Publish versioned release notes and compatibility information.
- Add reproducible release checks and artifact integrity verification.
- Improve documentation, examples, and support guidance.
- Define a clear license and contribution governance model.
## Guiding principles

1. **Quality before volume:** relevant research and useful content matter more than producing many results.
2. **Evidence and provenance:** users should be able to understand where research and claims came from.
3. **Human control:** approval remains explicit and publishing safeguards must not be bypassed.
4. **Reliability over demos:** handle empty, partial, delayed, and failed provider responses.
5. **Small operational footprint:** avoid infrastructure complexity until scale justifies it.
6. **Enterprise through evidence:** security, scalability, resilience, and auditability must be implemented and tested—not merely described.
