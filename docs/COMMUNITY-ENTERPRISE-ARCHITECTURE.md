# Community and Enterprise Architecture Plan

This document defines the intended technical boundary between the free Community Edition and a future paid Enterprise Edition. It is an architecture plan, not a statement that these capabilities are already implemented.

## 1. Product boundary

- **Community Core:** the public, Apache-2.0 project. It owns the core research, analysis, content, approval, scheduling, publishing abstractions, baseline integrations, and generally useful reliability fixes.
- **Enterprise Add-ons:** separately maintained commercial modules and services. They may add advanced identity, administration, compliance, deployment, and operational capabilities through documented extension points.
- **Shared interfaces:** stable contracts for providers, storage, authentication/authorization, workflow policies, audit events, and background jobs.

Do not create a second full application fork. Enterprise should consume versioned Community Core releases and add capabilities through supported interfaces.

## 2. Architecture principles

1. **Keep the current working application intact first.** Do not undertake a large package split or database rewrite solely to prepare for future editions.
2. **Extract boundaries incrementally.** Create interfaces only when a real feature needs a stable seam and tests can protect it.
3. **Core remains useful alone.** Community must build, install, run, and test without any private Enterprise package.
4. **No hidden runtime dependency.** The public app must not require a private package, private registry, license server, or Enterprise secret to start.
5. **Fail clearly.** If an optional Enterprise capability is unavailable, the Community app should continue to work and explain that the capability is not installed or enabled.
6. **Security belongs in the Core.** Secure defaults, input validation, secret handling, safe publishing, audit primitives, and vulnerability fixes must not be paywalled.
7. **Human approval remains a first-class safety boundary** for content publishing unless a user explicitly configures an automation policy.

## 3. Suggested logical modules

These are target boundaries, not instructions to create all directories immediately.

| Module | Community responsibility | Possible Enterprise extension |
|---|---|---|
| Research | Source adapters, normalization, provenance, deduplication, ranking | Managed source connectors, organization-wide research policies |
| AI providers | Provider interface, baseline provider adapters, safe configuration | Centralized provider governance, policy controls, managed routing |
| Content | Draft model, generation pipeline, platform-aware validation | Brand governance, approval policies, reusable organization templates |
| Workflow | Profiles, approval, scheduling, publishing contracts | Multi-team workflows, delegated approvals, advanced automation policies |
| Identity | Secure local/admin authentication foundation | SSO/SAML/OIDC, SCIM, advanced RBAC and workspace administration |
| Persistence | Current SQLite single-instance support and migrations as adopted | PostgreSQL HA deployment, managed backups, tenant-aware operations |
| Jobs | Reliable worker contract, retries, idempotency | Distributed queues, concurrency quotas, workload controls |
| Audit/operations | Core event and diagnostic hooks | Advanced audit export, retention controls, metrics, tracing, SIEM integrations |

## 4. Extension contract design

When extracting a boundary, define and test:
- A typed interface and versioned contract.
- Input/output schemas and validation rules.
- Error categories, timeout behavior, and retryability.
- Capability discovery and configuration validation.
- A Community implementation or safe default.
- Contract tests that Enterprise implementations must also pass.

Avoid importing private Enterprise modules from core modules. Enterprise modules should depend on public interfaces, not patch private behavior into core internals.

## 5. Data and tenant strategy

The current documented deployment is a single application/worker using SQLite. Do not claim horizontal scaling or multi-tenant isolation today.

Before enterprise multi-tenancy:
- Define workspace/tenant ownership for every customer-owned record.
- Enforce tenant scope in service/data-access boundaries, not only in UI filters.
- Add authorization tests proving cross-tenant reads and writes are denied.
- Design database migrations and backup/restore before switching production storage.
- Evaluate PostgreSQL and a migration tool against the existing data model; do not choose a migration strategy without inspecting current persistence code.
- Define encryption, secret storage, retention, deletion, and export policies.
- Keep customer credentials and content out of logs and telemetry.

A PostgreSQL migration alone does not make an application enterprise-ready. Isolation, authorization, concurrency, recovery, and operations all need evidence.

## 6. Enterprise readiness sequence

### Phase A — Core quality (current priority)
- Research relevance, source coverage, provenance, ranking, and deduplication.
- Reliable research-to-analysis-to-content context hand-off.
- Provider timeouts, malformed response handling, retries, and useful errors.
- End-to-end tests for research through approved draft.
- Publishing safety, idempotency, and audit regression tests.

### Phase B — Modular contracts
- Identify high-change boundaries from actual code.
- Extract provider, storage, job, and workflow contracts one at a time.
- Add contract tests before allowing optional implementations.
- Keep Community install and tests independent of Enterprise.

### Phase C — Secure multi-user foundation
- Authentication and authorization model.
- Workspace boundaries and tenant-scoped data access.
- RBAC, audit events, secure session and secret management.
- Cross-tenant security tests and threat review.

### Phase D — Production operations
- PostgreSQL and tested migration/rollback.
- Reliable distributed job execution and concurrency control.
- Structured logs, metrics, tracing, alerting.
- Backup/restore, retention, disaster recovery, rate limits, and deployment runbooks.
- Load, failure, and recovery tests.

### Phase E — Commercial Enterprise modules
Only after the public interfaces and operational foundations are stable:
- SSO/SCIM and advanced identity integrations.
- Advanced workspace administration and policy controls.
- Compliance/audit exports and retention management.
- Enterprise deployment automation, support, and service options.
- Additional proprietary modules that do not weaken Community security or basic usability.

## 7. Release and compatibility model

- Publish Community releases from the public repository using version tags and release notes.
- Version extension contracts and document breaking changes.
- Test each Enterprise release against a declared range of Community Core versions.
- Maintain a compatibility matrix and migration notes.
- Keep proprietary Enterprise source, build credentials, customer configurations, and private deployment assets outside the public repository.
- Continue upstreaming generally useful fixes to Community where the project owner has the rights to do so.

## 8. Legal and contribution boundary

See [Licensing and Community / Enterprise Model](LICENSING.md). Apache-2.0 allows downstream private modifications; it does not require users to submit them upstream. The draft CLA is not active. Do not rely on it for commercial relicensing until it has been finalized, signed through a verified process, and checked against the project's existing contribution history.

A customer obligation to provide modifications or assign rights must be negotiated in a separate commercial agreement. An open-source license cannot create that private contractual obligation by itself.
