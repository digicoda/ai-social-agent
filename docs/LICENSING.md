# Licensing and Community / Enterprise Model

## Current community license

The Community Edition in this repository is licensed under the standard **Apache License 2.0**. The root `LICENSE` file is the authoritative license text.

Apache-2.0 permits commercial use, modification, redistribution, and closed-source combinations, subject to its conditions. It includes an express, limited patent license from each contributor. It does **not** require downstream users to publish or send their modifications back to this repository.

## Intended product editions

The intended long-term product model is an open-core model:

| Edition | Intended model | Scope |
|---|---|---|
| Community | Free, public, Apache-2.0 | Shared core workflow, community integrations, baseline research, analysis, content generation, approval, scheduling, and publishing capabilities |
| Enterprise | Paid commercial offering | Separately developed enterprise modules, commercial services, deployment/support options, and advanced capabilities |

The exact feature boundary is a product decision and must be documented before Enterprise is sold. Do not remove existing Apache-2.0 rights from already released Community code.

## Recommended architecture

1. Keep the public repository as the Community Core and the canonical place for generally useful fixes.
2. Design stable, documented extension points for authentication, storage, workflow policies, integrations, observability, and administration.
3. Keep proprietary Enterprise modules in a separate private repository/package until the product boundary and build integration are proven.
4. Avoid maintaining a permanent full fork. Enterprise should depend on a versioned Community Core and add modules through supported interfaces.
5. Prefer security, reliability, performance, and generally useful bug fixes in the public Community Core.
6. Do not put secrets, customer data, private deployment configuration, or proprietary Enterprise source in the public repository.

The current application is not yet enterprise-ready. Implement and test multi-user identity, authorization, tenant isolation, production database support, background-job reliability, auditability, observability, backup/restore, and operational controls before making enterprise-readiness claims.

## Contributor rights and future commercial licensing

A Contributor License Agreement (CLA) is being prepared as a **draft only** in [CLA-DRAFT.md](legal/CLA-DRAFT.md). It is intended to let contributors retain ownership while granting the project owner the rights needed to use contributions in the Apache-2.0 community project and, where the signed agreement expressly permits, in separately licensed commercial offerings.

The draft is not active and must not be treated as a signed or legally approved agreement. Before requiring it or relying on it for commercial relicensing:

- Replace all placeholders with the correct legal project-owner identity and contact details.
- Obtain review by qualified intellectual-property counsel in the relevant jurisdictions.
- Choose and configure a transparent electronic signing / CLA verification process.
- Publish the final agreement and explain the scope before accepting a contributor's agreement.
- Keep a durable record of each accepted agreement and the GitHub identity / contribution it covers.
- Check whether a contributor's employer owns or controls the contribution; obtain the correct corporate authorization where needed.

A CLA does not automatically transfer copyright ownership. This project intends to use a non-exclusive license grant, not a blanket copyright assignment. A contributor must have the authority to grant the rights described in the final agreement.

## Important limits

- Apache-2.0 does not force a company to upstream its private changes, even when it uses the software commercially or as a hosted service.
- A CLA only grants rights over contributions that are actually submitted and covered by the signed agreement. It does not grant rights over unrelated private modifications a company never submits.
- A CLA signed for future contributions does not automatically cover earlier contributions. Existing code, prior contributors, open pull requests, copied snippets, assets, and dependencies require a provenance and license review before any dual-licensing claim is made.
- Code already released under Apache-2.0 remains available under that license. A later commercial offering cannot revoke those existing permissions.
- Third-party dependencies and assets remain subject to their own licenses. The project must preserve required notices and comply with all dependency terms.
- Do not promise customers that their private modifications will be returned. If a commercial customer must provide changes, negotiate that obligation in a separate customer contract or services agreement.

## Release checklist

Before announcing the Community Edition as Apache-2.0:

- [ ] Confirm the project owner has authority to license all code currently in the repository.
- [ ] Review existing contributors, merged pull requests, open pull requests, copied code, generated assets, and third-party files for provenance and license compatibility.
- [ ] Review Python dependencies and any bundled frontend, icon, font, image, model, or other assets.
- [ ] Confirm the copyright holder name for source-file notices, if notices are added.
- [ ] Merge the Apache-2.0 license change and update release/package metadata where applicable.
- [ ] Publish the final contribution policy and security contact.

Before enabling commercial relicensing of community contributions:

- [ ] Finalize and legally review the CLA.
- [ ] Configure and test CLA acceptance / verification.
- [ ] Require the final CLA only for contributions submitted after the policy is clearly announced.
- [ ] Track accepted contributions and their authors.
- [ ] Obtain separate permission for any earlier contribution not covered by the final agreement.
